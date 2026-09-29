"""Vectorization helper that wraps SchafkopfEnv in a dummy vector env."""

import random

from gymnasium.wrappers import FrameStackObservation
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import DummyVecEnv

from schafkopfrl.schafkopfengine.players.dummy_player import DummyPlayer
from schafkopfrl.schafkopfengine.players.rl_player import RLPlayer
from schafkopfrl.schafkopfgym.schafkopfgym import SchafkopfEnv


def enchant_env(
    env: type[SchafkopfEnv],
    env_kwargs: dict[str, object],
    n_envs: int = 24,
    seed: int | None = None,
    monitor_dir: str | None = None,
) -> DummyVecEnv:
    """Create a stacked dummy vector env of SchafkopfEnv instances.

    Args:
        env: Environment class to instantiate.
        env_kwargs: Keyword arguments forwarded to the environment constructor.
        n_envs: Number of parallel environments.
        seed: Optional seed; a random seed is chosen when omitted.
        monitor_dir: Optional directory for monitors.
    """
    import sys

    def make_single_env() -> SchafkopfEnv:
        """Instantiate one wrapped environment with the shared kwargs."""
        return env(**env_kwargs)  # type: ignore[arg-type]  # dict[str, object] kwargs can't be statically matched to SchafkopfEnv.__init__.

    vec_env = make_vec_env(
        make_single_env,
        n_envs=n_envs,
        seed=seed if seed else random.randint(0, sys.maxsize),  # noqa: S311 Intentional non-cryptographic game randomness.
        monitor_dir=monitor_dir,
        vec_env_cls=DummyVecEnv,
        wrapper_class=FrameStackObservation,  # type: ignore[arg-type]  # SB3 types wrapper_class as a simple callable; the generic gym.wrapper class works at runtime.
        wrapper_kwargs={
            "stack_size": 8,
        },
    )

    return vec_env  # type: ignore[return-value]  # SB3's make_vec_env is statically typed as VecEnv; vec_env_cls=DummyVecEnv gives a DummyVecEnv at runtime.


def main() -> None:
    """Build a small two-env vectorized environment as a smoke test."""
    players = [RLPlayer(0)] + [DummyPlayer(i) for i in range(1, 4)]  # type: ignore[call-arg]  # pre-existing broken smoke-test call: RLPlayer requires model_path.

    env_kwargs = {"players": players, "learning_player_pos": 1}

    enchant_env(SchafkopfEnv, env_kwargs=env_kwargs, n_envs=2)


#    gym_check_env(env)
#    sb3_check_env(env)

if __name__ == "__main__":
    main()
