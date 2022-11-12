#!/bin/bash

set -e
IFS=$'\n\t'

CURR_DIR=$(dirname "${0}")
I3_RESTORE_SAVE_FILE="${CURR_DIR}/programs/i3-save.py"

# Import common variables and functions
source "${CURR_DIR}/utils/common.sh"

# Handle errors
source "${CURR_DIR}/utils/error_handling.sh"

check_version_flag "$@"
check_dependencies

# Start logger
source "${CURR_DIR}/utils/logs.sh"
rotate_log

get_workspaces() {
    ALLWORKSPACES=$(i3-msg -t get_workspaces)
    workspaces=$(echo "${ALLWORKSPACES}" | jq -r '.[] | .name') # Match only the workspaces' names
    echo "${workspaces}"
}

save_workspace_layout() {
    workspace=${1}

    log "Saving layout for Workspace ${workspace}"
    # Replace slash in workspace name as file names cannot have slashes
    sanitized_ws_name=${ws//\//\{slash\}}

    file_name=${i3_PATH}/workspace_${sanitized_ws_name}_layout.json
    workspace_tree=$(i3-save-tree --workspace "${workspace}")

    # If workspace is empty (i.e doesn't contain any actual configuration lines)
    if [[ ! $workspace_tree == *"{"* ]]; then
        log "Empty layout for Workspace ${workspace}. Skipping..."
        return
    fi

    echo "$workspace_tree" > "$file_name"

    # Automatically edit the file
    sed -i 's|^\(\s*\)// "|\1"|g; /^\s*\/\//d' "$file_name"
}

save_workspace_layouts() {
    workspaces=$(get_workspaces)

    # Remove previous saved session. --force is used so it doesn't exit if a file isn't found
    rm --force "${i3_PATH}"/*_layout.json
    rm --force "${i3_PATH}"/*_programs.sh

    for ws in ${workspaces}; do
        save_workspace_layout ${ws}
    done
}

save_workspace_programs() {
    python "${I3_RESTORE_SAVE_FILE}" || error "An error occured saving the session's programs. View the logs for more details" 1
}

log "Saving current i3wm session"
save_workspace_layouts
save_workspace_programs
log "Finished saving current i3wm session"
