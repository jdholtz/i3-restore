# Contains useful functions for logging within the script.
# Functions can only be called after common.sh is sourced.

#####################################
# Initialize the log file
# Globals:
#   I3_RESTORE_LOG_FILE
#   LOG_DIR
#####################################
init_log() {
    # Create the directory and/or file if they don't exist
    mkdir -p "$LOG_DIR"
    touch "$I3_RESTORE_LOG_FILE"

    # Add the version to the log whenever it's initialized
    log "$(version)"
}

#####################################
# Rotate the current log to the old log
# (remove the old log file). Saving old
# logs makes it easier to debug sessions
# without the potential of them being erased.
# Globals:
#   I3_RESTORE_LOG_FILE
#   LOG_DIR
#   LOG_FILE_OLD
#   LOG_FILE_SIZE
#####################################
rotate_log() {
    local current_log_size
    current_log_size="$(wc <"$I3_RESTORE_LOG_FILE" --lines)"
    if [[ $current_log_size -gt $LOG_FILE_SIZE ]]; then
        cp "$I3_RESTORE_LOG_FILE" "$LOG_DIR/$LOG_FILE_OLD"
        rm "$I3_RESTORE_LOG_FILE"
    fi
}

#####################################
# Log a message into the log file
# Arguments:
#   The log message
# Globals:
#   I3_RESTORE_LOG_FILE
#   I3_RESORE_VERBOSE
#####################################
log() {
    local time
    time="$(date +"%F %T")"

    echo -e "$time: $1" >>"$I3_RESTORE_LOG_FILE"
    # Only log the message to stdout (not the time), if running in verbose mode
    [[ $I3_RESTORE_VERBOSE -ge 1 ]] && echo -e "$1" >&2 || return 0
}

init_log
