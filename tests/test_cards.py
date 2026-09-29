"""Tests for the deck and card mechanics."""

from schafkopfrl.schafkopfengine.cards import Card, Deck
from schafkopfrl.schafkopfengine.players.dummy_player import DummyPlayer
from schafkopfrl.schafkopfengine.players.player import Player
from schafkopfrl.schafkopfengine.public_gamestate import PublicGameState
from schafkopfrl.schafkopfengine.rules.rules import Rules
from schafkopfrl.schafkopfengine.utils.enums import Color, Game, Rank


def test_deck_has_32_cards() -> None:
    """A new deck contains the full 32 Schafkopf cards."""
    deck = Deck()
    assert len(deck.cards) == 32


def test_default_trump_suit() -> None:
    """In the default configuration the Herz cards and all obers/unters are trumps."""
    deck = Deck()
    # The trump list is computed during the first (no-op) rule adjustment.
    deck.adjust_cards(Rules.create(Game.RAMSCH, Color.NONE))
    trumps = deck.trumps
    assert len(trumps) == 14
    assert all(card.is_trump for card in trumps)
    assert trumps[0] > trumps[-1]


def test_deck_categories() -> None:
    """The color and rank category lookup tables are filled correctly.

    Note: The ober/unter cards are filed by rank, so each color category holds six cards.
    """
    deck = Deck()
    assert len(deck._cards_category[Color.HERZ]) == 6
    assert len(deck._cards_category[Rank.OBER]) == 4
    assert len(deck._cards_category[Rank.UNTER]) == 4
    assert len(deck._cards_category[Rank.ACE]) == 4
    assert all(len(deck._cards_category[color]) == 6 for color in list(Color) if color != Color.NONE)


def test_shuffle_reorders_but_keeps_cards() -> None:
    """Shuffling changes the order but not the membership of the deck."""
    deck = Deck()
    original = list(deck.cards)
    shuffled = deck.shuffel_cards(seed=42)
    assert set(shuffled) == set(original)
    assert len(shuffled) == 32


def test_deal_cards_deals_eight_each() -> None:
    """Dealing hands each player exactly eight cards covering the full deck."""
    players: list[Player] = [DummyPlayer(i) for i in range(4)]
    # Players need an attached game state before taking cards.
    PublicGameState(players, starting_pos=0)
    deck = Deck()
    deck.deal_cards(players, seed=7)
    dealt: set[Card] = set()
    for player in players:
        assert len(player.cards) == 8
        dealt.update(player.cards)
    assert dealt == set(deck.cards)


def test_reset_deck_recalculates_trumps() -> None:
    """Resetting the deck restores the default trump flags and ranks."""
    deck = Deck()
    deck.adjust_cards(Rules.create(Game.WENZ, Color.NONE))
    deck.reset_deck()

    heart_ace = next(card for card in deck.cards if card.color == Color.HERZ and card.rank == Rank.ACE)
    eichel_ober = next(card for card in deck._cards_category[Rank.OBER] if card.color == Color.EICHEL)
    eichel_seven = next(card for card in deck.cards if card.color == Color.EICHEL and card.rank == Rank.SEVEN)
    assert heart_ace.is_trump == 1
    assert eichel_ober.is_trump == 1
    assert eichel_ober.rank == Rank.OBER
    assert eichel_seven.is_trump == 0


def test_wenz_removes_hearts_and_downgrades_ober() -> None:
    """In Wenz all heart cards stop being trumps and the obers are downgraded."""
    deck = Deck()
    deck.adjust_cards(Rules.create(Game.WENZ, Color.NONE))
    heart = deck._cards_category[Color.HERZ][0]
    assert not heart.is_trump
    ober = deck._cards_category[Rank.OBER][0]
    assert ober.rank == Rank.OBER_LOW


def test_fablwenz_called_color_trump() -> None:
    """In a Farbwenz the called color becomes trump and the other obers are downgraded.

    The untern remain trumps, as in the real game.
    """
    deck = Deck()
    deck.adjust_cards(Rules.create(Game.FARBWENZ, Color.EICHEL))
    for card in deck.cards:
        if card.color == Color.EICHEL:
            assert card.is_trump
        if card.color == Color.GRAS and card.rank != Rank.UNTER:
            assert not card.is_trump
        if card.rank == Rank.UNTER:
            assert card.is_trump
    for card in deck._cards_category[Rank.OBER]:
        if card.color == Color.EICHEL:
            assert card.rank == Rank.OBER_LOW
            assert card.is_trump
        else:
            assert card.rank == Rank.OBER_LOW
            assert not card.is_trump


