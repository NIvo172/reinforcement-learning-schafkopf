"""Arena evaluation of agent lineups against a baseline opponent.

Each run plays a fixed number of seeded games between a lineup under test and a baseline lineup across all seating
permutations. Before each round the game is re-dealt until the round's target player ends up calling a Sauspiel, then the
round is evaluated and one event row per player is appended to a CSV report.
"""

import itertools
from pathlib import Path

from tqdm import tqdm

from schafkopfrl.schafkopfengine.players import player_factory
from schafkopfrl.schafkopfengine.players.player import Player
from schafkopfrl.schafkopfengine.public_gamestate import PublicGameState
from schafkopfrl.schafkopfengine.utils.enums import Game
from schafkopfrl.utils.log import get_logger

logger = get_logger("Arena")

SEEDS = 100  # Number of deck seeds per lineup.
ROUNDS = 4  # Number of rounds (one per seating of the caller) per arranged game.
MAX_RESTARTS = 100  # Re-deal budget per round before the round is skipped.

PLAYER_STRINGS = ["RL_BASIC"]  # Lineups under test (seats 0 and 1).
ENEMY_STRINGS = ["RSP"]  # Baseline opponents (seats 2 and 3).


def _create_lineup(name: str, start_uid: int, end_uid: int) -> list[Player]:
    """Create the player lineup for one team of a game.

    Args:
        name: Short name of the player type, as known to the player factory.
        start_uid: First player uid included in the lineup.
        end_uid: Last player uid (not included) in the lineup.

    Returns:
        The created players, in uid order.
    """
    lineup = player_factory.create_players(name, start_uid, end_uid)
    if not isinstance(lineup, list):
        msg = f"Unknown player lineup {name!r}; check the player factory for valid names."
        raise ValueError(msg)
    return lineup


def _player_type(player: object) -> str:
    """Return the player class name without the ``Player`` suffix (or the type name when absent)."""
    name = type(player).__name__
    return name[: -len("Player")] if name.endswith("Player") else name


def _log_round(game: PublicGameState, seed: int, arrangement: tuple[Player, ...], filename: str) -> None:
    """Append one event row per player of the evaluated round to the CSV report.

    Args:
        game: The evaluated public game state of the round.
        seed: The deck seed of the round.
        arrangement: The seating permutation of the round.
        filename: Name of the CSV report to append to.
    """
    for player in game.players:
        seat = game.players.index(player)
        event: dict[str, object] = {
            "SEED": seed,
            "ARRANGMENT": arrangement,
            "DEALER": game.dealer,
            "PLAYER": player,
            "UID": player.id,
            "PLAYER_SEATING": seat,
            "PLAYER_TYPE": _player_type(player),
            "TEAM": player.team,
            "WIN/LOSE": game.payout[seat],
            "TEAMMEMBER": player.teammember,
            "TEAMMEMBER_TYPE": _player_type(player.teammember) if player.teammember is not None else "",
        }
        game.log_event_to_csv(event, filename=Path(filename))


def _play_forced_round(game: PublicGameState, seed: int, caller: Player) -> bool:
    """Re-deal until a Sauspiel is called by the target player, then play and evaluate the round.

    Args:
        game: The public game state to run the round on.
        seed: The base deck seed of the round.
        caller: The player who must end up calling the round's Sauspiel.

    Returns:
        Whether the round could be started and was played; False when the re-deal budget ran out.
    """
    game.start_game(seed=seed)
    salt = 0
    while game.game_id != Game.SAUSPIEL or game.calling_player != caller:
        salt += 1
        if salt > MAX_RESTARTS:
            logger.warning(
                "Giving up on a round calling player %s at seed %s after %s re-deals.", caller, seed, MAX_RESTARTS
            )
            return False
        game.start_game(seed=seed + salt)

    assert game.playing_order is not None  # noqa: S101 Invariant: the last start_game set the playing order.
    nxt_player = game.playing_order[0]
    for _ in range(32):
        nxt_player = game.player_turn(nxt_player)

    game.evaluate()
    return True


def arena_basic() -> None:
    """Run the full arena evaluation and write per-player CSV events for every lineup."""
    for player_str in PLAYER_STRINGS:
        for enemy in ENEMY_STRINGS:
            lineup = _create_lineup(player_str, 0, 2) + _create_lineup(enemy, 2, 4)
            filename = f"{player_str}_{enemy}_{SEEDS}_RND_{ROUNDS}_TESTING5.csv"
            arrangements = list(itertools.permutations(lineup))

            for seed in tqdm(range(SEEDS), desc=f"{player_str} vs {enemy}"):
                for arrangement in arrangements:
                    game = PublicGameState(list(arrangement), starting_pos=0)
                    for round_no in range(1, ROUNDS + 1):
                        caller = arrangement[round_no % 4]
                        if not _play_forced_round(game, seed, caller):
                            continue
                        _log_round(game, seed, arrangement, filename)
                        game.dealer = game.players[(game.players.index(game.dealer) + 1) % 4]


if __name__ == "__main__":
    arena_basic()
