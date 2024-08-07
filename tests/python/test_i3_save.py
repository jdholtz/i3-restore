import subprocess
from unittest import mock

import psutil
import pytest
from pytest_mock import MockerFixture

with mock.patch("utils.get_logger"):
    # Don't actually log messages to a file
    from programs import i3_save

from programs.utils import JSON

# This needs to be accessed to be tested
# pylint: disable=protected-access


def test_main_creates_workspaces_correctly(mocker: MockerFixture) -> None:
    mock_workspace = mocker.patch.object(i3_save, "Workspace")
    mocker.patch("utils.get_workspaces", return_value=["ws1", "ws2"])

    i3_save.main()

    assert mock_workspace.call_count == 2


class TestWorkspace:
    def test_workspace_saves_containers_correctly(self, mocker: MockerFixture) -> None:
        i3_save.CONFIG.terminals = []
        mock_open = mocker.patch("pathlib.Path.open", new_callable=mock.mock_open)

        # Make sure the container with None pid doesn't get saved
        mocker.patch.object(i3_save.Container, "_get_pid", side_effect=["pid", "pid", None])
        mock_process = mocker.patch("psutil.Process")
        mock_process.return_value.cmdline.return_value = ["test_command"]

        properties = {
            "name": "test_workspace",
            "nodes": [
                {"nodes": [], "swallows": ["swallow1"]},
                {"nodes": [{"nodes": [], "swallows": []}]},
                {"nodes": [{"nodes": [], "swallows": []}]},
                {"nodes": [{"nodes": [], "swallows": []}]},
            ],
        }

        workspace = i3_save.Workspace(properties)
        assert len(workspace.containers) == 2

        handle = mock_open()
        assert handle.write.call_args[0][0].count("[[ $1 ==") == 2

    def test_workspace_does_not_save_with_no_containers(self, mocker: MockerFixture) -> None:
        mock_open = mocker.patch("pathlib.Path.open", new_callable=mock.mock_open)

        properties = {"name": "test_workspace", "nodes": []}
        workspace = i3_save.Workspace(properties)

        assert len(workspace.containers) == 0
        mock_open.assert_not_called()

    def test_workspace_saves_subprocesses_correctly(self, mocker: MockerFixture) -> None:
        mock_open = mocker.patch("pathlib.Path.open", new_callable=mock.mock_open)
        mocker.patch.object(i3_save.Container, "_get_pid")
        mocker.patch.object(i3_save.Container, "_get_cmdline_options")

        properties = {"name": "test_workspace", "nodes": []}
        container = i3_save.Container({})
        container.subprocess_command = "test_subprocess"

        workspace = i3_save.Workspace(properties)
        workspace.containers = [container]
        workspace._save()

        # Called once for the subprocess and once for the workspace
        assert mock_open.call_count == 2


