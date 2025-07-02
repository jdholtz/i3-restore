# Contains all functions that are used in both the
# i3-save and i3-restore scripts.

LOG_DIR="$ROOT_DIR/logs"
I3_RESTORE_LOG_FILE="$LOG_DIR/i3-restore.log"
I3_RESTORE_LOG_FILE_OLD="$LOG_DIR/i3-restore-old.log"
LOG_FILE_SIZE=1000

I3_RESTORE_VERBOSE=0
I3_RESTORE_INTERVAL=0

# shellcheck disable=SC2034
readonly LOG_DIR I3_RESTORE_LOG_FILE I3_RESTORE_LOG_FILE_OLD LOG_FILE_SIZE

# Set default if not configured
i3_PATH="${i3_PATH:=$HOME/.config/i3}"
readonly i3_PATH

#####################################
# Display the script's version
#####################################
version() {
    local version
    version="$(cat "$ROOT_DIR/VERSION")"
    echo "i3-restore v$version"
}

#####################################
# Display the script's usage
#####################################
usage() {
    local cmd="$1" spaces
    version
    echo
    echo "Usage:"
    if [[ "$(basename "$cmd")" == "i3-save" ]]; then
        spaces=""
        echo "    i3-save [options]   Save your current i3 session"
    else
        # More spaces should be added for the restore usage screen to line up all of the
        # descriptions for the flags
        spaces="        "
        echo "    i3-restore [options]        Restore your last saved i3 session"
    fi
    echo
    echo "Options:"

    if [[ "$(basename "$cmd")" == "i3-restore" ]]; then
        echo "    --save-interval <minutes>   Automatically save your session on an interval (default is 10 minutes)"
    fi

    echo "    -v, -vv            $spaces Increase the verbosity of the script. One v prints debug messages and"
    echo "                       $spaces two v's print all commands executed too"
    echo "    -h, --help         $spaces Display this help and exit"
    echo "    -V, --version      $spaces Display version information and exit"
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
            local cmd="${0##*/}"
            usage "$cmd"
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
        --save-interval)
            # shellcheck disable=SC2034
            I3_RESTORE_INTERVAL=1

            # Only set the interval minutes if it matches a nonnegative integer
            I3_RESTORE_INTERVAL_MINUTES=0
            if [[ $# -ge 2 ]] && [[ $2 =~ ^[0-9]+$ ]]; then
                # shellcheck disable=SC2034
                I3_RESTORE_INTERVAL_MINUTES=$2
                shift
            fi
            ;;
        -*)
            echo "Error: Unrecognized flag: $1"
            echo
            local cmd="${0##*/}"
            usage "$cmd"
            exit 2
            ;;
        esac
        shift
    done
}

#####################################
# Ensure the script's dependencies are installed.
#####################################
check_dependencies() {
    local deps dep

    deps=("jq" "xdotool")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            error "$dep is required for i3-restore!"
            exit 1
        fi
    done

    # Check for perl-anyevent-i3 by seeing if i3-save-tree fails
    if [[ "$(i3-save-tree 2>&1)" == "Can't locate AnyEvent/I3.pm"* ]]; then
        error "perl-anyevent-i3 is required for i3-restore!"
        exit 1
    fi
}
