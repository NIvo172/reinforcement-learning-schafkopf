"""Tests for the player classes and the player factory."""

import pytest
from conftest import make_player_team, run_full_game

from schafkopfrl.schafkopfengine.cards import Card
from schafkopfrl.schafkopfengine.players.dummy_player import DummyPlayer
from schafkopfrl.schafkopfengine.players.human_player import HumanPlayer
from schafkopfrl.schafkopfengine.players.player import Player
from schafkopfrl.schafkopfengine.players.player_factory import create_players
from schafkopfrl.schafkopfengine.players.random_player import RandomPlayer, RandomSauPlayer
from schafkopfrl.schafkopfengine.players.rl_player import RLPlayerLearning
from schafkopfrl.schafkopfengine.public_gamestate import PublicGameState
from schafkopfrl.schafkopfengine.rules.rules import Rules
from schafkopfrl.schafkopfengine.utils.enums import CARD_MODEL_ID, Color, Game, Rank, Team


def _make_card(color: Color, rank: Rank, is_trump: int = 0) -> Card:
    """Build a single card with the given attributes and its model id."""
    return Card(color, rank, 0, CARD_MODEL_ID[(color, rank)]).adjust(is_trump=is_trump)


def _standin_game(player: Player, gametype: object, trick_cards: list[Card] | None = None) -> PublicGameState:
    """Build an unstarted game state with player and wanted rules attached."""
    game = PublicGameState([player, RandomPlayer(1), RandomPlayer(2), RandomPlayer(3)], starting_pos=0)
    game._reset_to_first_turn()
    game.gametype = gametype  # type: ignore[assignment]
    game.calling_player = player
    game.team = [Team.NONCALLINGTEAM] * 4
    if trick_cards is not None:
        game.trick_current_cards = trick_cards
    player._publicgamestate = game
    return game


def _fresh_player() -> Player:
    """Create a new random player with a basic game state attached."""
    player = RandomPlayer(0)
    _standin_game(player, Rules.create(Game.RAMSCH, Color.NONE), [])
    return player


def test_take_cards_counts_colors_trumps_and_aces() -> None:
    """Taking cards populates the color, ace and trump counters."""
    player = _fresh_player()
    cards = [
        _make_card(Color.EICHEL, Rank.ACE),
        _make_card(Color.EICHEL, Rank.KING),
        _make_card(Color.GRAS, Rank.SEVEN),
        _make_card(Color.HERZ, Rank.ACE, is_trump=1),
        _make_card(Color.HERZ, Rank.UNTER, is_trump=1),
    ]
    player.take_cards(cards)
    assert set(player.cards) == set(cards)
    assert player.colors[Color.EICHEL] == 2
    assert player.colors[Color.GRAS] == 1
    assert player.aces[Color.EICHEL] == 1
    assert len(player.trumps) == 2


def test_take_cards_sorted() -> None:
    """Taken cards are stored in descending sort order."""
    player = _fresh_player()
    cards = [
        _make_card(Color.EICHEL, Rank.SEVEN),
        _make_card(Color.EICHEL, Rank.ACE),
        _make_card(Color.EICHEL, Rank.KING),
    ]
    player.take_cards(cards)
    ranks = [card.rank for card in player.cards]
    assert ranks == sorted(ranks, reverse=True)


def test_decount_card_updates_counters() -> None:
    """Decounting cards updates the hand, color and trump counters."""
    player = _fresh_player()
    ace = _make_card(Color.EICHEL, Rank.ACE)
    king = _make_card(Color.EICHEL, Rank.KING)
    trump = _make_card(Color.HERZ, Rank.UNTER, is_trump=1)
    player.take_cards([ace, king, trump])

    player._decount_card(ace)
    assert ace not in player.cards
    assert king in player.cards
    assert player.aces[Color.EICHEL] == 0
    assert player.colors[Color.EICHEL] == 1

    player._decount_card(trump)
    assert trump not in player.cards
    assert trump not in player.trumps


def test_decount_rufsau_clears_has_rufsau() -> None:
    """Decounting the rufsau card clears the has_rufsau flag."""
    player = _fresh_player()
    ace = _make_card(Color.EICHEL, Rank.ACE)
    game = _standin_game(player, Rules.create(Game.SAUSPIEL, Color.EICHEL))
    game._game_sau = ace
    player.take_cards([ace])
    player.has_rufsau = ace

    player._decount_card(ace)

    assert not player.has_rufsau


