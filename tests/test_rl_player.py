"""Tests for the RL player observation and action mechanics."""

import numpy as np
import pytest

from schafkopfrl.schafkopfengine.players.player import Player
from schafkopfrl.schafkopfengine.players.random_player import RandomPlayer
from schafkopfrl.schafkopfengine.players.rl_player import RL, RLPlayerLearning
from schafkopfrl.schafkopfengine.public_gamestate import PublicGameState
from schafkopfrl.schafkopfengine.utils.enums import Color, Game


class ForcedSoloRLPlayer(RLPlayerLearning):
    """RL player that always calls a solo on grass."""

    def choose_gametype(self) -> tuple[Game, Color]:
        """Return the fixed solo call."""
        return Game.SOLO, Color.GRAS


class ForcedRamschRLPlayer(RLPlayerLearning):
    """RL player that always answers ramsch."""

    def choose_gametype(self) -> tuple[Game, Color]:
        """Return the ramsch call."""
        return Game.RAMSCH, Color.NONE


class ForcedSoloRandomPlayer(RandomPlayer):
    """Random player that always calls the fixed solo."""

    def choose_gametype(self) -> tuple[Game, Color]:
        """Return the fixed solo call."""
        return Game.SOLO, Color.GRAS


def _int64(value: object) -> np.ndarray:
    """Cast an observation value to a one-dimensional int64 array."""
    return np.asarray(value).astype(np.int64)


def _solo_game(caller_seat: int = 3) -> tuple[PublicGameState, list[RLPlayerLearning]]:
    """Start a solo game with a fixed caller and return the state and RL players."""
    rl_players: list[RLPlayerLearning] = [ForcedSoloRLPlayer(i) for i in range(3)]
    players: list[Player] = [*rl_players, ForcedSoloRandomPlayer(3)]
    # The player after the dealer speaks first and wins the game search.
    starting_pos = (caller_seat - 1) % 4
    game = PublicGameState(players, starting_pos=starting_pos)
    game.start_game(seed=7)
    assert game.calling_player is players[caller_seat]
    return game, rl_players


def test_observe_keys_match_declared_space() -> None:
    """The observation dict covers exactly the keys of the declared space."""
    _game, rl_players = _solo_game()
    observation = rl_players[0].observe()
    assert set(observation.keys()) == set(rl_players[0]._basic_space().spaces.keys())


def test_observe_shapes() -> None:
    """Key observation vectors have the expected sizes."""
    _game, rl_players = _solo_game()
    observation = rl_players[0].observe()
    assert len(_int64(observation["handcards"])) == 8
    assert len(_int64(observation["allowed_actions"])) == 8
    assert len(np.asarray(observation["team_dist"])) == 4
    assert len(_int64(observation["player_00"])) == 13
    assert len(_int64(observation["trumps_left"])) == 14
    assert len(_int64(observation["cards_left"])) == 32
    assert int(_int64(observation["trick_number"]).item()) >= 1
    assert isinstance(observation["team"], int)


def test_allowed_actions_are_legal() -> None:
    """Every non-zero allowed action belongs to the legal move set."""
    _game, rl_players = _solo_game()
    rl_player = rl_players[0]
    allowed = [int(action) for action in _int64(rl_player.observe()["allowed_actions"])]
    for action in allowed:
        assert action == 0 or rl_player._check_legal_action(action)
    assert any(action != 0 for action in allowed)


def test_check_legal_action_rejects_illegal() -> None:
    """Action 0 (the padded placeholder) is never a legal action."""
    _game, rl_players = _solo_game()
    assert rl_players[0]._check_legal_action(0) is False


def test_rl_player_learning_hook_raises() -> None:
    """RLPlayerLearning refuses the abstract single-move hook by design."""
    _game, rl_players = _solo_game()
    with pytest.raises(RuntimeError):
        rl_players[0]._play_card(rl_players[0]._allowed_cards())


def test_get_team_obs_caller_solo() -> None:
    """For a solo caller the team distribution marks only the own seat with 1."""
    game, rl_players = _solo_game(caller_seat=0)
    caller = rl_players[0]
    team_obs = caller._get_team_obs()
    assert team_obs[game.players.index(caller)] == 1.0
    assert np.allclose(np.unique(team_obs), [0.33, 1.0])


def test_get_team_obs_solo_non_calling_legacy() -> None:
    """Legacy quirk: with a set teammate list the player/team comparison always fails."""
    _game, rl_players = _solo_game(caller_seat=0)
    team_obs = rl_players[1]._get_team_obs()
    assert np.all(team_obs == 0.0)


def test_get_team_obs_ramsch() -> None:
    """In ramsch (no caller) the own seat gets 1 and every other seat 0.5."""
    players: list[Player] = [ForcedRamschRLPlayer(i) for i in range(4)]
    game = PublicGameState(players, starting_pos=2)
    game.start_game(seed=7)
    player = players[1]
    assert isinstance(player, ForcedRamschRLPlayer)
    team_obs = player._get_team_obs()
    assert team_obs[game.players.index(player)] == 1.0
    others = [team_obs[i] for i in range(len(players)) if i != game.players.index(player)]
    assert all(value == 0.5 for value in others)


def test_observe_tracks_played_cards() -> None:
    """A played card shows up in the played_cards vector of the RL player."""
    game, rl_players = _solo_game(caller_seat=3)
    before = int(_int64(rl_players[0].observe()["played_cards"]).sum())
    assert game.playing_order is not None
    game.player_turn(game.playing_order[0])
    after = int(_int64(rl_players[0].observe()["played_cards"]).sum())
    assert after == game.cards_played[0].model_id
    assert after > before


def test_rl_subclass_contract() -> None:
    """RLPlayerLearning is an RL subclass with the default contra/retour answers."""
    player = RLPlayerLearning(0)
    assert isinstance(player, RL)
    assert player.contra() is False
    assert player.retour() is False
    chosen_game, chosen_color = player.choose_gametype_rule()
    assert chosen_game in Game
    assert chosen_color in Color
