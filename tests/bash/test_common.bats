#!/usr/bin/env bats

load "bats-assert/load"
load "bats-file/load"
load "bats-support/load"

COMMON_FILE="$(dirname "$(dirname "$(dirname "$BATS_TEST_FILENAME")")")/utils/common.bash"
VERSION="1.2.3"

setup() {
    # Set up the root directory
    ROOT_DIR="$(temp_make)"
    echo "$VERSION" >"$ROOT_DIR/VERSION"

    # Load the functions that will be tested
    # shellcheck disable=SC1090
    source "$COMMON_FILE"
}

teardown() {
    temp_del "$ROOT_DIR"
}

# Default mocks for the check_dependencies function
check_dependencies_mocks() {
    error() { echo "ERROR: $*"; }

    command() {
        # Only override the parameters we are using in check_dependencies
        if [[ $1 == "-v" && ($2 == "jq" || $2 == "xdotool") ]]; then
            return 0
        fi

        builtin command "$@"
    }

    # shellcheck disable=SC2329
    i3-save-tree() { echo "valid tree"; }
}

@test "version: includes the correct version" {
    run version
    assert_success
    assert_output --partial "$VERSION"
}

@test "usage: prints usage for i3-restore" {
    run usage i3-restore
    assert_success
    assert_output --partial "i3-restore [options]"
    assert_output --partial "--save-interval"
}

@test "usage: prints usage for i3-save" {
    run usage i3-save
    assert_success
    assert_output --partial "i3-save [options]"
    refute_output --partial "--save-interval"
}

@test "parse_flags: help flags trigger usage" {
    # shellcheck disable=SC2329
    usage() { echo "USAGE_CALLED"; }

    run parse_flags --help
    assert_success
    assert_output --partial "USAGE_CALLED"

    run parse_flags -h
    assert_success
    assert_output --partial "USAGE_CALLED"
}

@test "parse_flags: version flags trigger version" {
    version() { echo "VERSION_CALLED"; }

    run parse_flags --version
    assert_success
    assert_output --partial "VERSION_CALLED"

    run parse_flags -V
    assert_success
    assert_output --partial "VERSION_CALLED"
}

@test "parse_flags: verbosity flags set the verbosity level" {
    parse_flags -v
    assert_equal "$I3_RESTORE_VERBOSE" 1

    # Override to not execute 'set -x' as we can't use bats run command because we need to read the
    # variable
    set() { :; }

    parse_flags -vv
    assert_equal "$I3_RESTORE_VERBOSE" 2
}

@test "parse_flags: save interval sets the interval" {
    parse_flags --save-interval 10
    assert_equal "$I3_RESTORE_INTERVAL" 1
    assert_equal "$I3_RESTORE_INTERVAL_MINUTES" 10
}

@test "parse_flags: unknown flag triggers error" {
    usage() { echo "USAGE_CALLED"; }

    run parse_flags --unknown
    assert_failure
    assert_output --partial "Error"
    assert_output --partial "--unknown"
    assert_output --partial "USAGE_CALLED"
}

@test "check_dependencies: all installed" {
    check_dependencies_mocks

    run check_dependencies
    assert_success
}

@test "check_dependencies: missing jq triggers error" {
    check_dependencies_mocks

    # shellcheck disable=SC2329
    command() {
        # Only override the parameters we are using in check_dependencies
        if [[ $1 == "-v" ]]; then
            if [[ $2 == "jq" ]]; then
                return 1
            else
                return 0
            fi
        fi

        builtin command "$@"
    }

    run check_dependencies
    assert_failure
    assert_output --partial "ERROR"
    assert_output --partial "jq"
}

@test "check_dependencies: missing xdotool triggers error" {
    check_dependencies_mocks

    # shellcheck disable=SC2329
    command() {
        # Only override the parameters we are using in check_dependencies
        if [[ $1 == "-v" ]]; then
            if [[ $2 == "xdotool" ]]; then
                return 1
            else
                return 0
            fi
        fi

        builtin command "$@"
    }

    run check_dependencies
    assert_failure
    assert_output --partial "ERROR"
    assert_output --partial "xdotool"
}

@test "check_dependencies: missing perl-anyevent-i3 triggers error" {
    check_dependencies_mocks
    i3-save-tree() { echo "Can't locate AnyEvent/I3.pm..."; }

    run check_dependencies
    assert_failure
    assert_output --partial "ERROR"
    assert_output --partial "perl-anyevent-i3"
}
