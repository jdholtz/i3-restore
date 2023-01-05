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
    mkdir -p "${LOG_DIR}"
    touch "${I3_RESTORE_LOG_FILE}"
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
    current_log_size="$(wc <"${I3_RESTORE_LOG_FILE}" --lines)"
    if [[ ${current_log_size} -gt ${LOG_FILE_SIZE} ]]; then
        cp "${I3_RESTORE_LOG_FILE}" "${LOG_DIR}/${LOG_FILE_OLD}"
        rm "${I3_RESTORE_LOG_FILE}"
    fi
}

#####################################
# Log a message into the log file
# Arguments:
#   The log message
# Globals:
#   I3_RESTORE_LOG_FILE
#####################################
log() {
    echo -e "${1}" >>"${I3_RESTORE_LOG_FILE}"
}

init_log
