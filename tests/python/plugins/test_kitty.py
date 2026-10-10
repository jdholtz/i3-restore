import json
import subprocess
from unittest import mock

import pytest
from pytest_mock import MockerFixture

with mock.patch("utils.get_logger"):
    # Don't log messages to a file
    from programs.plugins import kitty

    with mock.patch("config.Config._read_config", return_value={}):
        # Don't read the config file
        from programs.i3_save import Container

# Overwrite for testing so it is deterministic
kitty.utils.i3_PATH = "/tmp/i3-restore-test"

TEST_PLUGIN_CONFIG = {
    "listen_socket": "test-socket",
    "scrollback": "all",
    "alternate_scrollback_subprocesses": [],
}

KITTY_CONTAINER_TREE = [
    {
        "platform_window_id": 9999,
        "tabs": [
            {
                "is_active": True,
                "layout": "fat",
                "windows": [
                    {
                        "env": {
                            "SHELL": "/bin/bash",
                        },
                        "cwd": "/home/test",
                        "id": 1,
                        "pid": 1,
                        "title": "Codex | 123e4567-e89b-12d3-a456-42661...",
                    }
                ],
            },
            {
                "is_active": False,
                "layout": "tall",
                "windows": [
                    {
                        "env": {},
                        "cwd": "/home",
                        "id": 2,
                        "pid": 2,
                    },
                    {
                        "env": {},
                        "cwd": "/",
                        "id": 3,
                        "pid": 2,
                    },
                ],
            },
        ],
    }
]

# The expected saved session for Kitty versions before 0.43.0
KITTY_CONTAINER_SESSION_OLD = """new_tab
layout fat
focus
launch --cwd="/home/test" /bin/bash -c 'cat "/tmp/i3-restore-test/kitty-scrollback-9999-1" && subprocess'
new_tab
layout tall
launch --cwd="/home" bash -c 'cat "/tmp/i3-restore-test/kitty-scrollback-9999-2" && bash'
launch --cwd="/" bash -c 'cat "/tmp/i3-restore-test/kitty-scrollback-9999-3" && bash'
"""  # noqa: E501

# The saved session returned directly by Kitty's @ ls (for versions 0.43.0 and newer)
KITTY_CONTAINER_SESSION_NEW_ORIGINAL = """
new_tab
layout fat
launch 'kitty-unserialize-data={"id": 1}' subprocess
focus

new_tab
layout tall
launch 'kitty-unserialize-data={"id": 2}'
launch 'kitty-unserialize-data={"id": 3}' --env SHELL=/bin/bash
focus

focus_tab 0
"""

# The expected saved session for Kitty versions 0.43.0 and newer
KITTY_CONTAINER_SESSION_NEW = """
new_tab
layout fat
launch 'kitty-unserialize-data={"id": 1}' --cwd="/home/test" /bin/bash -c 'cat "/tmp/i3-restore-test/kitty-scrollback-9999-1" && subprocess'
focus

new_tab
layout tall
launch 'kitty-unserialize-data={"id": 2}' --cwd="/home" bash -c 'cat "/tmp/i3-restore-test/kitty-scrollback-9999-2" && bash'
launch 'kitty-unserialize-data={"id": 3}' --cwd="/" bash -c 'cat "/tmp/i3-restore-test/kitty-scrollback-9999-3" && bash'
focus

focus_tab 0
"""  # noqa: E501

KITTY_CONTAINER_SESSION_MULTIPLE_OS_WINDOWS = """
new_tab
layout fat
launch 'kitty-unserialize-data={"id": 3}'
focus

focus_tab 0


new_os_window

new_tab
layout fat
launch 'kitty-unserialize-data={"id": 1}'
focus

focus_tab 0
"""


@pytest.fixture(autouse=True)
def container(mocker: MockerFixture) -> Container:
    mocker.patch.object(kitty, "KITTY_VERSION", (0, 48, 0))
    mocker.patch.object(Container, "_get_pid")
    mocker.patch.object(Container, "_get_cmdline_options")
    return Container({"window_properties": {}, "window": 9999})


