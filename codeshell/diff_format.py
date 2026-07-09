from __future__ import annotations

from codeshell.diff_review.models import ChangeSet, FileChange

APPLIED_DIFF_TITLE = "\u5df2\u5e94\u7528\u6587\u4ef6\u53d8\u66f4\uff1a"
CHANGES_HEADING = "\u4e3b\u8981\u6539\u52a8\uff1a"
DIFF_HEADING = "Diff\uff1a"
NO_TEXT_DIFF = "(no text diff available)"
NO_FILE_CHANGES = "- No file changes."


def _line_counts(change: FileChange) -> tuple[int, int]:
    added = 0
    removed = 0
    for line in change.diff_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return added, removed


def _change_summary_line(change: FileChange) -> str:
    added, removed = _line_counts(change)
    return f"- {change.path}: {change.kind}, +{added} -{removed}"


def format_applied_diff(change_set: ChangeSet) -> str:
    lines: list[str] = [APPLIED_DIFF_TITLE, "", CHANGES_HEADING]

    if change_set.changes:
        lines.extend(_change_summary_line(change) for change in change_set.changes)
    else:
        lines.append(NO_FILE_CHANGES)

    if change_set.stdout.strip():
        lines.extend(["", "Command output:", change_set.stdout.strip()])

    lines.extend(["", DIFF_HEADING])
    diff = change_set.render_diff()
    if diff:
        lines.extend(["```diff", diff, "```"])
    else:
        lines.append(NO_TEXT_DIFF)

    return "\n".join(lines)