def test_check_cards_recalculates_for_other_games() -> None:
    """For non-Sauepiel games the counters are recomputed from scratch."""
    player = _fresh_player()
    player._publicgamestate = _standin_game(player, Rules.create(Game.WENZ, Color.NONE))
    heart_ace = _make_card(Color.HERZ, Rank.ACE, is_trump=1)
    side = _make_card(Color.EICHEL, Rank.SEVEN)
    player.take_cards([heart_ace, side])
    player.check_cards(pre_game=False)
    assert player.trumps == [heart_ace]
    assert player.colors[Color.EICHEL] == 1


def test_allowed_gametypes_requires_no_ace_in_color() -> None:
    """The Sauspiel is only offered for colors without the ace in hand."""
    with_ace = _fresh_player()
    with_ace.take_cards([_make_card(Color.EICHEL, Rank.ACE), _make_card(Color.EICHEL, Rank.SEVEN)])
    games, colors = with_ace._allowed_gametypes()
    assert Game.SAUSPIEL not in games
    assert colors == []

    without_ace = _fresh_player()
    without_ace.take_cards([_make_card(Color.EICHEL, Rank.KING), _make_card(Color.GRAS, Rank.NINE)])
    games, colors = without_ace._allowed_gametypes()
    assert Game.SAUSPIEL in games
    assert colors == [Color.GRAS, Color.EICHEL]


def test_choose_gametype_rule() -> None:
    """The standard rule starts a Sauspiel with strong hands and ramsch otherwise."""
    weak = _fresh_player()
    weak.take_cards([_make_card(Color.EICHEL, Rank.SEVEN), _make_card(Color.GRAS, Rank.EIGHT)])
    assert weak.choose_gametype_rule() == (Game.RAMSCH, Color.NONE)

    strong = _fresh_player()
    trumps = [
        _make_card(Color.HERZ, Rank.ACE, is_trump=1),
        _make_card(Color.EICHEL, Rank.OBER, is_trump=1),
        _make_card(Color.GRAS, Rank.UNTER, is_trump=1),
        _make_card(Color.HERZ, Rank.UNTER, is_trump=1),
    ]
    strong.take_cards([*trumps, _make_card(Color.SCHELLEN, Rank.SEVEN)])
    game, color = strong.choose_gametype_rule()
    assert game == Game.SAUSPIEL
    assert color in (Color.SCHELLEN, Color.EICHEL, Color.GRAS)


def test_allowed_cards_first_card_any_card() -> None:
    """Opening a trick allows every card in hand."""
    player = _fresh_player()
    player._publicgamestate = _standin_game(player, Rules.create(Game.RAMSCH, Color.NONE), [])
    cards = [_make_card(Color.EICHEL, Rank.SEVEN), _make_card(Color.GRAS, Rank.ACE)]
    player.take_cards(cards)
    assert player._allowed_cards() == player.cards


def test_allowed_cards_follow_suit() -> None:
    """Following the lead suit is mandatory while the player holds that color."""
    player = _fresh_player()
    eichel_low = _make_card(Color.EICHEL, Rank.SEVEN)
    eichel_high = _make_card(Color.EICHEL, Rank.ACE)
    other = _make_card(Color.GRAS, Rank.NINE)
    player._publicgamestate = _standin_game(player, Rules.create(Game.RAMSCH, Color.NONE), [eichel_low])
    player.take_cards([eichel_low, eichel_high, other])
    assert set(player._allowed_cards()) == {eichel_low, eichel_high}


def test_allowed_cards_trump_forced() -> None:
    """A trump lead forces the player's trump cards."""
    player = _fresh_player()
    trump = _make_card(Color.HERZ, Rank.UNTER, is_trump=1)
    side = [
        _make_card(Color.EICHEL, Rank.SEVEN),
        _make_card(Color.GRAS, Rank.NINE),
        _make_card(Color.GRAS, Rank.ACE),
    ]
    player._publicgamestate = _standin_game(player, Rules.create(Game.RAMSCH, Color.NONE), [trump])
    player.take_cards([trump, *side])
    assert player._allowed_cards() == [trump]


