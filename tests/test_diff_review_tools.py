from __future__ import annotations

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


async def _run_tool(agent: Agent, call: ToolCallComplete):
    stream = agent._execute_tool(call)
    event = await anext(stream)
    assert isinstance(event, AppliedDiffEvent)
    result, _elapsed, _unknown = await anext(stream)
    with pytest.raises(StopAsyncIteration):
        await anext(stream)
    return event, result


@pytest.mark.asyncio
async def test_write_file_auto_applies_and_emits_diff(tmp_path: Path) -> None:
    target = tmp_path / "new.txt"
    agent = Agent(
        DummyClient(),
        create_default_registry(),
        "anthropic",
        work_dir=str(tmp_path),
        diff_review_manager=DiffReviewManager(),
    )

    event, result = await _run_tool(
        agent,
        ToolCallComplete("1", "WriteFile", {"file_path": str(target), "content": "hello\n"}),
    )

    assert event.change_set.changes[0].kind == "create"
    assert "+hello" in event.change_set.render_diff()
    assert result.is_error is False
    assert target.read_text(encoding="utf-8") == "hello\n"


@pytest.mark.asyncio
async def test_edit_file_auto_applies_and_emits_diff(tmp_path: Path) -> None:
    target = tmp_path / "edit.txt"
    target.write_text("old\n", encoding="utf-8")
    agent = Agent(
        DummyClient(),
        create_default_registry(),
        "anthropic",
        work_dir=str(tmp_path),
        diff_review_manager=DiffReviewManager(),
    )

    event, result = await _run_tool(
        agent,
        ToolCallComplete(
            "1",
            "EditFile",
            {"file_path": str(target), "old_string": "old", "new_string": "new"},
        ),
    )

    diff = event.change_set.render_diff()
    assert "-old" in diff
    assert "+new" in diff
    assert result.is_error is False
    assert target.read_text(encoding="utf-8") == "new\n"


@pytest.mark.asyncio
async def test_noninteractive_agent_auto_applies_diff_required_tool(tmp_path: Path) -> None:
    target = tmp_path / "x.txt"
    agent = Agent(
        DummyClient(),
        create_default_registry(),
        "anthropic",
        work_dir=str(tmp_path),
        diff_review_manager=DiffReviewManager(),
    )

    result = await agent._execute_tool_noninteractive(
        ToolCallComplete("1", "WriteFile", {"file_path": str(target), "content": "x"})
    )

    assert result.is_error is False
    assert "Diff review required" not in result.output
    assert "Applied diff:" not in result.output
    assert "\u5df2\u5e94\u7528\u6587\u4ef6\u53d8\u66f4" in result.output
    assert "```diff" in result.output
    assert "+x" in result.output
    assert target.read_text(encoding="utf-8") == "x"