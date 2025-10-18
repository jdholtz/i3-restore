#!/usr/bin/env bats

load "bats-assert/load"
load "bats-file/load"
load "bats-support/load"

PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$BATS_TEST_FILENAME")")")"
I3_SAVE_SOURCE="$PROJECT_ROOT/i3-save"

# The JSON tree layout that the mocked i3-save-tree will return
I3_SAVE_TREE_LAYOUT='{
    "name": "test",
    "swallows": [
       {
       // "class": "^test_class$",
       // "instance": "^test_instance$",
       // "machine": "^test_machine$",
       // "title": "^\\test$"
       }
    ],
    "type": "con"
}'

# The JSON of the workspaces that the mocked i3-msg will return
I3_MSG_WORKSPACES='[
    {"name":"1: ws1","output":"HDMI-1"},
    {"name":"2 - ws2","output":"DP-1"},
    {"name":"3","output":"DP-1"}
]'

setup() {
    TEST_DIR="$(temp_make)"

    i3_PATH="$TEST_DIR/i3_save_path"
    mkdir -p "$i3_PATH"

    # Mirror the minimal directory structure the script expects for sourcing
    local new_i3_save="$TEST_DIR/i3-save"
    cp "$I3_SAVE_SOURCE" "$new_i3_save"
    chmod +x "$TEST_DIR/i3-save"
    ln -s "$PROJECT_ROOT/utils" "$TEST_DIR/utils"
    cp "$PROJECT_ROOT/VERSION" "$TEST_DIR/VERSION"
    mkdir -p "$TEST_DIR/programs"
    : >"$TEST_DIR/programs/i3_save.py"

    # Load the functions that will be tested. Set ROOT_DIR so that the script can find its utils
    # shellcheck disable=SC1090
    ROOT_DIR=$TEST_DIR source "$new_i3_save"

    # Remove the trap set in the script so we don't actually call i3-msg and exit
    trap - ERR

    create_mocks
}

teardown() {
    temp_del "$TEST_DIR"
}

# shellcheck disable=SC2329
create_mocks() {
    i3-msg() {
        if [[ $1 == "--type" && $2 == "get_workspaces" ]]; then
            echo "$I3_MSG_WORKSPACES"
        elif [[ $1 == "--quiet" ]] && { [[ $2 =~ ^mark || $2 =~ ^unmark ]]; }; then
            # Ignore mark/unmark calls
            return 0
        else
            echo "Unexpected i3-msg call: $*"
            return 1
        fi
    }

    i3-save-tree() {
        if [[ $1 == "--workspace" ]]; then
            echo "$I3_SAVE_TREE_LAYOUT"
        else
            echo "Unexpected i3-save-tree call: $*"
            return 1
        fi
    }
}

# Create session files that should be removed when removing the previous session
create_session() {
    touch "$i3_PATH/workspace_old_layout.json"
    touch "$i3_PATH/old_programs.sh"
    touch "$i3_PATH/old_subprocess_3.sh"
    touch "$i3_PATH/web_browsers.sh"
    touch "$i3_PATH/kitty-session-1"
    touch "$i3_PATH/kitty-scrollback-1-1"
}

# Asserts that all previous session files created in `create_session` have been removed
assert_previous_session_removed() {
    assert_file_not_exists "$i3_PATH/workspace_old_layout.json"
    assert_file_not_exists "$i3_PATH/old_programs.sh"
    assert_file_not_exists "$i3_PATH/old_subprocess_3.sh"
    assert_file_not_exists "$i3_PATH/web_browsers.sh"
    assert_file_not_exists "$i3_PATH/kitty-session-1"
    assert_file_not_exists "$i3_PATH/kitty-scrollback-1-1"
}

@test "get_workspaces: retrieves workspace names and the display they are on" {
    run get_workspaces

    assert_success
    assert_output $'1: ws1\nHDMI-1\n2 - ws2\nDP-1\n3\nDP-1'
}

@test "remove_previous_session: deletes the previous session files" {
    create_session
    run remove_previous_session

    assert_success
    assert_previous_session_removed
}

@test "save_workspace_layout: saves layout for a given workspace" {
    local workspace_name="test/ws"
    local output_name="HDMI-1"
    run save_workspace_layout "$workspace_name" "$output_name"

    assert_success

    # We expect the file to be sanitized as the workspace name contains a slash
    expected_file="$i3_PATH/workspace_test{slash}ws_${output_name}_layout.json"
    assert_file_exists "$expected_file"

    # Verify that the swallows have been uncommented
    run cat "$expected_file"
    assert_success
    assert_output --partial '       {
       "class": "^test_class$",
       "instance": "^test_instance$",
       "machine": "^test_machine$",
       "title": "^\\test$"
       }'
}

@test "save_workspace_layout: skips saving empty workspace layouts" {
    local i3_save_three_no_layout="// vim:ts=4:sw=4:et"

    # shellcheck disable=SC2329
    i3-save-tree() {
        if [[ $1 == "--workspace" ]]; then
            echo "$i3_save_three_no_layout"
        else
            echo "Unexpected i3-save-tree call: $*"
            return 1
        fi
    }

    local workspace_name="empty_ws"
    local output_name="DP-1"

    run save_workspace_layout "$workspace_name" "$output_name"

    assert_success

    # The old layout file that should not be created
    assert_file_not_exists "$i3_PATH/workspace_empty_ws_DP-1_layout.json"
}

@test "save_workspace_layouts: removes previous session and saves each workspace" {
    create_session

    local expected_layout_1="$i3_PATH/workspace_1: ws1_HDMI-1_layout.json"
    local expected_layout_2="$i3_PATH/workspace_2 - ws2_DP-1_layout.json"
    local expected_layout_3="$i3_PATH/workspace_3_DP-1_layout.json"

    run save_workspace_layouts
    assert_success

    assert_previous_session_removed
    assert_file_exists "$expected_layout_1"
    assert_file_exists "$expected_layout_2"
    assert_file_exists "$expected_layout_3"
}

@test "save_workspace_programs: runs python save script" {
    # shellcheck disable=SC2329
    python3() { return 0; }

    run save_workspace_programs
    assert_success
}

@test "save_workspace_programs: failure triggers error" {
    python3() { return 1; }

    error() { return 0; }

    run save_workspace_programs
    # Should still succeed as error() succeeds
    assert_success
}
