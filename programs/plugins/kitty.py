from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import psutil

import utils

if TYPE_CHECKING:
    from .. import JSON, Config, Container


logger = utils.get_logger()


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


def parse_tree_to_session(container: Container, tree: JSON) -> str:
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
        # they layout of each window.
        # TODO: Save more than one window, even though the layout won't be restored exactly correct
        window = tab["windows"][0]

        # Using a process is a bit of a hack as most of the information is already in the tree.
        # However, the subprocess command logic can be reused this way and the tree doesn't have the
        # process name (which could be different than cmdline[0]).
        process = psutil.Process(window["pid"])

        shell = window["env"].get("SHELL", "bash")
        # The default launch command needs to change as a subprocess in Kitty should return back to
        # the shell after the subprocess exits
        container.check_if_subprocess(process, f"{{command}} && {shell}")

        subprocess_command = container.subprocess_command or ""
        if subprocess_command:
            # Wrapping the subprocess command in a shell launches it correctly using Kitty's launch
            # command
            subprocess_command = f"{shell} -c '{subprocess_command}'"

        output += f"launch --cwd={window['cwd']} {subprocess_command}\n"
        # Overwrite this so the main script doesn't save the container's subprocesses too
        container.subprocess_command = None

    logger.debug("Kitty session output:\n%s", output)
    return output


def create_session_file(container: Container, tree: JSON) -> str:
    """
    Create a session file for the container. The session file will be written under i3_PATH in the
    format kitty-session-{container_window_id}.
    """
    # Select the OS window that matches the container. Other OS windows under the same PID will be
    # saved separately in the main script (the main script saves each window, not each process).
    os_window = [window for window in tree if container.window_id == window["platform_window_id"]]
    os_window = os_window[0]

    session_contents = parse_tree_to_session(container, os_window)

    session_file = Path(utils.i3_PATH) / f"kitty-session-{container.window_id}"
    with session_file.open("w") as f:
        f.write(session_contents)

    return session_file


def main(container: Container, config: Config) -> None:
    logger.info("Saving Kitty container")
    listen_socket = get_listen_socket(config["listen_socket"], container.pid)
    logger.info("Kitty container listening on socket %s", listen_socket)
    container_tree = get_container_tree(listen_socket)
    logger.debug("Kitty container tree: %s", container_tree)
    session_file = create_session_file(container, container_tree)
    logger.info("Kitty session file created at %s", session_file)

    # Update the container's attributes so the Kitty session will be restored correctly
    container.command = f"kitty --session {session_file}"
    # The working directory is already set in the Kitty session, so this value can be any valid
    # directory. / is used as it is guaranteed to exist.
    container.working_directory = "/"
