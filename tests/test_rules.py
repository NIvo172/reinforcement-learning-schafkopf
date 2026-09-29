"""Tests for the game rule sets."""

import pytest

from schafkopfrl.schafkopfengine.rules.rules import Ramsch, Rules, Sauspiel, Solo, Wenz
from schafkopfrl.schafkopfengine.utils.enums import Color, Game


def test_create_returns_typed_rules() -> None:
    """Rules.create returns the matching rule subclass for every game type."""
    assert isinstance(Rules.create(Game.SAUSPIEL, Color.HERZ), Sauspiel)
    assert isinstance(Rules.create(Game.SOLO, Color.GRAS), Solo)
    assert isinstance(Rules.create(Game.WENZ, Color.NONE), Wenz)
    assert isinstance(Rules.create(Game.FARBWENZ, Color.EICHEL), Wenz)
    assert isinstance(Rules.create(Game.RAMSCH, Color.NONE), Ramsch)


def test_rules_parameters() -> None:
    """The fixed score parameters of each game type."""
    sauspiel = Rules.create(Game.SAUSPIEL, Color.HERZ)
    assert sauspiel.reward == 20
    assert sauspiel.winning_threshold == 61
    assert sauspiel.min_laufende == 3

    solo = Rules.create(Game.SOLO, Color.GRAS)
    assert solo.reward == 50
    assert solo.winning_threshold == 61
    assert solo.min_laufende == 3

    wenz = Rules.create(Game.WENZ, Color.NONE)
    assert wenz.reward == 50
    assert wenz.min_laufende == 2
    assert wenz.gameid == Game.WENZ
    assert wenz.gamename == "WENZ"

    farbwenz = Rules.create(Game.FARBWENZ, Color.EICHEL)
    assert farbwenz.winning_threshold == 61
    assert farbwenz.min_laufende == 3
    assert farbwenz.gameid == Game.FARBWENZ
    assert farbwenz.trump_color == Color.EICHEL
    assert farbwenz.gamename == "EICHEL-WENZ"

    ramsch = Rules.create(Game.RAMSCH, Color.NONE)
    assert ramsch.reward == 10
    assert ramsch.winning_threshold == 61


def test_create_rejects_unknown_game() -> None:
    """Rules.create raises for the unsupported SIE game type."""
    with pytest.raises(RuntimeError, match="SIE"):
        Rules.create(Game.SIE, Color.HERZ)


def test_sauspiel_searched_color() -> None:
    """The Sauspiel remembers the color of the searched ace."""
    sauspiel = Rules.create(Game.SAUSPIEL, Color.GRAS)
    assert sauspiel.searched_color == Color.GRAS  # type: ignore[attr-defined]
    assert sauspiel.trump_color == Color.HERZ


def test_schneider_win_reward() -> None:
    """The schneider win reward depends on the opponent's tricks and points."""
    assert Rules.reward_schneider_win(120, 0) == 20
    assert Rules.reward_schneider_win(91, 0) == 20  # Schneider plus schwarz.
    assert Rules.reward_schneider_win(91, 1) == 10  # Schneider only.
    assert Rules.reward_schneider_win(90, 1) == 0  # Below the schneider threshold.


def test_schneider_loss_reward() -> None:
    """The schneider loss rewards follow the same thresholds."""
    assert Rules.reward_schneider_loss(120, 0) == 20
    assert Rules.reward_schneider_loss(90, 0) == 20
    assert Rules.reward_schneider_loss(90, 1) == 10
    assert Rules.reward_schneider_loss(89, 1) == 0


def test_reprs() -> None:
    """The repr encodes the game name and, for the Sauspiel, the searched color."""
    assert "SAUSPIEL" in repr(Rules.create(Game.SAUSPIEL, Color.HERZ))
    assert "SOLO" in repr(Rules.create(Game.SOLO, Color.GRAS))
    assert "WENZ" in repr(Rules.create(Game.WENZ, Color.NONE))
    assert "RAMSCH" in repr(Rules.create(Game.RAMSCH, Color.NONE))


def test_card_setting_structure() -> None:
    """Every rule set carries card settings for all 8 ober/unter positions."""
    for rules in (
        Sauspiel(Color.HERZ),
        Solo(Color.GRAS),
        Wenz(Color.NONE),
        Wenz(Color.EICHEL),
        Ramsch(Color.NONE),
    ):
        assert len(rules.card_setting) == 8
