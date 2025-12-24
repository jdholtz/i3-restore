from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import psutil

import constants
import utils

if TYPE_CHECKING:
    from .. import JSON, Container


logger = utils.get_logger()

KITTY_LAUNCH_PREFIX = "launch "
KITTY_UNSERIALIZE_DATA_KEY = "kitty-unserialize-data="

USE_OLD_SESSION_SAVING = None
KITTY_NEW_SESSION_VERSION = (0, 43, 0)


def should_use_old_session_saving() -> None:
    """
    Determine whether to use the old session saving method (parsing the container tree) or the new
    method (using Kitty's session output format). The old method is used for Kitty versions below
    0.43.0, while the new method is used for Kitty 0.43.0 and above.
    """
    try:
        output = subprocess.check_output(["kitty", "--version"]).decode("utf-8")
        # The version is the second word in the output
        version_str = output.strip().split()[1]
        version_parts = version_str.split(".")
        version_tuple = tuple(int(part) for part in version_parts)
        return version_tuple < KITTY_NEW_SESSION_VERSION
    except (subprocess.CalledProcessError, IndexError, ValueError) as err:
        logger.error("Failed determining Kitty version: %s", err)
        # Default to using the old session saving method if the version cannot be determined
        return True


def get_listen_socket(listen_socket: str, pid: int) -> None:
    # Handle the custom placeholder that could appear in Kitty's listen_socket
    if "{kitty_pid}" in listen_socket:
        return listen_socket.replace("{kitty_pid}", str(pid))

    # If the kitty_pid placeholder doesn't exist, Kitty will automatically append -{pid} to the
    # listen_socket
    return f"{listen_socket}-{pid}"


def get_container_tree(listen_socket: str) -> JSON:
    """
    Use Kitty's remote control feature to get the container tree that listens on the provided
    listen_socket.
    """
    try:
        output = subprocess.check_output(
            ["kitty", "@", "--to", listen_socket, "ls", "--all-env-vars"]
        ).decode("utf-8")
    except subprocess.CalledProcessError as err:
        logger.error("Failed retrieving Kitty container tree")
        raise utils.PluginSaveError from err

    return json.loads(output)


def save_scrollback(window_id: int, os_window_id: int, plugin_config: JSON) -> Path | None:
    """
    Save the scrollback for a Kitty window.

    The 'scrollback' option in the plugin config controls how much of the scrollback gets saved.
    If it is 'none', the scrollback will not be saved. If 'screen', the scrollback that is visible
    will be saved. If 'all', the entire scrollback will be saved.

    Returns None when saving the scrollback is skipped or executing the command to save it fails.
    """
    scrollback_file = Path(utils.i3_PATH) / f"kitty-scrollback-{os_window_id}-{window_id}"

    scrollback_extent = plugin_config["scrollback"]
    if scrollback_extent not in constants.KITTY_SCROLLBACK_ACTION_OPTIONS:
        logger.debug("Skipping saving scrollback due to value being '%s'", scrollback_extent)
        return None

    logger.info("Saving scrollback for Kitty window")
    try:
        subprocess.check_call(
            [
                "kitty",
                "@",
                "--to",
                plugin_config["listen_socket"],
                "get-text",
                "--ansi",  # Save colors in the scrollback
                "--add-cursor",  # This is so the cursor will be in the same position on restore
                "--match",
                f"id:{window_id}",  # Only match the current window
                f"--extent={scrollback_extent}",
            ],
            stdout=scrollback_file.open("w"),
        )
    except subprocess.CalledProcessError as err:
        logger.error(
            "Failed retrieving Kitty scrollback for OS window ID %s and window ID %s: %s",
            os_window_id,
            window_id,
            err,
        )
        return None

    logger.info("Scrollback output saved at '%s'", scrollback_file)
    return scrollback_file


