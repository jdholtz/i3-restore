LOG_DIR="$(dirname "${0}")/logs"
I3_RESTORE_LOG_FILE="${LOG_DIR}/i3-restore.log"

# Trap all errors. Uses the filename to identify which part of the script was run
trap 'error "An unknown error occured. Run ${0##*/} manually to see the error" 1' ERR

# Displays an error using i3-nagbar
# First argument is the error message
# Second argument (optional) is to add a button to view logs (has to be 1)
error() {
    # Add arguments
    local args=()
    args+=( '-m' "i3-restore: ${1}")
    args+=( '-t error')
    [[ "${2}" == 1 ]] && args+=( '-b' "View Logs" "i3-sensible-editor ${I3_RESTORE_LOG_FILE}" )

    i3-nagbar "${args[@]}" >/dev/null 2>&1
}
