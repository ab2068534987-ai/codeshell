from __future__ import annotations

import codecs
import difflib

from .models import FileSnapshot

MAX_TEXT_BYTES = 512 * 1024
MAX_DIFF_CHARS = 20000
MAX_DIFF_LINES = 400


def is_binary_bytes(data: bytes) -> bool:
    sample = data[:8192]
    if b"\x00" in sample:
        return True
    decoder = codecs.getincrementaldecoder("utf-8")()
    try:
        decoder.decode(sample, final=False)
    except UnicodeDecodeError:
        return True
    return False


def decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def _snapshot_lines(snapshot: FileSnapshot) -> list[str]:
    if not snapshot.exists or snapshot.content is None:
        return []
    return decode_text(snapshot.content).splitlines(keepends=True)


def _truncated(text: str) -> str:
    lines = text.splitlines()
    truncated = False
    if len(lines) > MAX_DIFF_LINES:
        lines = lines[:MAX_DIFF_LINES]
        truncated = True
    result = "\n".join(lines)
    if len(result) > MAX_DIFF_CHARS:
        result = result[:MAX_DIFF_CHARS]
        truncated = True
    if truncated:
        result = result.rstrip() + "\n... diff truncated ..."
    return result


def render_file_diff(before: FileSnapshot, after: FileSnapshot) -> str:
    path = after.path if after.exists else before.path
    if before.is_binary or after.is_binary:
        return f"Binary file changed: {path}"
    if before.size > MAX_TEXT_BYTES or after.size > MAX_TEXT_BYTES:
        return f"Large file changed: {path} ({before.size} -> {after.size} bytes)"
    if before.content is None and before.exists:
        return f"File content omitted before change: {path}"
    if after.content is None and after.exists:
        return f"File content omitted after change: {path}"

    before_name = f"a/{path}" if before.exists else "/dev/null"
    after_name = f"b/{path}" if after.exists else "/dev/null"
    diff = difflib.unified_diff(
        _snapshot_lines(before),
        _snapshot_lines(after),
        fromfile=before_name,
        tofile=after_name,
        lineterm="",
    )
    return _truncated("\n".join(diff))


def render_summary(before: FileSnapshot, after: FileSnapshot, kind: str) -> str:
    path = after.path if after.exists else before.path
    if kind == "create":
        return f"create {path} ({after.size} bytes)"
    if kind == "delete":
        return f"delete {path} ({before.size} bytes)"
    return f"modify {path} ({before.size} -> {after.size} bytes)"
