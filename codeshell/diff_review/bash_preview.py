from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

from codeshell.tools.base import SKIP_DIRS
from codeshell.tools.bash import run_shell_command

from .models import ChangeSet
from .snapshot import compare_snapshots, snapshot_tree


def _ignore_names(_dir: str, names: list[str]) -> set[str]:
    return {name for name in names if name in SKIP_DIRS}



_WINDOWS_ABS_RE = re.compile(r"(?i)(^|[\s'\"])[a-z]:[\\/]")
_POSIX_ABS_RE = re.compile(r"(^|[\s'\"])/(?!/)")


def _command_looks_contained(command: str, real_root: Path) -> bool:
    normalized = command.replace("\\", "/")
    root_text = str(real_root).replace("\\", "/")
    if root_text and root_text in normalized:
        return False
    home_text = str(Path.home()).replace("\\", "/")
    if home_text and home_text in normalized:
        return False
    if _WINDOWS_ABS_RE.search(command):
        return False
    if _POSIX_ABS_RE.search(command):
        return False
    if ".." in Path(command.replace('"', '').replace("'", '')).parts:
        return False
    return True

def _workdir_safe_for_preview(work_dir: Path) -> bool:
    try:
        work_dir.resolve()
        return True
    except OSError:
        return False


async def preview_bash_command(
    command: str,
    timeout: int,
    work_dir: str,
    description: str,
) -> ChangeSet:
    real_root = Path(work_dir).resolve()
    if not _workdir_safe_for_preview(real_root) or not real_root.exists():
        return ChangeSet(
            tool_name="Bash",
            description=description,
            work_dir=str(real_root),
            is_preview_error=True,
            error_message=f"Cannot preview Bash command: invalid workdir {work_dir}",
        )
    if not _command_looks_contained(command, real_root):
        return ChangeSet(
            tool_name="Bash",
            description=description,
            work_dir=str(real_root),
            is_preview_error=True,
            error_message=(
                "Cannot safely preview Bash command: absolute paths or parent "
                "directory traversal are not supported without an OS sandbox"
            ),
        )

    tmp_parent = Path(tempfile.mkdtemp(prefix="codeshell-diff-preview-"))
    preview_root = tmp_parent / "worktree"
    try:
        shutil.copytree(real_root, preview_root, symlinks=True, ignore=_ignore_names)
        before = snapshot_tree(preview_root)
        result = await run_shell_command(command, timeout=timeout, cwd=str(preview_root))
        if result.is_error:
            return ChangeSet(
                tool_name="Bash",
                description=description,
                work_dir=str(real_root),
                stdout=result.output,
                is_preview_error=True,
                error_message=result.output,
                preview_root=str(preview_root),
            )
        after = snapshot_tree(preview_root)
        changes = compare_snapshots(before, after)
        return ChangeSet(
            tool_name="Bash",
            description=description,
            work_dir=str(real_root),
            changes=changes,
            stdout=result.output,
            preview_root=str(preview_root),
        )
    except Exception as e:
        return ChangeSet(
            tool_name="Bash",
            description=description,
            work_dir=str(real_root),
            is_preview_error=True,
            error_message=f"Cannot preview Bash command: {e}",
            preview_root=str(preview_root),
        )
