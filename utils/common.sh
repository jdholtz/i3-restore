# Contains all functions that are used in both the
# i3-save and i3-restore scripts.

LOG_DIR="$(dirname "${0}")/logs"
I3_RESTORE_LOG_FILE="${LOG_DIR}/i3-restore.log"
LOG_FILE_OLD="i3-restore-old.log"
LOG_FILE_SIZE=1000

# Set default if not configured
i3_PATH="${i3_PATH:=${HOME}/.config/i3}"

#####################################
# Display the script's version if it was
# passed as a flag. It doesn't work perfectly,
# (i.e --versionf would still print the version)
# but it is sufficient enough.
# Arguments:
#   All arguments passed into either script
#####################################
check_version_flag() {
    if [[ ! "${@#--version}" = "$@" || ! "${@#-v}" = "$@" ]]; then
        version="$(cat VERSION)"
        echo "i3-restore version ${version}"
        exit
    fi
}

#####################################
# Ensure the script's dependencies are installed.
#####################################
check_dependencies() {
    local deps=("jq" "xdotool")
    for dep in "${deps[@]}"; do
        if ! command -v "${dep}" >/dev/null 2>&1; then
            error "${dep} is required for i3-restore!"
            exit
        fi
    done

    # Check for perl-anyevent-i3 by seeing if i3-save-tree fails
    if [[ "$(i3-save-tree 2>&1)" == "Can't locate AnyEvent/I3.pm"* ]]; then
        error "perl-anyevent-i3 is required for i3-restore!"
        exit
    fi
}