def get_window_subprocess_command(
    container: Container, window: JSON, plugin_config: JSON
) -> str | None:
    """
    Create the subprocess command to restore any subprocesses in the current window. If a subprocess
    is running and is configured to be saved, it will be saved and restored. Otherwise, if the
    window's scrollback is configured to be saved, it will be restored as a subprocess using 'cat'.
    Last, if there is no subprocess or scrollback to save, no subprocess command will be returned.
    """
    # Using a process is a bit of a hack as most of the information is already in the window tree.
    # However, the subprocess command logic can be reused this way and the tree doesn't have the
    # process name (which could be different than cmdline[0]).
    process = psutil.Process(window["pid"])

    shell = window["env"].get("SHELL", "bash")
    # The default launch command needs to change as a subprocess in Kitty should return back to
    # the shell after the subprocess exits
    container.check_if_subprocess(process, f"{{command}} && {shell}")

    subprocess_command = None
    if container.subprocess_command:
        # Wrap the subprocess command in a shell so it launches correctly with Kitty's launch
        # command
        subprocess_command = f"{shell} -c '{container.subprocess_command}'"
        # Overwrite this so the main script doesn't save the container's subprocess too
        container.subprocess_command = None
    else:
        scrollback_file = save_scrollback(window["id"], container.window_id, plugin_config)
        if scrollback_file is not None:
            subprocess_command = f"{shell} -c 'cat \"{scrollback_file}\" && {shell}'"

    return subprocess_command


def get_window_launch_command(container: Container, window: JSON, plugin_config: JSON) -> str:
    """
    Create a window's launch command to restore its working directory, any subprocesses that are
    running in it, and its scrollback (if configured to do so). The scrollback will be restored
    as a subprocess.
    """
    launch_command = f'launch --cwd="{window["cwd"]}"'
    subprocess_command = get_window_subprocess_command(container, window, plugin_config)
    if subprocess_command:
        launch_command += " " + subprocess_command

    return launch_command + "\n"


def parse_tree_to_session(container: Container, os_window_tree: JSON, plugin_config: JSON) -> str:
    """
    Parse a Kitty container tree into a session that can be used to restore the layout and programs
    that this container is running.

    This function is only used for Kitty versions below 0.43.0, as Kitty 0.43.0+ provides a way to
    retrieve this session directly, allowing for fully accurate restores.
    """
    logger.info("Parsing container tree into session")

    output = ""
    for tab in os_window_tree["tabs"]:
        output += "new_tab\n"
        output += f"layout {tab['layout']}\n"

        if tab["is_active"]:
            output += "focus\n"

        # In Kitty versions below 0.43.0, the window layouts won't be restored perfectly as the
        # Kitty tree doesn't provide enough information to do so.
        for window in tab["windows"]:
            output += get_window_launch_command(container, window, plugin_config)

    logger.debug("Kitty session output:\n%s", output)
    return output


def get_session_contents(listen_socket: str) -> str:
    """
    Get the Kitty container's session contents using the session output format in kitty @ ls (only
    in Kitty 0.43.0+)
    """
    logger.info("Retrieving Kitty session contents")
    try:
        output = subprocess.check_output(
            ["kitty", "@", "--to", listen_socket, "ls", "--all-env-vars", "--output-format=session"]
        ).decode("utf-8")
    except subprocess.CalledProcessError as err:
        logger.error("Failed retrieving Kitty session")
        raise utils.PluginSaveError from err

    return output