def test_fablwenz_hearts_special_case() -> None:
    """A Farbwenz on heart keeps its trumps but downgrades the other obers."""
    deck = Deck()
    deck.adjust_cards(Rules.create(Game.FARBWENZ, Color.HERZ))
    for card in deck._cards_category[Color.HERZ]:
        assert card.is_trump
    for card in deck._cards_category[Rank.OBER]:
        if card.color != Color.HERZ:
            assert card.rank == Rank.OBER_LOW
            assert not card.is_trump


def test_solo_swaps_trump_suit() -> None:
    """A solo moves the trump status from hearts to the solo color."""
    deck = Deck()
    deck.adjust_cards(Rules.create(Game.SOLO, Color.GRAS))
    grass_ace = next(card for card in deck.cards if card.color == Color.GRAS and card.rank == Rank.ACE)
    heart_king = next(card for card in deck.cards if card.color == Color.HERZ and card.rank == Rank.KING)
    gras_seven = next(card for card in deck.cards if card.color == Color.GRAS and card.rank == Rank.SEVEN)
    assert grass_ace.is_trump
    assert gras_seven.is_trump
    assert not heart_king.is_trump


def test_sauspiel_and_ramsch_keep_defaults() -> None:
    """Sauspiel and ramsch do not change the default trump configuration."""
    deck = Deck()
    deck.adjust_cards(Rules.create(Game.SAUSPIEL, Color.HERZ))
    assert len(deck.trumps) == 14
    deck.adjust_cards(Rules.create(Game.RAMSCH, Color.NONE))
    assert len(deck.trumps) == 14


def test_card_adjust_returns_self() -> None:
    """Card adjustments mutate the card in place and return it for chaining."""
    card = Card(Color.EICHEL, Rank.KING, 4, 1)
    result = card.adjust(is_trump=1, score=2).adjust(rank=Rank.TEN)
    assert result is card
    assert card.is_trump == 1
    assert card.score == 2
    assert card.rank == Rank.TEN


def test_card_trump_beats_non_trump() -> None:
    """A trump card beats any non-trump card."""
    trump = Card(Color.HERZ, Rank.ACE, 11, 1).adjust(is_trump=1)
    non_trump = Card(Color.EICHEL, Rank.ACE, 11, 2)
    assert trump > non_trump
    assert non_trump < trump
    assert not non_trump > trump


def test_card_color_beats_other_color() -> None:
    """For different colors the first played card (left side) always wins."""
    eichel = Card(Color.EICHEL, Rank.SEVEN, 0, 1)
    gras = Card(Color.GRAS, Rank.ACE, 11, 2)
    assert eichel > gras
    # The ordering is not transitive: the left-hand card always wins over a different color.
    assert gras > eichel
    assert not gras < eichel


def test_card_rank_ordering_same_color() -> None:
    """Inside one suit the higher rank wins."""
    lower = Card(Color.EICHEL, Rank.SEVEN, 0, 1)
    higher = Card(Color.EICHEL, Rank.ACE, 11, 2)
    assert higher > lower
    assert lower < higher
    assert not higher > higher


def test_trump_rank_ordering() -> None:
    """Trumps compare by their rank ids, which put ober above unter above ace."""
    unter = Card(Color.GRAS, Rank.UNTER, 2, 1).adjust(is_trump=1)
    ober = Card(Color.EICHEL, Rank.OBER, 3, 2).adjust(is_trump=1)
    ace = Card(Color.HERZ, Rank.ACE, 11, 3).adjust(is_trump=1)

    assert ober > unter
    assert unter > ace
    assert ace < ober


def test_card_repr_contains_metadata() -> None:
    """The repr exposes color, rank, score, trump flag and the model id."""
    card = Card(Color.HERZ, Rank.ACE, 11, 21).adjust(is_trump=1)
    text = repr(card)
    assert "HERZ" in text
    assert "ACE" in text
    assert "S:11" in text
    assert "T:1" in text
    assert "ID:21" in text
