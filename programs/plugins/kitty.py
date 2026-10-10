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

KITTY_VERSION = None
# The version we can use the new session format to restore sessions fully.
KITTY_NEW_SESSION_VERSION = (0, 43, 0)
# The version we can use the launch kitten synchronously to retrieve alternate scrollback.
KITTY_SYNCHRONOUS_LAUNCH_VERSION = (0, 44, 0)
# The version we can use the get-text kitten for alternate scrollback retrieval.
KITTY_GET_TEXT_ALTERNATE_SCROLLBACK_VERSION = (0, 48, 0)


def get_kitty_version() -> tuple[int, int, int]:
    """
    Get the installed Kitty version. Fallback to an old version when retrieval fails to use the
    legacy save methods.
    """
    try:
        output = subprocess.check_output(["kitty", "--version"]).decode("utf-8")
        # The version is the second word in the output
        version_str = output.strip().split()[1]
        major, minor, patch = (int(part) for part in version_str.split(".")[:3])
        return major, minor, patch
    except (subprocess.CalledProcessError, IndexError, ValueError) as err:
        logger.error("Failed determining Kitty version: %s", err)
        return (0, 0, 0)


def get_listen_socket(listen_socket: str, pid: int) -> str:
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


def save_scrollback(
    window_id: int, os_window_id: int, plugin_config: JSON, *, alternate_screen: bool = False
) -> Path | None:
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

    if alternate_screen:
        # "alternate" saves the scrollback only in view from the alternate screen and
        # "alternate_scrollback" saves the scrollback from the alternate screen.
        scrollback_extent = "alternate" if scrollback_extent == "screen" else "alternate_scrollback"

    logger.info("Saving scrollback for Kitty window")
    try:
        if not alternate_screen or KITTY_VERSION >= KITTY_GET_TEXT_ALTERNATE_SCROLLBACK_VERSION:
            command = [
                "kitty",
                "@",
                "--to",
                plugin_config["listen_socket"],
                "get-text",
                "--ansi",  # Save colors in the scrollback
            ]
            if not alternate_screen:
                command.append("--add-cursor")
            command.extend(
                [
                    "--match",
                    f"id:{window_id}",  # Only match the current window
                    f"--extent={scrollback_extent}",
                ]
            )
            subprocess.check_call(command, stdout=scrollback_file.open("w"))
        else:
            # get-text does not support alternate screens before Kitty 0.48.0. Get the alternate
            # screen scrollback from the launch kitten instead.
            command = [
                "kitten",
                "@",
                "--to",
                plugin_config["listen_socket"],
                "launch",
                "--source-window",
                f"id:{window_id}",
                "--type=background",
                f"--stdin-source=@{scrollback_extent}",
                "--stdin-add-formatting",
            ]
            if KITTY_VERSION >= KITTY_SYNCHRONOUS_LAUNCH_VERSION:
                # Kitty 0.44.0+ supports running the launch kitten synchronously.
                command.append("--wait-for-child-to-exit")
            command.extend(["sh", "-c", 'cat > "$1"', "sh", str(scrollback_file)])
            subprocess.check_call(command, stdout=subprocess.DEVNULL)
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


