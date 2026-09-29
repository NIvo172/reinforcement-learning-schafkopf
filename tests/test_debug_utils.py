"""Tests for the debug window helpers (headless-safe subset only)."""

from schafkopfrl.schafkopfengine.utils import debug


def test_update_returns_false_without_window() -> None:
    """update() reports failure when no status window is running."""
    assert debug.update("some text") is False


def test_is_running_false_without_window() -> None:
    """is_running() is False before the window thread was started."""
    assert debug.is_running() is False
