"""Shared fixtures and helpers for the Schafkopf test suite."""

import pytest

from schafkopfrl.schafkopfengine.players.player import Player
from schafkopfrl.schafkopfengine.players.random_player import RandomPlayer
from schafkopfrl.schafkopfengine.public_gamestate import PublicGameState
from schafkopfrl.schafkopfengine.utils.enums import Color, Game


class ForcedGamePlayer(RandomPlayer):
    """A random player that always chooses a fixed game type."""

    def __init__(self, uid: int, gametype: Game, color: Color = Color.NONE) -> None:
        super().__init__(uid)
        self.fixed_gametype = gametype
        self.fixed_color = color

    def choose_gametype(self) -> tuple[Game, Color]:
        """Return the fixed game type and color."""
        return self.fixed_gametype, self.fixed_color


class FixedContraPlayer(RandomPlayer):
    """A random player whose contra and retour answers are fixed."""

    def __init__(self, uid: int, contra: bool, retour: bool) -> None:
        super().__init__(uid)
        self.fixed_contra = contra
        self.fixed_retour = retour

    def contra(self) -> bool:
        """Return the fixed contra decision."""
        return self.fixed_contra

    def retour(self) -> bool:
        """Return the fixed retour decision."""
        return self.fixed_retour


def make_player_team(player_cls: type[Player] = RandomPlayer) -> list[Player]:
    """Build a team of four players of the given class."""
    return [player_cls(i) for i in range(4)]


def run_full_game(
    players: list[Player] | None = None,
    seed: int = 0,
    starting_pos: int = 0,
) -> PublicGameState:
    """Play a complete game between the given players and return the evaluated state.

    Args:
        players: Optional team of four players; random players by default.
        seed: Seed for the deck shuffle.
        starting_pos: Seat position of the dealer.

    Returns:
        The evaluated public game state after all 32 cards have been played.
    """
    if players is None:
        players = make_player_team()
    game = PublicGameState(list(players), starting_pos=starting_pos)
    nxt_player = game.start_game(seed=seed)
    for _ in range(32):
        nxt_player = game.player_turn(nxt_player)
    game.evaluate()
    return game


@pytest.fixture
def random_players() -> list[Player]:
    """Return a fresh team of four random players."""
    return make_player_team()


@pytest.fixture
def game_seed() -> list[int]:
    """Return a list of deck seeds used to vary the dealt hands."""
    return [1, 7, 42]
