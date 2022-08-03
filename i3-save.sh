#!/bin/bash

set -e
IFS=$'\n\t'

# Check if user has jq installed
if ! command -v jq >/dev/null 2>&1; then
	echo "jq is required for i3-restore!"
	exit
fi

# Check for perl-anyevent-i3 by seeing if i3-save-tree fails
if [[ $(i3-save-tree 2>&1) == "Can't locate AnyEvent/I3.pm"* ]]; then
	echo "perl-anyevent-i3 is required for i3-restore!"
	exit
fi

# Set default if not configured
i3_PATH="${i3_PATH:=${HOME}/.config/i3}"

ALLWORKSPACES=$(i3-msg -t get_workspaces)
workspaces=$(echo "${ALLWORKSPACES}" | jq -r '.[] | .name') # Match only the workspaces' names

# Remove previous saved session. -f is there so it doesn't exit if rm fails (file isn't found)
rm -f "${i3_PATH}"/*.json

for ws in ${workspaces}; do
    filename=${i3_PATH}/workspace_${ws}_layout.json
    workspace_tree=$(i3-save-tree --workspace "${ws}")

    # If workspace is empty (i.e doesn't contain any actual configuration lines)
    if [[ ! $workspace_tree == *"{"* ]]; then
        continue
    fi

    echo "$workspace_tree" > "$filename"

	# Automatically edit the file
    sed -i 's|^\(\s*\)// "|\1"|g; /^\s*\/\//d' "$filename"
done

DIR=$(dirname "${0}")
python "${DIR}"/programs/i3-save.py

# Execute command passed as an argument. For use with the i3 config file and so it can be manually executed
# without exiting out of the session
"$@"
