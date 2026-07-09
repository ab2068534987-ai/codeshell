from __future__ import annotations

import hashlib
from pathlib import Path

from codeshell.tools.base import SKIP_DIRS

from .models import FileChange, FileSnapshot
from .render import MAX_TEXT_BYTES, is_binary_bytes, render_file_diff, render_summary


def to_rel_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def snapshot_missing(rel_path: str) -> FileSnapshot:
    return FileSnapshot(path=rel_path, exists=False)


def snapshot_file(root: str | Path, rel_path: str) -> FileSnapshot:
    root_path = Path(root).resolve()
    target = (root_path / Path(rel_path)).resolve()
    try:
        target.relative_to(root_path)
    except ValueError:
        raise ValueError(f"path outside worktree: {rel_path}")
    if not target.exists() or not target.is_file():
        return snapshot_missing(rel_path.replace("\\", "/"))

    data = target.read_bytes()
    is_binary = is_binary_bytes(data)
    keep_content = (not is_binary) and len(data) <= MAX_TEXT_BYTES
    return FileSnapshot(
        path=rel_path.replace("\\", "/"),
        exists=True,
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
        is_binary=is_binary,
        content=data if keep_content else None,
    )


def _skip_dir(path: Path) -> bool:
    return path.name in SKIP_DIRS


def snapshot_tree(root: str | Path) -> dict[str, FileSnapshot]:
    root_path = Path(root).resolve()
    snapshots: dict[str, FileSnapshot] = {}
    if not root_path.exists():
        return snapshots
    for path in root_path.rglob("*"):
        if any(_skip_dir(parent) for parent in path.relative_to(root_path).parents):
            continue
        if path.is_dir():
            if _skip_dir(path):
                continue
            continue
        if not path.is_file():
            continue
        rel = to_rel_path(root_path, path)
        snapshots[rel] = snapshot_file(root_path, rel)
    return snapshots


def make_change(before: FileSnapshot, after: FileSnapshot) -> FileChange | None:
    if before.exists and after.exists and before.sha256 == after.sha256:
        return None
    if not before.exists and not after.exists:
        return None
    if before.exists and not after.exists:
        kind = "delete"
    elif not before.exists and after.exists:
        kind = "create"
    else:
        kind = "modify"
    return FileChange(
        path=after.path if after.exists else before.path,
        kind=kind,
        before=before,
        after=after,
        diff_text=render_file_diff(before, after),
        summary=render_summary(before, after, kind),
    )


def compare_snapshots(
    before: dict[str, FileSnapshot],
    after: dict[str, FileSnapshot],
) -> list[FileChange]:
    changes: list[FileChange] = []
    for rel in sorted(set(before) | set(after)):
        b = before.get(rel) or snapshot_missing(rel)
        a = after.get(rel) or snapshot_missing(rel)
        change = make_change(b, a)
        if change is not None:
            changes.append(change)
    return changes
