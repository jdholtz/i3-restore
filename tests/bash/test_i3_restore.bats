#!/usr/bin/env bats

load "bats-assert/load"
load "bats-file/load"
load "bats-support/load"

PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$BATS_TEST_FILENAME")")")"
I3_RESTORE_SOURCE="$PROJECT_ROOT/i3-restore"
I3_TREE_FILE="$PROJECT_ROOT/tests/bash/test_data/i3_tree.json"

# Regex patterns to use for matching i3-msg calls
MOVE_WORKSPACE_REGEX="^workspace .+;\s* move workspace to output .+$"
APPEND_LAYOUT_REGEX="^workspace .+;\s* append_layout .+$"

setup() {
    TEST_DIR="$(temp_make)"

    i3_PATH="$TEST_DIR/i3_restore_path"
    mkdir -p "$i3_PATH"

    local new_i3_restore="$TEST_DIR/i3-restore"
    cp "$I3_RESTORE_SOURCE" "$new_i3_restore"
    chmod +x "$new_i3_restore"
    ln -s "$PROJECT_ROOT/utils" "$TEST_DIR/utils"
    cp "$PROJECT_ROOT/VERSION" "$TEST_DIR/VERSION"

    # Set ROOT_DIR so that the script can find its utils
    # shellcheck disable=SC1090
    ROOT_DIR=$TEST_DIR source "$new_i3_restore"

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
        while [[ $1 == "--quiet" ]]; do
            # Ignore the --quiet flag for easier parsing
            shift
        done

        if [[ $1 == "--type" && $2 == "get_tree" ]]; then
            cat "$I3_TREE_FILE"
        elif [[ $1 =~ ^workspace ]]; then
            # Ignore calls to focus on a workspace
            return 0
        elif [[ $1 =~ [[:space:]]unmark[[:space:]] ]]; then
            # Ignore calls to unmark windows
            return 0
        elif [[ $1 == "restart" ]]; then
            # Ignore calls to restart i3
            return 0
        else
            echo "Unexpected i3-msg call: $*"
            return 1
        fi
    }

    sleep() {
        return 0
    }
}

create_restore_programs_files() {
    local workspace_name="$1"
    workspace_name_sanitized="${workspace_name// /\{space\}}"
    local programs_file="$i3_PATH/workspace_${workspace_name_sanitized}_programs.sh"
    local subprocess_0="$i3_PATH/workspace_${workspace_name_sanitized}_subprocess_0.sh"
    local subprocess_1="$i3_PATH/workspace_${workspace_name_sanitized}_subprocess_1.sh"

    cat <<EOF >"$programs_file"
command0
command1
EOF
    touch "$subprocess_0"
    touch "$subprocess_1"
}

check_restore_programs_files() {
    local workspace_name="$1"
    workspace_name_sanitized="${workspace_name// /\{space\}}"
    local programs_file="$i3_PATH/workspace_${workspace_name_sanitized}_programs.sh"
    local subprocess_0="$i3_PATH/workspace_${workspace_name_sanitized}_subprocess_0.sh"
    local subprocess_1="$i3_PATH/workspace_${workspace_name_sanitized}_subprocess_1.sh"

    assert_file_executable "$programs_file"
    assert_file_executable "$subprocess_0"
    assert_file_executable "$subprocess_1"
}

# Mock i3-msg for restore_programs tests. The arguments are a file to track the number of calls that
# started programs (the number of lines in the file) and the expected programs file scripts that are
# called to start programs.
mock_i3_msg_restore_programs() {
    # Use a file to track the number of program calls so it is accessible in the test scope (during
    # the test the variables are only modified in a subshell)
    program_calls_file="$1"
    touch "$program_calls_file"
    shift

    programs_files="$*"

    # Save the original i3-msg function (the global mock) so we can call it in our mock
    eval "$(declare -f i3-msg | sed 's/^i3-msg/restore_programs_i3-msg/')"

    # shellcheck disable=SC2329
    i3-msg() {
        if [[ $1 == "--quiet" && $2 == "exec" ]]; then
            local container_num file num_program_calls workspace_name

            file="$3"
            container_num="$4"
            # Match any of the programs files we expect
            if ! grep -Fxq -- "$file" <<<"$programs_files"; then
                echo "Unexpected i3-msg exec call: $*"
                return 1
            fi

            # Extract the workspace name from the programs file path
            workspace_name="$(basename "$file")"
            workspace_name="${workspace_name#*_}"
            workspace_name="${workspace_name%_*}"
            workspace_name="${workspace_name%_*}"
            workspace_name="${workspace_name//\{space\}/ }"

            # Correlate the container number only with the workspace name (to handle multiple workspaces)
            num_program_calls=$(grep -c "^$workspace_name" "$program_calls_file")
            if [[ $container_num != "$num_program_calls" ]]; then
                echo "Expected container number $num_program_calls, got $container_num"
                return 1
            fi

            echo "$workspace_name" >>"$program_calls_file"
            return 0
        fi

        # Call the original i3-msg mock
        restore_programs_i3-msg "$@"
    }
}

