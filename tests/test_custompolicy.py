"""Tests for the custom action-masked policy."""

from typing import Any, cast

import numpy as np
import pytest
import torch as th
from gymnasium import spaces
from stable_baselines3.common.distributions import Distribution

from schafkopfrl.schafkopfengine.players import RandomPlayer, RLPlayerLearning
from schafkopfrl.schafkopfgym.custompolicy import CustomMultiInputPolicy
from schafkopfrl.schafkopfgym.schafkopfgym import SchafkopfEnv


def _make_env() -> SchafkopfEnv:
    """Build an environment with one learning player and three random opponents."""
    return SchafkopfEnv(
        dealer_pos=1,
        make_players=lambda: [RLPlayerLearning(0), RandomPlayer(1), RandomPlayer(2), RandomPlayer(3)],
        learning_player_pos=1,
    )


def _single_observation(seed: int) -> dict[str, np.ndarray]:
    """Build one real observation dict from the environment as numpy arrays."""
    env = _make_env()
    obs, _info = env.reset(seed=seed)
    return {key: np.asarray(value) for key, value in obs.items()}


def _tensor_observation(seed: int) -> dict[str, th.Tensor]:
    """Convert a fresh observation into a batch of one dict of tensors."""
    return {key: th.as_tensor(value).unsqueeze(0) for key, value in _single_observation(seed).items()}


@pytest.fixture
def policy() -> CustomMultiInputPolicy:
    """Return a freshly built custom policy."""
    env = _make_env()
    observation_space = cast(spaces.Dict, env.observation_space)
    action_space = env.action_space
    return CustomMultiInputPolicy(observation_space, action_space, lr_schedule=lambda _steps: 3e-4)


def test_policy_is_masking_policy(policy: CustomMultiInputPolicy) -> None:
    """The policy inherits the multi-input actor-critic base and uses the 33-action space."""
    from stable_baselines3.common.policies import MultiInputActorCriticPolicy

    assert isinstance(policy, MultiInputActorCriticPolicy)
    discrete = cast("spaces.Discrete[np.integer[Any]]", policy.action_space)
    assert discrete.n == 33


def test_predict_action_is_allowed(policy: CustomMultiInputPolicy) -> None:
    """predict never returns a masked-out action."""
    obs = _single_observation(seed=7)
    allowed = {int(action) for action in obs["allowed_actions"] if int(action) != 0}
    predicted_action, state = policy.predict(obs, deterministic=True)
    action = int(np.asarray(predicted_action).reshape(-1)[0])
    assert state is None
    assert action in allowed


def test_predict_return_dist(policy: CustomMultiInputPolicy) -> None:
    """predict with return_dist yields a usable distribution over all 33 actions."""
    obs = _single_observation(seed=9)
    dist, state = policy.predict(obs, deterministic=False, return_dist=True)
    assert state is None
    distribution = cast(Distribution, dist)
    predicted = np.asarray(distribution.get_actions(deterministic=True))
    assert predicted.size >= 1
    assert int(predicted.reshape(-1)[0]) <= 32


def test_predict_rejects_obs_info_tuple(policy: CustomMultiInputPolicy) -> None:
    """Passing a (obs, info) tuple is rejected explicitly."""
    with pytest.raises(ValueError, match="tuple"):
        policy.predict((np.zeros(3), {"y": 2}))


def test_forward_shapes(policy: CustomMultiInputPolicy) -> None:
    """forward returns batched actions, values, and log probabilities."""
    obs = _tensor_observation(seed=7)
    actions, values, log_prob = policy.forward(obs, deterministic=True)
    assert isinstance(actions, th.Tensor)
    assert isinstance(values, th.Tensor)
    assert isinstance(log_prob, th.Tensor)
    assert values.shape[0] == 1
    assert log_prob.shape[0] == 1
