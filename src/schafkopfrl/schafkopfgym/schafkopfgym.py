"""Gymnasium environment for Schafkopf and a small debug entry point."""

import random
import time
from collections.abc import Callable
from typing import cast

import gymnasium as gym
from gymnasium.utils.env_checker import check_env as gym_check_env
from gymnasium.wrappers import FrameStackObservation
from stable_baselines3.common.env_checker import check_env as sb3_check_env

from schafkopfrl.schafkopfengine.players.dummy_player import DummyPlayer
from schafkopfrl.schafkopfengine.players.player import Player
from schafkopfrl.schafkopfengine.players.rl_player import RL, RLPlayer
from schafkopfrl.schafkopfengine.public_gamestate import PublicGameState
from schafkopfrl.schafkopfengine.utils.enums import Game

# Evaluated once at import time, preserving the original default semantics.
DEFAULT_DEALER_POS = random.randint(0, 3) - 1  # noqa: S311 Intentional non-cryptographic game randomness.


def _make_dummy_players() -> list[Player]:
    """Build the default team of four dummy players."""
    return [DummyPlayer(i) for i in range(4)]


class SchafkopfEnv(gym.Env[dict[str, object], int]):
    """Custom Environment that follows gym interface."""

    def __init__(
        self,
        dealer_pos: int = DEFAULT_DEALER_POS,
        make_players: Callable[[], list[Player]] = _make_dummy_players,
        learning_player_pos: int = 0,
    ) -> None:
        """Initialize the environment and its public game state.

        Args:
            dealer_pos: Seat position of the dealer.
            make_players: Factory returning the list of players for the game.
            learning_player_pos: Number of leading players that are learning agents.
        """
        super().__init__()

        # This var sets the learning agents
        # so that non learning players can just
        # play a card. The learning players should
        # always be set at the start of the players
        # list. Default to 0 all autoplay.

        # self.deck = Deck().new_standard_cards()
        self.players = make_players()
        self.learning_player = self.players[:learning_player_pos]
        self.dealer_pos = dealer_pos
        self.publicgamestate = PublicGameState(self.players, self.dealer_pos)
        self.nxt_player: Player | None = None

        # This need to be in every learning player.
        self.observation_space = cast(
            RL, self.players[0]
        )._basic_space()  # Only to pass the check_env; the leading player is an RL player.
        self.action_space = gym.spaces.Discrete(33)
        self.last_obs: dict[str, object] | None = None

    def reset(
        self, seed: int | None = None, options: dict[str, object] | None = None
    ) -> tuple[dict[str, object], dict[str, object]]:
        """Reset the game and fast-forward to the learning agent's turn.

        Args:
            seed: Optional seed for the environment's random number generator.
            options: Optional dict of reset options.
        """
        super().reset(seed=seed)
        first_player = self.publicgamestate.start_game()
        while self.publicgamestate.game_id != Game.SAUSPIEL:
            first_player = self.publicgamestate.start_game()

        # This needs to fast forward to the learning agent.
        # A trick in a reset will never be complete so we dont
        # check if its complete.
        if first_player in self.learning_player:
            observation = cast(dict[str, object], first_player.observe())
            self.nxt_player = first_player
        else:
            self.nxt_player = self.publicgamestate.player_turn(first_player)
            while self.nxt_player not in self.learning_player and len(self.publicgamestate.cards_played) != 32:
                self.nxt_player = self.publicgamestate.player_turn(self.nxt_player)
            observation = cast(dict[str, object], self.nxt_player.observe())

        info: dict[str, object] = {}
        self.last_obs = observation
        return observation, info

    def step(self, action: int) -> tuple[dict[str, object], int, bool, bool, dict[str, object]]:
        """Play one action from the learning agent and return the gym step tuple.

        Args:
            action: Index of the card to play.
        """
        if self.nxt_player is None:
            raise RuntimeError("Call reset() before step().")

        self.nxt_player = self.publicgamestate.player_turn(self.nxt_player, action)

        while self.nxt_player not in self.learning_player and not self._is_end_game():
            self.nxt_player = self.publicgamestate.player_turn(self.nxt_player)

        if self._is_end_game():
            # In the last turn there would be no observation generated.
            obs = cast(dict[str, object], self.players[0].observe())
            reward = self._get_trick_reward(obs)

            self.publicgamestate.evaluate()
            reward += self.publicgamestate.payout[0] * 8 if self.publicgamestate.payout[0] > 0 else -480

            return obs, reward, True, True, {}

        observation = cast(dict[str, object], self.nxt_player.observe())
        reward = self._get_trick_reward(observation)

        self.last_obs = observation

        return observation, reward, False, False, {}

    def _get_trick_reward(self, observation: dict[str, object]) -> int:
        """Compute the reward for the last trick from the observation.

        Args:
            observation: Latest observation from the game.
        """
        player_card = self.publicgamestate.played_cards_player[self.publicgamestate.players[0]][-1]

        # Player or team member wins trick.
        if self.publicgamestate.trick_owner[-1] == self.publicgamestate.players[0] or (
            self.publicgamestate.players[0].teammember
            and (self.publicgamestate.trick_owner[-1] == self.publicgamestate.players[0].teammember)
        ):
            reward: int = self.publicgamestate.trick_points[-1]
            reward += 4 * player_card.score
        else:  # (self.publicgamestate.trick_owner[-1] != self.publicgamestate.players[0]):
            reward = -self.publicgamestate.trick_points[-1]
            reward -= 4 * player_card.score

        return reward

    def render(self) -> None:
        """Rendering is not implemented for this environment."""
        pass

    def close(self) -> None:
        """Close the environment; nothing to release."""
        pass

    def _is_end_game(self) -> bool:
        """Return True once all 32 cards have been played."""
        return len(self.publicgamestate.cards_played) == 32


def main() -> None:
    """Run a quick debug loop of random moves against the environment."""
    SIM = 800_000

    players = [RLPlayer(0)] + [DummyPlayer(i) for i in range(1, 4)]  # type: ignore[call-arg]  # pre-existing broken debug call: RLPlayer requires model_path.
    og_env = SchafkopfEnv(players=players, learning_player_pos=1)  # type: ignore[call-arg]  # pre-existing broken debug call: __init__ takes make_players, not players.
    env: FrameStackObservation[dict[str, object], int, dict[str, object]] = FrameStackObservation(og_env, stack_size=8)

    gym_check_env(og_env)
    sb3_check_env(og_env)
    gym_check_env(env.unwrapped)
    sb3_check_env(env.unwrapped)

    wrong_count = 0
    start_time = time.perf_counter()
    env.reset()
    for _ in range(SIM):
        _, wrong_card, that, this, _ = env.step(random.randint(0, 32))  # noqa: S311 Intentional non-cryptographic game randomness.
        while wrong_card == -100:
            _, wrong_card, that, this, _ = env.step(random.randint(0, 32))  # noqa: S311 Intentional non-cryptographic game randomness.
            wrong_count += 1

        if this or that:
            env.reset()

    end_time = time.perf_counter()
    print(end_time - start_time)  # noqa: T201 Intentional interactive/CLI output.
    print(wrong_count)  # noqa: T201 Intentional interactive/CLI output.


if __name__ == "__main__":
    main()
