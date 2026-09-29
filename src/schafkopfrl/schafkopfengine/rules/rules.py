"""Game types and score rules for Schafkopf."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import final

from schafkopfrl.schafkopfengine.utils.enums import DEFAULT_CARD_SETTING, Color, Game, Rank


class Rules(ABC):
    """Base class with the fixed score parameters of a Schafkopf game type."""

    @abstractmethod
    def __init__(
        self,
        gameid: Game,
        gamename: str,
        trump_color: Color,
        reward: int,
        winning_threshold: int,
        min_laufende: int,
        reward_laufende: int = 10,
    ) -> None:
        """Store the fixed score parameters of a game type.

        Args:
            gameid: The enum id of the game type.
            gamename: The name of the game type.
            trump_color: The trump color of the game.
            reward: The base reward for winning the game.
            winning_threshold: The points needed to win the game.
            min_laufende: The minimum trumps needed for a laufende reward.
            reward_laufende: The reward for a laufende.
        """
        self.gameid = gameid
        self.gamename = gamename
        self.trump_color = trump_color
        self.reward = reward
        self.winning_threshold = winning_threshold
        self.min_laufende = min_laufende
        self.reward_laufende = reward_laufende

    @staticmethod
    def create(game: Game, trump_color: Color) -> Rules:
        """Create the rule set for a game type.

        Args:
            game: The game type to create the rule set for.
            trump_color: The trump color used by the game type.
        """
        match game:
            case Game.SAUSPIEL:
                return Sauspiel(trump_color)
            case Game.SOLO:
                return Solo(trump_color)
            case Game.WENZ | Game.FARBWENZ:
                return Wenz(trump_color)
            case Game.RAMSCH:
                return Ramsch(Color.NONE)

        raise RuntimeError(f"Unsupported game type: {game.name}")

    @final
    @staticmethod
    def reward_schneider_win(points: int, amount_tricks: int) -> int:
        """This method calculates the reward for schneider and schwarz.

        Since the points differ when the playing team loses there are, two seperate methods.
        """
        reward = 0

        if amount_tricks == 0:
            # Schneider + Schwarz
            return 20

        if points >= 120 - 29:
            # Schneider
            return 10

        return reward

    @final
    @staticmethod
    def reward_schneider_loss(points: int, amount_tricks: int) -> int:
        """See ``reward_schneider_win``."""
        reward = 0

        if amount_tricks == 0:
            # Schneider + Schwarz
            return 20
        if points >= 120 - 30:
            # Schneider
            return 10

        return reward

    def __repr__(self) -> str:  # noqa: D105 Docstring for repr excluded by convention.
        return f"{self.gamename}, {self.gameid}"


class Sauspiel(Rules):
    """The scoring rules of the Sauspiel game type."""

    def __init__(self, searched_color: Color) -> None:
        """Create the Sauspiel rule set.

        Args:
            searched_color: The color of the searched ace.
        """
        super().__init__(
            gameid=Game.SAUSPIEL,
            gamename=Game.SAUSPIEL.name,
            trump_color=Color.HERZ,
            reward=20,
            winning_threshold=61,
            min_laufende=3,
        )
        self.searched_color = searched_color
        self.card_setting = DEFAULT_CARD_SETTING

    def __repr__(self) -> str:  # noqa: D105 Docstring for repr excluded by convention.
        return f"{self.gamename}, {self.searched_color.name}"


class Solo(Rules):
    """The scoring rules of the Solo game type."""

    def __init__(self, trump_color: Color) -> None:
        """Create the Solo rule set.

        Args:
            trump_color: The trump color played in the solo.
        """
        super().__init__(
            gameid=Game.SOLO,
            gamename=Game.SOLO.name,
            trump_color=trump_color,
            reward=50,
            winning_threshold=61,
            min_laufende=3,
        )
        self.card_setting = DEFAULT_CARD_SETTING


class Wenz(Rules):
    """The scoring rules of the Wenz and Farbwenz game types."""

    def __init__(self, trump_color: Color) -> None:
        """Create the Wenz rule set.

        Args:
            trump_color: The trump color for a Farbwenz, or Color.NONE for a Wenz.
        """
        gameid = Game.FARBWENZ if trump_color != Color.NONE else Game.WENZ
        gamename = f"{trump_color.name}-WENZ" if trump_color != Color.NONE else "WENZ"
        min_laufende = 3 if trump_color != Color.NONE else 2

        super().__init__(
            gameid=gameid,
            gamename=gamename,
            trump_color=trump_color,
            reward=50,
            winning_threshold=61,
            min_laufende=min_laufende,
        )

        self.card_setting = {
            (Color.EICHEL, Rank.OBER): (Rank.OBER_LOW, 0, 3),
            (Color.GRAS, Rank.OBER): (Rank.OBER_LOW, 0, 3),
            (Color.HERZ, Rank.OBER): (Rank.OBER_LOW, 0, 3),
            (Color.SCHELLEN, Rank.OBER): (Rank.OBER_LOW, 0, 3),
            (Color.EICHEL, Rank.UNTER): (Rank.UNTER, 1, 2),
            (Color.GRAS, Rank.UNTER): (Rank.UNTER, 1, 2),
            (Color.HERZ, Rank.UNTER): (Rank.UNTER, 1, 2),
            (Color.SCHELLEN, Rank.UNTER): (Rank.UNTER, 1, 2),
        }


class Ramsch(Rules):
    """The scoring rules of the Ramsch game type."""

    def __init__(self, trump_color: Color) -> None:
        """Create the Ramsch rule set.

        Args:
            trump_color: The trump color (always Herz in Ramsch).
        """
        super().__init__(
            gameid=Game.RAMSCH,
            gamename=Game.RAMSCH.name,
            trump_color=Color.HERZ,
            reward=10,
            winning_threshold=61,
            min_laufende=3,
        )
        self.card_setting = DEFAULT_CARD_SETTING