def get_new_launch_command(
    container: Container, plugin_config: JSON, old_launch_command: str, window_objs: dict[int, JSON]
) -> str:
    """
    The default Kitty launch command (in the conditions this script calls it) is in the format:
    launch 'kitty-unserialize-data={"id": <id>}' <flags> <command>

    We need to extract the window ID to create the new launch command. This function parses the old
    launch command to do so. It relies on Kitty's behavior for the launch command format to stay
    consistent, so this may break in future versions of Kitty. It currently works from Kitty 0.43.0
    to 0.45.0.
    """

    # First, get the start of the unserialize data JSON
    kitty_key_start = old_launch_command.find(KITTY_UNSERIALIZE_DATA_KEY, len(KITTY_LAUNCH_PREFIX))
    data_start = kitty_key_start + len(KITTY_UNSERIALIZE_DATA_KEY)

    # Next, retrieve the full JSON to extract the window ID
    data_json, _ = json.JSONDecoder().raw_decode(old_launch_command[data_start:])
    window_id = data_json["id"]

    launch_command = get_window_launch_command(container, window_objs[window_id], plugin_config)

    # Use all the data present in the old unserialize data. Only ID should be present, but in case
    # any more data is added in future Kitty versions, preserve it.
    new_unserialize_data = "'kitty-unserialize-data=" + json.dumps(data_json) + "'"

    # Construct the new launch command with the updated unserialize data
    return (
        f"{KITTY_LAUNCH_PREFIX}{new_unserialize_data} {launch_command[len(KITTY_LAUNCH_PREFIX) :]}"
    )


def replace_launch_commands(
    container: Container, os_window_tree: JSON, plugin_config: JSON, session_contents: str
) -> str:
    """
    Replace the launch commands Kitty creates in the session contents to restore subprocesses and
    scrollback for each window.
    """
    # First, map window IDs to their window objects for easy access
    window_objs = {}
    for tab in os_window_tree["tabs"]:
        for window in tab["windows"]:
            window_objs[window["id"]] = window

    session_lines = session_contents.splitlines(keepends=True)
    updated_session_lines = []

    # Keep all lines the same except for launch commands, which need to be updated
    for line in session_lines:
        if line.startswith(KITTY_LAUNCH_PREFIX):
            launch_command = get_new_launch_command(container, plugin_config, line, window_objs)
            logger.debug("Updated launch command:\nOld: %sNew: %s", line, launch_command)
            updated_session_lines.append(launch_command)
        else:
            updated_session_lines.append(line)

    return "".join(updated_session_lines)


def create_session_file(container: Container, tree: JSON, plugin_config: JSON) -> Path:
    """
    Create a session file for the container. The session file will be written under i3_PATH in the
    format kitty-session-{container.window_id}.
    """
    # Select the OS window that matches the container. Other OS windows under the same PID will be
    # saved separately in the main script (the main script saves each window, not each process).
    os_window = [window for window in tree if container.window_id == window["platform_window_id"]]
    os_window = os_window[0]

    if USE_OLD_SESSION_SAVING:
        # Use the old method of parsing the container tree into a session when using Kitty versions
        # below 0.43.0
        session_contents = parse_tree_to_session(container, os_window, plugin_config)
    else:
        session_contents = get_session_contents(plugin_config["listen_socket"])
        session_contents = replace_launch_commands(
            container, os_window, plugin_config, session_contents
        )

    session_file = Path(utils.i3_PATH) / f"kitty-session-{container.window_id}"
    with session_file.open("w") as f:
        f.write(session_contents)

    return session_file


def main(container: Container, config: JSON) -> None:
    logger.info("Saving Kitty container")

    global USE_OLD_SESSION_SAVING
    if USE_OLD_SESSION_SAVING is None:
        # Determine which session saving method to use (on first run only)
        USE_OLD_SESSION_SAVING = should_use_old_session_saving()
        logger.info("Using old Kitty session saving method: %s", USE_OLD_SESSION_SAVING)

    # Copy to not overwrite the original config
    plugin_config = config.copy()

    plugin_config["listen_socket"] = get_listen_socket(config["listen_socket"], container.pid)
    logger.info("Kitty container listening on socket %s", plugin_config["listen_socket"])

    container_tree = get_container_tree(plugin_config["listen_socket"])
    logger.debug("Kitty container tree: %s", container_tree)

    session_file = create_session_file(container, container_tree, plugin_config)
    logger.info("Kitty session file created at %s", session_file)

    # Update the container's attributes so the Kitty session will be restored correctly
    container.command = f"kitty --session '{session_file}'"
    # The working directory is already set in the Kitty session, so this value can be any valid
    # directory. / is used as it is guaranteed to exist.
    container.working_directory = "/"