def test_allowed_cards_after_suit_emptied() -> None:
    """Without the lead color the player may play any card except the rufsau."""
    player = _fresh_player()
    side = [
        _make_card(Color.EICHEL, Rank.SEVEN),
        _make_card(Color.GRAS, Rank.NINE),
        _make_card(Color.GRAS, Rank.ACE),
    ]
    lead = _make_card(Color.HERZ, Rank.ACE, is_trump=0)
    player._publicgamestate = _standin_game(player, Rules.create(Game.RAMSCH, Color.NONE), [lead])
    player.take_cards(side)
    player.colors[Color.HERZ] = 0

    assert set(player._allowed_cards()) == set(side)
    assert player._publicgamestate.colors_left_player[player][Color.HERZ] is False


def test_allowed_cards_rufsau_must_follow() -> None:
    """In a Sauspiel the held rufsau must follow the searched color lead."""
    player = _fresh_player()
    rufsau = _make_card(Color.GRAS, Rank.ACE)
    other = _make_card(Color.EICHEL, Rank.SEVEN)
    lead = _make_card(Color.GRAS, Rank.KING)
    player._publicgamestate = _standin_game(player, Rules.create(Game.SAUSPIEL, Color.GRAS), [lead])
    player.take_cards([rufsau, other])
    player.has_rufsau = rufsau
    player.colors[Color.GRAS] = 1
    assert player._allowed_cards() == [rufsau]


def test_allowed_cards_fall_back_when_suit_gone() -> None:
    """The player is not forced on a searched color lead without that color."""
    player = _fresh_player()
    other = _make_card(Color.EICHEL, Rank.SEVEN)
    lead = _make_card(Color.GRAS, Rank.KING)
    player._publicgamestate = _standin_game(player, Rules.create(Game.SAUSPIEL, Color.GRAS), [lead])
    player.take_cards([other])
    player.colors[Color.GRAS] = 0
    assert player._allowed_cards() == [other]


def test_davonlaufen_blocks_rufsau_play() -> None:
    """A running player may lead any card instead of the rufsau."""
    player = _fresh_player()
    rufsau = _make_card(Color.GRAS, Rank.ACE)
    other = _make_card(Color.EICHEL, Rank.SEVEN)
    player._publicgamestate = _standin_game(player, Rules.create(Game.SAUSPIEL, Color.GRAS), [])
    player.take_cards([rufsau, other])
    player.has_rufsau = rufsau
    player.colors[Color.GRAS] = 4
    assert player._check_davonlaufen()
    assert player._allowed_cards() == player.cards


def test_dummy_player_never_calls() -> None:
    """The dummy player returns a playable game type and never contra or retour."""
    player = DummyPlayer(0)
    game, _color = player.choose_gametype()
    assert game in (Game.RAMSCH, Game.SAUSPIEL, Game.FARBWENZ, Game.WENZ, Game.SOLO)
    assert player.contra() is False
    assert player.retour() is False


def test_random_sau_plays_rule_and_never_contra() -> None:
    """The random sau player follows the standard rule and stays peaceful."""
    player = RandomSauPlayer(0)
    player._publicgamestate = PublicGameState(
        [player, RandomPlayer(1), RandomPlayer(2), RandomPlayer(3)], starting_pos=0
    )
    assert player.contra() is False
    assert player.retour() is False
    player.take_cards([_make_card(Color.EICHEL, Rank.SEVEN), _make_card(Color.GRAS, Rank.EIGHT)])
    assert player.choose_gametype() == (Game.RAMSCH, Color.NONE)


def test_random_players_randomize_contra() -> None:
    """Random players make random contra and retour decisions."""
    player = RandomPlayer(0)
    assert isinstance(player.contra(), bool)
    assert isinstance(player.retour(), bool)


@pytest.mark.parametrize("choice", ["0", "1"])
def test_human_player_contra_retour(monkeypatch: pytest.MonkeyPatch, choice: str) -> None:
    """The human player parses the contra and retour answer from stdin."""
    monkeypatch.setattr("builtins.input", lambda *_args: choice)
    player = HumanPlayer(0)
    assert player.contra() == (choice == "1")
    assert player.retour() == (choice == "1")


def test_human_player_plays_first_allowed_card(monkeypatch: pytest.MonkeyPatch) -> None:
    """The human player selects the card announced on stdin."""
    monkeypatch.setattr("builtins.input", lambda *_args: "0")
    player = HumanPlayer(0)
    low = _make_card(Color.EICHEL, Rank.SEVEN)
    high = _make_card(Color.EICHEL, Rank.ACE)
    assert player._play_card([low, high]) is low
    assert player._play_card([high, low]) is high


