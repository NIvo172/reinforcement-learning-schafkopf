"""Tests for the vectorized environment helper."""

from typing import cast

import numpy as np

from schafkopfrl.schafkopfengine.players import RandomPlayer, RLPlayerLearning
from schafkopfrl.schafkopfgym.schafkopfgym import SchafkopfEnv
from schafkopfrl.schafkopfgym.vec_env_schafkopfgym import enchant_env


def _env_kwargs() -> dict[str, object]:
    """Environment constructor kwargs for one learning plus three random players."""
    return {
        "make_players": lambda: [RLPlayerLearning(0), RandomPlayer(1), RandomPlayer(2), RandomPlayer(3)],
        "learning_player_pos": 1,
    }


def test_enchant_env_resets_and_steps() -> None:
    """Two sub-envs can be reset and stepped with frame-stacked observations."""
    vec_env = enchant_env(SchafkopfEnv, env_kwargs=_env_kwargs(), n_envs=2, seed=1)
    try:
        # The FrameStackObservation wrapper returns a dict of stacked arrays (n_envs, stack_size, ...).
        obs = cast("dict[str, object]", vec_env.reset())
        allowed_all = np.asarray(obs["allowed_actions"])
        assert allowed_all.shape[0] == 2

        def legal_action(i: int) -> int:
            allowed = allowed_all[i][-1]
            return int(allowed[allowed != 0][0] if (allowed != 0).any() else allowed[0])

        actions = np.array([legal_action(0), legal_action(1)])
        step_result = vec_env.step(actions)
        next_obs = cast("dict[str, object]", step_result[0])
        rewards = step_result[1]
        dones = step_result[2]
        assert rewards.shape[0] == 2
        assert dones.shape[0] == 2
        assert np.asarray(next_obs["handcards"]).shape[0] == 2
    finally:
        vec_env.close()


def test_enchant_env_observation_shape() -> None:
    """Each sub-observation exposes the frame-stacked keys of the space."""
    vec_env = enchant_env(SchafkopfEnv, env_kwargs=_env_kwargs(), n_envs=1, seed=5)
    try:
        obs = cast("dict[str, object]", vec_env.reset())
        assert "handcards" in obs
        assert "allowed_actions" in obs
        handcards = np.asarray(obs["handcards"])
        assert handcards.shape == (1, 8, 8)
    finally:
        vec_env.close()
