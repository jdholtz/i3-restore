#!/usr/bin/env bats

load "bats-assert/load"
load "bats-file/load"
load "bats-support/load"

AUTO_SAVING_FILE="$(dirname "$(dirname "$(dirname "$BATS_TEST_FILENAME")")")/utils/automatic_saving.bash"

setup() {
    # Load the functions that will be tested
    # shellcheck disable=SC1090
    source "$AUTO_SAVING_FILE"

    # Don't log output by default
    # shellcheck disable=SC2317
    log() { :; }
}

@test "get_sleep_time: valid integer input returns correct seconds" {
    run get_sleep_time 5
    assert_success
    assert_output "300"
}

@test "get_sleep_time: zero input returns default time in seconds" {
    run get_sleep_time 0
    assert_success
    assert_output "$((DEFAULT_INTERVAL_TIME * 60))"
}

@test "get_sleep_time: non-numeric input returns default time in seconds" {
    run get_sleep_time abc
    assert_success
    assert_output "$((DEFAULT_INTERVAL_TIME * 60))"
}

@test "check_i3_alive: i3 process alive" {
    # shellcheck disable=SC2317
    ps() {
        # Only override the parameters we are using in check_dependencies
        if [[ $1 == "--pid" ]] && [[ $2 == 123 ]]; then
            echo "PID TTY          TIME CMD"
            echo "100 tty1     00:00:01 i3"
        else
            command ps "$@"
        fi
    }

    # We need to inspect log output to see if the function behaves correctly
    # shellcheck disable=SC2317
    log() {
        echo "LOG: $*"
    }

    run check_i3_alive 123

    assert_success
    # Even on failure, the function succeeds, so we need to check the output
    refute_output --partial "Original i3 process is not alive anymore"
}

@test "check_i3_alive: i3 process dead exits with 0" {
    # shellcheck disable=SC2317
    ps() {
        if [[ $1 == "--pid" ]] && [[ $2 == 123 ]]; then
            echo "PID TTY          TIME CMD"
        else
            command ps "$@"
        fi
    }

    # We need to inspect log output to see if the function behaves correctly
    # shellcheck disable=SC2317
    log() {
        echo "LOG: $*"
    }

    run check_i3_alive 123

    # Exits with 0 even if the i3 process is not found
    assert_success
    assert_output --partial "Original i3 process is not alive anymore"
}

@test "start_save_interval: saves the session on an interval until the i3 process is dead" {
    export I3_RESTORE_INTERVAL_MINUTES=1

    TEST_DIR="$(temp_make)"

    # Make the mock 'i3-save' script so we can ensure it is called
    cat >"$I3_RESTORE_SAVE_FILE" <<EOF
#!/usr/bin/env bash
echo "save called" >> $TEST_DIR/test-i3-save.log
EOF
    chmod +x "$I3_RESTORE_SAVE_FILE"

    # Set up all the mock functions

    get_sleep_time() {
        if [[ $1 -ne $I3_RESTORE_INTERVAL_MINUTES ]]; then
            echo "Unexpected interval in get_sleep_time: $1"
            exit 1
        fi

        echo "$((I3_RESTORE_INTERVAL_MINUTES * 60))"
    }

    pidof() {
        if [[ $1 == "i3" ]]; then
            echo 1234
        else
            command pidof "$@"
        fi
    }

    local call_count=0
    check_i3_alive() {
        if [[ $1 -ne 1234 ]]; then
            echo "Unexpected PID in check_i3_alive: $1"
            exit 1
        fi

        # Exit after 3 calls
        [[ $call_count -ge 3 ]] && exit 0

        ((call_count++))
    }

    # Simulate sleep and command execution
    sleep() {
        if [[ $1 -ne "$((I3_RESTORE_INTERVAL_MINUTES * 60))" ]]; then
            echo "Unexpected sleep time in sleep: $1"
            exit 1
        fi
    }

    run start_save_interval
    assert_success

    # Make sure the save script was called the expected number of times
    assert_equal "$(wc -l <"$TEST_DIR/test-i3-save.log")" 3

    # This is a readonly variable, so we can't set it. We just have to remove it when it is done. This
    # file is at libexec/bats-core/i3-save
    rm -f "$I3_RESTORE_SAVE_FILE"
    temp_del "$TEST_DIR"
}
