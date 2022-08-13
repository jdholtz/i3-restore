#!/bin/bash

set -e
IFS=$'\n\t'

# Check for the version flag in every argument
if [[ ! "${@#--version}" = "$@" || ! "${@#-v}" = "$@" ]]; then
    version=$(cat VERSION)
    echo "i3-restore version ${version}"
    exit
fi

# Set default if not configured
i3_PATH="${i3_PATH:=${HOME}/.config/i3}"

FILES=$(ls ${i3_PATH} | grep "_layout.json")

for file in ${FILES}; do
	# Get workspace name from file name
	workspace_name=${file#*_}
	workspace_name=${workspace_name%_*}

	# Unsanitize the workspace name
	workspace_name=${workspace_name//\{slash\}/\/}

	# Append the layout of every saved workspace
	i3-msg "workspace --no-auto-back-and-forth ${workspace_name}; append_layout ${i3_PATH}/${file}" > /dev/null
done

# Now run the python script to restore the programs in the containers
DIR=$(dirname $0)
python $DIR/programs/i3-restore.py
