from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import psutil

import utils

if TYPE_CHECKING:
    from .. import JSON, Container


logger = utils.get_logger()

KITTY_SCROLLBACK_ACTION_OPTIONS = ["all", "screen"]


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
        output = subprocess.check_output(["kitty", "@", "--to", listen_socket, "ls"]).decode(
            "utf-8"
        )
    except subprocess.CalledProcessError as err:
        logger.error("Failed retrieving Kitty container tree")
        raise utils.PluginSaveError from err

    return json.loads(output)


def save_scrollback(window_id: int, os_window_id: int, plugin_config: JSON) -> Optional[Path]:
    """
    Save the scrollback for a Kitty window.

    The 'scrollback' option in the plugin config controls how much of the scrollback gets saved.
    If it is 'none', the scrollback will not be saved. If 'screen', the scrollback that is visible
    will be saved. If 'all', the entire scrollback will be saved.

    Returns None when saving the scrollback is skipped or executing the command to save it fails.
    """
    scrollback_file = Path(utils.i3_PATH) / f"kitty-scrollback-{os_window_id}-{window_id}"

    scrollback_extent = plugin_config["scrollback"]
    if scrollback_extent not in KITTY_SCROLLBACK_ACTION_OPTIONS:
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

    logger.info("Scrollback output saved at %s", scrollback_file)
    return scrollback_file


def get_window_subprocess_command(
    container: Container, window: JSON, plugin_config: JSON
) -> Optional[str]:
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
    launch_command = f"launch --cwd={window['cwd']}"
    subprocess_command = get_window_subprocess_command(container, window, plugin_config)
    if subprocess_command:
        launch_command += " " + subprocess_command

    return launch_command + "\n"


def parse_tree_to_session(container: Container, tree: JSON, plugin_config: JSON) -> str:
    """
    Parse a Kitty container tree into a session that can be used to restore the exact layout and
    programs that this container is running.
    """
    logger.info("Parsing container tree into session")

    output = ""
    for tab in tree["tabs"]:
        output += "new_tab\n"

        if tab["is_active"]:
            output += "focus\n"

        # Only save the first window in a tab. Kitty currently doesn't have a way to restore
        # the layout of multiple windows in a tab.
        # TODO: Save more than one window, even though the layout won't be restored exactly correct
        window = tab["windows"][0]

        output += get_window_launch_command(container, window, plugin_config)

    logger.debug("Kitty session output:\n%s", output)
    return output


def create_session_file(container: Container, tree: JSON, plugin_config: JSON) -> Path:
    """
    Create a session file for the container. The session file will be written under i3_PATH in the
    format kitty-session-{container.window_id}.
    """
    # Select the OS window that matches the container. Other OS windows under the same PID will be
    # saved separately in the main script (the main script saves each window, not each process).
    os_window = [window for window in tree if container.window_id == window["platform_window_id"]]
    os_window = os_window[0]

    session_contents = parse_tree_to_session(container, os_window, plugin_config)

    session_file = Path(utils.i3_PATH) / f"kitty-session-{container.window_id}"
    with session_file.open("w") as f:
        f.write(session_contents)

    return session_file


def main(container: Container, config: JSON) -> None:
    logger.info("Saving Kitty container")

    # Copy to not overwrite the original config
    plugin_config = config.copy()

    plugin_config["listen_socket"] = get_listen_socket(config["listen_socket"], container.pid)
    logger.info("Kitty container listening on socket %s", plugin_config["listen_socket"])

    container_tree = get_container_tree(plugin_config["listen_socket"])
    logger.debug("Kitty container tree: %s", container_tree)

    session_file = create_session_file(container, container_tree, plugin_config)
    logger.info("Kitty session file created at %s", session_file)

    # Update the container's attributes so the Kitty session will be restored correctly
    container.command = f"kitty --session {session_file}"
    # The working directory is already set in the Kitty session, so this value can be any valid
    # directory. / is used as it is guaranteed to exist.
    container.working_directory = "/"
