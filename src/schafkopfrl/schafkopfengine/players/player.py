"""Player implementations for the Schafkopf engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, final

from schafkopfrl.schafkopfengine.cards import Card
from schafkopfrl.schafkopfengine.rules.rules import Sauspiel
from schafkopfrl.schafkopfengine.utils.enums import Color, Game, Rank, Team

if TYPE_CHECKING:
    from schafkopfrl.schafkopfengine.public_gamestate import PublicGameState

# from schafkopfrl.utils.log import get_logger
# logger = get_logger('Player')


class Player(ABC):
    """Abstract base class for all Schafkopf players."""

    def __init__(self, uid: int) -> None:
        """Initialize the player with its unique id.

        Args:
            uid: Unique player id.
        """
        super().__init__()
        self.id = uid
        self._seat: int | None = None
        self.cards: list[Card] = []
        self.colors: dict[Color, int] = {color: 0 for color in Color if color is not Color.NONE}
        self.aces: dict[Color, int] = {color: 0 for color in Color if color is not Color.NONE}
        self.trumps: list[Card] = []
        self.team: Team | None = None
        self.teammember: Player | list[Player] | None = None
        # False before the ruf is known; the rufsau Card itself afterwards.
        self.has_rufsau: Card | bool = False
        self._publicgamestate: PublicGameState | None = None

    #    def contra_retour_update(self):
    #        if not self.teammember:
    #
    #            if self.team == Team.NONCALLINGTEAM:
    #                if self != self._publicgamestate.contra_player:
    #                    self.teammember = self._publicgamestate.contra_player
    #                if self._publicgamestate.contra_player != self._publicgamestate.calling_player:
    #
    #
    #            if self.team == Team.CALLINGTEAM and self != self._publicgamestate.retour_player:
    #                self.teammember = self._publicgamestate.retour_player

    @final
    def choose_gametype_rule(
        self, color_threshold: int = 2, trumps_threshold: int = 4, trump_strengh_threshold: int = 2
    ) -> tuple[Game, Color]:
        """Ensure that all players play under the same setting.

        For training this can be adjusted within the player.

        Args:
            color_threshold: Maximum number of colors to start a Sau.
            trumps_threshold: Minimum number of trumps to start a Sau.
            trump_strengh_threshold: Minimum number of strong trumps to start a Sau.
        """
        games, colors = self._allowed_gametypes()
        strong_trumps = 0
        for card in self.cards:
            if card.is_trump and card.rank >= Rank.UNTER:
                strong_trumps += 1
        if (
            Game.SAUSPIEL in games
            and len(colors) <= color_threshold
            and len(self.trumps) >= trumps_threshold
            and strong_trumps >= trump_strengh_threshold
        ):
            min_count = 99
            for color in colors:
                c_count = len([card for card in self.cards if card.color == color and not card.is_trump])
                if c_count <= min_count:
                    color_to_play = color
            return Game.SAUSPIEL, color_to_play
        return Game.RAMSCH, Color.NONE

    #########################
    ### Start Game Update ###
    #########################

    @final
    def add_gamestate(self, publicgamestate: PublicGameState) -> None:
        """Store the public gamestate of the current round.

        Args:
            publicgamestate: Public gamestate object of the round.
        """
        self._reset()
        self._publicgamestate = publicgamestate

    @final
    def _set_initial_team(self) -> None:
        """Set the team based on the information given by the game_search class."""
        assert self._publicgamestate is not None  # noqa: S101 Internal invariant debug check.
        if self == self._publicgamestate.calling_player:
            self.team = Team.CALLINGTEAM

        elif self._publicgamestate.game_id == Game.SAUSPIEL and self.has_rufsau:
            self.team = Team.CALLINGTEAM
            self.teammember = self._publicgamestate.calling_player
        elif self._publicgamestate.game_id == Game.RAMSCH:
            self.team = Team.NONCALLINGTEAM
        else:
            self.team = Team.NONCALLINGTEAM
            self.teammember = [
                player for player in self._publicgamestate.players if player != self._publicgamestate.calling_player
            ]

        self._publicgamestate.team.append(self.team)

    def found_game_update(self) -> None:
        """Update the player after the game type was found."""
        self.check_cards(pre_game=False)
        self._sort_cards()
        self._set_initial_team()

    def check_cards(self, pre_game: bool) -> None:
        """Count the cards of the hand and update the color and trump counters.

        Args:
            pre_game: Whether the game type is not known yet.
        """
        # Since at start there is no game_id it need to be skiped.
        assert self._publicgamestate is not None  # noqa: S101 Internal invariant debug check.
        if pre_game:
            for card in self.cards:
                if not card.is_trump:
                    self.colors[card.color] += 1
                    if card.rank == Rank.ACE:
                        self.aces[card.color] += 1
                else:
                    self.trumps.append(card)

        elif self._publicgamestate.game_id == Game.SAUSPIEL:
            # Adding if player has rufsau.
            if self.aces[self._publicgamestate.game_color]:
                assert self._publicgamestate.game_sau is not None  # noqa: S101 Internal invariant debug check.
                self.has_rufsau = self._publicgamestate.game_sau

        else:
            # Recalculated cards, if other gametype.
            self.colors = {color: 0 for color in Color if color is not Color.NONE}
            self.aces = {color: 0 for color in Color if color is not Color.NONE}
            self.trumps = []

            for card in self.cards:
                if not card.is_trump:
                    self.colors[card.color] += 1
                    if card.rank == Rank.ACE:
                        self.aces[card.color] += 1
                else:
                    self.trumps.append(card)

    @final
    def take_cards(self, cards: list[Card]) -> None:
        """Take the dealt cards of the player.

        Args:
            cards: The cards dealt to the player.
        """
        self.cards = cards
        self.check_cards(pre_game=True)
        self._sort_cards()

    #####################
    ### Heavy Lifting ###
    #####################

    @final
    def _allowed_gametypes(self) -> tuple[list[Game], list[Color]]:
        """This method returns the allowed gametypes the player is allowed to choose form."""
        allowed = [
            Game.RAMSCH,
            Game.FARBWENZ,
            Game.WENZ,
            Game.SOLO,
        ]  # Always allowed.

        allowed_sauspiel_color = []

        if self.colors[Color.SCHELLEN] and not self.aces[Color.SCHELLEN]:
            allowed_sauspiel_color += [Color.SCHELLEN]
        if self.colors[Color.GRAS] and not self.aces[Color.GRAS]:
            allowed_sauspiel_color += [Color.GRAS]
        if self.colors[Color.EICHEL] and not self.aces[Color.EICHEL]:
            allowed_sauspiel_color += [Color.EICHEL]

        if allowed_sauspiel_color:
            allowed += [Game.SAUSPIEL]

        return allowed, allowed_sauspiel_color

    @final
    def _allowed_cards(self) -> list[Card]:
        """Return the cards that the player is allowed to play.

        The Rules class should have an
        - Check if first player?
            - Check if "Gerufene" in hand? Yes
                - 4 gerufene Farbe? Yes
                    - Alle Karten.
                - nein
                    - Nicht "Gerufene"

        - Already cards played
            - Trump played?
                - Trumps

            - First Card color in hands? Yes
                -   Sau-Zugeben. (Davongelaufen nicht zugeben)
                -   Zugeben.
            - First Card color in hands? No
                -   All cards.
        """
        assert self._publicgamestate is not None  # noqa: S101 Internal invariant debug check.
        played_cards = self._publicgamestate.trick_current_cards

        if len(played_cards) == 0:
            if self._publicgamestate.game_id == Game.SAUSPIEL and self.has_rufsau:
                if self._check_davonlaufen():
                    return self.cards
                return [
                    card
                    for card in self.cards
                    if card.color != self._publicgamestate.game_color or card.is_trump or card.rank == Rank.ACE
                ]
            return self.cards

        if len(self.cards) == 1:
            return self.cards

        first_card = played_cards[0]

        if first_card.is_trump:
            if len(self.trumps) > 0:
                # Trumpf zugeben.
                return self.trumps

            # Trumpf frei.
            self._publicgamestate.trumps_left_player[self] = False
            return [card for card in self.cards if card != self.has_rufsau]

        if not first_card.is_trump:
            if self._publicgamestate.game_id == Game.SAUSPIEL:  # noqa: SIM102
                # Bedienpflicht hier kein davonlaufen möglich.
                if (
                    isinstance(self._publicgamestate.gametype, Sauspiel)
                    and first_card.color == self._publicgamestate.gametype.searched_color
                    and isinstance(self.has_rufsau, Card)
                ):
                    return [self.has_rufsau]

            if self.colors[first_card.color] > 0:
                return [card for card in self.cards if card.color == first_card.color and not card.is_trump]

            # Farb frei.
            self._publicgamestate.colors_left_player[self][first_card.color] = False
            return [card for card in self.cards if card != self.has_rufsau]

    def _check_davonlaufen(self) -> bool:
        assert self._publicgamestate is not None  # noqa: S101 Internal invariant debug check.
        return bool(self.has_rufsau) and self.colors[self._publicgamestate.game_color] >= 4

    ################
    ### Abstract ###
    ################

    @abstractmethod
    def observe(self) -> object:
        """Return the observation of the player for the game."""
        pass

    @abstractmethod
    def _reset(self) -> None:
        self.cards = []
        self.team = None
        self.teammember = None
        self.has_rufsau = False
        self.colors = {color: 0 for color in Color if color is not Color.NONE}
        self.aces = {color: 0 for color in Color if color is not Color.NONE}
        self.trumps = []
        # self._publicgamestate = None

    @abstractmethod
    def contra(self) -> bool:
        """Return True if the player declares Contra."""
        pass

    @abstractmethod
    def retour(self) -> bool:
        """Return True if the player declares Retour."""
        pass

    @abstractmethod
    def _play_card(self, allowed_cards: list[Card]) -> Card:
        pass

    def play_card(self, action: int | None = None) -> Card:
        """Return the card played from the allowed cards of the player."""
        allowed_cards = self._allowed_cards()
        selected_card = self._play_card(allowed_cards)
        self._decount_card(selected_card)

        return selected_card

    @abstractmethod
    def choose_gametype(self) -> tuple[Game, Color]:
        """This method returns the gametype and the color, that the player choose."""

    def _decount_card(self, card: Card) -> None:
        assert self._publicgamestate is not None  # noqa: S101 Internal invariant debug check.
        if self._publicgamestate.game_id == Game.SAUSPIEL and card == self._publicgamestate.game_sau:
            self.has_rufsau = False

        if card.is_trump:
            self.trumps.remove(card)

        else:
            if card.rank != Rank.ACE:
                self.colors[card.color] -= 1

            else:
                self.colors[card.color] -= 1
                self.aces[card.color] -= 1

        self.cards.remove(card)

    ##############
    ### Things ###
    ##############

    @final
    def _sort_cards(self) -> None:
        self.cards = sorted(self.cards, key=lambda card: (card.is_trump, card.rank, card.color), reverse=True)

    ###########
    ### Log ###
    ###########

    @final
    def log_player(self) -> None:
        """Build the log message for the current turn of the player."""
        _msg = (
            f"### TURN: {self} ###\n"
            + "Handcards:\n"
            + ("").join([f"{card}" if idx % 3 != 2 else f"{card}\n" for idx, card in enumerate(self.cards)])
            + "\n"
            + f"Teammember:\n{self.teammember}\n"
            + f"Has Sau:\n{self.has_rufsau if self.has_rufsau else '----'}"
            + "\n####################\n"
        )
        # logger.info(_msg)
        # print(_msg)

    def __repr__(self) -> str:
        """Return the string representation of the player."""
        msg = f"Player ID {self.id}, {str(type(self)).split('.')[-1][:-2]}"
        return msg
