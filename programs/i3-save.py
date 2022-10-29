import json
import os
from pathlib import Path
import subprocess

import psutil

from config import SUBPROCESS_PROGRAMS, TERMINALS
import utils

# Get path where layouts were saved. Sets a default if the environment variable isn't set
HOME = os.getenv("HOME")
i3_PATH = os.getenv("i3_PATH", f"{HOME}/.config/i3")


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

                self.containers.append(Container(container))
            else:
                self.get_containers(container)

    def save(self):
        # Don't save if there are no containers in the workspace
        if len(self.containers) == 0:
            logger.debug("No containers found for Workspace %s. Skipping...", self.name)
            return

        logger.debug("Number of containers: %s", len(self.containers))
        sanitized_name = self.name.replace("/", "{slash}")
        file = Path(i3_PATH) / f"workspace_{sanitized_name}_programs.json"

        with file.open("w") as f:
            programs = []
            for container in self.containers:
                programs.append({
                    "command": container.command,
                    "working_directory": container.working_directory,
                })

            logger.debug("Saving container programs: %s", programs)
            f.write(json.dumps(programs, indent=2))


class Container:
    def __init__(self, properties):
        self.pid = None
        self.command = None
        self.working_directory = None

        self.get_pid(properties)
        self.get_cmdline_options(properties)

    def get_pid(self, properties):
        pid_info = subprocess.check_output(["xprop", "_NET_WM_PID", "-id", str(properties["window"])]).decode("utf-8").rstrip()
        self.pid = int(pid_info.split("= ")[1])

    def get_cmdline_options(self, properties):
        process = psutil.Process(self.pid)

        # First, check if it is a terminal
        for terminal in TERMINALS:
            if properties["window_properties"]["class"] == terminal["class"]:
                logger.debug("Main process of container is a terminal")

                # The terminal command is set here manually so the custom command used to restore the subprocess
                # works as expected and doesn't store "[terminal] -e bash -c ..."
                self.command = [terminal["command"]]
                self.working_directory = process.children()[0].cwd()

                self.check_if_subprocess(process)
                return

        self.command = process.cmdline()
        self.working_directory = process.cwd()

    # Get the subprocess recursively. This means the newest subprocess
    # will be saved and restored
    def check_if_subprocess(self, process):
        for child in reversed(process.children(True)):
            child_name = child.name()
            for program in SUBPROCESS_PROGRAMS:
                if child_name == program["name"]:
                    logger.debug("Subprocess '%s' found in main process '%s'", child_name, process.name())
                    self.command = child.cmdline()
                    return


if __name__ == "__main__":
    logger = utils.get_logger()

    try:
        main()
    except Exception as err:
        logger.exception(err)
