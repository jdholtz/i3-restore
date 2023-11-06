from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import psutil

import config
import utils

# Get path where layouts were saved. Sets a default if the environment variable isn't set
HOME = os.getenv("HOME")
i3_PATH = os.getenv("i3_PATH", f"{HOME}/.config/i3")

# Type alias for JSON
JSON = utils.JSON

CONFIG = config.Config()

# Set up the web browsers dictionary to keep track of already running web browsers
WEB_BROWSERS_DICT = dict.fromkeys(CONFIG.web_browsers, False)

logger = utils.get_logger()


def main() -> None:
    workspaces = utils.get_workspaces()
    for workspace in workspaces:
        Workspace(workspace)


class Workspace:
    """
    Process all containers inside a workspace. Save their
    startup commands to a file so they can be restored
    """

    def __init__(self, properties: JSON) -> None:
        self.name = properties["name"]

        # For some reason, i3 doesn't execute scripts with a space in the name correctly
        # so this will be used when for script file names
        self.sanitized_name = self.name.replace("/", "{slash}").replace(" ", "{space}")
        self.containers = []

        logger.debug("Saving programs for Workspace %s", self.name)
        self.get_containers(properties)
        self.save()

    def get_containers(self, properties: JSON) -> None:
        """Recursive function to get all containers in a workspace"""
        containers = properties["nodes"]
        for container in containers:
            if len(container["nodes"]) == 0:
                # Make sure it isn't a template window and it actually has a program running
                if len(container["swallows"]) != 0:
                    continue

                con = Container(container)
                if con.command is not None:
                    self.containers.append(con)
            else:
                self.get_containers(container)

    def save(self) -> None:
        """Save all the containers' commands in a file"""

        # Don't save if there are no containers in the workspace
        if len(self.containers) == 0:
            logger.debug("No containers found for Workspace %s. Skipping...", self.name)
            return

        logger.debug("Number of containers: %s", len(self.containers))

        file = Path(i3_PATH) / f"workspace_{self.sanitized_name}_programs.sh"

        program_commands = ""
        for i, container in enumerate(self.containers):
            logger.debug(
                "Saving container with command %s and working directory %s",
                container.command,
                container.working_directory,
            )

            # Each command is prefixed with a selection statement so we have control
            # to restore only one container at a time. This ensures the containers restore
            # reliably in the correct order.
            program_commands += f'[[ $1 == {i} ]] && cd "{container.working_directory}" && '

            # Containers with subprocess commands need to save where they stored the
            # subprocess command so it could be executed correctly when restored
            if container.subprocess_command:
                subprocess_file = self.save_subprocess(container, i)
                program_commands += f"I3_RESTORE_SUBPROCESS_SCRIPT={subprocess_file} "

            program_commands += f"{container.command}\n"

        with file.open("w") as f:
            f.write(program_commands)

    def save_subprocess(self, container: Container, container_num: int) -> Path:
        """
        Write the subprocess command to a separate file. This makes executed commands
        behave (nearly) identically to how it would be executed in a terminal.
        """
        file = Path(i3_PATH) / f"workspace_{self.sanitized_name}_subprocess_{container_num}.sh"
        with file.open("w") as f:
            f.write(container.subprocess_command)

        return file


class Container:
    """
    Responsible for retrieving the correct command and working directory
    of the container.
    """

    def __init__(self, properties: JSON) -> None:
        self.command = None
        self.subprocess_command = None
        self.working_directory = None

        self.pid = self.get_pid(properties)

        try:
            self.get_cmdline_options(properties)
        except psutil.ZombieProcess:
            # This happens when i3 restore is attempting to save a container that was very recently
            # killed and the process hasn't been cleaned up yet
            logger.debug("Container is a zombie process. Skipping...")
            # Don't save the container since it doesn't actually exist anymore
            self.command = None
        except psutil.AccessDenied:
            logger.debug(
                "Access denied while trying to access container command line options. Skipping..."
            )
            # Don't save the container if it fails to access all of its attributes
            self.command = None

    @staticmethod
    def get_pid(properties: JSON) -> Optional[int]:
        """Get the PID of the current container"""
        try:
            pid_info = subprocess.check_output(
                ["xdotool", "getwindowpid", str(properties["window"])], stderr=subprocess.DEVNULL
            ).decode("utf-8")
            pid_info = int(pid_info)
        except subprocess.CalledProcessError:
            logger.debug("No PID associated with container. Skipping...")
            pid_info = None

        return pid_info

    def get_cmdline_options(self, properties: JSON) -> None:
        """Set the command and working directory of the container"""
        if self.pid is None:
            return

        process = psutil.Process(self.pid)

        # First, check if it is a terminal
        for terminal in CONFIG.terminals:
            if properties["window_properties"]["class"] == terminal["class"]:
                logger.debug("Main process of container is a terminal")

                # The terminal command is set here manually so the custom command used to restore
                # the subprocess works as expected and doesn't store "[terminal] -e bash -c ..."
                self.command = terminal["command"]

                self.check_if_subprocess(process)

                # Get the working directory of the last process because some terminals
                # store working directories different than others (which is why it can't
                # just be grabbed from the main process)
                self.working_directory = process.children()[-1].cwd()
                return

        self.command = " ".join(process.cmdline())
        self.working_directory = process.cwd()

        # Next, handle saving web browsers. We only want to save the first
        # instance -- not every instance -- because the browser will handle
        # restoring every instance.
        self.handle_web_browser()

    def check_if_subprocess(self, process: psutil.Process) -> None:
        """
        Checks whether or not the process has any subprocesses that should be
        saved. Examples of subprocesses that run in the terminal include Vim,
        Emacs, and cmus.

        Since the subprocesses are retrieved recursively, the newest subprocess
        will be saved and restored.
        """
        for child in reversed(process.children(True)):
            child_name = child.name()
            for program in CONFIG.subprocesses:
                if child_name == program["name"]:
                    logger.debug(
                        "Subprocess '%s' found in main process '%s'", child_name, process.name()
                    )

                    command = child.cmdline()[0]
                    cmd_args = child.cmdline()[1:]
                    save_args = program.get("args", [])

                    # First, check if the subprocess includes the desired arguments
                    includes_save_arg = any(arg in cmd_args for arg in save_args)
                    if save_args and not includes_save_arg:
                        logger.debug(
                            "Skipping saving subprocess as it doesn't include desired arguments"
                        )
                        return

                    # Next, build the command
                    for arg in cmd_args:
                        command += " " + arg.replace(" ", r"\ ")

                    launch_command = program.get("launch_command", "{command}")
                    self.subprocess_command = launch_command.replace("{command}", command)
                    return

    def handle_web_browser(self) -> None:
        """Checks whether the container's program is a web browser"""
        for web_browser in CONFIG.web_browsers:
            if web_browser in self.command:
                self.save_web_browser(web_browser)
                self.command = None
                return

    def save_web_browser(self, web_browser: str) -> None:
        """
        Saves the web browser to a separate file only if it has not
        been saved already. Since the script uses the browsers'
        restore features, only execute one instance of the browser.
        """
        if WEB_BROWSERS_DICT.get(web_browser):
            # The web browser has already been called, so don't save it again
            logger.debug(
                "Container detected as a web browser, but a web browser instance "
                "has already been saved. Skipping..."
            )
            return

        logger.debug("Saving container as a web browser")
        WEB_BROWSERS_DICT[web_browser] = True

        with open(f"{i3_PATH}/web_browsers.sh", "a") as f:
            f.write(f"{self.command}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        logger.exception(err)
        sys.exit(1)
