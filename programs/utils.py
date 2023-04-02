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


def get_logger() -> logging.RootLogger:
    project_dir = os.path.dirname(os.path.dirname(__file__))
    log_file = os.getenv("I3_RESTORE_LOG_FILE", f"{project_dir}/{DEFAULT_LOG_FILE}")

    logger = logging.getLogger("i3-restore")
    logger.handlers = []  # Ensure there are no handlers before adding our own
    logger.setLevel(logging.DEBUG)  # The minimum level for all handlers

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter("")
    file_handler.setLevel(logging.DEBUG)

    # Print error messages to stdout
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter("")
    stream_handler.setLevel(logging.ERROR)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
