from __future__ import annotations

from codeshell.prompts import build_system_prompt


def test_system_prompt_includes_completion_report_format() -> None:
    prompt = build_system_prompt(work_dir=".")

    assert "# Completion reports" in prompt
    assert "\u4e3b\u8981\u6539\u52a8" in prompt
    assert "\u9a8c\u8bc1\u7ed3\u679c" in prompt
    assert "\u8865\u5145\u8bf4\u660e" in prompt
    assert "Never invent verification results" in prompt
    assert "overrides the short end-of-turn summary rule" in prompt
    assert "follow the Completion reports section instead" in prompt
    assert "generic offers" in prompt