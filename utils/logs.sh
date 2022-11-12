# Functions can only be called after common.sh is sourced

init_log() {
    # Create the directory and/or file if they don't exist
    mkdir -p "${LOG_DIR}"
    touch "${I3_RESTORE_LOG_FILE}"
}

rotate_log() {
    # Rotate current log to old log file (removing the old log file)
    # Saving old logs will make it easier to debug sessions without
    # the potential of them being erased
    local current_log_size=$(< "${I3_RESTORE_LOG_FILE}" wc -l)
    if [[ "${current_log_size}" -gt "${LOG_FILE_SIZE}" ]]; then
        cp "${I3_RESTORE_LOG_FILE}" "${LOG_DIR}/${LOG_FILE_OLD}"
        rm "${I3_RESTORE_LOG_FILE}"
    fi
}

log() {
    echo -e $1 >> "${I3_RESTORE_LOG_FILE}"
}

init_log
