# Contains useful functions to display errors to the user.
# Must only be used after sourcing common.sh

# Trap all errors. Uses the filename to identify which part of the script was run
trap 'error "An unknown error occured. Run ${0##*/} manually to see the error" 1' ERR

#####################################
# Displays an error using i3-nagbar
# Arguments:
#   Error message
#   Boolean to add button to view logs (Optional)
#####################################
error() {
    # Add arguments
    local args=()
    args+=( "-m" "i3-restore: ${1}")
    args+=( "-t error")

    if [[ -n "${2}" ]]; then
        args+=( "-b" "View Logs" "i3-sensible-editor ${I3_RESTORE_LOG_FILE}" )
        args+=( "-b" "Run Manually" "${0}" )
    fi

    i3-nagbar "${args[@]}" >/dev/null 2>&1
}
