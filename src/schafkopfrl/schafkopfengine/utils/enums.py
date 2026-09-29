"""Enums and card settings for the Schafkopf engine."""

from enum import IntEnum
from types import MappingProxyType


class Game(IntEnum):
    """This Enum provides the priority of a gametype."""

    RAMSCH = 0
    SAUSPIEL = 1
    FARBWENZ = 2
    WENZ = 3
    SOLO = 4
    SIE = 5


class Team(IntEnum):
    """The two teams of a Schafkopf game."""

    CALLINGTEAM = 0
    NONCALLINGTEAM = 1


class Color(IntEnum):
    """This Enum provides the colors and their partail ordering."""

    EICHEL = 4
    GRAS = 3
    HERZ = 2
    SCHELLEN = 1
    NONE = 0


class Rank(IntEnum):
    """This Enum provides the (default) rank."""

    SEVEN = 70
    EIGHT = 80
    NINE = 90
    UNTER_LOW = 91
    OBER_LOW = 92
    KING = 95
    TEN = 100
    ACE = 110
    UNTER = 120
    OBER = 130


Score: dict[Rank, int] = {
    Rank.SEVEN: 0,
    Rank.EIGHT: 0,
    Rank.NINE: 0,
    Rank.KING: 4,
    Rank.TEN: 10,
    Rank.ACE: 11,
    Rank.UNTER_LOW: 2,
    Rank.UNTER: 2,
    Rank.OBER_LOW: 3,
    Rank.OBER: 3,
}

CARD_MODEL_ID: dict[tuple[Color, Rank], int] = {
    (color, rank): idx
    for idx, (color, rank) in enumerate(
        (
            (color, rank)
            for color in Color
            if color != Color.NONE
            for rank in Rank
            if rank not in [Rank.UNTER_LOW, Rank.OBER_LOW]
        ),
        start=1,  # Index starting at 1, 0 represents no card in the model.
    )
}

DEFAULT_CARD_SETTING = MappingProxyType(
    {
        (Color.EICHEL, Rank.OBER): (Rank.OBER, 1, Score[Rank.OBER]),
        (Color.GRAS, Rank.OBER): (Rank.OBER, 1, Score[Rank.OBER]),
        (Color.HERZ, Rank.OBER): (Rank.OBER, 1, Score[Rank.OBER]),
        (Color.SCHELLEN, Rank.OBER): (Rank.OBER, 1, Score[Rank.OBER]),
        (Color.EICHEL, Rank.UNTER): (Rank.UNTER, 1, Score[Rank.UNTER]),
        (Color.GRAS, Rank.UNTER): (Rank.UNTER, 1, Score[Rank.UNTER]),
        (Color.HERZ, Rank.UNTER): (Rank.UNTER, 1, Score[Rank.UNTER]),
        (Color.SCHELLEN, Rank.UNTER): (Rank.UNTER, 1, Score[Rank.UNTER]),
    }
)
