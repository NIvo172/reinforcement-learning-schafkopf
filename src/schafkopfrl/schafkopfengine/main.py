"""Play Schafkopf games: interactive console play and batch simulation."""

import argparse
from collections.abc import Sequence

from schafkopfrl.schafkopfengine.players import player_factory
from schafkopfrl.schafkopfengine.players.player import Player
from schafkopfrl.schafkopfengine.public_gamestate import PublicGameState


def main() -> None:
    """Play 8000 games between random policy players."""
    GAMES = 8000
    PLAYERS = [*player_factory.create_players("RP", 0, 1), *player_factory.create_players("RP", 1, 4)]  # type: ignore[misc]  # create_players returns list[Player] | int; "RP" always yields a list

    game = PublicGameState(PLAYERS, starting_pos=0)

    for _ in range(GAMES):
        nxt_player = game.start_game()

        for _ in range(32):
            nxt_player = game.player_turn(nxt_player)

        game.evaluate()

        game.dealer = game.players[(game.players.index(game.dealer) + 1) % 4]


def _create_players(humans: int) -> list[Player]:
    """Create human players for the first seats and random players for the rest."""
    created = (
        player_factory.create_players("Human", 0, humans),
        player_factory.create_players("RP", humans, 4),
    )

    players: list[Player] = []
    for lineup in created:
        if not isinstance(lineup, list):
            msg = f"Could not create the player lineup ({humans} human seat(s))"
            raise ValueError(msg)
        players.extend(lineup)

    return players


def play(humans: int = 1, games: int = 1) -> int:
    """Play Schafkopf interactively against random players.

    The first ``humans`` seats are human players and the remaining seats are filled with random players, so the default
    run is one human player against three random players.

    Args:
        humans: Number of human players (0-4).
        games: Number of games to play.
    """
    players = _create_players(humans)
    totals = [0] * len(players)

    try:
        for game_no in range(1, games + 1):
            print(f"Game {game_no}")
            game = PublicGameState(players, starting_pos=0)

            nxt_player = game.start_game()
            for _ in range(32):
                nxt_player = game.player_turn(nxt_player)

            game.evaluate()
            totals = [total + payout for total, payout in zip(totals, game.payout, strict=True)]

            for seat, (player, payout, total) in enumerate(zip(players, game.payout, totals, strict=True)):
                who = type(player).__name__
                print(f"  seat {seat} ({who}): {payout:+d} this game, total {total:+d}")
    except KeyboardInterrupt:
        print("Interrupted; totals so far:")
        for seat, total in enumerate(totals):
            print(f"  seat {seat}: {total:+d}")
        return 130

    return 0


def cli(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point that starts an interactive game of Schafkopf."""
    parser = argparse.ArgumentParser(
        prog="schafkopf",
        description="Play Schafkopf in the console: human players against random players.",
    )
    parser.add_argument(
        "--humans",
        type=int,
        default=1,
        metavar="N",
        help="Number of human players between 0 and 4; the remaining seats are random (default: 1).",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=1,
        metavar="N",
        help="Number of games to play (default: 1).",
    )

    args = parser.parse_args(argv)
    if not 0 <= args.humans <= 4:
        parser.error("--humans must be between 0 and 4")
    if args.games < 1:
        parser.error("--games must be at least 1")

    return play(humans=args.humans, games=args.games)


if __name__ == "__main__":
    raise SystemExit(cli())