class TestContainer:
    def test_container_initializes_correctly(self, mocker: MockerFixture) -> None:
        mock_get_pid = mocker.patch.object(i3_save.Container, "_get_pid")
        mock_get_cmd_options = mocker.patch.object(i3_save.Container, "_get_cmdline_options")

        i3_save.Container({})
        mock_get_pid.assert_called_once_with({})
        mock_get_cmd_options.assert_called_once_with({})

    @pytest.mark.parametrize("exception", [psutil.AccessDenied, psutil.ZombieProcess(None)])
    def test_container_handles_psutil_expcetions(
        self, mocker: MockerFixture, exception: psutil.Error
    ) -> None:
        mocker.patch.object(i3_save.Container, "_get_pid")
        mocker.patch.object(i3_save.Container, "_get_cmdline_options", side_effect=exception)

        container = i3_save.Container({})
        assert container.command is None

    def test_get_pid_returns_the_pid(self, mocker: MockerFixture) -> None:
        mocker.patch("subprocess.check_output", return_value=b"1111")
        properties = {"window": 1}

        pid = i3_save.Container._get_pid(properties)
        assert pid == 1111

    def test_get_pid_handles_called_process_error(self, mocker: MockerFixture) -> None:
        mocker.patch(
            "subprocess.check_output", side_effect=subprocess.CalledProcessError(None, None)
        )
        properties = {"window": 1}

        pid = i3_save.Container._get_pid(properties)
        assert pid is None

    def test_get_cmdline_options_does_not_run_with_no_pid(self, mocker: MockerFixture) -> None:
        mocker.patch.object(i3_save.Container, "_get_pid", return_value=None)
        mock_process = mocker.patch("psutil.Process")

        i3_save.Container({})
        mock_process.assert_not_called()

    def test_get_cmdline_options_saves_terminals(self, mocker: MockerFixture) -> None:
        mocker.patch.object(i3_save.Container, "_get_pid")
        mocker.patch("psutil.Process")

        i3_save.CONFIG.terminals = [{"command": "test_command", "class": "test_class"}]
        properties = {"window_properties": {"class": "test_class"}}
        container = i3_save.Container(properties)

        assert container.command == "test_command"

    @pytest.mark.parametrize("window_props", [{"class": "not_terminal"}, {}])
    def test_get_cmdline_options_saves_processes(
        self, mocker: MockerFixture, window_props: JSON
    ) -> None:
        mocker.patch.object(i3_save.Container, "_get_pid")
        mock_process = mocker.patch("psutil.Process")
        mock_process.return_value.cmdline.return_value = ["test_command"]
        mock_process.return_value.cwd.return_value = "test_dir"

        i3_save.CONFIG.terminals = [{"command": "test_command", "class": "test_class"}]
        container = i3_save.Container({"window_properties": window_props})

        assert container.command == "test_command"
        assert container.working_directory == "test_dir"

    def test_check_if_subprocess_saves_subprocess(self, mocker: MockerFixture) -> None:
        mocker.patch.object(i3_save.Container, "_get_pid")
        mocker.patch.object(i3_save.Container, "_get_cmdline_options")

        mock_process = mocker.patch("psutil.Process")
        mock_process2 = mocker.patch("psutil.Process")
        mock_process.cmdline.return_value = ["test_command", "--test-arg", "file name"]
        mock_process.name.return_value = "subprocess2"
        mock_process.children.return_value = [mock_process2, mock_process]

        i3_save.CONFIG.subprocesses = [
            {"name": "subprocess1"},
            {"name": "subprocess2", "args": ["--test-arg", "-t"]},
        ]
        container = i3_save.Container({})
        container._check_if_subprocess(mock_process)

        assert container.subprocess_command == r"test_command --test-arg file\ name"

    def test_check_if_subprocess_saves_subprocess_with_custom_launch_command(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(i3_save.Container, "_get_pid")
        mocker.patch.object(i3_save.Container, "_get_cmdline_options")

        mock_process = mocker.patch("psutil.Process")
        mock_process.cmdline.return_value = ["test_command"]
        mock_process.name.return_value = "subprocess"
        mock_process.children.return_value = [mock_process]

        i3_save.CONFIG.subprocesses = [
            {"name": "subprocess", "launch_command": "{command} and more!"}
        ]

        container = i3_save.Container({})
        container._check_if_subprocess(mock_process)

        assert container.subprocess_command == r"test_command and more!"

    def test_check_if_subprocess_does_not_save_subprocess_without_necessary_args(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(i3_save.Container, "_get_pid")
        mocker.patch.object(i3_save.Container, "_get_cmdline_options")

        mock_process = mocker.patch("psutil.Process")
        mock_process.cmdline.return_value = ["test_command", "--not-test-arg"]
        mock_process.name.return_value = "subprocess"
        mock_process.children.return_value = [mock_process]

        i3_save.CONFIG.subprocesses = [{"name": "subprocess", "args": ["--test-arg"]}]

        container = i3_save.Container({})
        container._check_if_subprocess(mock_process)

        assert container.subprocess_command is None

    def test_check_if_subprocess_does_not_save_non_configured_subprocess(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(i3_save.Container, "_get_pid")
        mocker.patch.object(i3_save.Container, "_get_cmdline_options")

        mock_process = mocker.patch("psutil.Process")
        mock_process.cmdline.return_value = ["test_command", "file name"]
        mock_process.name.return_value = "subprocess2"
        mock_process.children.return_value = [mock_process]

        i3_save.CONFIG.subprocesses = [{"name": "subprocess1"}]

        container = i3_save.Container({})
        container._check_if_subprocess(mock_process)

        assert container.subprocess_command is None

    def test_handle_web_browser_saves_configured_browsers(self, mocker: MockerFixture) -> None:
        mocker.patch.object(i3_save.Container, "_get_pid")
        mocker.patch.object(i3_save.Container, "_get_cmdline_options")
        mock_save_browser = mocker.patch.object(i3_save.Container, "_save_web_browser")

        i3_save.CONFIG.web_browsers = ["test_browser"]
        container = i3_save.Container({})
        container.command = "test_browser"
        container._handle_web_browser()

        mock_save_browser.assert_called_once()
        assert container.command is None

    def test_handle_web_browser_does_not_save_non_configured_browsers(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(i3_save.Container, "_get_pid")
        mocker.patch.object(i3_save.Container, "_get_cmdline_options")
        mock_save_browser = mocker.patch.object(i3_save.Container, "_save_web_browser")

        i3_save.CONFIG.web_browsers = ["browser1"]
        container = i3_save.Container({})
        container.command = "browser2"
        container._handle_web_browser()

        mock_save_browser.assert_not_called()
        assert container.command == "browser2"

    def test_save_web_browser_does_not_save_browsers_already_saved(
        self, mocker: MockerFixture
    ) -> None:
        mock_open = mocker.patch("builtins.open")
        mocker.patch.object(i3_save.Container, "_get_pid")
        mocker.patch.object(i3_save.Container, "_get_cmdline_options")

        i3_save.WEB_BROWSERS_DICT = {"test_browser": True}
        container = i3_save.Container({})
        container._save_web_browser("test_browser")

        mock_open.assert_not_called()

    def test_save_web_browser_saves_browser_in_file(self, mocker: MockerFixture) -> None:
        mock_open = mocker.patch("builtins.open", new_callable=mock.mock_open)
        mocker.patch.object(i3_save.Container, "_get_pid")
        mocker.patch.object(i3_save.Container, "_get_cmdline_options")

        i3_save.WEB_BROWSERS_DICT = {"test_browser": False}
        container = i3_save.Container({})
        container.command = "test_browser_command"
        container._save_web_browser("test_browser")

        handle = mock_open()
        assert handle.write.call_args[0][0] == "test_browser_command\n"