# Mock i3-msg for restore_layout tests. The arguments are variable names to count the calls to
# the move workspace and append layout commands were called, respectively.
mock_i3_msg_restore_layout() {
    local move_workspace_calls="$1" append_layout_calls="$2"

    # Save the original i3-msg function (the global mock) so we can call it in our mock
    eval "$(declare -f i3-msg | sed 's/^i3-msg/restore_layout_i3-msg/')"

    # shellcheck disable=SC2329
    i3-msg() {
        if [[ $1 =~ $MOVE_WORKSPACE_REGEX ]]; then
            ((move_workspace_calls++)) || true
            return 0
        elif [[ $1 =~ $APPEND_LAYOUT_REGEX ]]; then
            ((append_layout_calls++)) || true
            return 0
        fi

        # Call the original i3-msg mock
        restore_layout_i3-msg "$@"
    }
}

# Create an i3-msg script mock for kill_empty_containers tests. The deleted container IDs
# are logged to the provided file. The PATH is modified to use this mock for i3-msg calls.
create_i3_msg_script_mock() {
    local deleted_containers_log="$1"

    # Save the original i3-msg function (the global mock) so we can call it in our mock
    eval "$(declare -f i3-msg | sed 's/^i3-msg/original_i3-msg/')"

    local test_bin="$TEST_DIR/bin"
    mkdir -p "$test_bin"
    PATH="$test_bin:$PATH"

    cat >"$test_bin/i3-msg" <<EOF
#!/bin/bash
if [[ \$2 == "kill" ]]; then
    container_id="\$1"
    container_id="\${container_id#*=}"  # Remove [id= prefix
    container_id="\${container_id%]}"   # Remove trailing ]
    echo "\$container_id" >> "$deleted_containers_log"
    exit 0
fi

# Call the original i3-msg mock
original_i3-msg "$@"
EOF
    chmod +x "$test_bin/i3-msg"
}

# Mock i3-msg for restore_browsers tests. The arguments are the expected browsers file and a variable name
# to track if i3-msg was called to execute the browsers file.
mock_i3_msg_exec_browsers() {
    local browsers_file="$1" i3_msg_called="$2"

    # Save the original i3-msg function (the global mock) so we can call it in our mock
    eval "$(declare -f i3-msg | sed 's/^i3-msg/exec_browsers_i3-msg/')"

    # shellcheck disable=SC2329
    i3-msg() {
        if [[ $1 == "exec" && $2 == "$browsers_file" ]]; then
            i3_msg_called=1
            return 0
        fi

        # Call the original i3-msg mock
        exec_browsers_i3-msg "$@"
    }
}

@test "get_window_ids_on_workspace: handles no windows gracefully" {
    run get_window_ids_on_workspace "nonexistent_workspace"
    assert_success
    assert_output ""
}

@test "get_window_ids_on_workspace: gets window IDs on workspace" {
    run get_window_ids_on_workspace "Workspace 1"
    assert_success
    assert_output $'101\n102\n201\n202'
}

@test "restore_programs: handles no programs file gracefully" {
    run restore_programs "nonexistent_workspace"
    assert_success
    assert_output ""
}

@test "restore_programs: restores programs and subprocesses" {
    # Test two containers are started for each of the two programs, and that the subprocess scripts
    # are executable (the subprocess scripts are called in the programs file, so we don't test
    # their restoration here)

    local workspace_name="Workspace 1"
    local programs_file="$i3_PATH/workspace_Workspace{space}1_programs.sh"

    create_restore_programs_files "$workspace_name"

    local program_calls_file="$TEST_DIR/program_calls.log"
    mock_i3_msg_restore_programs "$program_calls_file" "$programs_file"

    run restore_programs "$workspace_name"

    assert_success
    check_restore_programs_files "$workspace_name"

    # Ensure both programs were started
    assert_equal "$(wc --lines <"$program_calls_file")" 2

    # Ensure the correct window IDs were returned (the 2 newly started programs)
    assert_output $'101\n102\n201\n202'
}

