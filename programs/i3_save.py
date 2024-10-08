from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

import psutil

import config
import constants
import plugins.kitty
import utils

# Plugins that are supported to have custom save algorithms. The key is the window class and the
# value is the module to use to save the container (the module's 'main' function will be called).
SUPPORTED_PLUGINS = {constants.KITTY_CLASS: plugins.kitty}

# Type alias for JSON
JSON = utils.JSON

CONFIG = config.Config()

# Set up the web browsers dictionary to keep track of already running web browsers
WEB_BROWSERS_DICT = dict.fromkeys(CONFIG.web_browsers, False)

logger = utils.get_logger()


def main() -> None:
    workspaces = utils.get_workspaces()
    for workspace in workspaces:
        logger.debug("Workspace tree: %s", workspace)
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

        logger.info("Saving programs for Workspace %s", self.name)
        self._get_containers(properties)
        self._save()

    def _get_containers(self, properties: JSON) -> None:
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
                self._get_containers(container)

    def _save(self) -> None:
        """Save all the containers' commands in a file"""

        # Don't save if there are no containers in the workspace
        if len(self.containers) == 0:
            logger.info("No containers found for Workspace %s. Skipping...", self.name)
            return

        logger.info("Number of containers: %s", len(self.containers))

        file = Path(utils.i3_PATH) / f"workspace_{self.sanitized_name}_programs.sh"

        program_commands = "#!/usr/bin/env bash\n"
        for i, container in enumerate(self.containers):
            logger.info(
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
                subprocess_file = self._save_subprocess(container, i)
                program_commands += f"I3_RESTORE_SUBPROCESS_SCRIPT={subprocess_file} "

            program_commands += f"{container.command}\n"

        logger.debug("File: %s. Program commands: %s", file, program_commands)
        with file.open("w") as f:
            f.write(program_commands)

    def _save_subprocess(self, container: Container, container_num: int) -> Path:
        """
        Write the subprocess command to a separate file. This makes executed commands
        behave (nearly) identically to how it would be executed in a terminal.
        """
        file = (
            Path(utils.i3_PATH) / f"workspace_{self.sanitized_name}_subprocess_{container_num}.sh"
        )
        logger.debug("File: %s. Subprocess command: %s", file, container.subprocess_command)
        subprocess_cmd = "#!/usr/bin/env bash\n" + container.subprocess_command
        with file.open("w") as f:
            f.write(subprocess_cmd)

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
        self.window_class = properties["window_properties"].get("class")
        self.window_id = properties["window"]

        self.pid = self._get_pid()

        try:
            self._get_cmdline_options()
        except psutil.ZombieProcess:
            # This happens when i3 restore is attempting to save a container that was very recently
            # killed and the process hasn't been cleaned up yet
            logger.info("Container is a zombie process. Skipping...")
            # Don't save the container since it doesn't actually exist anymore
            self.command = None
        except psutil.AccessDenied:
            logger.info(
                "Access denied while trying to access container command line options. Skipping..."
            )
            # Don't save the container if it fails to access all of its attributes
            self.command = None

    def _get_pid(self) -> Optional[int]:
        """Get the PID of the current container"""
        try:
            pid_info = subprocess.check_output(
                ["xdotool", "getwindowpid", str(self.window_id)], stderr=subprocess.DEVNULL
            ).decode("utf-8")
            pid = int(pid_info)
        except subprocess.CalledProcessError:
            logger.info("No PID associated with container. Skipping...")
            pid = None

        return pid

    def _get_cmdline_options(self) -> None:
        """Set the command and working directory of the container"""
        if self.pid is None:
            return

        # Use a custom save plugin to save this container. The container will be saved normally if
        # the plugin is not enabled or the plugin fails to save it.
        if self.window_class in CONFIG.enabled_plugins and self._save_with_plugin():
            return

        process = psutil.Process(self.pid)

        # First, check if it is a terminal
        for terminal in CONFIG.terminals:
            if self.window_class == terminal["class"]:
                logger.info("Main process of container is a terminal")

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
        self._handle_web_browser()

    def _save_with_plugin(self) -> bool:
        """
        Save the container using a supported plugin. Returns true when the container is successfully
        saved, false if an error occurred or if no plugin supports saving this window. This function
        assumes that the plugin is enabled in the user config.
        """
        if self.window_class not in SUPPORTED_PLUGINS:
            logger.error("Plugin not supported: %s. Saving container regularly", self.window_class)
            return False

        logger.info("Saving container with plugin: %s", self.window_class)
        plugin_config = CONFIG.enabled_plugins[self.window_class]

        try:
            SUPPORTED_PLUGINS[self.window_class].main(self, plugin_config)
            return True
        except utils.PluginSaveError:
            return False

    def check_if_subprocess(
        self, process: psutil.Process, default_launch_command: str = "{command}"
    ) -> None:
        """
        Checks whether or not the process has any subprocesses that should be
        saved. Examples of subprocesses that run in the terminal include Vim,
        Emacs, and cmus.

        Since the subprocesses are retrieved recursively, the newest subprocess
        will be saved and restored.
        """
        # Prepending the current process is useful when the process is not a terminal (which can
        # happen when some plugins use it)
        processes = [process] + process.children(True)

        for child in reversed(processes):
            child_name = child.name()
            for program in CONFIG.subprocesses:
                if child_name != program["name"]:
                    continue

                logger.info(
                    "Subprocess '%s' found in main process '%s'", child_name, process.name()
                )

                cmd_line = child.cmdline()
                logger.debug("Subprocess command line: %s", cmd_line)
                command, cmd_args = cmd_line[0], cmd_line[1:]
                save_args = program.get("args", [])

                # First, check if the subprocess includes the desired arguments
                includes_save_arg = any(arg in cmd_args for arg in save_args)
                if save_args and not includes_save_arg:
                    logger.info(
                        "Skipping saving subprocess as it doesn't include desired arguments"
                    )
                    return

                # Next, build the command
                for arg in cmd_args:
                    command += " " + arg.replace(" ", r"\ ")

                launch_command = program.get("launch_command", default_launch_command)
                self.subprocess_command = launch_command.replace("{command}", command)
                return

    def _handle_web_browser(self) -> None:
        """Checks whether the container's program is a web browser"""
        for web_browser in CONFIG.web_browsers:
            if web_browser in self.command:
                self._save_web_browser(web_browser)
                self.command = None
                return

    def _save_web_browser(self, web_browser: str) -> None:
        """
        Saves the web browser to a separate file only if it has not
        been saved already. Since the script uses the browsers'
        restore features, only execute one instance of the browser.
        """
        if WEB_BROWSERS_DICT.get(web_browser):
            # The web browser has already been called, so don't save it again
            logger.info(
                "Container detected as a web browser, but a web browser instance "
                "has already been saved. Skipping..."
            )
            return

        logger.info("Saving container as a web browser")
        WEB_BROWSERS_DICT[web_browser] = True

        file = Path(utils.i3_PATH) / "web_browsers.sh"
        logger.debug("Web browser file: %s. Command: %s", file, self.command)
        with open(file, "a") as f:
            f.write(f"{self.command}\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        logger.exception(err)
        sys.exit(1)
