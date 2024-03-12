# Contains all functions that are used in both the
# i3-save and i3-restore scripts.

LOG_DIR="${CURR_DIR}/logs"
I3_RESTORE_LOG_FILE="${LOG_DIR}/i3-restore.log"
LOG_FILE_OLD="i3-restore-old.log"
LOG_FILE_SIZE=1000

I3_RESTORE_VERBOSE=0
I3_RESTORE_INTERVAL=0

# shellcheck disable=SC2034
readonly LOG_DIR I3_RESTORE_LOG_FILE LOG_FILE_OLD LOG_FILE_SIZE

# Set default if not configured
i3_PATH="${i3_PATH:=${HOME}/.config/i3}"
readonly i3_PATH

#####################################
# Display the script's version
#####################################
version() {
    version="$(cat "${CURR_DIR}/VERSION")"
    echo "i3-restore v${version}"
}

#####################################
# Display the script's usage
#####################################
usage() {
    local cmd="${0##*/}"
    version
    echo
    echo "Usage:"
    if [[ "$(basename "$cmd")" == "i3-save" ]]; then
        echo "    ${cmd} [options]      Save your current i3 session"
    else
        echo "    ${cmd} [options]      Restore your last saved i3 session"
    fi
    echo
    echo "Options:"

    if [[ "$(basename "$cmd")" == "i3-restore" ]]; then
        echo "    --interval <minutes>   Automatically save your session on an interval (default is 10 minutes)"
    fi

    echo "    -v, -vv                Increase the verbosity of the script. One v prints debug messages and"
    echo "                           two v's print all commands executed too"
    echo "    -h, --help             Display this help and exit"
    echo "    -V, --version          Display version information and exit"
    echo
    echo "For more information, check out https://github.com/jdholtz/i3-restore#readme"
}

#####################################
# Parse all the flags passed through the command
# line.
# Arguments:
#   All arguments passed into either script
#####################################
parse_flags() {
    while [[ $# != 0 ]]; do
        case "$1" in
        --help | -h)
            usage
            exit
            ;;
        --version | -V)
            version
            exit
            ;;
        -v)
            I3_RESTORE_VERBOSE=1
            ;;
        -vv)
            # shellcheck disable=SC2034
            I3_RESTORE_VERBOSE=2
            set -x # Print all commands executed
            ;;
        --interval)
            # shellcheck disable=SC2034
            I3_RESTORE_INTERVAL=1
            # shellcheck disable=SC2034
            I3_RESTORE_INTERVAL_MINUTES="${2}"
            ;;
        esac
        shift
    done
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
