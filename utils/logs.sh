LOG_DIR="logs"
LOG_FILE="${LOG_DIR}/i3-restore.log"
LOG_FILE_OLD="i3-restore-old.log"
LOG_FILE_SIZE=1000

init_log() {
    # Create the directory and/or file if they don't exist
    mkdir -p "${LOG_DIR}"
    touch "${LOG_FILE}"
}

rotate_log() {
    # Rotate current log to old log file (removing the old log file)
    # Saving old logs will make it easier to debug sessions without
    # the potential of them being erased
    local current_log_size=$(< "${LOG_FILE}" wc -l)
    if [[ "${current_log_size}" -gt "${LOG_FILE_SIZE}" ]]; then
        cp "${LOG_FILE}" "${LOG_DIR}/${LOG_FILE_OLD}"
        rm "${LOG_FILE}"
    fi
}

log() {
    echo -e $1 >> "${LOG_FILE}"
}

init_log
