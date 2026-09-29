"""Tests for the enum and card model id mappings."""

from schafkopfrl.schafkopfengine.utils.enums import CARD_MODEL_ID, Color, Game, Rank, Score, Team


def test_game_priority_order() -> None:
    """The game enum ids increase with the priority of the game type."""
    assert Game.RAMSCH < Game.SAUSPIEL < Game.FARBWENZ < Game.WENZ < Game.SOLO
    assert int(Game.SIE) == 5


def test_team_members() -> None:
    """The two teams are addressable by distinct ids."""
    assert int(Team.CALLINGTEAM) == 0
    assert int(Team.NONCALLINGTEAM) == 1
    assert len(list(Team)) == 2


def test_color_partial_ordering() -> None:
    """The colors encode a partial ordering in their id values."""
    assert Color.EICHEL > Color.GRAS > Color.HERZ > Color.SCHELLEN > Color.NONE
    assert len(list(Color)) == 5


def test_rank_ids() -> None:
    """The default rank ids increase with the value of the card."""
    assert Rank.SEVEN < Rank.EIGHT < Rank.NINE < Rank.KING < Rank.TEN < Rank.ACE
    assert Rank.UNTER_LOW < Rank.OBER_LOW
    assert int(Rank.UNTER) == 120
    assert int(Rank.OBER) == 130


def test_score_table() -> None:
    """The score table matches the classic Schafkopf values."""
    assert Score[Rank.SEVEN] == 0
    assert Score[Rank.KING] == 4
    assert Score[Rank.TEN] == 10
    assert Score[Rank.ACE] == 11
    assert Score[Rank.UNTER] == 2
    assert Score[Rank.OBER] == 3
    assert len(Score) == len(list(Rank))


def test_score_total_is_120() -> None:
    """A full deck scores exactly 120 points per game."""
    total = sum(
        Score[rank]
        for color in Color
        if color != Color.NONE
        for rank in Rank
        if rank not in (Rank.UNTER_LOW, Rank.OBER_LOW)
    )
    assert total == 120


def test_card_model_id_mapping() -> None:
    """Every physical card has a unique model id and zero is reserved."""
    expected_ids = {}
    index = 1
    for color in Color:
        if color == Color.NONE:
            continue
        for rank in Rank:
            if rank in (Rank.UNTER_LOW, Rank.OBER_LOW):
                continue
            expected_ids[(color, rank)] = index
            index += 1
    assert len(expected_ids) == 32
    assert expected_ids == CARD_MODEL_ID
    assert 0 not in CARD_MODEL_ID.values()
