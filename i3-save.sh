#!/bin/bash

set -e
IFS=$'\n\t'

# Check for the version flag in every argument
if [[ ! "${@#--version}" = "$@" || ! "${@#-v}" = "$@" ]]; then
    version=$(cat VERSION)
    echo "i3-restore version ${version}"
    exit
fi

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

# Start logger and import log function
source utils/logs.sh
rotate_log

# Set default if not configured
i3_PATH="${i3_PATH:=${HOME}/.config/i3}"

ALLWORKSPACES=$(i3-msg -t get_workspaces)
workspaces=$(echo "${ALLWORKSPACES}" | jq -r '.[] | .name') # Match only the workspaces' names

# Remove previous saved session. -f is there so it doesn't exit if rm fails (file isn't found)
rm -f "${i3_PATH}"/*.json

log "Saving current i3wm session"

for ws in ${workspaces}; do
    log "Saving layout for Workspace ${ws}"
    # Replace slash in workspace name as file names cannot have slashes
    sanitized_ws_name=${ws//\//\{slash\}}

    file_name=${i3_PATH}/workspace_${sanitized_ws_name}_layout.json
    workspace_tree=$(i3-save-tree --workspace "${ws}")

    # If workspace is empty (i.e doesn't contain any actual configuration lines)
    if [[ ! $workspace_tree == *"{"* ]]; then
        log "Empty layout for Workspace ${ws}. Skipping..."
        continue
    fi

    echo "$workspace_tree" > "$file_name"

    # Automatically edit the file
    sed -i 's|^\(\s*\)// "|\1"|g; /^\s*\/\//d' "$file_name"
done

DIR=$(dirname "${0}")
python "${DIR}"/programs/i3-save.py

log "Finished saving current i3wm session"

# Execute commands passed as an argument. For use with the i3 config file and so it can be manually executed
# without exiting out of the session
[ "$@" ] && log "Executing arguments as a command: $@" # Only log if arguments are passed in
"$@"
