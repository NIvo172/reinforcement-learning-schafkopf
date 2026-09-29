"""Interactive human player for the Schafkopf engine."""

from __future__ import annotations

from typing import TYPE_CHECKING

from schafkopfrl.schafkopfengine.players.player import Player
from schafkopfrl.schafkopfengine.utils.enums import Color, Game

if TYPE_CHECKING:
    from schafkopfrl.schafkopfengine.cards import Card


class HumanPlayer(Player):
    """Player that makes its decisions via interactive console input."""

    def __init__(self, uid: int) -> None:
        """Initialize the human player with its unique id.

        Args:
            uid: Unique player id.
        """
        super().__init__(uid)

    def _play_card(self, allowed_cards: list[Card]) -> Card:
        # self.log_player()

        for idx, card in enumerate(allowed_cards):
            print(f"{idx}: {card}")  # noqa: T201 Intentional interactive/CLI output.

        choosen_card = int(input(f"Choose Card 0-{len(allowed_cards) - 1}: "))

        while choosen_card <= 0 and choosen_card >= len(allowed_cards):
            choosen_card = int(input(f"Choose Card 0-{len(allowed_cards) - 1}: "))

        selected_card = allowed_cards[choosen_card]

        return selected_card

    def choose_gametype(self) -> tuple[Game, Color]:
        """Ask the user for the game type via the console."""
        # self.log_player()
        self.cards = sorted(self.cards, key=lambda card: (card.is_trump, card.rank, card.color), reverse=True)
        choosen_gametype = -1
        choosen_color = -1

        allowed_gametypes, allowed_sauspiel_colors = self._allowed_gametypes()

        for idx, gametype in enumerate(allowed_gametypes):
            print(f"{idx}. {gametype.name}")  # noqa: T201

        while choosen_gametype < 0 or choosen_gametype >= len(allowed_gametypes):
            choosen_gametype = int(input("Choose gametype: "))

        choosen_gametype = allowed_gametypes[choosen_gametype]
        print(f"Choosen game: {choosen_gametype.name}")  # noqa: T201

        if choosen_gametype == Game.SAUSPIEL:
            for idx, color in enumerate(allowed_sauspiel_colors):
                print(f"{idx}. {color.name}")  # noqa: T201
            while choosen_color < 0 or choosen_color >= len(allowed_sauspiel_colors):
                choosen_color = int(input("Choose color:"))
            choosen_color = allowed_sauspiel_colors[choosen_color]
        elif choosen_gametype == Game.WENZ or choosen_gametype == Game.RAMSCH:
            choosen_color = Color.NONE
        else:
            for idx, color in enumerate(Color):
                if color == Color.NONE:
                    continue
                print(f"{idx}. {color.name}")  # noqa: T201

            while choosen_color < 0 or choosen_color >= 4:
                choosen_color = int(input("Choose color: "))

            choosen_color = list(Color)[choosen_color]

        print(f"Choosen color: {choosen_color}")  # noqa: T201

        return choosen_gametype, choosen_color

    def contra(self) -> bool:
        """Ask the user whether to call Contra."""
        contra = input("Contra? (0: No / 1: Yes)")
        while contra != "0" and contra != "1":
            contra = input("Contra? (0: No / 1: Yes)")
        return contra == "1"

    def retour(self) -> bool:
        """Ask the user whether to call Retour."""
        retour = input("Retour? (0: No / 1: Yes)")
        while retour != "0" and retour != "1":
            retour = input("Retour? (0: No / 1: Yes)")
        return retour == "1"

    def observe(self) -> None:
        """This player has no observation space."""

    def _reset(self) -> None:
        super()._reset()
