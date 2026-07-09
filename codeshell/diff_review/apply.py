from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from codeshell.tools.base import ToolResult

from .models import ChangeSet, FileChange
from .snapshot import snapshot_file


def _safe_target(root: Path, rel_path: str) -> Path:
    target = (root / Path(rel_path)).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        raise ValueError(f"path outside worktree: {rel_path}")
    return target


def _after_bytes(change: FileChange, change_set: ChangeSet) -> bytes:
    if change.after.content is not None:
        return change.after.content
    if change_set.preview_root:
        source = _safe_target(Path(change_set.preview_root), change.path)
        if source.exists() and source.is_file():
            return source.read_bytes()
    raise ValueError(f"content unavailable for {change.path}")


def _validate(change_set: ChangeSet) -> str | None:
    root = Path(change_set.work_dir).resolve()
    for change in change_set.changes:
        try:
            target = _safe_target(root, change.path)
        except ValueError as e:
            return str(e)
        current = snapshot_file(root, change.path)
        before = change.before
        if before.exists != current.exists:
            return f"Workspace changed before applying diff: {change.path}"
        if before.exists and before.sha256 != current.sha256:
            return f"Workspace changed before applying diff: {change.path}"
        if change.kind == "create" and target.exists():
            return f"Target already exists before applying diff: {change.path}"
    return None


def apply_change_set(
    change_set: ChangeSet,
    file_cache: Any = None,
    file_state_cache: Any = None,
    file_history: Any = None,
) -> ToolResult:
    if change_set.is_preview_error:
        return ToolResult(output=change_set.error_message, is_error=True)
    err = _validate(change_set)
    if err:
        return ToolResult(output=err, is_error=True)

    root = Path(change_set.work_dir).resolve()
    changed_paths: list[Path] = []
    try:
        for change in change_set.changes:
            target = _safe_target(root, change.path)
            if file_history is not None:
                file_history.track_edit(str(target))
            if change.kind == "delete":
                if target.exists():
                    target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                data = _after_bytes(change, change_set)
                target.write_bytes(data)
            changed_paths.append(target)

        for target in changed_paths:
            resolved = str(target.resolve())
            if file_cache is not None:
                file_cache.invalidate(resolved)
            if file_state_cache is not None and target.exists():
                file_state_cache.update(resolved)
    except Exception as e:
        return ToolResult(output=f"Error applying reviewed diff: {e}", is_error=True)

    count = len(change_set.changes)
    noun = "file" if count == 1 else "files"
    output = f"Applied reviewed diff for {count} {noun}."
    if change_set.stdout and change_set.tool_name == "Bash":
        output += "\n\nPreview command output:\n" + change_set.stdout.strip()
    return ToolResult(output=output, is_error=False)