@test "unmap_windows: unmaps each provided window" {
    local window_ids=$'10\n11\n12'

    xdotool_unmap_ids=()
    # shellcheck disable=SC2329
    xdotool() {
        if [[ $1 != "windowunmap" ]]; then
            echo "Unexpected xdotool call: $*"
            return 1
        fi

        xdotool_unmap_ids+=("$2")
        return 0
    }

    unmap_windows "$window_ids"

    local status=$?
    [[ $status -eq 0 ]] || fail "Expected success, got $status"

    # Convert the IDs collected back to a newline-separated string for comparison
    assert_equal "$(printf '%s\n' "${xdotool_unmap_ids[@]}")" "$window_ids"
}

@test "map_windows: maps each provided window" {
    local window_ids=$'10\n11\n12'

    xdotool_map_ids=()
    # shellcheck disable=SC2329
    xdotool() {
        if [[ $1 != "windowmap" ]]; then
            echo "Unexpected xdotool call: $*"
            return 1
        fi

        xdotool_map_ids+=("$2")
        return 0
    }

    map_windows "$window_ids"

    local status=$?
    [[ $status -eq 0 ]] || fail "Expected success, got $status"

    # Convert the IDs collected back to a newline-separated string for comparison
    assert_equal "$(printf '%s\n' "${xdotool_map_ids[@]}")" "$window_ids"
}

@test "restore_layout: moves workspace then appends layout" {
    local workspace_name="ws1"
    local display="HDMI-1"
    local layout_file="$i3_PATH/workspace_${workspace_name}_${display}_layout.json"

    local move_workspace_calls=0
    local append_layout_calls=0
    mock_i3_msg_restore_layout move_workspace_calls append_layout_calls

    # shellcheck disable=SC2218
    restore_layout "$layout_file" "$workspace_name" "$display"

    local status=$?
    [[ $status -eq 0 ]] || fail "Expected success, got $status"

    assert_equal "$move_workspace_calls" 1
    assert_equal "$append_layout_calls" 1
}

@test "restore_workspace: restores programs, layout, and remaps windows" {
    local workspace_name="Workspace 1"
    local display="HDMI-1"
    local layout_file="$i3_PATH/workspace_Workspace 1_${display}_layout.json"
    local programs_file="$i3_PATH/workspace_Workspace{space}1_programs.sh"

    create_restore_programs_files "$workspace_name"

    # Mock the underlying xdotool calls to unmap and map the windows
    local xdotool_unmap_calls=0
    local xdotool_map_calls=0
    # shellcheck disable=SC2329
    xdotool() {
        if [[ $1 == "windowunmap" ]]; then
            echo "$2"
            ((xdotool_unmap_calls++)) || true
        elif [[ $1 == "windowmap" ]]; then
            echo "$2"
            ((xdotool_map_calls++)) || true
        else
            echo "Unexpected xdotool call: $*"
            return 1
        fi
    }

    # Mock the underlying i3-msg calls for restoring the layout
    local move_workspace_calls=0
    local append_layout_calls=0
    mock_i3_msg_restore_layout move_workspace_calls append_layout_calls

    # Mock the underlying i3-msg calls for restoring the programs
    local program_calls_file="$TEST_DIR/program_calls.log"
    mock_i3_msg_restore_programs "$program_calls_file" "$programs_file"

    restore_workspace "$layout_file"

    local status=$?
    [[ $status -eq 0 ]] || fail "Expected success, got $status"

    check_restore_programs_files "$workspace_name"
    # Ensure the programs were started
    assert_equal "$(wc --lines <"$program_calls_file")" 2

    # Ensure the expected underlying calls were made
    assert_equal "$xdotool_unmap_calls" 4
    assert_equal "$xdotool_map_calls" 4
    assert_equal "$move_workspace_calls" 1
    assert_equal "$append_layout_calls" 1
}

@test "kill_empty_containers: recursively kills empty containers" {
    local deleted_containers_log="$TEST_DIR/deleted_containers.log"
    create_i3_msg_script_mock "$deleted_containers_log"

    run kill_empty_containers

    assert_success
    assert_equal "$(cat "$deleted_containers_log")" $'203\n201\n202'
}

