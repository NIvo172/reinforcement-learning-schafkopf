"""Random player implementations for the Schafkopf engine."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from schafkopfrl.schafkopfengine.players.player import Player
from schafkopfrl.schafkopfengine.utils.enums import Color, Game

if TYPE_CHECKING:
    from schafkopfrl.schafkopfengine.cards import Card


class RandomPlayer(Player):
    """This is a random player."""

    def __init__(self, uid: int) -> None:
        """Initialize the random player with its unique id.

        Args:
            uid: Unique player id.
        """
        super().__init__(uid)
        self._colors = [color for color in Color if color != Color.NONE]

    def _play_card(self, allowed_cards: list[Card]) -> Card:
        return random.choice(allowed_cards)  # noqa: S311 Intentional non-cryptographic game randomness.

    def choose_gametype(self) -> tuple[Game, Color]:
        """Return a randomly chosen game type and color."""
        allowed_gametypes, allowed_color = self._allowed_gametypes()

        random_game = random.choice(allowed_gametypes)  # noqa: S311 Intentional non-cryptographic game randomness.

        if random_game in {Game.RAMSCH, Game.WENZ}:
            return random_game, Color.NONE
        if random_game == Game.SAUSPIEL:
            return random_game, random.choice(allowed_color)  # noqa: S311 Intentional non-cryptographic game randomness.
        if random_game in {Game.FARBWENZ, Game.SOLO}:
            return random_game, random.choice(self._colors)  # noqa: S311 Intentional non-cryptographic game randomness.

        raise RuntimeError(f"Unsupported game type: {random_game.name}")

    def contra(self) -> bool:
        """Return a random Contra decision."""
        return bool(random.randint(0, 1))  # noqa: S311 Intentional non-cryptographic game randomness.

    def retour(self) -> bool:
        """Return a random Retour decision."""
        return bool(random.randint(0, 1))  # noqa: S311 Intentional non-cryptographic game randomness.

    def _reset(self) -> None:
        super()._reset()

    def observe(self) -> None:
        """This player has no observation space."""


class RandomSauPlayer(RandomPlayer):
    """This is a random player, that always chooses rufspiel."""

    def __init__(self, uid: int) -> None:
        """Initialize the random Sau player with its unique id.

        Args:
            uid: Unique player id.
        """
        super().__init__(uid)

    def choose_gametype(self) -> tuple[Game, Color]:
        """Choose the game type according to the standard rule."""
        return self.choose_gametype_rule()

    def contra(self) -> bool:
        """Never call Contra."""
        return False

    def retour(self) -> bool:
        """Never call Retour."""
        return False
