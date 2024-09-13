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

KITTY_CONTAINER_SESSION = """new_tab
layout fat
focus
launch --cwd=/home/test /bin/bash -c 'subprocess'
new_tab
layout tall
launch --cwd=/home bash -c 'cat "/tmp/i3-restore-test/kitty-scrollback-9999-2" && bash'
launch --cwd=/ bash -c 'cat "/tmp/i3-restore-test/kitty-scrollback-9999-3" && bash'
"""


@pytest.fixture(autouse=True)
def container(mocker: MockerFixture) -> Container:
    mocker.patch.object(Container, "_get_pid")
    mocker.patch.object(Container, "_get_cmdline_options")
    return Container({"window_properties": {}, "window": 9999})


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
    # pylint: disable-next=c-extension-no-member
    with pytest.raises(kitty.utils.PluginSaveError):
        kitty.get_container_tree("test-socket")


def test_save_scrollback_skips_with_none_scrollback_config() -> None:
    plugin_config = {"listen_socket": "test-socket", "scrollback": "none"}
    assert kitty.save_scrollback(0, 0, plugin_config) is None


def test_save_scrollback_handles_failed_command(mocker: MockerFixture) -> None:
    mocker.patch("subprocess.check_call", side_effect=subprocess.CalledProcessError(None, None))
    mocker.patch("pathlib.Path.open")
    plugin_config = {"listen_socket": "test-socket", "scrollback": "all"}
    assert kitty.save_scrollback(0, 0, plugin_config) is None


def test_save_scrollback_saves_scrollback(mocker: MockerFixture) -> None:
    mocker.patch("subprocess.check_call")
    mocker.patch("pathlib.Path.open")

    plugin_config = {"listen_socket": "test-socket", "scrollback": "all"}
    session_file = kitty.save_scrollback(11, 94, plugin_config)

    assert session_file.name == "kitty-scrollback-94-11"


def test_get_window_subprocess_command_returns_subprocess_command(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = "subprocess"
    mocker.patch.object(container, "check_if_subprocess")

    window_tree = KITTY_CONTAINER_TREE[0]["tabs"][0]["windows"][0]

    assert (
        kitty.get_window_subprocess_command(container, window_tree, {})
        == "/bin/bash -c 'subprocess'"
    )
    assert container.subprocess_command is None


def test_get_window_subprocess_command_returns_subprocess_with_scrollback(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = None

    mocker.patch.object(container, "check_if_subprocess")
    mocker.patch("subprocess.check_call")
    mocker.patch("pathlib.Path.open")

    window_tree = KITTY_CONTAINER_TREE[0]["tabs"][1]["windows"][0]
    plugin_config = {"listen_socket": "test-socket", "scrollback": "all"}

    subprocess_cmd = kitty.get_window_subprocess_command(container, window_tree, plugin_config)

    # Ensure the most important parts of the command are present
    assert "bash -c 'cat" in subprocess_cmd
    assert "kitty-scrollback-9999-2" in subprocess_cmd
    assert " && bash" in subprocess_cmd


def test_get_window_subprocess_command_returns_no_subprocess_when_none_is_present(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = None
    mocker.patch.object(container, "check_if_subprocess")

    window_tree = KITTY_CONTAINER_TREE[0]["tabs"][1]["windows"][0]
    plugin_config = {"listen_socket": "test-socket", "scrollback": "none"}

    assert kitty.get_window_subprocess_command(container, window_tree, plugin_config) is None


def test_get_window_launch_command_returns_launch_command_without_subprocess(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = None
    mocker.patch.object(container, "check_if_subprocess")

    window_tree = KITTY_CONTAINER_TREE[0]["tabs"][0]["windows"][0]
    plugin_config = {"listen_socket": "test-socket", "scrollback": "none"}

    launch_cmd = kitty.get_window_launch_command(container, window_tree, plugin_config)

    assert "launch" in launch_cmd
    assert window_tree["cwd"] in launch_cmd


def test_parse_tree_to_session_parses_tree_into_session_correctly(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = "subprocess"

    mocker.patch.object(container, "check_if_subprocess")
    mocker.patch("subprocess.check_call")
    mocker.patch("pathlib.Path.open")

    plugin_config = {"listen_socket": "test-socket", "scrollback": "all"}
    session_output = kitty.parse_tree_to_session(container, KITTY_CONTAINER_TREE[0], plugin_config)

    assert session_output == KITTY_CONTAINER_SESSION


def test_create_session_file_gets_session_output_and_writes_to_file(
    mocker: MockerFixture, container: Container
) -> None:
    container.subprocess_command = "subprocess"

    mocker.patch.object(container, "check_if_subprocess")
    mocker.patch("subprocess.check_call")
    mock_open = mocker.patch("pathlib.Path.open", new_callable=mock.mock_open)

    plugin_config = {"listen_socket": "test-socket", "scrollback": "all"}
    session_file = kitty.create_session_file(container, KITTY_CONTAINER_TREE, plugin_config)

    handle = mock_open()
    assert (
        handle.write.call_args[0][0] == KITTY_CONTAINER_SESSION
    ), "Kitty container session was not saved correctly"

    assert session_file.name == "kitty-session-9999"


def test_main_saves_a_kitty_container(mocker: MockerFixture, container: Container) -> None:
    container.subprocess_command = "subprocess"

    mocker.patch.object(container, "check_if_subprocess")
    mocker.patch("pathlib.Path.open")

    kitty_tree_command_output = json.dumps(KITTY_CONTAINER_TREE).encode("utf-8")
    mocker.patch("subprocess.check_output", return_value=kitty_tree_command_output)

    plugin_config = {"listen_socket": "test-socket", "scrollback": "none"}
    kitty.main(container, plugin_config)

    assert "kitty-session-9999" in container.command
