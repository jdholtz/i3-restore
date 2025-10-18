load "bats-assert/load"
load "bats-file/load"
load "bats-support/load"

LOGS_FILE="$(dirname "$(dirname "$(dirname "$BATS_TEST_FILENAME")")")/utils/logs.bash"
VERSION="1.2.3"

setup() {
    # Create the logs file first as sourcing the logs file will initialize the log
    TEST_DIR="$(temp_make)"
    export LOG_DIR="$TEST_DIR/logs"
    export I3_RESTORE_LOG_FILE="$LOG_DIR/test_i3_restore.log"
    export I3_RESTORE_LOG_FILE_OLD="$LOG_DIR/test_i3_restore_old.log"
    export LOG_FILE_SIZE=5

    # shellcheck disable=SC2329
    version() {
        echo "$VERSION"
    }

    # Load the functions that will be tested
    # shellcheck disable=SC1090
    source "$LOGS_FILE"
}

teardown() {
    temp_del "$TEST_DIR"
}

@test "init_log: sets up logs correctly" {
    # This should already be called as init_log is called when sourced, but we'll call it again just
    # in case
    run init_log
    assert_success

    assert_file_exist "$I3_RESTORE_LOG_FILE"
}

@test "rotate_log: does not rotate if log is small" {
    printf "line\n%.0s" {1..3} >"$I3_RESTORE_LOG_FILE"
    run rotate_log
    assert_success
    assert_file_exist "$I3_RESTORE_LOG_FILE"
    assert_file_not_exist "$I3_RESTORE_LOG_FILE_OLD"
}

@test "rotate_log: rotates log if line count exceeds limit" {
    printf "line\n%.0s" {1..10} >"$I3_RESTORE_LOG_FILE"
    run rotate_log
    assert_success
    assert_file_not_exist "$I3_RESTORE_LOG_FILE"
    assert_file_exist "$I3_RESTORE_LOG_FILE_OLD"
}

@test "log: writes message to log file" {
    log "test message"
    assert_file_exist "$I3_RESTORE_LOG_FILE"

    run cat "$I3_RESTORE_LOG_FILE"
    assert_line --partial "test message"
}

@test "log: echoes message to stderr in verbose mode" {
    export I3_RESTORE_VERBOSE=1
    run log "visible message"
    # Make sure the message is printed to stderr
    assert_output "visible message"

    # Make sure the message is also logged
    assert_file_exist "$I3_RESTORE_LOG_FILE"
    run cat "$I3_RESTORE_LOG_FILE"
    assert_line --partial "visible message"
}
