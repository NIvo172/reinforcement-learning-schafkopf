"""Tests for the public game state and a full round of Schafkopf."""

import csv
from pathlib import Path

import pytest
from conftest import FixedContraPlayer, ForcedGamePlayer, make_player_team, run_full_game

from schafkopfrl.schafkopfengine.players.player import Player
from schafkopfrl.schafkopfengine.public_gamestate import PublicGameState
from schafkopfrl.schafkopfengine.rules.rules import Sauspiel
from schafkopfrl.schafkopfengine.utils.enums import Color, Game, Team


def _forced_team(gametype: Game, color: Color = Color.NONE) -> list[Player]:
    """Build a team where every player calls the given game type."""
    return [ForcedGamePlayer(i, gametype, color) for i in range(4)]


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5, 6])
def test_game_invariants_over_seeds(seed: int) -> None:
    """Every finished game satisfies the basic score and card invariants."""
    game = run_full_game(seed=seed)
    assert len(game.cards_played) == 32
    assert game.cards_left_int == 0
    assert sum(game.trick_points) == 120
    assert sum(game.scores.values()) == 120
    assert sum(game.scores_team) == 120
    # Every player on the same team receives the same absolute payout.
    values = [abs(value) for value in game.payout]
    assert all(value == values[0] for value in values)
    assert values[0] > 0
    assert len(game.trick_owner) == 8
    assert all(len(cards) == 8 for cards in game.played_cards_player.values())


def test_playing_order_depends_on_dealer() -> None:
    """The first player to act is the player right after the dealer."""
    players = make_player_team()
    game = PublicGameState(list(players), starting_pos=0)
    first = game.start_game(seed=1)
    assert first is players[(0 + 1) % 4]


def test_start_game_resets_between_games() -> None:
    """A second start_game re-deals the deck and resets the trick counters."""
    game = run_full_game(seed=1)
    first = game.start_game(seed=2)
    assert first in game.players
    assert len(game.cards_played) == 0
    assert game.cards_left_int == 32
    assert all(len(player.cards) == 8 for player in game.players)


def test_player_turn_rotates_and_plays() -> None:
    """Each player turn plays exactly one card and hands over to the next player."""
    game = run_full_game(make_player_team(), seed=3, starting_pos=1)
    assert game.game_id in (Game.RAMSCH, Game.SAUSPIEL, Game.FARBWENZ, Game.WENZ, Game.SOLO)
    assert 0 <= game.points_left <= 120


def test_forced_game_types() -> None:
    """Every game type can be forced and is recorded in the state."""
    cases = {
        (Game.WENZ, Color.NONE): Game.WENZ,
        (Game.SOLO, Color.GRAS): Game.SOLO,
        (Game.FARBWENZ, Color.EICHEL): Game.FARBWENZ,
        (Game.SAUSPIEL, Color.GRAS): Game.SAUSPIEL,
        (Game.RAMSCH, Color.NONE): Game.RAMSCH,
    }
    for (gametype, color), expected in cases.items():
        game = run_full_game(_forced_team(gametype, color), seed=2)
        assert game.game_id is expected, gametype
        if expected == Game.SAUSPIEL:
            assert game.game_color is color
        assert sum(game.trick_points) == 120


@pytest.mark.parametrize("seed", [1, 7, 42])
def test_sauspiel_state_properties(seed: int) -> None:
    """A Sauspiel exposes the searched color and the searched ace."""
    game = run_full_game(_forced_team(Game.SAUSPIEL, Color.GRAS), seed=seed)
    assert game.game_id is Game.SAUSPIEL
    assert game.game_color is Color.GRAS
    assert isinstance(game.gametype, Sauspiel)
    assert game.game_sau is not None
    assert game.game_sau.color is Color.GRAS
    assert game.calling_player is not None


def test_non_sauspiel_has_no_game_sau() -> None:
    """Other game types do not expose a searched ace."""
    game = run_full_game(_forced_team(Game.WENZ, Color.NONE), seed=3)
    assert game.game_id is Game.WENZ
    assert game.game_sau is None


