from __future__ import annotations

import os
import re
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

import utils

if TYPE_CHECKING:
    import psutil

    from ..i3_save import Container


logger = utils.get_logger()

THREAD_ID_PREFIX_RE = re.compile(
    r"(?:^| \| )"  # Require start of the title or Codex's title separator
    # UUID pattern to 29 characters, followed by an ellipsis
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{5})\.\.\."
    r"(?= \| |$)"  # Require end of the title or Codex's title separator
)


def get_thread_id_prefix(window_title: str) -> str:
    """Extract the single truncated Codex thread ID from a terminal title."""
    matches = THREAD_ID_PREFIX_RE.findall(window_title)
    if len(matches) != 1:
        logger.error(
            "Expected one truncated Codex thread ID in terminal title, found %s", len(matches)
        )
        raise utils.PluginSaveError

    return matches[0]


def get_sessions_path() -> Path:
    if codex_home := os.getenv("CODEX_HOME"):
        return Path(codex_home) / "sessions"
    return Path.home() / ".codex" / "sessions"


def find_session_id(thread_id_prefix: str) -> str:
    """Resolve a truncated thread ID to one full ID from a Codex rollout filename."""
    sessions_path = get_sessions_path()
    try:
        matches = [
            path
            for path in sessions_path.rglob(f"rollout-*-{thread_id_prefix}*.jsonl")
            if path.is_file()
        ]
    except OSError as err:
        logger.error("Failed searching Codex sessions under '%s': %s", sessions_path, err)
        raise utils.PluginSaveError from err

    if not matches:
        logger.error("No Codex session matching thread ID prefix '%s'", thread_id_prefix)
        raise utils.PluginSaveError

    # Match the first file found as it is negligible that a collision will occur between two
    # different sessions with the same thread ID prefix.
    return matches[0].stem[-36:]


def main(
    container: Container,
    process: psutil.Process,
    window_title: str,
    launch_command: str,
) -> None:
    """Update a container so its Codex subprocess resumes the current thread on restore."""
    thread_id_prefix = get_thread_id_prefix(window_title)
    session_id = find_session_id(thread_id_prefix)

    cmdline = process.cmdline()
    if not cmdline:
        logger.error("Codex subprocess has an empty command line")
        raise utils.PluginSaveError

    resume_command = shlex.join([cmdline[0], "resume", session_id])
    container.subprocess_command = launch_command.replace("{command}", resume_command)
