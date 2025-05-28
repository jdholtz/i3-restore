import json
import subprocess
from unittest import mock

import psutil
import pytest
from pytest_mock import MockerFixture

with mock.patch("utils.get_logger"):
    with mock.patch("config.Config._read_config", return_value={}):
        # Don't log messages or read the config file
        from programs import i3_save

from programs import constants
from programs.utils import JSON

WORKSPACE = """{
    "name": "test_workspace",
    "nodes": [
        {"nodes": [], "swallows": ["swallow1"]},
        {"nodes": [{"nodes": [], "swallows": [], "window": 999, "window_properties": {}}]},
        {"nodes": [{"nodes": [], "swallows": [], "window": 999, "window_properties": {}}]},
        {"nodes": [{"nodes": [], "swallows": [], "window": 999, "window_properties": {}}]}
    ]
}"""

I3_TREE = bytes(
    f"""{{
    "nodes": [
        {{}},
        {{ "nodes": [{{"type": "con", "nodes": [{WORKSPACE}]}} , {{"type": ""}}] }},
        {{ "nodes": [{{"type": "con", "nodes": [{WORKSPACE}, {WORKSPACE} ]}}] }}
    ]
}}""",
    encoding="utf-8",
)


def test_main_creates_workspaces_correctly(mocker: MockerFixture) -> None:
    mock_workspace = mocker.patch.object(i3_save, "Workspace")
    mocker.patch("subprocess.check_output", return_value=I3_TREE)

    i3_save.main()

    # There are three workspaces in the i3 tree
    assert mock_workspace.call_count == 3


class TestWorkspace:
    def test_workspace_saves_containers_correctly(self, mocker: MockerFixture) -> None:
        i3_save.CONFIG.terminals = []
        mock_open = mocker.patch("pathlib.Path.open", new_callable=mock.mock_open)

        # Make sure the container with no pid doesn't get saved (the third container in the
        # WORKSPACE)
        mocker.patch(
            "subprocess.check_output",
            side_effect=[b"1", b"2", subprocess.CalledProcessError(None, None)],
        )
        mocker.patch("psutil.Process")

        workspace = i3_save.Workspace(json.loads(WORKSPACE))
        assert len(workspace.containers) == 2

        handle = mock_open()
        assert handle.write.call_args[0][0].count("[[ $1 ==") == 2, (
            "Containers were not saved in the correct format"
        )

    def test_workspace_does_not_save_with_no_containers(self, mocker: MockerFixture) -> None:
        mock_open = mocker.patch("pathlib.Path.open", new_callable=mock.mock_open)

        properties = {"name": "test_workspace", "nodes": []}
        workspace = i3_save.Workspace(properties)

        assert len(workspace.containers) == 0
        mock_open.assert_not_called()

    def test_workspace_saves_subprocesses_correctly(self, mocker: MockerFixture) -> None:
        mock_open = mocker.patch("pathlib.Path.open", new_callable=mock.mock_open)
        # Mock these class methods so they don't run. Their functionality is not tested at all in
        # this test
        mocker.patch.object(i3_save.Container, "_get_pid")
        mocker.patch.object(i3_save.Container, "_get_cmdline_options")

        properties = {"name": "test_workspace", "nodes": [], "window": 999, "window_properties": {}}
        container = i3_save.Container(properties)
        container.subprocess_command = "test_subprocess"

        workspace = i3_save.Workspace(properties)
        workspace.containers = [container]
        workspace._save()

        assert mock_open.call_count == 2, "Only the workspace and subprocess should be saved"


