from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest
from pytest_mock import MockerFixture

with mock.patch("utils.get_logger"):
    # Don't log messages to a file
    from programs.plugins import codex


SESSION_ID = "123e4567-e89b-12d3-a456-426614174000"
THREAD_ID_PREFIX = SESSION_ID[:29]
WINDOW_TITLE = f"codex | project | {THREAD_ID_PREFIX}..."


def create_rollout_mock(mocker: MockerFixture, session_id: str = SESSION_ID) -> mock.Mock:
    rollout = mocker.Mock()
    rollout.is_file.return_value = True
    rollout.stem = f"rollout-2026-07-18T12-00-00-{session_id}"
    return rollout


@pytest.mark.parametrize(
    ("window_title", "expected"),
    [
        (WINDOW_TITLE, THREAD_ID_PREFIX),
        (WINDOW_TITLE.upper(), THREAD_ID_PREFIX.upper()),
        (f"working | {THREAD_ID_PREFIX}... | done", THREAD_ID_PREFIX),
        (f"{THREAD_ID_PREFIX}... | done", THREAD_ID_PREFIX),
    ],
)
def test_get_thread_id_prefix_extracts_truncated_id(window_title: str, expected: str) -> None:
    assert codex.get_thread_id_prefix(window_title) == expected


@pytest.mark.parametrize(
    "window_title",
    [
        "Codex | project",
        SESSION_ID,
        f"{THREAD_ID_PREFIX}..",
        f"{THREAD_ID_PREFIX}... {THREAD_ID_PREFIX}...",
        f"/tmp/{THREAD_ID_PREFIX}.../project",
        f"project-{THREAD_ID_PREFIX}...",
        f"{THREAD_ID_PREFIX}.../project",
        f"working {THREAD_ID_PREFIX}... done",
    ],
)
def test_get_thread_id_prefix_rejects_invalid_titles(window_title: str) -> None:
    with pytest.raises(codex.utils.PluginSaveError):
        codex.get_thread_id_prefix(window_title)


def test_get_sessions_path_uses_codex_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    assert codex.get_sessions_path() == tmp_path / "sessions"


def test_get_sessions_path_defaults_to_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    monkeypatch.delenv("CODEX_HOME", raising=False)
    mocker.patch.object(codex.Path, "home", return_value=tmp_path)
    assert codex.get_sessions_path() == tmp_path / ".codex" / "sessions"


def test_find_session_id_resolves_rollout(mocker: MockerFixture) -> None:
    sessions_path = mocker.Mock()
    sessions_path.rglob.return_value = [create_rollout_mock(mocker)]
    mocker.patch.object(codex, "get_sessions_path", return_value=sessions_path)

    assert codex.find_session_id(THREAD_ID_PREFIX) == SESSION_ID


def test_find_session_id_rejects_no_match(mocker: MockerFixture) -> None:
    sessions_path = mocker.Mock()
    sessions_path.rglob.return_value = []
    mocker.patch.object(codex, "get_sessions_path", return_value=sessions_path)

    with pytest.raises(codex.utils.PluginSaveError):
        codex.find_session_id(THREAD_ID_PREFIX)


def test_find_session_id_uses_first_of_multiple_matches(mocker: MockerFixture) -> None:
    first_session_id = f"{THREAD_ID_PREFIX}1111111"
    first_rollout = create_rollout_mock(mocker, first_session_id)
    second_rollout = create_rollout_mock(mocker)
    sessions_path = mocker.Mock()
    sessions_path.rglob.return_value = [first_rollout, second_rollout]
    mocker.patch.object(codex, "get_sessions_path", return_value=sessions_path)

    assert codex.find_session_id(THREAD_ID_PREFIX) == first_session_id


def test_find_session_id_handles_search_error(mocker: MockerFixture) -> None:
    sessions_path = mocker.Mock()
    sessions_path.rglob.side_effect = PermissionError
    mocker.patch.object(codex, "get_sessions_path", return_value=sessions_path)

    with pytest.raises(codex.utils.PluginSaveError):
        codex.find_session_id(THREAD_ID_PREFIX)


def test_main_builds_resume_command(mocker: MockerFixture) -> None:
    container = SimpleNamespace(subprocess_command=None)
    process = mocker.Mock()
    process.cmdline.return_value = ["/usr/bin/codex", "--model", "test"]
    mocker.patch.object(codex, "find_session_id", return_value=SESSION_ID)

    codex.main(container, process, WINDOW_TITLE, "{command} && bash")

    assert container.subprocess_command == f"/usr/bin/codex resume {SESSION_ID} && bash"


def test_main_rejects_empty_process_command(mocker: MockerFixture) -> None:
    container = SimpleNamespace(subprocess_command=None)
    process = mocker.Mock()
    process.cmdline.return_value = []
    mocker.patch.object(codex, "find_session_id", return_value=SESSION_ID)

    with pytest.raises(codex.utils.PluginSaveError):
        codex.main(container, process, WINDOW_TITLE, "{command}")
