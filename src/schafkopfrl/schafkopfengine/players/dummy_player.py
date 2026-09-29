"""Dummy player implementations for the Schafkopf engine."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from schafkopfrl.schafkopfengine.players.player import Player
from schafkopfrl.schafkopfengine.utils.enums import Color, Game

if TYPE_CHECKING:
    from schafkopfrl.schafkopfengine.cards import Card


class DummyPlayer(Player):
    """This is a dummy player, always playing the highest card."""

    def __init__(self, uid: int) -> None:
        """Initialize the dummy player with its unique id.

        Args:
            uid: Unique player id.
        """
        super().__init__(uid)

    def _play_card(self, allowed_cards: list[Card]) -> Card:
        """Return the highest allowed card of the hand."""
        return sorted(allowed_cards, key=lambda card: (card.is_trump, card.rank, card.color), reverse=True)[0]

    def choose_gametype(self) -> tuple[Game, Color]:
        """Return a randomly chosen game type and color."""
        allowed_gametypes, allowed_color = self._allowed_gametypes()

        random_game = random.choice(allowed_gametypes)  # noqa: S311 Intentional non-cryptographic game randomness.

        if random_game in {Game.RAMSCH, Game.WENZ}:
            return random_game, Color.NONE
        if random_game == Game.SAUSPIEL:
            return random_game, random.choice(allowed_color)  # noqa: S311 Intentional non-cryptographic game randomness.
        if random_game in {Game.FARBWENZ, Game.SOLO}:
            return random_game, random.choice(  # noqa: S311 Intentional non-cryptographic game randomness.
                [color for color in Color if color != Color.NONE]
            )

        raise RuntimeError(f"Unsupported game type: {random_game.name}")

    def contra(self) -> bool:
        """Never call Contra."""
        return False  # random.randint(0,1)

    def retour(self) -> bool:
        """Never call Retour."""
        return False  # random.randint(0,1)

    def _reset(self) -> None:
        super()._reset()

    def observe(self) -> None:
        """This player has no observation space."""
