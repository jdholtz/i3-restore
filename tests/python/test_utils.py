import logging
import os

from pytest_mock import MockerFixture

from programs import utils


def test_get_workspaces_parses_tree_correctly(mocker: MockerFixture) -> None:
    tree = {
        "nodes": [
            {},
            {"nodes": [{"type": "con", "nodes": ["ws1"]}, {"type": ""}]},
            {"nodes": [{"type": "con", "nodes": ["ws2", "ws3"]}]},
        ]
    }
    mocker.patch("programs.utils.get_tree", return_value=tree)

    workspaces = utils.get_workspaces()
    assert workspaces == ["ws1", "ws2", "ws3"]


def test_get_tree_retrieves_the_current_i3_tree(mocker: MockerFixture) -> None:
    expected_tree = b'{"tree": "i3"}'
    mock_check_output = mocker.patch("subprocess.check_output", return_value=expected_tree)
    tree = utils.get_tree()
    assert tree == {"tree": "i3"}
    mock_check_output.assert_called_once_with(["i3-msg", "-t", "get_tree"])


def test_get_logger_initializes_the_logger_correctly(mocker: MockerFixture) -> None:
    # Ensure the environment variable is read from. Also, don't actually write to a file
    mocker.patch.dict(os.environ, {"I3_RESTORE_LOG_FILE": "/dev/null"})
    logger = utils.get_logger()

    assert len(logger.handlers) == 2
    assert logger.handlers[0].baseFilename == "/dev/null"
    assert logger.handlers[1].level == logging.ERROR
