#!/usr/bin/env bats

load "bats-assert/load"
load "bats-file/load"
load "bats-support/load"

PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$BATS_TEST_FILENAME")")")"

setup() {
    TEST_DIR="$(temp_make)"
}

teardown() {
    temp_del "$TEST_DIR"
}

@test "save_session: publishes timestamped snapshots and prunes old snapshots" {
    local save_script="$PROJECT_ROOT/i3-save"
    local save_path="$TEST_DIR/session-state"

    run bash -s -- "$save_script" "$save_path" <<'EOF'
set -euo pipefail
save_script="$1"
save_path="$2"
i3_PATH="$save_path"
ROOT_DIR="$(dirname "$save_script")"
source "$save_script"
trap - ERR
save_workspace_layouts() {
    echo "layout" >"$I3_RESTORE_SAVE_PATH/layout"
}
save_workspace_programs() {
    echo "programs" >"$I3_RESTORE_SAVE_PATH/programs"
}
I3_RESTORE_SNAPSHOT_HISTORY=2
date() { echo "$MOCK_DATE"; }
MOCK_DATE=20260903-220000
save_session
MOCK_DATE=20260903-221000
save_session
MOCK_DATE=20260903-222000
save_session
EOF

    assert_success
    assert_dir_exists "$save_path/snapshots/20260903-221000"
    assert_dir_exists "$save_path/snapshots/20260903-222000"
    assert_dir_not_exists "$save_path/snapshots/20260903-220000"
    assert_file_exists "$save_path/snapshots/20260903-222000/layout"
    assert_file_exists "$save_path/snapshots/20260903-222000/programs"
}

@test "save_session: only publishes a snapshot after saving succeeds" {
    local save_script="$PROJECT_ROOT/i3-save"
    local save_path="$TEST_DIR/session-state"

    run bash -s -- "$save_script" "$save_path" <<'EOF'
set -euo pipefail
save_script="$1"
save_path="$2"
i3_PATH="$save_path"
ROOT_DIR="$(dirname "$save_script")"
source "$save_script"
trap - ERR
save_workspace_layouts() {
    echo "layout" >"$I3_RESTORE_SAVE_PATH/layout"
}
save_workspace_programs() {
    return 1
}
I3_RESTORE_SNAPSHOT_HISTORY=2
date() { echo "20260903-220000"; }
save_session
EOF

    assert_failure
    assert_dir_not_exists "$save_path/snapshots/20260903-220000"
    run find "$save_path/snapshots" -mindepth 1 -maxdepth 1 -type d
    assert_output ""
}

@test "select_snapshot: selects the latest timestamped snapshot" {
    local restore_script="$PROJECT_ROOT/i3-restore"
    local session_path="$TEST_DIR/session-state"
    mkdir -p "$session_path/snapshots/20260903-220000"
    mkdir -p "$session_path/snapshots/20260903-221000"

    run bash -s -- "$restore_script" "$session_path" <<'EOF'
set -euo pipefail
restore_script="$1"
i3_PATH="$2"
ROOT_DIR="$(dirname "$restore_script")"
source "$restore_script"
trap - ERR
log() { :; }
I3_RESTORE_SNAPSHOT_NAME=latest
select_snapshot
printf '%s\n' "$i3_PATH"
EOF

    assert_success
    assert_output "$session_path/snapshots/20260903-221000"
}

@test "select_snapshot: fails clearly for a missing snapshot" {
    local restore_script="$PROJECT_ROOT/i3-restore"
    local session_path="$TEST_DIR/session-state"
    run bash -s -- "$restore_script" "$session_path" <<'EOF'
set -euo pipefail
restore_script="$1"
i3_PATH="$2"
ROOT_DIR="$(dirname "$restore_script")"
source "$restore_script"
trap - ERR
error() { echo "$1"; return 1; }
I3_RESTORE_SNAPSHOT_NAME=missing
select_snapshot
EOF

    assert_failure
    assert_output --partial "Snapshot not found: missing"
}
