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
    from programs import i3_save


KITTY_CONTAINER_TREE = [
    {
        "platform_window_id": 9999,
        "tabs": [
            {
                "is_active": True,
                "windows": [
                    {
                        "env": {
                            "SHELL": "/bin/bash",
                        },
                        "cwd": "/home",
                        "pid": 1,
                    }
                ],
            },
            {
                "is_active": False,
                "windows": [
                    {
                        "env": {},
                        "cwd": "/home",
                        "pid": 2,
                    }
                ],
            },
        ],
    }
]

KITTY_CONTAINER_SESSION = """new_tab
focus
launch --cwd=/home /bin/bash -c 'subprocess'
new_tab
launch --cwd=/home \n"""


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


def test_parse_tree_to_session(mocker: MockerFixture) -> None:
    container = i3_save.Container({"window_properties": {}, "window": 9999})
    mocker.patch.object(container, "check_if_subprocess")
    container.subprocess_command = "subprocess"

    assert (
        kitty.parse_tree_to_session(container, KITTY_CONTAINER_TREE[0]) == KITTY_CONTAINER_SESSION
    )


def test_create_session_file_gets_session_output_and_writes_to_file(mocker: MockerFixture) -> None:
    mock_open = mocker.patch("pathlib.Path.open", new_callable=mock.mock_open)

    container = i3_save.Container({"window_properties": {}, "window": 9999})
    mocker.patch.object(container, "check_if_subprocess")
    container.subprocess_command = "subprocess"

    session_file = kitty.create_session_file(container, KITTY_CONTAINER_TREE)

    handle = mock_open()
    assert (
        handle.write.call_args[0][0] == KITTY_CONTAINER_SESSION
    ), "Kitty container session was not saved correctly"

    assert session_file.name == "kitty-session-9999"


def test_main_saves_a_kitty_container(mocker: MockerFixture) -> None:
    mocker.patch("pathlib.Path.open")

    container = i3_save.Container({"window_properties": {}, "window": 9999})
    mocker.patch.object(container, "check_if_subprocess")
    container.subprocess_command = "subprocess"

    kitty_tree_command_output = json.dumps(KITTY_CONTAINER_TREE).encode("utf-8")

    mocker.patch("subprocess.check_output", return_value=kitty_tree_command_output)
    kitty.main(container, {"listen_socket": "test-socket"})

    assert "kitty-session-9999" in container.command
