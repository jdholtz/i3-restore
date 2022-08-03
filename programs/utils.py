import json
import subprocess


def get_workspaces():
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


def get_tree():
    tree = subprocess.check_output(["i3-msg", "-t", "get_tree"]).decode("utf-8")
    return json.loads(tree)