@pytest.mark.parametrize(
    ("version_line", "expected_version"),
    [
        ("kitty 0.42.2 created by Kovid Goyal", (0, 42, 2)),
        ("kitty 0.48.0 created by Kovid Goyal", (0, 48, 0)),
        ("kitty 0.48.0.1 created by Kovid Goyal", (0, 48, 0)),
    ],
)
def test_get_kitty_version_returns_parsed_version(
    version_line: str, expected_version: tuple[int, int, int], mocker: MockerFixture
) -> None:
    mocker.patch("subprocess.check_output", return_value=version_line.encode("utf-8"))
    assert kitty.get_kitty_version() == expected_version


def test_get_kitty_version_returns_old_version_on_error(mocker: MockerFixture) -> None:
    mocker.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(None, None))
    assert kitty.get_kitty_version() == (0, 0, 0)


@pytest.mark.parametrize(
    "version_line",
    [
        "kitty abc created by Kovid Goyal",
        "kitty a.b.c created by Kovid Goyal",
        "0.43.0",
    ],
)
def test_get_kitty_version_returns_old_version_on_bad_version(
    version_line: str, mocker: MockerFixture
) -> None:
    mocker.patch("subprocess.check_output", return_value=version_line.encode("utf-8"))
    assert kitty.get_kitty_version() == (0, 0, 0)


def test_get_listen_socket_default_format() -> None:
    expected_listen_socket = "test-123"
    assert kitty.get_listen_socket("test", 123) == expected_listen_socket


def test_get_listen_socket_with_placeholder() -> None:
    expected_listen_socket = "test_123123_123"
    assert (
        kitty.get_listen_socket("test_{kitty_pid}{kitty_pid}_{kitty_pid}", 123)
        == expected_listen_socket
    )


def test_get_container_tree_retrieves_container_tree(mocker: MockerFixture) -> None:
    mocker.patch("subprocess.check_output", return_value=b'{"container_tree": {}}')
    assert kitty.get_container_tree("test-socket") == {"container_tree": {}}


def test_get_container_raises_plugin_save_error_when_command_fails(mocker: MockerFixture) -> None:
    mocker.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(None, None))
    with pytest.raises(kitty.utils.PluginSaveError):
        kitty.get_container_tree("test-socket")


def test_save_scrollback_skips_with_none_scrollback_config() -> None:
    plugin_config = TEST_PLUGIN_CONFIG | {"scrollback": "none"}
    assert kitty.save_scrollback(0, 0, plugin_config) is None


def test_save_scrollback_handles_failed_command(mocker: MockerFixture) -> None:
    mocker.patch("subprocess.check_call", side_effect=subprocess.CalledProcessError(None, None))
    mocker.patch("pathlib.Path.open")
    assert kitty.save_scrollback(0, 0, TEST_PLUGIN_CONFIG) is None


def test_save_scrollback_saves_scrollback(mocker: MockerFixture) -> None:
    mock_check_call = mocker.patch("subprocess.check_call")
    mocker.patch("pathlib.Path.open")

    session_file = kitty.save_scrollback(11, 94, TEST_PLUGIN_CONFIG)

    assert session_file.name == "kitty-scrollback-94-11"
    assert "--extent=all" in mock_check_call.call_args.args[0]
    assert "--add-cursor" in mock_check_call.call_args.args[0]


@pytest.mark.parametrize(
    ("configured_extent", "expected_extent"),
    [("screen", "alternate"), ("all", "alternate_scrollback")],
)
def test_save_scrollback_uses_alternate_extent_when_enabled(
    configured_extent: str, expected_extent: str, mocker: MockerFixture
) -> None:
    mock_check_call = mocker.patch("subprocess.check_call")
    mocker.patch("pathlib.Path.open")
    plugin_config = TEST_PLUGIN_CONFIG | {"scrollback": configured_extent}

    kitty.save_scrollback(11, 94, plugin_config, alternate_screen=True)

    command = mock_check_call.call_args.args[0]
    assert f"--extent={expected_extent}" in command
    assert "--add-cursor" not in command


