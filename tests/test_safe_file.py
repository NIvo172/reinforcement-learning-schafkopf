"""Tests for the safe file appending helper."""

from pathlib import Path

from schafkopfrl.utils.safe_file import append_to_log

REPO_ROOT = Path(__file__).resolve().parent.parent
REL_NAME = "reports/unit/safe_file_test.log"


def test_append_to_log_creates_and_appends() -> None:
    """append_to_log creates the parent directories and appends content twice."""
    target = (REPO_ROOT / REL_NAME).resolve()
    try:
        append_to_log(REL_NAME, "first line\n")
        append_to_log(REL_NAME, "second line\n")
        assert target.is_file()
        content = target.read_text(encoding="utf-8")
        assert "first line" in content
        assert "second line" in content
        assert content.index("first line") < content.index("second line")
    finally:
        target.unlink(missing_ok=True)
        target.parent.rmdir()
