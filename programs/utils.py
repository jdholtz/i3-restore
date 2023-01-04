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

    logging.basicConfig(filename=log_file, filemode="a", level=logging.DEBUG, format="")
    logger = logging.getLogger()

    # Print error messages to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.ERROR)
    logger.addHandler(handler)

    return logger
