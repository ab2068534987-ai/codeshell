import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from codeshell.app import CodeShellApp
from codeshell.context_indicator import ContextUsageIndicator
from codeshell.conversation import ConversationManager


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_make_banner_uses_gold_dragon() -> None:
    work_dir = "E:/project_codeshell/codeshell-python"
    banner = CodeShellApp._make_banner(model="qwen-plus", work_dir=work_dir)
    plain = banner.plain

    assert "CodeShell v0.1.0" in plain
    assert "qwen-plus" in plain
    assert work_dir in plain
    assert "/\\_/\\" not in plain
    assert "( o.o )" not in plain
    assert " > ^ <" not in plain
    assert "____/  \\____/  \\____" in plain
    assert "/___   o  __  o   ___\\" in plain
    assert "\\___      __      ___/" in plain
    assert "\\__/||  ||\\__/" in plain
    assert "~" not in plain
    assert ">" not in plain

    lines = plain.splitlines()
    assert len(lines) == 5
    qwen_line = next(i for i, line in enumerate(lines) if "qwen-plus" in line)
    work_dir_line = next(i for i, line in enumerate(lines) if work_dir in line)
    assert work_dir_line == qwen_line + 1
    assert any("color(220)" in str(span.style) for span in banner.spans)


def test_title_bar_height_matches_dragon_banner() -> None:
    css = (PROJECT_ROOT / "codeshell" / "styles.tcss").read_text(encoding="utf-8")
    title_block = css.split("#title-bar {", 1)[1].split("}", 1)[0]

    assert "height: 5;" in title_block
    assert "dock: top;" in title_block
    assert "width: 100%;" in title_block
    assert "padding: 0 1;" in title_block



def test_status_bar_preserves_content_row_above_border() -> None:
    css = (PROJECT_ROOT / "codeshell" / "styles.tcss").read_text(encoding="utf-8")
    status_block = css.split("#status-bar {", 1)[1].split("}", 1)[0]

    assert "height: 2;" in status_block
    assert "min-height: 2;" in status_block
    assert "border-top: solid #303030;" in status_block

@pytest.mark.asyncio
async def test_app_stylesheet_loads_in_headless_mode() -> None:
    app = CodeShellApp([])

    async with app.run_test(size=(100, 30)):
        pass



def test_status_bar_preserves_content_row_above_border() -> None:
    css = (PROJECT_ROOT / "codeshell" / "styles.tcss").read_text(encoding="utf-8")
    status_block = css.split("#status-bar {", 1)[1].split("}", 1)[0]

    assert "height: 2;" in status_block
    assert "min-height: 2;" in status_block
    assert "border-top: solid #303030;" in status_block

@pytest.mark.asyncio
async def test_status_bar_mounts_context_usage_indicator() -> None:
    app = CodeShellApp([])

    async with app.run_test(size=(100, 30)):
        indicator = app.query_one("#context-usage", ContextUsageIndicator)
        assert indicator.rendered_symbol == "\u25cb"
        assert indicator.tooltip == "Context: unknown"



def test_status_bar_preserves_content_row_above_border() -> None:
    css = (PROJECT_ROOT / "codeshell" / "styles.tcss").read_text(encoding="utf-8")
    status_block = css.split("#status-bar {", 1)[1].split("}", 1)[0]

    assert "height: 2;" in status_block
    assert "min-height: 2;" in status_block
    assert "border-top: solid #303030;" in status_block

@pytest.mark.asyncio
async def test_chat_submit_ignores_duplicate_while_submission_is_pending(monkeypatch) -> None:
    app = CodeShellApp([])
    calls: list[str] = []
    gate = asyncio.Event()

    async def fake_dispatch(text: str) -> None:
        calls.append(text)
        await gate.wait()

    monkeypatch.setattr(app, "_dispatch_command", fake_dispatch)

    first = asyncio.create_task(app.on_chat_input_submitted(SimpleNamespace(text="hello")))
    await asyncio.sleep(0)
    await app.on_chat_input_submitted(SimpleNamespace(text="hello"))
    gate.set()
    await first

    assert calls == ["hello"]



def test_status_bar_preserves_content_row_above_border() -> None:
    css = (PROJECT_ROOT / "codeshell" / "styles.tcss").read_text(encoding="utf-8")
    status_block = css.split("#status-bar {", 1)[1].split("}", 1)[0]

    assert "height: 2;" in status_block
    assert "min-height: 2;" in status_block
    assert "border-top: solid #303030;" in status_block

@pytest.mark.asyncio
async def test_finish_streaming_clears_submit_guard() -> None:
    app = CodeShellApp([])
    app._streaming = True
    app._submitting = True

    app._finish_streaming()

    assert app._streaming is False
    assert app._submitting is False


def test_command_context_persists_resume_candidates_between_commands() -> None:
    app = CodeShellApp([])

    first = app._build_command_context("")
    first.config["_resume_candidates"] = ["session_a"]
    second = app._build_command_context("resume 1")

    assert second.config["_resume_candidates"] == ["session_a"]
    assert second.config["registry"] is app.command_registry


def test_set_conversation_refreshes_context_usage_indicator(monkeypatch) -> None:
    app = CodeShellApp([])
    conv = ConversationManager()
    conv.add_user_message("x" * 350)
    calls: list[int] = []

    monkeypatch.setattr(
        app,
        "_update_context_usage_indicator",
        lambda: calls.append(app.conversation.current_tokens()),
    )

    app._set_conversation(conv)

    assert app.conversation is conv
    assert calls == [100]