@pytest.mark.parametrize(("version", "should_wait"), [((0, 43, 0), False), ((0, 47, 0), True)])
def test_save_subprocess_scrollback_uses_legacy_launch(
    version: tuple[int, int, int], should_wait: bool, mocker: MockerFixture
) -> None:
    mocker.patch.object(kitty, "KITTY_VERSION", version)
    mock_check_call = mocker.patch("subprocess.check_call")
    kitty.save_scrollback(11, 94, TEST_PLUGIN_CONFIG, alternate_screen=True)

    command = mock_check_call.call_args.args[0]
    assert "launch" in command
    assert ("--wait-for-child-to-exit" in command) is should_wait


def test_get_window_restore_command_returns_subprocess_command(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = "subprocess"
    mock_check = mocker.patch.object(container, "check_if_subprocess")
    mock_process = mocker.patch("psutil.Process")

    window_tree = KITTY_CONTAINER_TREE[0]["tabs"][0]["windows"][0]

    assert (
        kitty.get_window_restore_command(
            container, window_tree, TEST_PLUGIN_CONFIG | {"scrollback": "none"}
        )
        == "/bin/bash -c 'subprocess'"
    )
    assert container.subprocess_command is None
    mock_check.assert_called_once_with(
        mock_process.return_value,
        "{command} && /bin/bash",
        "Codex | 123e4567-e89b-12d3-a456-42661...",
    )


def test_get_window_restore_command_returns_scrollback_command(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = None

    mocker.patch.object(container, "check_if_subprocess")
    mocker.patch("psutil.Process")
    mocker.patch("subprocess.check_call")
    mocker.patch("pathlib.Path.open")

    window_tree = KITTY_CONTAINER_TREE[0]["tabs"][1]["windows"][0]
    subprocess_cmd = kitty.get_window_restore_command(container, window_tree, TEST_PLUGIN_CONFIG)

    # Ensure the most important parts of the command are present
    assert "bash -c 'cat" in subprocess_cmd
    assert "kitty-scrollback-9999-2" in subprocess_cmd
    assert " && bash" in subprocess_cmd


def test_get_window_restore_command_uses_alternate_scrollback_for_configured_subprocess(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = "subprocess"

    mocker.patch.object(container, "check_if_subprocess", return_value="nvim")
    mocker.patch("psutil.Process")
    mock_check_call = mocker.patch("subprocess.check_call")
    mocker.patch("pathlib.Path.open")

    window_tree = KITTY_CONTAINER_TREE[0]["tabs"][0]["windows"][0]
    plugin_config = TEST_PLUGIN_CONFIG | {"alternate_scrollback_subprocesses": ["vim", "nvim"]}

    subprocess_cmd = kitty.get_window_restore_command(container, window_tree, plugin_config)

    assert subprocess_cmd == (
        "/bin/bash -c 'cat \"/tmp/i3-restore-test/kitty-scrollback-9999-1\" && subprocess'"
    )
    assert "--extent=alternate_scrollback" in mock_check_call.call_args.args[0]


def test_get_window_restore_command_uses_normal_scrollback_for_main_screen_subprocess(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = "subprocess"

    mocker.patch.object(container, "check_if_subprocess", return_value="codex")
    mocker.patch("psutil.Process")
    mock_check_call = mocker.patch("subprocess.check_call")
    mocker.patch("pathlib.Path.open")

    window_tree = KITTY_CONTAINER_TREE[0]["tabs"][0]["windows"][0]
    plugin_config = TEST_PLUGIN_CONFIG | {"alternate_scrollback_subprocesses": ["vim", "nvim"]}

    kitty.get_window_restore_command(container, window_tree, plugin_config)

    command = mock_check_call.call_args.args[0]
    assert "--extent=all" in command
    assert "--add-cursor" in command


def test_get_window_restore_command_returns_none_when_no_subprocess_or_scrollback(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = None
    mocker.patch.object(container, "check_if_subprocess")
    mocker.patch("psutil.Process")

    window_tree = KITTY_CONTAINER_TREE[0]["tabs"][1]["windows"][0]
    plugin_config = TEST_PLUGIN_CONFIG | {"scrollback": "none"}

    assert kitty.get_window_restore_command(container, window_tree, plugin_config) is None


def test_get_window_launch_command_returns_launch_command_without_subprocess(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = None
    mocker.patch.object(container, "check_if_subprocess")
    mocker.patch("psutil.Process")

    window_tree = KITTY_CONTAINER_TREE[0]["tabs"][0]["windows"][0]
    plugin_config = TEST_PLUGIN_CONFIG | {"scrollback": "none"}

    launch_cmd = kitty.get_window_launch_command(container, window_tree, plugin_config)

    assert "launch" in launch_cmd
    assert window_tree["cwd"] in launch_cmd


def test_parse_tree_to_session_parses_tree_into_session_correctly(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = "subprocess"

    mocker.patch.object(container, "check_if_subprocess")
    mocker.patch("psutil.Process")
    mocker.patch("subprocess.check_call")
    mocker.patch("pathlib.Path.open")

    session_output = kitty.parse_tree_to_session(
        container, KITTY_CONTAINER_TREE[0], TEST_PLUGIN_CONFIG
    )

    assert session_output == KITTY_CONTAINER_SESSION_OLD


def test_get_session_contents_retrieves_session_contents(mocker: MockerFixture) -> None:
    mocker.patch(
        "subprocess.check_output", return_value=KITTY_CONTAINER_SESSION_NEW_ORIGINAL.encode("utf-8")
    )
    assert kitty.get_session_contents("test-socket") == KITTY_CONTAINER_SESSION_NEW_ORIGINAL


def test_get_session_contents_raises_plugin_save_error_when_command_fails(
    mocker: MockerFixture,
) -> None:
    mocker.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(None, None))
    with pytest.raises(kitty.utils.PluginSaveError):
        kitty.get_session_contents("test-socket")


def test_get_launch_unserialize_data_raises_when_data_is_missing() -> None:
    with pytest.raises(ValueError, match="does not contain unserialize data"):
        kitty.get_launch_unserialize_data("launch --cwd=/home")


def test_get_new_launch_command_gets_command_from_correct_window(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = "subprocess"
    unserialize_data = f'{kitty.KITTY_UNSERIALIZE_DATA_KEY}{{"id": 1}}'
    old_launch_command = (
        f"{kitty.KITTY_LAUNCH_PREFIX}'{unserialize_data}' --env SHELL=/bin/bash vim"
    )
    window_objs = {
        1: KITTY_CONTAINER_TREE[0]["tabs"][0]["windows"][0],
        2: KITTY_CONTAINER_TREE[0]["tabs"][1]["windows"][0],
        3: KITTY_CONTAINER_TREE[0]["tabs"][1]["windows"][1],
    }

    mocker.patch.object(container, "check_if_subprocess")
    mocker.patch("psutil.Process")
    mocker.patch("subprocess.check_call")
    mocker.patch("pathlib.Path.open")

    launch_cmd = kitty.get_new_launch_command(
        container, TEST_PLUGIN_CONFIG, old_launch_command, window_objs
    )

    assert "launch" in launch_cmd
    assert unserialize_data in launch_cmd
    assert window_objs[1]["cwd"] in launch_cmd


def test_filter_session_contents_for_os_window_keeps_matching_os_window() -> None:
    os_window = {
        "tabs": [
            {
                "windows": [
                    {
                        "id": 3,
                    }
                ]
            }
        ]
    }

    session_contents = kitty.filter_session_contents_for_os_window(
        KITTY_CONTAINER_SESSION_MULTIPLE_OS_WINDOWS, os_window
    )

    assert 'kitty-unserialize-data={"id": 3}' in session_contents
    assert 'kitty-unserialize-data={"id": 1}' not in session_contents
    assert "new_os_window" not in session_contents


def test_filter_session_contents_for_os_window_raises_when_no_window_matches() -> None:
    os_window = {
        "tabs": [
            {
                "windows": [
                    {
                        "id": 1,
                    }
                ]
            }
        ]
    }
    session_contents = """new_tab
launch 'kitty-unserialize-data={\"id\": 2}'
new_os_window
new_tab
launch 'kitty-unserialize-data={\"id\": 3}'
"""

    with pytest.raises(kitty.utils.PluginSaveError):
        kitty.filter_session_contents_for_os_window(session_contents, os_window)


def test_replace_launch_commands_replaces_all_launch_commands(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = "subprocess"

    mocker.patch.object(container, "check_if_subprocess")
    mocker.patch("psutil.Process")
    mocker.patch("subprocess.check_call")
    mocker.patch("pathlib.Path.open")

    new_session_contents = kitty.replace_launch_commands(
        container, KITTY_CONTAINER_TREE[0], TEST_PLUGIN_CONFIG, KITTY_CONTAINER_SESSION_NEW_ORIGINAL
    )

    assert new_session_contents == KITTY_CONTAINER_SESSION_NEW


def test_create_session_file_gets_session_output_and_writes_to_file(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = "subprocess"

    # Test new session saving by default
    mocker.patch.object(kitty, "KITTY_VERSION", (0, 43, 0))

    mocker.patch.object(container, "check_if_subprocess")
    mocker.patch("psutil.Process")
    mocker.patch("subprocess.check_call")
    mocker.patch(
        "subprocess.check_output", return_value=KITTY_CONTAINER_SESSION_NEW_ORIGINAL.encode("utf-8")
    )
    mock_open = mocker.patch("pathlib.Path.open", new_callable=mock.mock_open)

    session_file = kitty.create_session_file(container, KITTY_CONTAINER_TREE, TEST_PLUGIN_CONFIG)

    handle = mock_open()
    assert handle.write.call_args[0][0] == KITTY_CONTAINER_SESSION_NEW, (
        "Kitty container session was not saved correctly"
    )

    assert session_file.name == "kitty-session-9999"


def test_create_session_file_gets_session_output_and_writes_to_file_old_session_saving(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = "subprocess"

    # Test old session saving
    mocker.patch.object(kitty, "KITTY_VERSION", (0, 42, 0))

    mocker.patch.object(container, "check_if_subprocess")
    mocker.patch("psutil.Process")
    mocker.patch("subprocess.check_call")
    mock_open = mocker.patch("pathlib.Path.open", new_callable=mock.mock_open)

    session_file = kitty.create_session_file(container, KITTY_CONTAINER_TREE, TEST_PLUGIN_CONFIG)

    handle = mock_open()
    assert handle.write.call_args[0][0] == KITTY_CONTAINER_SESSION_OLD, (
        "Kitty container session was not saved correctly with old session saving"
    )

    assert session_file.name == "kitty-session-9999"


def test_main_saves_a_kitty_container(mocker: MockerFixture, container: Container) -> None:
    version_output = b"kitty 0.44.0 created by Kovid Goyal"
    container.subprocess_command = "subprocess"
    mocker.patch.object(kitty, "KITTY_VERSION", None)

    mocker.patch.object(container, "check_if_subprocess")
    mocker.patch("psutil.Process")
    mocker.patch("pathlib.Path.open")

    kitty_tree_command_output = json.dumps(KITTY_CONTAINER_TREE).encode("utf-8")
    kitty_session_output = KITTY_CONTAINER_SESSION_NEW_ORIGINAL.encode("utf-8")
    mocker.patch(
        "subprocess.check_output",
        side_effect=[
            version_output,
            kitty_tree_command_output,
            kitty_session_output,
            kitty_tree_command_output,
            kitty_session_output,
        ],
    )

    plugin_config = TEST_PLUGIN_CONFIG | {"scrollback": "none"}
    kitty.main(container, plugin_config)

    assert "kitty-session-9999" in container.command
    # Ensure the session file is wrapped in quotes
    session_file = container.command.split(" ")[-1]
    assert session_file.startswith("'")
    assert session_file.endswith("'")

    # Second call to make sure the old session saving cached value is used instead of re-checking
    # the version each invocation
    container.subprocess_command = "subprocess"
    kitty.main(container, plugin_config)
    assert "kitty-session-9999" in container.command
