import json
import logging
import os
import subprocess
import sys
from typing import Any, Dict, List

DEFAULT_LOG_FILE = "logs/i3-restore.log"

# Type alias for JSON
JSON = Dict[str, Any]


def get_workspaces() -> List[JSON]:
    """
    Retrieve a list of all workspaces currently active along with their
    trees that contain all the containers on each workspace.
    """
    all_workspaces = []

    tree = get_tree()

    # Remove the first output as it is not wanted
    outputs = tree["nodes"][1:]

    for output in outputs:
        dockareas = output["nodes"]
        for dockarea in dockareas:
            if dockarea["type"] == "con":
                workspaces = dockarea["nodes"]
                for workspace in workspaces:
                    all_workspaces.append(workspace)

    return all_workspaces


def get_tree() -> JSON:
    """Get the current active i3 tree"""
    tree = subprocess.check_output(["i3-msg", "-t", "get_tree"]).decode("utf-8")
    return json.loads(tree)


# Custom logging formatter to add prefixes to debug messages
class Formatter(logging.Formatter):  # pragma: no cover
    FORMATS = {logging.DEBUG: "+ %(message)s"}

    def format(self, record):
        log_format = self.FORMATS.get(record.levelno, "")
        formatter = logging.Formatter(log_format)
        return formatter.format(record)


def get_logger() -> logging.RootLogger:
    project_dir = os.path.dirname(os.path.dirname(__file__))
    log_file = os.getenv("I3_RESTORE_LOG_FILE", f"{project_dir}/{DEFAULT_LOG_FILE}")

    logger = logging.getLogger("i3-restore")
    logger.handlers = []  # Ensure there are no handlers before adding our own
    logger.setLevel(logging.DEBUG)  # The minimum level for all handlers

    formatter = logging.Formatter("%(asctime)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Print error messages to stdout
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(Formatter())

    # Set verbosity level based on flags initialized through the command line
    log_level = logging.ERROR
    verbose_level = os.getenv("I3_RESTORE_VERBOSE")
    if verbose_level == "1":
        log_level = logging.INFO
    elif verbose_level == "2":
        log_level = logging.DEBUG

    stream_handler.setLevel(log_level)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger


# Custom exception for when a plugin fails to save a container.
class PluginSaveError(Exception):
    pass