def get_window_restore_command(
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
    # the shell after the subprocess exits.
    subprocess_name = container.check_if_subprocess(
        process, f"{{command}} && {shell}", window.get("title", "")
    )

    subprocess_command = None
    if container.subprocess_command:
        restore_command = container.subprocess_command
        scrollback_file = save_scrollback(
            window["id"],
            container.window_id,
            plugin_config,
            alternate_screen=subprocess_name in plugin_config["alternate_scrollback_subprocesses"],
        )
        if scrollback_file is not None:
            restore_command = f'cat "{scrollback_file}" && {restore_command}'
        # Wrap the subprocess command in a shell so it launches correctly with Kitty's launch
        # command.
        subprocess_command = f"{shell} -c '{restore_command}'"
        # Overwrite this so the main script doesn't save the container's subprocess too.
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
    subprocess_command = get_window_restore_command(container, window, plugin_config)
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


def get_launch_unserialize_data(launch_command: str) -> JSON:
    """Extract the Kitty unserialize data from a serialized session launch command."""
    kitty_key_start = launch_command.find(KITTY_UNSERIALIZE_DATA_KEY, len(KITTY_LAUNCH_PREFIX))
    if kitty_key_start == -1:
        raise ValueError("Kitty launch command does not contain unserialize data")

    data_start = kitty_key_start + len(KITTY_UNSERIALIZE_DATA_KEY)
    data_json, _ = json.JSONDecoder().raw_decode(launch_command[data_start:])
    return data_json


def filter_session_contents_for_os_window(session_contents: str, os_window_tree: JSON) -> str:
    """
    Keep only the session block for the OS window currently being saved.

    Kitty's session output can include multiple OS windows for one Kitty process, separated by
    new_os_window. i3-restore saves each OS window separately, so each generated session file should
    only contain the block matching the selected i3 container.
    """
    selected_window_ids = {
        window["id"] for tab in os_window_tree["tabs"] for window in tab["windows"]
    }
    session_blocks = []
    current_block = []

    for line in session_contents.splitlines(keepends=True):
        if line == "new_os_window\n":
            session_blocks.append(current_block)
            current_block = []
        else:
            current_block.append(line)

    session_blocks.append(current_block)

    for block in session_blocks:
        block_window_ids = {
            get_launch_unserialize_data(line)["id"]
            for line in block
            if line.startswith(KITTY_LAUNCH_PREFIX)
        }
        if block_window_ids and block_window_ids <= selected_window_ids:
            return "".join(block)

    logger.error("Failed matching Kitty session output to OS window")
    raise utils.PluginSaveError


def get_new_launch_command(
    container: Container, plugin_config: JSON, old_launch_command: str, window_objs: dict[int, JSON]
) -> str:
    """
    The default Kitty launch command (in the conditions this script calls it) is in the format:
    launch 'kitty-unserialize-data={"id": <id>}' <flags> <command>

    We need to extract the window ID to create the new launch command. This function parses the old
    launch command to do so. It relies on Kitty's behavior for the launch command format to stay
    consistent, so this may break in future versions of Kitty. It currently works from Kitty 0.43.0
    to 0.49.2.
    """

    data_json = get_launch_unserialize_data(old_launch_command)
    window_id = data_json["id"]

    launch_command = get_window_launch_command(container, window_objs[window_id], plugin_config)

    # Use all the data present in the old unserialize data. Only ID should be present, but in case
    # any more data is added in future Kitty versions, preserve it.
    new_unserialize_data = "'kitty-unserialize-data=" + json.dumps(data_json) + "'"

    # Construct the new launch command with the updated unserialize data.
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
    # First, map window IDs to their window objects for easy access.
    window_objs = {}
    for tab in os_window_tree["tabs"]:
        for window in tab["windows"]:
            window_objs[window["id"]] = window

    session_lines = session_contents.splitlines(keepends=True)
    updated_session_lines = []

    # Keep all lines the same except for launch commands, which need to be updated.
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

    if KITTY_VERSION < KITTY_NEW_SESSION_VERSION:
        # Use the old method of parsing the container tree into a session when using Kitty versions
        # below 0.43.0.
        session_contents = parse_tree_to_session(container, os_window, plugin_config)
    else:
        session_contents = get_session_contents(plugin_config["listen_socket"])
        session_contents = filter_session_contents_for_os_window(session_contents, os_window)
        session_contents = replace_launch_commands(
            container, os_window, plugin_config, session_contents
        )

    session_file = Path(utils.i3_PATH) / f"kitty-session-{container.window_id}"
    with session_file.open("w") as f:
        f.write(session_contents)

    return session_file


def main(container: Container, config: JSON) -> None:
    logger.info("Saving Kitty container")

    global KITTY_VERSION
    if KITTY_VERSION is None:
        # Determine the Kitty version on first run only.
        KITTY_VERSION = get_kitty_version()
        logger.info("Kitty version: %s", ".".join(str(part) for part in KITTY_VERSION))

    # Copy to not overwrite the original config.
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
