#!/bin/bash

set -e
IFS=$'\n\t'
CURR_DIR=$(dirname "${0}")

# Handle errors
source "${CURR_DIR}/utils/error_handling.sh"

# Check for the version flag in every argument
if [[ ! "${@#--version}" = "$@" || ! "${@#-v}" = "$@" ]]; then
    version=$(cat VERSION)
    echo "i3-restore version ${version}"
    exit
fi

# Start logger and import log function
source "${CURR_DIR}/utils/logs.sh"

# Set default if not configured
i3_PATH="${i3_PATH:=${HOME}/.config/i3}"

FILES=$(ls ${i3_PATH} | grep "_layout.json")

log "Restoring current i3wm session"

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

for file in ${FILES}; do
    # Get workspace name from file name
    workspace_name=${file#*_}
    workspace_name=${workspace_name%_*}

    # Unsanitize the workspace name
    workspace_name=${workspace_name//\{slash\}/\/}

    log "Restoring layout for Workspace ${workspace_name}"

    # Append the layout of every saved workspace
    i3-msg "workspace --no-auto-back-and-forth ${workspace_name}; append_layout ${i3_PATH}/${file}" > /dev/null

    restore_programs ${workspace_name}
done

# Make sure to reload to fix any graphical errors (specifically with firefox)
# But first wait until all programs are loaded
sleep 2
log "Restarting session to fix graphical errors"
i3-msg restart

log "Finished restoring current i3wm session\n"
