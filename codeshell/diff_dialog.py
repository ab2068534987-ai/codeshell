from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Markdown, Static

from codeshell.diff_format import format_applied_diff
from codeshell.diff_review.models import ChangeSet, DiffReviewResponse


def _escape_markup(text: str) -> str:
    return text.replace("[", "\\[")


class InlineDiffReviewWidget(Vertical, can_focus=True):
    BINDINGS = [
        Binding("up", "cursor_up", "Up", priority=True),
        Binding("down", "cursor_down", "Down", priority=True),
        Binding("enter", "select", "Select", priority=True),
        Binding("escape", "deny", "Deny", priority=True),
    ]

    class Responded(Message):
        def __init__(self, response: DiffReviewResponse) -> None:
            super().__init__()
            self.response = response

    def __init__(self, change_set: ChangeSet, **kwargs) -> None:
        super().__init__(id="diff-review-inline", **kwargs)
        self._change_set = change_set
        self._cursor = 0
        self._options = [
            ("Approve changes", DiffReviewResponse.APPROVE),
            ("Reject changes", DiffReviewResponse.DENY),
        ]

    def compose(self) -> ComposeResult:
        yield Static(self._build_content(), id="diff-review-content")

    def on_mount(self) -> None:
        self.focus()

    def _build_content(self) -> str:
        summary = _escape_markup(self._change_set.summary_text())
        diff = _escape_markup(self._change_set.render_diff())
        lines = [
            "\n  [bold yellow]File changes require review[/bold yellow]",
            "",
            summary,
            "",
            "  [bold]Diff[/bold]",
            diff or "(no text diff available)",
            "",
            "  Do you want to apply these changes?",
            "",
        ]
        for idx, (label, _response) in enumerate(self._options):
            if idx == self._cursor:
                lines.append(f" [bold cyan]>[/bold cyan] {idx + 1}. [bold]{label}[/bold]")
            else:
                lines.append(f"   {idx + 1}. [dim]{label}[/dim]")
        return "\n".join(lines)

    def _refresh(self) -> None:
        self.query_one("#diff-review-content", Static).update(self._build_content())

    def action_cursor_up(self) -> None:
        if self._cursor > 0:
            self._cursor -= 1
            self._refresh()

    def action_cursor_down(self) -> None:
        if self._cursor < len(self._options) - 1:
            self._cursor += 1
            self._refresh()

    def action_select(self) -> None:
        _label, response = self._options[self._cursor]
        self.post_message(self.Responded(response))

    def action_deny(self) -> None:
        self.post_message(self.Responded(DiffReviewResponse.DENY))

class InlineAppliedDiffWidget(Vertical):
    def __init__(self, change_set: ChangeSet, **kwargs) -> None:
        classes = " ".join(filter(None, [kwargs.pop("classes", ""), "applied-diff-inline"]))
        super().__init__(classes=classes, **kwargs)
        self._change_set = change_set

    def compose(self) -> ComposeResult:
        yield Markdown(self._build_content(), classes="applied-diff-content")

    def _build_content(self) -> str:
        return _escape_markup(format_applied_diff(self._change_set))