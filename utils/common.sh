# Functions and variables shared between both scripts

LOG_DIR="$(dirname "${0}")/logs"
I3_RESTORE_LOG_FILE="${LOG_DIR}/i3-restore.log"
LOG_FILE_OLD="i3-restore-old.log"
LOG_FILE_SIZE=1000

# Set default if not configured
i3_PATH="${i3_PATH:=${HOME}/.config/i3}"

check_version_flag() {
    # This doesn't work perfectly, but it still works when it needs to
    # One example where it wouldn't work is if a flag --versionf was passed,
    # it would still print the version.
    if [[ ! "${@#--version}" = "$@" || ! "${@#-v}" = "$@" ]]; then
        version=$(cat VERSION)
        echo "i3-restore version ${version}"
        exit
    fi
}

check_dependencies() {
    # Check if jq is installed
    if ! command -v jq >/dev/null 2>&1; then
        error "jq is required for i3-restore!"
        exit
    fi

    # Check for perl-anyevent-i3 by seeing if i3-save-tree fails
    if [[ $(i3-save-tree 2>&1) == "Can't locate AnyEvent/I3.pm"* ]]; then
        error "perl-anyevent-i3 is required for i3-restore!"
        exit
    fi
}
