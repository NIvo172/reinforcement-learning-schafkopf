"""Cards and deck for the Schafkopf engine."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from schafkopfrl.schafkopfengine.rules.rules import Rules
from schafkopfrl.schafkopfengine.utils.enums import CARD_MODEL_ID, Color, Game, Rank, Score

if TYPE_CHECKING:
    from schafkopfrl.schafkopfengine.players.player import Player


class Deck:
    """A deck of 32 Schafkopf cards.

    If I would like to extend this class, so that I could configure different games, like druids, I would need to remove
    the default stuff from schafkopf. This would mean that I would have to change the scoring value too. This could be
    done by adding it to the card_setting. I will keep the score as a default mapping since this.
    """

    def __init__(self) -> None:
        """Create a fresh Schafkopf deck."""
        self.cards: list[Card] = []
        self.trumps: list[Card] = []

        self._cards_category: dict[Color | Rank, list[Card]] = {
            Color.HERZ: [],
            Color.EICHEL: [],
            Color.SCHELLEN: [],
            Color.GRAS: [],
            Rank.OBER: [],
            Rank.UNTER: [],
            Rank.ACE: [],
        }
        self._init_deck()

    def _init_deck(self) -> None:
        """This method creates a "fresh" deck with new cards."""
        self.cards.clear()
        excluded_ranks = {Rank.UNTER_LOW, Rank.OBER_LOW}

        for color in Color:
            if color != Color.NONE:
                for rank in Rank:
                    if rank not in excluded_ranks:
                        card = Card(color, rank, Score[rank], model_id=CARD_MODEL_ID[(color, rank)])
                        if card.rank == Rank.OBER or card.rank == Rank.UNTER or card.color == Color.HERZ:
                            card.adjust(is_trump=1)
                            if card.rank == Rank.OBER or card.rank == Rank.UNTER:
                                self._cards_category[card.rank].append(card)
                            else:
                                self._cards_category[card.color].append(card)
                                if card.rank == Rank.ACE:
                                    self._cards_category[card.rank].append(card)
                        else:
                            self._cards_category[card.color].append(card)
                            if card.rank == Rank.ACE:
                                self._cards_category[card.rank].append(card)

                        self.cards.append(card)

    def reset_deck(self) -> Deck:
        """Reset all cards to the default Schafkopf configuration."""
        for card in self.cards:
            if card.color == Color.HERZ:
                card.adjust(is_trump=1)
            elif card.rank == Rank.OBER or card.rank == Rank.OBER_LOW:
                card.adjust(is_trump=1, rank=Rank.OBER)
            elif card.rank == Rank.UNTER or card.rank == Rank.UNTER_LOW:
                card.adjust(is_trump=1, rank=Rank.UNTER)
            else:
                card.adjust(is_trump=0)

        return self

    def adjust_cards(self, gametype: Rules) -> None:
        """Adjust the card attributes according to the given gametype.

        Both the value and the trump attribute of the cards can change, e.g. for Wenz the obers lose their trump
        attribute.

        Args:
            gametype: The rules of the game type to configure the deck for.
        """
        if gametype.gameid == Game.RAMSCH or gametype.gameid == Game.SAUSPIEL:
            # No adjustments needed.
            pass

        if gametype.gameid == Game.WENZ:
            for card in self._cards_category[Rank.OBER]:
                card.adjust(is_trump=0, rank=Rank.OBER_LOW)

            for card in self._cards_category[Color.HERZ]:
                card.adjust(is_trump=0)

        if gametype.gameid == Game.FARBWENZ:
            if gametype.trump_color == Color.HERZ:
                for card in self._cards_category[Rank.OBER]:
                    if card.color != gametype.trump_color:
                        card.adjust(is_trump=0, rank=Rank.OBER_LOW)
                    else:
                        card.adjust(is_trump=1, rank=Rank.OBER_LOW)
            else:
                for card in self._cards_category[gametype.trump_color]:
                    card.adjust(is_trump=1)

                for card in self._cards_category[Color.HERZ]:
                    card.adjust(is_trump=0)

                for card in self._cards_category[Rank.OBER]:
                    if card.color == gametype.trump_color:
                        card.adjust(is_trump=1, rank=Rank.OBER_LOW)
                    else:
                        card.adjust(is_trump=0, rank=Rank.OBER_LOW)

        if gametype.gameid == Game.SOLO:
            # No change needed if Herz solo.
            if gametype.trump_color == Color.HERZ:
                pass
            else:
                for card in self._cards_category[Color.HERZ]:
                    card.adjust(is_trump=0)
                for card in self._cards_category[gametype.trump_color]:
                    card.adjust(is_trump=1)

        self._get_trumps()

    def deal_cards(self, players: list[Player], seed: int | None = None) -> None:
        """Deal eight cards to each player.

        Args:
            players: The players that receive the cards.
            seed: Optional seed for the shuffle.
        """
        shuffled_cards = self.shuffel_cards(seed=seed)

        for player in players:
            player.take_cards(shuffled_cards[:8])
            shuffled_cards = shuffled_cards[8:]

    def _get_trumps(self) -> None:
        trumps = [card for card in self.cards if card.is_trump]
        trumps = sorted(trumps, key=lambda card: (card.rank, card.color), reverse=True)
        self.trumps = trumps

    def shuffel_cards(self, seed: int | None = None) -> list[Card]:
        """Shuffle the deck and return the shuffled cards.

        Args:
            seed: Optional seed for the shuffle.
        """
        shuffled_cards = self.cards[:]
        random.shuffle(shuffled_cards)
        return shuffled_cards


class Card:
    """A single card of a card game.

    In every card game there are different kind of cards, different color, value, score and if the card is a trump. All
    card games will have cards with color and value. In some card games the colors have a partial ranking, in others they
    don't have a ranking. This and other factors lead to me not going to try to implement all card games, but schafkopf
    only. So there will be code that is specific for schafkopf. E.g. ``__repr__`` color has ranking.
    """

    def __init__(self, color: Color, rank: Rank, score: int, model_id: int) -> None:
        """Create a card with its initial color, rank, score and model id.

        Args:
            color: The color of the card.
            rank: The rank of the card.
            score: The score value of the card.
            model_id: The unique model id of the card.
        """
        self.model_id = model_id
        self.id = (color, rank)
        self.color = color
        self.rank = rank
        self.score = score
        self.is_trump = 0

    def adjust(
        self,
        rank: Rank | None = None,
        is_trump: int | None = None,
        score: int | None = None,
        model_id: int | None = None,
    ) -> Card:
        """This adjusts the cards value, trump and score attribute."""
        if rank is not None:
            self.rank = rank
        if is_trump is not None:
            self.is_trump = is_trump
        if score is not None:
            self.score = score
        if model_id is not None:
            self.model_id = model_id
        return self

    def __repr__(self) -> str:  # noqa: D105 Docstring for repr excluded by convention.
        return f"[{self.id[0].name}, {self.id[1].name}, S:{self.score}, T:{self.is_trump}, ID:{self.model_id}]"

    def __gt__(self, other: Card) -> bool:
        """Check if this card is greater than another card.

        The leftside card is treated like it is the first card and would be greater then the rightside card, if the
        colors differ.

        Args:
            other: The card to compare against.
        """
        # Easy trump comparison
        if self.is_trump > other.is_trump:
            return True
        if self.is_trump < other.is_trump:
            return False

        # From here self.is_trump == other.is_trump

        if not self.is_trump:
            # Different color played
            if self.color != other.color:
                return True
            if self.rank > other.rank:  # noqa: SIM103
                return True
            return False

        if self.rank > other.rank:
            return True

        if self.rank == other.rank:
            return self.color > other.color

        return False

    def __lt__(self, other: Card) -> bool:
        """Check if this card is smaller than another card.

        Args:
            other: The card to compare against.
        """
        return not (self > other)


def main() -> None:
    """Create a deck and print all its cards."""
    deck = Deck()
    for card in deck.cards:
        print(card)  # noqa: T201 Intentional interactive/CLI output.


if __name__ == "__main__":
    main()
