"""Tests for the training factory helpers."""

from schafkopfrl.schafkopfengine.players.dummy_player import DummyPlayer
from schafkopfrl.schafkopfengine.players.random_player import RandomSauPlayer
from schafkopfrl.schafkopfengine.players.rl_player import RLPlayerLearning
from schafkopfrl.schafkopfgym.training.rl_training import make_players_rng, make_players_tholu


def test_make_players_rng() -> None:
    """The random setup pairs one learning player with random opponents."""
    players = make_players_rng()
    assert len(players) == 4
    assert isinstance(players[0], RLPlayerLearning)
    assert all(isinstance(player, RandomSauPlayer) for player in players[1:])
    assert [player.id for player in players] == [0, 1, 2, 3]


def test_make_players_tholu() -> None:
    """The tholu setup ends with a dummy player acting as the computer opponent."""
    players = make_players_tholu()
    assert len(players) == 4
    assert isinstance(players[0], RLPlayerLearning)
    assert all(isinstance(player, RandomSauPlayer) for player in players[1:3])
    assert isinstance(players[3], DummyPlayer)
