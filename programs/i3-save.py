import os
from pathlib import Path
import subprocess
import sys

import psutil

from config import SUBPROCESS_PROGRAMS, TERMINALS, WEB_BROWSERS
import utils

# Get path where layouts were saved. Sets a default if the environment variable isn't set
HOME = os.getenv("HOME")
i3_PATH = os.getenv("i3_PATH", f"{HOME}/.config/i3")

# Set up the web browsers dictionary to keep track of already running web browsers
WEB_BROWSERS_DICT = dict.fromkeys(WEB_BROWSERS, False)


def main():
    workspaces = utils.get_workspaces()
    for workspace in workspaces:
        Workspace(workspace)


class Workspace:
    def __init__(self, properties):
        self.name = properties["name"]
        self.containers = []

        logger.debug("Saving programs for Workspace %s", self.name)
        self.get_containers(properties)
        self.save()

    # Recursive function to get all containers in a workspace
    def get_containers(self, properties):
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

    def save(self):
        # Don't save if there are no containers in the workspace
        if len(self.containers) == 0:
            logger.debug("No containers found for Workspace %s. Skipping...", self.name)
            return

        logger.debug("Number of containers: %s", len(self.containers))

        # For some reason, i3 doesn't execute scripts with a space in the name correctly
        sanitized_name = self.name.replace("/", "{slash}").replace(" ", "{space}")
        file = Path(i3_PATH) / f"workspace_{sanitized_name}_programs.sh"

        program_commands = ""
        for i, container in enumerate(self.containers):
            logger.debug("Saving container with command %s and working directory %s",
                         container.command, container.working_directory)

            # Each command is prefixed with a selection statement so we have control
            # to restore only one container at a time. This ensures the containers restore
            # reliably in the correct order.
            program_commands += f"[[ $1 == {i} ]] && cd \"{container.working_directory}\" " \
                                f"&& {container.command}\n"

        with file.open("w") as f:
            f.write(program_commands)


class Container:
    def __init__(self, properties):
        self.command = None
        self.working_directory = None

        self.pid = self.get_pid(properties)
        self.get_cmdline_options(properties)

    @staticmethod
    def get_pid(properties):
        pid_info = subprocess.check_output(["xprop", "_NET_WM_PID", "-id", str(properties["window"])]).decode("utf-8").rstrip()
        return int(pid_info.split("= ")[1])

    def get_cmdline_options(self, properties):
        process = psutil.Process(self.pid)

        # First, check if it is a terminal
        for terminal in TERMINALS:
            if properties["window_properties"]["class"] == terminal["class"]:
                logger.debug("Main process of container is a terminal")

                # The terminal command is set here manually so the custom command used to restore the subprocess
                # works as expected and doesn't store "[terminal] -e bash -c ..."
                self.command = terminal["command"]
                self.working_directory = process.children()[0].cwd()

                self.check_if_subprocess(process)
                return

        self.command = " ".join(process.cmdline())
        self.working_directory = process.cwd()

        # Next, handle saving web browsers. We only want to save the first
        # instance -- not every instance -- because the browser will handle
        # restoring every instance.
        self.handle_web_browser()

    # Get the subprocess recursively. This means the newest subprocess
    # will be saved and restored
    def check_if_subprocess(self, process):
        for child in reversed(process.children(True)):
            child_name = child.name()
            for program in SUBPROCESS_PROGRAMS:
                if child_name == program["name"]:
                    logger.debug("Subprocess '%s' found in main process '%s'", child_name, process.name())
                    command = child.cmdline()[0]
                    for arg in child.cmdline()[1:]:
                        command += " " + arg.replace(" ", r"\ ")

                    self.command = program["launch_command"].replace("{command}", command)
                    return

    def handle_web_browser(self) -> None:
        for web_browser in WEB_BROWSERS:
            if web_browser in self.command:
                self.save_web_browser(web_browser)
                self.command = None
                return

    def save_web_browser(self, web_browser: str) -> None:
        if WEB_BROWSERS_DICT.get(web_browser):
            # The web browser has already been called, so don't save it again
            # Browsers restore all tabs in one go, even multiple windows
            logger.debug("Container detected as a web browser, but a web browser instance "
                         "has already been saved. Skipping...")
            return

        logger.debug("Saving container as a web browser")
        WEB_BROWSERS_DICT[web_browser] = True

        with open(f"{i3_PATH}/web_browsers.sh", "a") as f:
            f.write(f"{self.command}\n")


if __name__ == "__main__":
    logger = utils.get_logger()

    try:
        main()
    except Exception as err:
        logger.exception(err)
        sys.exit(1)