@test "restore_browsers: does nothing when there are no browsers to restore" {
    assert_file_not_exists "$i3_PATH/web_browsers.sh"

    local i3_msg_called=0
    mock_i3_msg_exec_browsers "$i3_PATH/web_browsers.sh" i3_msg_called

    restore_browsers

    local status=$?
    [[ $status -eq 0 ]] || fail "Expected success, got $status"

    assert_equal "$i3_msg_called" 0
}

@test "restore_browsers: restores browsers from web_browsers.sh" {
    local browsers_file="$i3_PATH/web_browsers.sh"
    touch "$browsers_file"

    local i3_msg_called=0
    mock_i3_msg_exec_browsers "$browsers_file" i3_msg_called

    restore_browsers

    local status=$?
    [[ $status -eq 0 ]] || fail "Expected success, got $status"

    assert_equal "$i3_msg_called" 1
}

@test "restore_workspaces: restores workspace layouts, programs, and browsers and cleans up" {
    local workspace_names=("Workspace 1" "Workspace 2")
    local display="HDMI-1"
    local programs_files=()

    for workspace_name in "${workspace_names[@]}"; do
        create_restore_programs_files "$workspace_name"
        programs_files+=("$i3_PATH/workspace_${workspace_name// /\{space\}}_programs.sh")
        touch "$i3_PATH/workspace_${workspace_name}_${display}_layout.json"
    done

    local browsers_file="$i3_PATH/web_browsers.sh"
    touch "$browsers_file"

    local deleted_containers_log="$TEST_DIR/deleted_containers.log"
    create_i3_msg_script_mock "$deleted_containers_log"

    # Mock the underlying xdotool calls to unmap and map the windows
    local xdotool_unmap_calls=0
    local xdotool_map_calls=0
    xdotool() {
        if [[ $1 == "windowunmap" ]]; then
            echo "$2"
            ((xdotool_unmap_calls++)) || true
        elif [[ $1 == "windowmap" ]]; then
            echo "$2"
            ((xdotool_map_calls++)) || true
        else
            echo "Unexpected xdotool call: $*"
            return 1
        fi
    }

    # Mock the underlying i3-msg calls for restoring the layout
    local move_workspace_calls=0
    local append_layout_calls=0
    mock_i3_msg_restore_layout move_workspace_calls append_layout_calls

    # Mock the underlying i3-msg calls for restoring the programs
    local program_calls_file="$TEST_DIR/program_calls.log"
    mock_i3_msg_restore_programs "$program_calls_file" "${programs_files[*]}"

    # Mock the underlying i3-msg calls for restoring the browsers
    local i3_msg_called=0
    mock_i3_msg_exec_browsers "$browsers_file" i3_msg_called

    restore_workspaces "$display"

    local status=$?
    [[ $status -eq 0 ]] || fail "Expected success, got $status"

    for workspace_name in "${workspace_names[@]}"; do
        check_restore_programs_files "$workspace_name"
        assert_equal "$(grep -c "^$workspace_name" "$program_calls_file")" 2
    done

    # Ensure the expected underlying calls were made to restore the layouts and programs on each
    # workspace
    assert_equal "$xdotool_unmap_calls" 6 # 4 windows on Workspace 1, 2 on Workspace 2
    assert_equal "$xdotool_map_calls" 6   # 4 windows on Workspace 1, 2 on Workspace 2
    assert_equal "$move_workspace_calls" 2
    assert_equal "$append_layout_calls" 2

    # Ensure the browsers were restored
    assert_equal "$i3_msg_called" 1

    # Ensure the empty containers were killed
    assert_equal "$(cat "$deleted_containers_log")" $'203\n201\n202'
}

@test "start_automatic_saving: does nothing when interval disabled" {
    local I3_RESTORE_INTERVAL=0
    local start_save_interval_calls=0

    # shellcheck disable=SC2329
    start_save_interval() {
        ((start_save_interval_calls++)) || true
    }

    # Don't use run as we want to capture the number of calls to start_save_interval
    start_automatic_saving

    local status=$?
    [[ $status -eq 0 ]] || fail "Expected success, got $status"

    assert_equal "$start_save_interval_calls" 0
}

@test "start_automatic_saving: starts interval when enabled" {
    # shellcheck disable=SC2034
    local I3_RESTORE_INTERVAL=1
    local start_save_interval_calls=0

    # shellcheck disable=SC2329
    start_save_interval() {
        ((start_save_interval_calls++)) || true
    }

    # Don't use run as we want to capture the number of calls to start_save_interval
    start_automatic_saving

    local status=$?
    [[ $status -eq 0 ]] || fail "Expected success, got $status"

    assert_equal "$start_save_interval_calls" 1
}
