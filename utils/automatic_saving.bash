# Automatically save i3 layouts + programs on an interval
# Functions can only be called after common.sh is sourced.

I3_RESTORE_SAVE_FILE="$(dirname "${0}")/i3-save"
DEFAULT_INTERVAL_TIME=10

#####################################
# Get the sleep time (in seconds) from the
# argument. If the argument is not a number,
# the default time will be returned
# Globals:
#   DEFAULT_INTERVAL_TIME
# Arguments:
#   sleep time, in minutes
# Returns:
#   the sleep time in seconds
#####################################
get_sleep_time() {
    local sleep_time="${1}"

    if ! [[ ${sleep_time} =~ ^[0-9]+$ ]]; then
        message="Sleep time not passed in (or is invalid). Using "
        message+="default time of ${DEFAULT_INTERVAL_TIME} minutes"
        log "${message}"
        sleep_time="${DEFAULT_INTERVAL_TIME}"
    fi

    # Convert sleep time to seconds
    sleep_time=$((sleep_time * 60))
    echo "${sleep_time}"
}

#####################################
# Ensure the same i3 process that
# automatic saving was started with
# is still running. Otherwise, i3-msg
# will fail to connect even when a new
# i3 process is started.
# Arguments:
#   Original i3 PID
#####################################
check_i3_alive() {
    if ! ps -p "${1}" | grep "i3"; then
        message="Original i3 process is not alive anymore. "
        message+="Exiting automatic scheduling"
        log "${message}"
        exit 0
    fi
}

#####################################
# Save the current i3wm session automatically
# on an interval.
# Globals:
#   I3_RESTORE_SAVE_FILE
# Arguments:
#   interval time, in minutes
#####################################
start_save_interval() {
    sleep_time="$(get_sleep_time "${1}")"
    i3_pid="$(pidof i3)"

    log "Starting automatic saving on an interval of ${sleep_time} seconds"
    while true; do
        sleep "${sleep_time}"
        check_i3_alive "${i3_pid}"
        echo "Automatically saving current i3wm session"
        "${I3_RESTORE_SAVE_FILE}"
    done
}
