from __future__ import annotations

import sys
from pathlib import Path

import pytest

from codeshell.agent import Agent, AppliedDiffEvent
from codeshell.client import LLMClient
from codeshell.diff_review import DiffReviewManager
from codeshell.tools import create_default_registry
from codeshell.tools.base import ToolCallComplete


class DummyClient(LLMClient):
    async def stream(self, conversation, system: str = "", tools=None):
        if False:
            yield None  # pragma: no cover


def _py_cmd(code: str) -> str:
    escaped = code.replace('"', '\\"')
    return f'python -c "{escaped}"'


async def _run_bash(agent: Agent, command: str):
    stream = agent._execute_tool(ToolCallComplete("1", "Bash", {"command": command, "timeout": 30}))
    event = await anext(stream)
    assert isinstance(event, AppliedDiffEvent)
    result, _elapsed, _unknown = await anext(stream)
    return event, result


@pytest.mark.asyncio
async def test_bash_preview_auto_applies_created_file(tmp_path: Path) -> None:
    agent = Agent(
        DummyClient(),
        create_default_registry(),
        "anthropic",
        work_dir=str(tmp_path),
        diff_review_manager=DiffReviewManager(),
    )
    command = _py_cmd("from pathlib import Path; Path('made.txt').write_text('ok\\n')")

    event, result = await _run_bash(agent, command)

    assert event.change_set.changes[0].kind == "create"
    assert not result.is_error
    assert (tmp_path / "made.txt").read_text(encoding="utf-8") == "ok\n"


@pytest.mark.asyncio
async def test_bash_preview_delete_file_auto_applies(tmp_path: Path) -> None:
    victim = tmp_path / "victim.txt"
    victim.write_text("bye\n", encoding="utf-8")
    agent = Agent(
        DummyClient(),
        create_default_registry(),
        "anthropic",
        work_dir=str(tmp_path),
        diff_review_manager=DiffReviewManager(),
    )
    command = _py_cmd("from pathlib import Path; Path('victim.txt').unlink()")

    event, result = await _run_bash(agent, command)

    assert event.change_set.changes[0].kind == "delete"
    assert not result.is_error
    assert not victim.exists()


@pytest.mark.asyncio
async def test_bash_no_changes_returns_output_without_review(tmp_path: Path) -> None:
    agent = Agent(
        DummyClient(),
        create_default_registry(),
        "anthropic",
        work_dir=str(tmp_path),
        diff_review_manager=DiffReviewManager(),
    )
    stream = agent._execute_tool(ToolCallComplete("1", "Bash", {"command": _py_cmd("print('hello')"), "timeout": 30}))

    result, _elapsed, _unknown = await anext(stream)

    assert not result.is_error
    assert "hello" in result.output