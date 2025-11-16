#!/usr/bin/env bats

load "bats-assert/load"
load "bats-file/load"
load "bats-support/load"

ERROR_HANDLING_FILE="$(dirname "$(dirname "$(dirname "$BATS_TEST_FILENAME")")")/utils/error_handling.bash"

setup() {
    # Load the functions that will be tested
    # shellcheck disable=SC1090
    source "$ERROR_HANDLING_FILE"
}

@test "error: calls i3-nagbar" {
    i3-nagbar() {
        # Just validate there are arguments passed in
        [[ -n $* ]]
    }

    run error "Test error message"
    assert_success
}
