import json
import os
import subprocess
import time

import utils

from config import SUBPROCESS_PROGRAMS, WEB_BROWSERS

# Get path where layouts were saved. Sets a default if the environment variable isn't set
HOME = os.getenv("HOME")
i3_PATH = os.getenv("i3_PATH", f"{HOME}/.config/i3")

# Set up the web browsers dictionary to keep track of already running web browsers
WEB_BROWSERS_DICT = dict.fromkeys(WEB_BROWSERS, False)


def main():
    workspaces = utils.get_workspaces()
    for workspace in workspaces:
        Workspace(workspace)

    # Finally, make sure to reload to fix any graphical errors (specifically with firefox)
    # But first wait until all programs are loaded
    time.sleep(7)
    subprocess.run(["i3-msg", "restart"])


class Workspace:
    def __init__(self, properties):
        self.name = properties["name"]
        self.containers = []
        self.load_containers()
        self.restore()

    def load_containers(self):
        try:
            with open(f"{i3_PATH}/workspace_{self.name}_programs.json", "r") as file:
                containers = json.load(file)

            for container in containers:
                self.containers.append(Container(container))
        except FileNotFoundError:
            # No programs were running on this workspace when saved
            pass

    def restore(self):
        # First, focus on the workspace
        subprocess.run(["i3-msg", f"workspace --no-auto-back-and-forth {self.name}"])

        # Then, restore each container
        for container in self.containers:
            container.restore()

            # Move focus to next workspace (everything is saved in order so it can be restored in order like this)
            subprocess.run(["i3-msg", "focus next"])

            # Make sure i3 has processed all commands and everything is restored exactly how it was
            time.sleep(0.2)


class Container:
    def __init__(self, properties):
        self.command = properties["command"]
        self.working_directory = properties["working_directory"]

    def restore(self):
        command = " ".join(self.command)

        # First, handle web browsers
        for web_browser in WEB_BROWSERS_DICT:
            if web_browser in command:
                # The web browser has already been called, so don't execute it again
                # Browsers restore all tabs in one go, even multiple windows
                if WEB_BROWSERS_DICT.get(web_browser):
                    return

                WEB_BROWSERS_DICT[web_browser] = True

        # Then, handle any programs that run as subprocesses
        for program in SUBPROCESS_PROGRAMS:
            if program["name"] == self.command[0]:
                command = self.handle_subprocesses(program)

        subprocess.run(["i3-msg", f"exec cd \"{self.working_directory}\" && {command}"])

    def handle_subprocesses(self, subprocess):
        # First, replace all spaces in args with backslashes because the process doesn't save backslashes
        for i, arg in enumerate(self.command[1:], start=1):
            self.command[i] = arg.replace(" ", "\ ")

        command = " ".join(self.command)
        full_command = subprocess["launch_command"].replace("{command}", command) # Replace placeholder with actual command

        return full_command


if __name__ == "__main__":
    main()
