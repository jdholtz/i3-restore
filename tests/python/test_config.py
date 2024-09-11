from typing import Any, Dict
from unittest import mock

import pytest
from pytest_mock import MockerFixture

with mock.patch("utils.get_logger"):
    # Don't actually log messages to a file
    from programs import config

# This needs to be accessed to be tested
# pylint: disable=protected-access


# Make sure we don't actually read the config file. The
# mocks can still be overridden in each test
@pytest.fixture(autouse=True)
def mock_open(mocker: MockerFixture) -> None:
    mocker.patch("builtins.open")
    mocker.patch("json.load")


def test_config_exits_on_error_in_config_file(mocker: MockerFixture) -> None:
    invalid_config = {"subprocesses": "invalid"}
    mocker.patch("json.load", return_value=invalid_config)

    with pytest.raises(SystemExit):
        config.Config()


def test_read_config_reads_the_config_file_correctly(mocker: MockerFixture) -> None:
    expected_config = {"test": "data"}
    mocker.patch("json.load", return_value=expected_config)

    test_config = config.Config()
    config_content = test_config._read_config()

    assert config_content == expected_config


def test_read_config_returns_empty_config_when_file_is_not_found(mocker: MockerFixture) -> None:
    mocker.patch("builtins.open", side_effect=FileNotFoundError())

    test_config = config.Config()
    config_content = test_config._read_config()

    assert config_content == {}


@pytest.mark.parametrize(
    "config_content",
    [
        {"subprocesses": "invalid"},
        {"terminals": "invalid"},
        {"web_browsers": "invalid"},
        {"enabled_plugins": []},
    ],
)
def test_parse_config_raises_exception_with_invalid_entries(config_content: Dict[str, Any]) -> None:
    test_config = config.Config()

    with pytest.raises(TypeError):
        test_config._parse_config(config_content)


def test_parse_config_sets_the_correct_config_values() -> None:
    json_config = {
        "subprocesses": ["subprocess1", "subprocess2"],
        "terminals": ["terminal1", "terminal2"],
        "web_browsers": ["browser1", "browser2"],
        "enabled_plugins": {"plugin": {"test": "config"}},
    }

    test_config = config.Config()
    test_config._parse_config(json_config)

    assert test_config.subprocesses == json_config["subprocesses"]
    assert test_config.terminals == json_config["terminals"]
    assert test_config.web_browsers == json_config["web_browsers"]
    assert test_config.enabled_plugins == json_config["enabled_plugins"]


def test_parse_config_does_not_set_values_when_a_config_value_is_empty() -> None:
    test_config = config.Config()
    expected_config = config.Config()

    test_config._parse_config({})

    assert test_config.subprocesses == expected_config.subprocesses
    assert test_config.terminals == expected_config.terminals
    assert test_config.web_browsers == test_config.web_browsers
