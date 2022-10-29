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

for file in ${FILES}; do
	# Get workspace name from file name
	workspace_name=${file#*_}
	workspace_name=${workspace_name%_*}

	# Unsanitize the workspace name
	workspace_name=${workspace_name//\{slash\}/\/}

    log "Restoring layout for Workspace ${file}"

	# Append the layout of every saved workspace
	i3-msg "workspace --no-auto-back-and-forth ${workspace_name}; append_layout ${i3_PATH}/${file}" > /dev/null
done

# Now run the python script to restore the programs in the containers
error_message=$(python "${CURR_DIR}/programs/i3-restore.py")
[[ ! -z "${error_message}" ]] && error "An error occured restoring the session's programs. View the logs for more details" 1

log "Finished restoring current i3wm session\n"
