#!/bin/bash

set -e
IFS=$'\n\t'
CURR_DIR=$(dirname "${0}")

# Import common variables and functions
source "${CURR_DIR}/utils/common.sh"

# Handle errors
source "${CURR_DIR}/utils/error_handling.sh"

check_version_flag "$@"

# Start logger
source "${CURR_DIR}/utils/logs.sh"

restore_programs() {
    workspace_name=${1}

    # Sanitize the workspace name so it matches the file name
    sanitized_ws_name=${workspace_name// /\{space\}}
    sanitized_ws_name=${sanitized_ws_name//\//\{slash\}}
    file="${i3_PATH}/workspace_${sanitized_ws_name}_programs.sh"

    if [[ ! -f "${file}" ]]; then
        log "No programs file found for Workspace ${workspace_name}"
        return 0
    fi

    log "Restoring programs for Workspace ${workspace_name}"

    # Focus on the workspace. It should already be foucsed
    # from appending the layout, but this is here as a safety
    i3-msg "workspace --no-auto-back-and-forth ${workspace_name}"

    # Make the file executable
    chmod +x "${file}"

    # The number of containers are needed for the script to select
    # which command it wants to execute for every container
    num_containers=$(wc -l < "${file}")
    log "Number of containers: ${num_containers}"
    for (( i=0; i<num_containers; i++ )); do
        # Execute the command in the script pertaining to 'i'
        i3-msg exec ${file} $i

        # The script needs a little time to execute, otherwise the programs
        # won't get restored in the correct place
        sleep 0.2

        # Focus on the next container in the workspace.
        i3-msg focus next
    done
}

restore_workspace() {
    workspace_name=${1}

    # Unsanitize the workspace name
    workspace_name=${workspace_name//\{slash\}/\/}

    log "Restoring layout for Workspace ${workspace_name}"

    # Append the layout of every saved workspace
    i3-msg "workspace --no-auto-back-and-forth ${workspace_name}; append_layout ${i3_PATH}/${file}" > /dev/null

    restore_programs ${workspace_name}
}

kill_empty_containers() {
    containers=$(i3-msg -t get_tree | jq '.nodes[]')

    # Recursively get all containers that still have swallow criteria (meaning
    # they never got populated) and kill them
    while [ -n "${containers}" ]; do
        empty_containers=$(echo "${containers}" | jq 'select(( .swallows == [] | not ) and ( .type == "con" )) .window')

        if [[ -n "${empty_containers}" ]]; then
            num_containers=$(echo ${empty_containers} | wc -w)
            # Kill all containers with 'xkill' using their window IDs
            log "Killing ${num_containers} empty containers"
            echo "${empty_containers}" | xargs -d " " -I % xkill -id %
        fi

        containers=$(echo "${containers}" | jq '.nodes[]')
    done
}

restore_workspaces() {
    FILES=$(ls ${i3_PATH} | grep "_layout.json")

    for file in ${FILES}; do
        # Get workspace name from file name
        workspace_name=${file#*_}
        workspace_name=${workspace_name%_*}

        restore_workspace ${workspace_name}
    done

    # Wait for the programs to load and the layout windows to get swallowed
    sleep 2

    # Clean up any leftover containers that didn't get swallowed
    kill_empty_containers

    # Reload i3 to fix any graphical errors (specifically with firefox)
    log "Restarting session to fix graphical errors"
    i3-msg restart
}

log "Restoring current i3wm session"
restore_workspaces
log "Finished restoring current i3wm session\n"
