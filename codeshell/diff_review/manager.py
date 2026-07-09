from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from codeshell.tools.base import ToolResult

from .apply import apply_change_set
from .bash_preview import preview_bash_command
from .models import ChangeSet, FileSnapshot
from .render import is_binary_bytes
from .snapshot import make_change, snapshot_file


class DiffReviewManager:
    def __init__(
        self,
        file_cache: Any = None,
        file_state_cache: Any = None,
        file_history: Any = None,
    ) -> None:
        self.file_cache = file_cache
        self.file_state_cache = file_state_cache
        self.file_history = file_history

    def supports(self, tool_name: str) -> bool:
        return tool_name in {"EditFile", "WriteFile", "Bash"}

    async def prepare(self, tool_name: str, params: BaseModel, work_dir: str) -> ChangeSet:
        if tool_name == "EditFile":
            return self._prepare_edit_file(params, work_dir)
        if tool_name == "WriteFile":
            return self._prepare_write_file(params, work_dir)
        if tool_name == "Bash":
            command = str(getattr(params, "command", ""))
            timeout = int(getattr(params, "timeout", 120))
            return await preview_bash_command(
                command=command,
                timeout=timeout,
                work_dir=work_dir,
                description=command,
            )
        return ChangeSet(
            tool_name=tool_name,
            description=tool_name,
            work_dir=work_dir,
            is_preview_error=True,
            error_message=f"Diff review is not available for {tool_name}",
        )

    def apply(self, change_set: ChangeSet) -> ToolResult:
        return apply_change_set(
            change_set,
            file_cache=self.file_cache,
            file_state_cache=self.file_state_cache,
            file_history=self.file_history,
        )

    def _rel_path(self, work_dir: str, file_path: str) -> str:
        root = Path(work_dir).resolve()
        path = Path(file_path).expanduser()
        if not path.is_absolute():
            path = root / path
        resolved = path.resolve()
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError as e:
            raise ValueError(f"path outside worktree: {file_path}") from e

    def _state_check(self, work_dir: str, rel_path: str, exists_only: bool) -> str | None:
        if self.file_state_cache is None:
            return None
        path = Path(work_dir).resolve() / Path(rel_path)
        if exists_only and not path.exists():
            return None
        ok, err = self.file_state_cache.check(str(path.resolve()))
        return None if ok else err

    def _snapshot_from_bytes(self, rel_path: str, data: bytes, exists: bool = True) -> FileSnapshot:
        is_binary = is_binary_bytes(data)
        return FileSnapshot(
            path=rel_path,
            exists=exists,
            sha256=hashlib.sha256(data).hexdigest() if exists else "",
            size=len(data) if exists else 0,
            is_binary=is_binary,
            content=data if exists else None,
        )

    def _error(self, tool_name: str, description: str, work_dir: str, message: str) -> ChangeSet:
        return ChangeSet(
            tool_name=tool_name,
            description=description,
            work_dir=work_dir,
            is_preview_error=True,
            error_message=message,
        )

    def _prepare_edit_file(self, params: BaseModel, work_dir: str) -> ChangeSet:
        file_path = str(getattr(params, "file_path", ""))
        old_string = str(getattr(params, "old_string", ""))
        new_string = str(getattr(params, "new_string", ""))
        description = f"Edit {file_path}"
        try:
            rel = self._rel_path(work_dir, file_path)
            state_error = self._state_check(work_dir, rel, exists_only=True)
            if state_error:
                return self._error("EditFile", description, work_dir, state_error)
            target = Path(work_dir).resolve() / Path(rel)
            if not target.exists():
                return self._error("EditFile", description, work_dir, f"Error: file not found: {file_path}")
            before = snapshot_file(work_dir, rel)
            content = target.read_text(encoding="utf-8")
            count = content.count(old_string)
            if count == 0:
                return self._error("EditFile", description, work_dir, "Error: old_string not found in file")
            if count > 1:
                return self._error("EditFile", description, work_dir, f"Error: old_string found {count} times, must be unique")
            new_content = content.replace(old_string, new_string, 1)
            after = self._snapshot_from_bytes(rel, new_content.encode("utf-8"))
            change = make_change(before, after)
            changes = [change] if change else []
            return ChangeSet("EditFile", description, str(Path(work_dir).resolve()), changes=changes)
        except Exception as e:
            return self._error("EditFile", description, work_dir, f"Error preparing diff: {e}")

    def _prepare_write_file(self, params: BaseModel, work_dir: str) -> ChangeSet:
        file_path = str(getattr(params, "file_path", ""))
        content = str(getattr(params, "content", ""))
        description = f"Write {file_path}"
        try:
            rel = self._rel_path(work_dir, file_path)
            state_error = self._state_check(work_dir, rel, exists_only=True)
            if state_error:
                return self._error("WriteFile", description, work_dir, state_error)
            before = snapshot_file(work_dir, rel)
            after = self._snapshot_from_bytes(rel, content.encode("utf-8"))
            change = make_change(before, after)
            changes = [change] if change else []
            return ChangeSet("WriteFile", description, str(Path(work_dir).resolve()), changes=changes)
        except Exception as e:
            return self._error("WriteFile", description, work_dir, f"Error preparing diff: {e}")
