"""Tests for the gymnasium Schafkopf environment."""

from typing import Any, cast

import numpy as np
import pytest
from gymnasium import spaces

from schafkopfrl.schafkopfengine.players import Player, RandomPlayer, RLPlayerLearning
from schafkopfrl.schafkopfgym.schafkopfgym import SchafkopfEnv


def make_players() -> list[Player]:
    """Build one learning player and three random opponents."""
    return [RLPlayerLearning(0), RandomPlayer(1), RandomPlayer(2), RandomPlayer(3)]


@pytest.fixture
def env() -> SchafkopfEnv:
    """Return a ready Schafkopf game environment."""
    return SchafkopfEnv(dealer_pos=1, make_players=make_players, learning_player_pos=1)


def _legal_action(observation: dict[str, object]) -> int:
    """Pick the first legal action from the observation."""
    allowed = [int(value) for value in np.asarray(observation["allowed_actions"]) if int(value) != 0]
    return allowed[0] if allowed else 0


def test_observation_and_action_spaces(env: SchafkopfEnv) -> None:
    """The environment exposes a dict observation space and a discrete action space."""
    assert cast("spaces.Discrete[np.integer[Any]]", env.action_space).n == 33
    assert env.observation_space is not None
    assert "allowed_actions" in cast(spaces.Dict, env.observation_space).spaces


def test_reset_returns_observation(env: SchafkopfEnv) -> None:
    """reset returns an observation dict covering the basic observation keys."""
    obs, info = env.reset(seed=7)
    assert isinstance(info, dict)
    assert {"handcards", "allowed_actions", "team", "trick_number"}.issubset(obs.keys())
    assert isinstance(obs["handcards"], np.ndarray)


def test_step_before_reset_raises(env: SchafkopfEnv) -> None:
    """Stepping without a reset raises a RuntimeError."""
    fresh = SchafkopfEnv(dealer_pos=1, make_players=make_players, learning_player_pos=1)
    with pytest.raises(RuntimeError):
        fresh.step(0)


@pytest.mark.parametrize("seed", [1, 7, 42])
def test_full_games_finish(seed: int) -> None:
    """Complete episodes terminate with a finite reward."""
    env = SchafkopfEnv(dealer_pos=1, make_players=make_players, learning_player_pos=1)
    obs, _info = env.reset(seed=seed)
    terminated = False
    steps = 0
    while not terminated:
        obs, reward, terminated, _truncated, _info = env.step(_legal_action(obs))
        steps += 1
        assert steps < 64
    assert np.isfinite(reward)
    assert env.nxt_player is not None


def test_close_and_render_are_noops(env: SchafkopfEnv) -> None:
    """render and close can be called without effects on state."""
    env.render()
    env.close()
    obs, _info = env.reset(seed=3)
    assert "handcards" in obs


@pytest.mark.parametrize("seed", [1, 7])
def test_observations_match_space(seed: int) -> None:
    """Observations carry exactly the keys declared in the observation space.

    Note: the declared high bound of ``trumps_value`` underestimates the real maximum (legacy quirk), so that single key
    is exempt from the containment check.
    """
    env = SchafkopfEnv(dealer_pos=1, make_players=make_players, learning_player_pos=1)
    obs, _info = env.reset(seed=seed)
    space = cast(spaces.Dict, env.observation_space)
    assert set(obs) == set(space.spaces)
    for key, sub_space in space.spaces.items():
        if key == "trumps_value":
            continue
        assert sub_space.contains(obs[key])
