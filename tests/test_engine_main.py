"""Tests for the engine entry points (batch and interactive play)."""

from unittest import mock

import pytest

from schafkopfrl.schafkopfengine import main as engine_main


def test_main_plays_games() -> None:
    """The engine entry point completes a batch of simulated games without errors."""
    engine_main.main()


def test_play_one_human_against_three_random() -> None:
    """One human player (always answering '0') finishes a game against three random players."""
    with mock.patch("builtins.input", return_value="0") as input_mock:
        assert engine_main.play(humans=1, games=1) == 0

    assert input_mock.called


def test_play_all_random() -> None:
    """Zero human players runs a fully random game without any console input."""
    with mock.patch("builtins.input", side_effect=AssertionError("no input expected")):
        assert engine_main.play(humans=0, games=1) == 0


def test_cli_defaults_to_one_human() -> None:
    """The console script defaults to one human player against three random players."""
    with mock.patch("builtins.input", return_value="0"):
        assert engine_main.cli([]) == 0


def test_cli_rejects_more_than_four_humans() -> None:
    """The console script rejects a number of human players outside the range 0-4."""
    with pytest.raises(SystemExit):
        engine_main.cli(["--humans", "9"])


def test_cli_rejects_zero_games() -> None:
    """The console script rejects a zero number of games."""
    with pytest.raises(SystemExit):
        engine_main.cli(["--games", "0"])
