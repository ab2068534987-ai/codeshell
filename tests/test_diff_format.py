from __future__ import annotations

from codeshell.diff_format import format_applied_diff
from codeshell.diff_review.models import ChangeSet, FileChange, FileSnapshot


def _snapshot(path: str, content: bytes | None, exists: bool = True) -> FileSnapshot:
    return FileSnapshot(
        path=path,
        exists=exists,
        sha256="hash" if exists else "",
        size=len(content or b"") if exists else 0,
        content=content,
    )


def test_format_applied_diff_includes_summary_counts_and_code_block() -> None:
    change = FileChange(
        path="codeshell/agent.py",
        kind="modify",
        before=_snapshot("codeshell/agent.py", b"old\n"),
        after=_snapshot("codeshell/agent.py", b"new\n"),
        diff_text="--- a/codeshell/agent.py\n+++ b/codeshell/agent.py\n@@ -1 +1 @@\n-old\n+new",
    )
    change_set = ChangeSet("EditFile", "Edit file", ".", changes=[change])

    output = format_applied_diff(change_set)

    assert "\u5df2\u5e94\u7528\u6587\u4ef6\u53d8\u66f4" in output
    assert "\u4e3b\u8981\u6539\u52a8" in output
    assert "- codeshell/agent.py: modify, +1 -1" in output
    assert "```diff" in output
    assert "-old" in output
    assert "+new" in output


def test_format_applied_diff_handles_create_and_no_text_diff() -> None:
    change = FileChange(
        path="new.txt",
        kind="create",
        before=_snapshot("new.txt", None, exists=False),
        after=_snapshot("new.txt", b"hello\n"),
        diff_text="",
        summary="create new.txt",
    )
    change_set = ChangeSet("WriteFile", "Write file", ".", changes=[change])

    output = format_applied_diff(change_set)

    assert "- new.txt: create, +0 -0" in output
    assert "```diff" in output
    assert "create new.txt" in output


def test_format_applied_diff_handles_empty_change_set() -> None:
    change_set = ChangeSet("Bash", "noop", ".", changes=[])

    output = format_applied_diff(change_set)

    assert "- No file changes." in output
    assert "(no text diff available)" in output