def test_human_player_choose_ramsch(monkeypatch: pytest.MonkeyPatch) -> None:
    """The human player can select the first offered game type."""
    monkeypatch.setattr("builtins.input", lambda *_args: "0")
    player = HumanPlayer(0)
    player._publicgamestate = PublicGameState(
        [player, RandomPlayer(1), RandomPlayer(2), RandomPlayer(3)], starting_pos=0
    )
    player.take_cards([_make_card(Color.EICHEL, Rank.SEVEN), _make_card(Color.EICHEL, Rank.ACE)])
    game, color = player.choose_gametype()
    assert game == Game.RAMSCH
    assert color == Color.NONE


def test_observe_is_noop_for_basic_players() -> None:
    """Non-RL players expose a no-op observe method."""
    for cls in (DummyPlayer, RandomPlayer, RandomSauPlayer, HumanPlayer):
        assert cls(0).observe() is None


def _team_signature(players: list[Player] | int) -> tuple[str, list[int]] | int:
    """Summarize a player team as (class name, ids) for easy comparison."""
    if isinstance(players, int):
        return players
    return (type(players[0]).__name__, [player.id for player in players])


def test_player_factory_known_names() -> None:
    """The factory maps the known names to the matching player classes."""
    assert _team_signature(create_players("DP", 0, 4)) == ("DummyPlayer", [0, 1, 2, 3])
    assert _team_signature(create_players("RP", 2, 4)) == ("RandomPlayer", [2, 3])
    assert _team_signature(create_players("RSP", 0, 2)) == ("RandomSauPlayer", [0, 1])
    assert _team_signature(create_players("Human", 0, 4)) == ("HumanPlayer", [0, 1, 2, 3])


def test_player_factory_unknown_returns_minus_one() -> None:
    """Unknown factory names are signalled with the value minus one."""
    assert create_players("NOPE", 0, 4) == -1


def test_teams_are_set_after_game() -> None:
    """Every finished game assigns both teams to all players."""
    game = run_full_game(seed=5)
    assert set(game.team) <= {Team.CALLINGTEAM, Team.NONCALLINGTEAM}
    assert all(player.team in (Team.CALLINGTEAM, Team.NONCALLINGTEAM) for player in game.players)
    if game.game_id == Game.SAUSPIEL:
        callers = [player for player in game.players if player.team == Team.CALLINGTEAM]
        assert 1 <= len(callers) <= 2


def test_dummy_team_game_completes() -> None:
    """A game of dummies plays out all 32 cards."""
    game = run_full_game(make_player_team(DummyPlayer), seed=3)
    assert len(game.cards_played) == 32
    assert len(game.trick_owner) == 8


def test_sau_team_game_completes() -> None:
    """A game among random sau players plays out and scores the full 120 points."""
    game = run_full_game(make_player_team(RandomSauPlayer), seed=9)
    assert game.game_id in (Game.RAMSCH, Game.SAUSPIEL, Game.FARBWENZ, Game.WENZ, Game.SOLO)
    assert sum(game.trick_points) == 120


def test_rl_player_learning_basic_space() -> None:
    """The learning player exposes a fully specified observation space."""
    space = RLPlayerLearning(0)._basic_space()
    assert "handcards" in space.spaces
    assert "allowed_actions" in space.spaces
    assert space.sample() is not None


def test_rl_player_choose_gametype_thresholds() -> None:
    """The learning player's rule may start a Sauspiel on strong hands."""
    player = RLPlayerLearning(0)
    _standin_game(player, Rules.create(Game.RAMSCH, Color.NONE), [])
    trumps = [
        _make_card(Color.HERZ, Rank.ACE, is_trump=1),
        _make_card(Color.HERZ, Rank.OBER, is_trump=1),
        _make_card(Color.EICHEL, Rank.OBER, is_trump=1),
    ]
    player.take_cards([*trumps, _make_card(Color.SCHELLEN, Rank.SEVEN)])
    game, _color = player.choose_gametype()
    assert game in (Game.RAMSCH, Game.SAUSPIEL)


def test_rl_player_learning_play_card_updates_hand() -> None:
    """Playing a legal action removes the card from the learning player's hand."""
    player = RLPlayerLearning(0)
    low = _make_card(Color.EICHEL, Rank.SEVEN)
    high = _make_card(Color.EICHEL, Rank.ACE)
    player._publicgamestate = _standin_game(player, Rules.create(Game.RAMSCH, Color.NONE), [high])
    player.take_cards([low, high])

    played = player.play_card(low.model_id)
    assert played is low
    assert player.cards == [high]