class TestContainer:
    @pytest.mark.parametrize("exception", [psutil.AccessDenied, psutil.ZombieProcess(None)])
    def test_container_handles_psutil_exceptions(
        self, mocker: MockerFixture, exception: psutil.Error
    ) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1")
        mocker.patch.object(i3_save.Container, "_get_cmdline_options", side_effect=exception)

        container = i3_save.Container({"window": 9999, "window_properties": {}})
        assert container.command is None

    def test_get_pid_returns_the_pid(self, mocker: MockerFixture) -> None:
        mocker.patch("subprocess.check_output", return_value=b"99999")
        mocker.patch("psutil.Process")

        container = i3_save.Container({"window": 9999, "window_properties": {}})
        assert container._get_pid() == 99999

    def test_get_pid_handles_called_process_error(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "subprocess.check_output", side_effect=subprocess.CalledProcessError(None, None)
        )

        container = i3_save.Container({"window": 9999, "window_properties": {}})
        assert container._get_pid() is None

    def test_get_cmdline_options_does_not_run_with_no_pid(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "subprocess.check_output", side_effect=subprocess.CalledProcessError(None, None)
        )
        mock_process = mocker.patch("psutil.Process")

        i3_save.Container({"window": 9999, "window_properties": {}})
        mock_process.assert_not_called()

    def test_get_cmdline_options_uses_plugin_for_matching_window_class(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1")
        mock_process = mocker.patch("psutil.Process")

        # Add the config so it's seen as a plugin enabled by the user
        i3_save.CONFIG.enabled_plugins = {constants.KITTY_CLASS: {"listen_socket": "test_socket"}}

        mock_saver = mocker.patch.object(i3_save.SUPPORTED_PLUGINS[constants.KITTY_CLASS], "main")
        properties = {"window_properties": {"class": constants.KITTY_CLASS}, "window": 9999}

        i3_save.Container(properties)

        mock_saver.assert_called_once()
        mock_process.assert_not_called()

    def test_get_cmdline_options_saves_normally_when_plugin_fails_to_save(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1")
        mocker.patch("psutil.Process")

        # Add the config so it's seen as a plugin enabled by the user
        i3_save.CONFIG.enabled_plugins = {constants.KITTY_CLASS: {"listen_socket": "test_socket"}}
        i3_save.CONFIG.terminals = [{"command": "test_command", "class": constants.KITTY_CLASS}]

        mocker.patch.object(
            i3_save.SUPPORTED_PLUGINS[constants.KITTY_CLASS],
            "main",
            side_effect=i3_save.utils.PluginSaveError,
        )
        properties = {"window_properties": {"class": constants.KITTY_CLASS}, "window": 9999}

        container = i3_save.Container(properties)
        assert container.command == "test_command"

    def test_get_cmdline_options_saves_terminals(self, mocker: MockerFixture) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1")
        mocker.patch("psutil.Process")

        i3_save.CONFIG.terminals = [{"command": "test_command", "class": "test_class"}]
        properties = {"window_properties": {"class": "test_class"}, "window": 9999}
        container = i3_save.Container(properties)

        assert container.command == "test_command"

    @pytest.mark.parametrize("window_props", [{"class": "not_terminal"}, {}])
    def test_get_cmdline_options_saves_processes(
        self, mocker: MockerFixture, window_props: JSON
    ) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1")

        # Create a mock process
        mock_process = mocker.patch("psutil.Process")
        mock_process.return_value.cmdline.return_value = ["test_command"]
        mock_process.return_value.cwd.return_value = "test_dir"

        i3_save.CONFIG.terminals = [{"command": "test_command", "class": "test_class"}]
        container = i3_save.Container({"window_properties": window_props, "window": 9999})

        assert container.command == "test_command"
        assert container.working_directory == "test_dir"

    def test_save_with_plugin_skips_saving_when_plugin_not_supported(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1")

        properties = {"window_properties": {"class": "unknown"}, "window": 9999}
        container = i3_save.Container(properties)

        assert not container._save_with_plugin()

    def test_save_with_plugin_handles_plugin_save_errors(self, mocker: MockerFixture) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1")
        mocker.patch.object(
            i3_save.SUPPORTED_PLUGINS[constants.KITTY_CLASS],
            "main",
            side_effect=i3_save.utils.PluginSaveError,
        )

        properties = {"window_properties": {"class": constants.KITTY_CLASS}, "window": 9999}
        container = i3_save.Container(properties)

        assert not container._save_with_plugin()

    def test_check_if_subprocess_saves_subprocess(self, mocker: MockerFixture) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1")

        mock_process = mocker.patch("psutil.Process")
        mock_process2 = mocker.patch("psutil.Process")
        mock_process.cmdline.return_value = ["test_command", "--test-arg", "file name"]
        mock_process.name.return_value = "subprocess2"
        mock_process.children.return_value = [mock_process2, mock_process]

        i3_save.CONFIG.terminals = [{"command": "test_command", "class": "terminal"}]
        i3_save.CONFIG.subprocesses = [
            {"name": "subprocess1"},
            {"name": "subprocess2", "args": ["--test-arg", "-t"]},
        ]
        container = i3_save.Container({"window": 9999, "window_properties": {"class": "terminal"}})
        container.check_if_subprocess(mock_process)

        # The space should be escaped
        assert container.subprocess_command == r"test_command --test-arg file\ name"

    def test_check_if_subprocess_saves_subprocess_with_custom_launch_command(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1")

        mock_process = mocker.patch("psutil.Process")
        mock_process.cmdline.return_value = ["test_command"]
        mock_process.name.return_value = "subprocess"
        mock_process.children.return_value = [mock_process]

        i3_save.CONFIG.terminals = [{"command": "test_command", "class": "terminal"}]
        i3_save.CONFIG.subprocesses = [
            {"name": "subprocess", "launch_command": "{command} and more!"}
        ]

        container = i3_save.Container({"window": 9999, "window_properties": {"class": "terminal"}})
        container.check_if_subprocess(mock_process)

        assert container.subprocess_command == r"test_command and more!"

    def test_check_if_subprocess_does_not_save_subprocess_without_include_args(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1")

        mock_process = mocker.patch("psutil.Process")
        mock_process.cmdline.return_value = ["test_command", "--not-test-arg"]
        mock_process.name.return_value = "subprocess"
        mock_process.children.return_value = [mock_process]

        i3_save.CONFIG.subprocesses = [{"name": "subprocess", "include_args": ["--test-arg"]}]

        container = i3_save.Container({"window": 9999, "window_properties": {"class": "terminal"}})
        container.check_if_subprocess(mock_process)

        assert container.subprocess_command is None

    def test_check_if_subprocess_does_not_save_subprocess_without_deprecated_args(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1")

        mock_process = mocker.patch("psutil.Process")
        mock_process.cmdline.return_value = ["test_command", "--not-test-arg"]
        mock_process.name.return_value = "subprocess"
        mock_process.children.return_value = [mock_process]

        i3_save.CONFIG.subprocesses = [{"name": "subprocess", "args": ["--test-arg"]}]

        container = i3_save.Container({"window": 9999, "window_properties": {"class": "terminal"}})
        container.check_if_subprocess(mock_process)

        assert container.subprocess_command is None

    def test_check_if_subprocess_does_not_save_subprocess_with_exclude_args(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1")

        mock_process = mocker.patch("psutil.Process")
        mock_process.cmdline.return_value = ["test_command", "--test-arg"]
        mock_process.name.return_value = "subprocess"
        mock_process.children.return_value = [mock_process]

        i3_save.CONFIG.subprocesses = [{"name": "subprocess", "exclude_args": ["--test-arg"]}]

        container = i3_save.Container({"window": 9999, "window_properties": {"class": "terminal"}})
        container.check_if_subprocess(mock_process)

        assert container.subprocess_command is None

    def test_check_if_subprocess_does_not_save_non_configured_subprocess(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1")

        mock_process = mocker.patch("psutil.Process")
        mock_process.cmdline.return_value = ["test_command", "file name"]
        mock_process.name.return_value = "subprocess2"
        mock_process.children.return_value = [mock_process]

        i3_save.CONFIG.subprocesses = [{"name": "subprocess1"}]

        container = i3_save.Container({"window": 9999, "window_properties": {"class": "terminal"}})
        container.check_if_subprocess(mock_process)

        assert container.subprocess_command is None

    def test_handle_web_browser_saves_configured_browsers(self, mocker: MockerFixture) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1")
        mocker.patch("psutil.Process")
        mock_save_browser = mocker.patch.object(i3_save.Container, "_save_web_browser")

        i3_save.CONFIG.terminals = []
        i3_save.CONFIG.web_browsers = ["test_browser"]
        container = i3_save.Container({"window": 9999, "window_properties": {}})
        container.command = "test_browser"
        container._handle_web_browser()

        mock_save_browser.assert_called_once()
        assert container.command is None

    def test_handle_web_browser_does_not_save_non_configured_browsers(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1")
        mocker.patch("psutil.Process")
        mock_save_browser = mocker.patch.object(i3_save.Container, "_save_web_browser")

        i3_save.CONFIG.terminals = []
        i3_save.CONFIG.web_browsers = ["browser1"]
        container = i3_save.Container({"window": 9999, "window_properties": {}})
        container.command = "not_a_browser"
        container._handle_web_browser()

        mock_save_browser.assert_not_called()
        assert container.command == "not_a_browser"

    def test_save_web_browser_does_not_save_browsers_already_saved(
        self, mocker: MockerFixture
    ) -> None:
        mock_open = mocker.patch("builtins.open")
        mocker.patch("subprocess.check_output", return_value=b"1")
        mocker.patch("psutil.Process")

        i3_save.WEB_BROWSERS_DICT = {"test_browser": True}
        container = i3_save.Container({"window": 9999, "window_properties": {}})
        container._save_web_browser("test_browser")

        mock_open.assert_not_called()

    def test_save_web_browser_saves_browser_in_file(self, mocker: MockerFixture) -> None:
        mock_open = mocker.patch("builtins.open", new_callable=mock.mock_open)
        mocker.patch("subprocess.check_output", return_value=b"1")
        mocker.patch("psutil.Process")

        i3_save.WEB_BROWSERS_DICT = {"test_browser": False}
        container = i3_save.Container({"window": 9999, "window_properties": {}})
        container.command = "test_browser_command"
        container._save_web_browser("test_browser")

        handle = mock_open()
        assert handle.write.call_args[0][0] == "test_browser_command\n"