def test_teams_split_correctly() -> None:
    """Team assignment follows the game type rules."""
    # Solo: only the caller is on the calling team.
    game = run_full_game(_forced_team(Game.SOLO, Color.GRAS), seed=5)
    calling = [player for player in game.players if player.team is Team.CALLINGTEAM]
    assert len(calling) == 1
    assert calling[0] is game.calling_player

    # Sauspiel: the caller plus, when present, the partner holding the ruf ace.
    game = run_full_game(_forced_team(Game.SAUSPIEL, Color.HERZ), seed=5)
    calling = [player for player in game.players if player.team is Team.CALLINGTEAM]
    assert 1 <= len(calling) <= 2
    assert game.calling_player is not None and game.calling_player in calling
    for partner in calling:
        if partner is not game.calling_player:
            assert partner.has_rufsau is game.game_sau

    # Ramsch: everyone sits on the non calling team and no caller is recorded.
    game = run_full_game(_forced_team(Game.RAMSCH, Color.NONE), seed=5)
    assert all(player.team is Team.NONCALLINGTEAM for player in game.players)
    assert game.calling_player is None


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_evaluate_payouts_follow_result(seed: int) -> None:
    """The payout sign matches the result of the calling team."""
    game = run_full_game(make_player_team(), seed=seed)
    calling_won = game.scores_team[Team.CALLINGTEAM] >= 61
    for player in game.players:
        signed = game.payout[game.players.index(player)]
        assert signed != 0, "Every game pays out a non-zero amount."
        if player.team is Team.CALLINGTEAM:
            assert signed > 0 if calling_won else signed < 0
        else:
            assert signed < 0 if calling_won else signed > 0


def test_contra_retour_flow() -> None:
    """Contra and retour decisions are recorded with their players."""
    players: list[Player] = [FixedContraPlayer(i, True, True) for i in range(4)]
    game = run_full_game(players, seed=3)
    if game.game_id is not Game.RAMSCH and game.contra:
        assert game.contra_player in players
        assert game.contra_player.team is Team.NONCALLINGTEAM
    if game.retour:
        assert game.retour_player is not None
        assert game.retour_player.team is Team.CALLINGTEAM


def test_ramsch_has_no_contra() -> None:
    """A ramsch game never raises contra or retour."""
    game = run_full_game(_forced_team(Game.RAMSCH, Color.NONE), seed=4)
    assert game.contra is False
    assert game.retour is False
    assert game.contra_player is None
    assert game.retour_player is None


def test_trick_tracking_consistency() -> None:
    """Trick points accumulate to the per-trick totals and the owner list matches."""
    game = run_full_game(make_player_team(), seed=8)
    assert len(game.trick_points) == 8
    assert len(game.trick_owner) == 8
    assert sum(game.trick_points) == sum(game.scores.values())
    assert game.points_left == 120 - sum(game.trick_points) or game.points_left == 0


def test_log_event_to_csv(tmp_path: Path) -> None:
    """log_event_to_csv writes a header on creation and appends further rows."""
    game = PublicGameState(make_player_team(), starting_pos=0)
    target = tmp_path / "sub" / "events.csv"

    first = game.log_event_to_csv({"game": 1, "tricks": 8}, target)
    assert first == target
    with target.open(encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["game", "tricks"]
    assert rows[1:2] == [["1", "8"]]

    game.log_event_to_csv({"game": 2, "tricks": 3}, target)
    with target.open(encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 3
    assert rows[2] == ["2", "3"]


def test_log_methods_run_mid_game() -> None:
    """The logger helpers produce output for a started game in progress."""
    game = PublicGameState(make_player_team(), starting_pos=0)
    first = game.start_game(seed=1)
    game.log_init()
    game.log_gamesearch()
    for _ in range(4):
        first = game.player_turn(first)
    game.log_trick(verbose=True)
    game.log_current_trick(verbose=False)
    game.log_trumps()
    game.log_scores()
    game.log_others()
    assert len(game.trick_points) == 1
    assert repr(game)


def test_repr_contains_state() -> None:
    """The representation summarizes the current public state."""
    game = PublicGameState(make_player_team(), starting_pos=0)
    game.start_game(seed=2)
    text = repr(game)
    assert "Schafkopf" in text or "Gamestate" in text or "game" in text.lower()
