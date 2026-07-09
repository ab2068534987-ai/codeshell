from __future__ import annotations

from textual.widgets import Markdown

from codeshell.diff_dialog import InlineAppliedDiffWidget, InlineDiffReviewWidget
from codeshell.diff_review.models import ChangeSet, DiffReviewResponse, FileChange, FileSnapshot


def _change_set() -> ChangeSet:
    before = FileSnapshot(path="a.txt", exists=True, sha256="old", size=4, content=b"old\n")
    after = FileSnapshot(path="a.txt", exists=True, sha256="new", size=4, content=b"new\n")
    change = FileChange(
        path="a.txt",
        kind="modify",
        before=before,
        after=after,
        diff_text="--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new",
        summary="modify a.txt (4 -> 4 bytes)",
    )
    return ChangeSet(tool_name="EditFile", description="Edit a.txt", work_dir=".", changes=[change])


def test_diff_review_widget_renders_summary_and_diff() -> None:
    widget = InlineDiffReviewWidget(_change_set())

    content = widget._build_content()

    assert "File changes require review" in content
    assert "modify a.txt" in content
    assert "--- a/a.txt" in content
    assert "+++ b/a.txt" in content
    assert "Approve changes" in content
    assert "Reject changes" in content


def test_applied_diff_widget_renders_read_only_formatted_diff() -> None:
    widget = InlineAppliedDiffWidget(_change_set())

    content = widget._build_content()

    assert "\u5df2\u5e94\u7528\u6587\u4ef6\u53d8\u66f4" in content
    assert "\u4e3b\u8981\u6539\u52a8" in content
    assert "- a.txt: modify, +1 -1" in content
    assert "```diff" in content
    assert "--- a/a.txt" in content
    assert "+++ b/a.txt" in content
    assert "Approve changes" not in content
    assert "Reject changes" not in content


def test_diff_review_widget_escape_uses_deny() -> None:
    assert DiffReviewResponse.DENY.value == "deny"

def test_applied_diff_widget_uses_markdown_renderer() -> None:
    widget = InlineAppliedDiffWidget(_change_set())

    child = list(widget.compose())[0]

    assert isinstance(child, Markdown)

def test_applied_diff_widget_allows_multiple_instances() -> None:
    first = InlineAppliedDiffWidget(_change_set())
    second = InlineAppliedDiffWidget(_change_set())

    first_child = list(first.compose())[0]
    second_child = list(second.compose())[0]

    assert first.id is None
    assert second.id is None
    assert first_child.id is None
    assert second_child.id is None
