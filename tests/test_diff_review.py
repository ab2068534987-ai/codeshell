from __future__ import annotations

from pathlib import Path

from codeshell.diff_review import DiffReviewManager
from codeshell.diff_review.apply import apply_change_set
from codeshell.diff_review.render import is_binary_bytes
from codeshell.diff_review.snapshot import compare_snapshots, snapshot_tree
from codeshell.tools.file_state_cache import FileStateCache
from codeshell.tools.write_file import Params


def test_snapshot_compare_create_modify_delete(tmp_path: Path) -> None:
    (tmp_path / "keep.txt").write_text("old\n", encoding="utf-8")
    (tmp_path / "remove.txt").write_text("bye\n", encoding="utf-8")
    before = snapshot_tree(tmp_path)

    (tmp_path / "keep.txt").write_text("new\n", encoding="utf-8")
    (tmp_path / "add.txt").write_text("hello\n", encoding="utf-8")
    (tmp_path / "remove.txt").unlink()
    after = snapshot_tree(tmp_path)

    changes = compare_snapshots(before, after)
    by_path = {c.path: c for c in changes}

    assert by_path["add.txt"].kind == "create"
    assert by_path["keep.txt"].kind == "modify"
    assert by_path["remove.txt"].kind == "delete"
    assert "+hello" in by_path["add.txt"].diff_text
    assert "-old" in by_path["keep.txt"].diff_text
    assert "+new" in by_path["keep.txt"].diff_text


def test_binary_change_renders_summary(tmp_path: Path) -> None:
    (tmp_path / "blob.bin").write_bytes(b"\x00\x01old")
    before = snapshot_tree(tmp_path)
    (tmp_path / "blob.bin").write_bytes(b"\x00\x02new")
    after = snapshot_tree(tmp_path)

    changes = compare_snapshots(before, after)

    assert len(changes) == 1
    assert changes[0].kind == "modify"
    assert "Binary file changed" in changes[0].diff_text


def test_apply_change_set_detects_conflict(tmp_path: Path) -> None:
    target = tmp_path / "conflict.txt"
    target.write_text("old\n", encoding="utf-8")
    manager = DiffReviewManager()

    change_set = manager._prepare_write_file(
        Params(file_path=str(target), content="new\n"),
        str(tmp_path),
    )
    target.write_text("external\n", encoding="utf-8")

    result = apply_change_set(change_set)

    assert result.is_error is True
    assert "Workspace changed" in result.output
    assert target.read_text(encoding="utf-8") == "external\n"


def test_apply_change_set_blocks_path_escape(tmp_path: Path) -> None:
    manager = DiffReviewManager()

    change_set = manager._prepare_write_file(
        Params(file_path=str(tmp_path.parent / "escape.txt"), content="x"),
        str(tmp_path),
    )

    assert change_set.is_preview_error is True
    assert "outside worktree" in change_set.error_message


def test_utf8_boundary_sample_is_not_binary() -> None:
    data = ("a" * 8190 + "中").encode("utf-8")

    try:
        data[:8192].decode("utf-8")
    except UnicodeDecodeError:
        truncated_sample_is_invalid = True
    else:
        truncated_sample_is_invalid = False

    assert truncated_sample_is_invalid is True
    assert is_binary_bytes(data) is False


def test_apply_write_file_with_chinese_boundary_content(tmp_path: Path) -> None:
    target = tmp_path / "chinese.py"
    content = "a" * 8190 + "中文内容\n"
    manager = DiffReviewManager()

    change_set = manager._prepare_write_file(
        Params(file_path=str(target), content=content),
        str(tmp_path),
    )
    result = apply_change_set(change_set)

    assert result.is_error is False
    assert target.read_text(encoding="utf-8") == content


def test_file_state_cache_update_skips_binary_file(tmp_path: Path) -> None:
    target = tmp_path / "report.docx"
    target.write_bytes(b"PK\x03\x04\x80\x00binary")
    cache = FileStateCache()

    cache.update(str(target))

    ok, err = cache.check(str(target))
    assert ok is False
    assert "has not been read" in err


def test_apply_change_set_with_binary_output_does_not_fail_cache_update(tmp_path: Path) -> None:
    target = tmp_path / "report.docx"
    cache = FileStateCache()
    manager = DiffReviewManager(file_state_cache=cache)
    content = "PK\x03\x04" + chr(0x80) + "binary payload"

    change_set = manager._prepare_write_file(
        Params(file_path=str(target), content=content),
        str(tmp_path),
    )
    result = apply_change_set(change_set, file_state_cache=cache)

    assert result.is_error is False
    assert target.read_bytes() == content.encode("utf-8")