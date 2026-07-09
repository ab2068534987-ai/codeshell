from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal


ChangeKind = Literal["create", "modify", "delete"]


@dataclass
class FileSnapshot:
    path: str
    exists: bool
    sha256: str = ""
    size: int = 0
    is_binary: bool = False
    content: bytes | None = None


@dataclass
class FileChange:
    path: str
    kind: ChangeKind
    before: FileSnapshot
    after: FileSnapshot
    diff_text: str = ""
    summary: str = ""

    def display_summary(self) -> str:
        if self.summary:
            return self.summary
        return f"{self.kind}: {self.path}"


@dataclass
class ChangeSet:
    tool_name: str
    description: str
    work_dir: str
    changes: list[FileChange] = field(default_factory=list)
    stdout: str = ""
    is_preview_error: bool = False
    error_message: str = ""
    preview_root: str | None = None

    def has_changes(self) -> bool:
        return bool(self.changes)

    def summary_text(self) -> str:
        counts = {"create": 0, "modify": 0, "delete": 0}
        for change in self.changes:
            counts[change.kind] += 1
        lines = [
            f"Tool: {self.tool_name}",
            f"Action: {self.description}",
            (
                "Files: "
                f"{counts['create']} created, "
                f"{counts['modify']} modified, "
                f"{counts['delete']} deleted"
            ),
        ]
        for change in self.changes:
            lines.append(f"  - {change.display_summary()}")
        if self.stdout:
            lines.append("")
            lines.append("Command output:")
            lines.append(self.stdout.strip())
        return "\n".join(lines)

    def render_diff(self, max_lines: int = 240) -> str:
        lines: list[str] = []
        for change in self.changes:
            lines.append(f"# {change.kind}: {change.path}")
            if change.diff_text:
                lines.extend(change.diff_text.rstrip().splitlines())
            else:
                lines.append(change.display_summary())
            lines.append("")
        if len(lines) > max_lines:
            omitted = len(lines) - max_lines
            lines = lines[:max_lines]
            lines.append(f"... diff truncated, {omitted} line(s) omitted ...")
        return "\n".join(lines).rstrip()

    def path_for(self, root: str | Path, rel_path: str) -> Path:
        return Path(root) / Path(rel_path)


class DiffReviewResponse(Enum):
    APPROVE = "approve"
    DENY = "deny"
