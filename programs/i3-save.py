import json
import os
from pathlib import Path
import subprocess

import psutil

from config import TERMINALS, TERMINAL_EDITORS
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
            return

        file = Path(i3_PATH) / f"workspace_{self.name}_programs.json"

        with file.open("w") as f:
            programs = []
            for container in self.containers:
                programs.append({
                    "command": container.command,
                    "working_directory": container.working_directory,
                })

            f.write(json.dumps(programs, indent=2))


class Container:
    def __init__(self, properties):
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
                # The terminal command is set here manually so the custom command used to restore the terminal editor
                # works as expected and doesn't store "[terminal] -e bash -c ..."
                self.command = [terminal["command"]]
                self.working_directory = process.children()[0].cwd()

                self.check_if_terminal_editor(process)
                return

        self.command = process.cmdline()
        self.working_directory = process.cwd()

    def check_if_terminal_editor(self, process):
        # Get terminal editor process. They will all be the grandchild of the current process
        try:
            grandchild = process.children(True)[1]
        except IndexError:
            return

        for editor in TERMINAL_EDITORS:
            if grandchild.name() == editor["name"]:
                self.command = grandchild.cmdline()
                return


if __name__ == "__main__":
    main()
