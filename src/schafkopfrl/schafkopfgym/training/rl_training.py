"""Iterative PPO training loop for the Schafkopf RL agent."""

from pathlib import Path

from stable_baselines3 import PPO

from schafkopfrl.schafkopfengine.players.dummy_player import DummyPlayer
from schafkopfrl.schafkopfengine.players.player import Player
from schafkopfrl.schafkopfengine.players.random_player import RandomSauPlayer
from schafkopfrl.schafkopfengine.players.rl_player import RLPlayer, RLPlayerLearning

# from torch.profiler import ProfilerActivity, profile, record_function
from schafkopfrl.schafkopfgym.custompolicy import CustomMultiInputPolicy
from schafkopfrl.schafkopfgym.schafkopfgym import SchafkopfEnv
from schafkopfrl.schafkopfgym.tb_callback import HParamAndSaveCallback
from schafkopfrl.schafkopfgym.vec_env_schafkopfgym import enchant_env

# TRAINING:
# OBSERVATIONSPACE:
# REWARD:
# PARAMS:


def make_players_rng() -> list[Player]:
    """Build a team of one learning player and three random Saus players."""
    return [RLPlayerLearning(0)] + [RandomSauPlayer(i) for i in range(1, 4)]


def make_players_tholu() -> list[Player]:
    """Build a team with random opponents and one dummy (tholu) player."""
    return [RLPlayerLearning(0)] + [RandomSauPlayer(i) for i in range(1, 3)] + [DummyPlayer(i) for i in range(3, 4)]


def make_players_self() -> list[Player]:
    """Build a team with random opponents and a previous model copy."""
    return (
        [RLPlayerLearning(0)]
        + [RandomSauPlayer(i) for i in range(1, 3)]
        + [RLPlayer(i, model_path="iter_model.zip'") for i in range(3, 4)]
    )


def make_players_self_tholu() -> list[Player]:
    """Build a team with previous-model copies and a dummy player."""
    return (
        [RLPlayerLearning(0)]
        + [RandomSauPlayer(i) for i in range(1, 2)]
        + [RLPlayer(i, model_path="iter_model.zip'") for i in range(2, 3)]
        + [DummyPlayer(i) for i in range(3, 4)]
    )


def main() -> None:
    """Run the iterative training loop over opponent configurations."""
    total_timesteps = 8_000_000

    env_kwargs = {"make_players": make_players_rng, "learning_player_pos": 1}

    env = enchant_env(SchafkopfEnv, env_kwargs=env_kwargs, n_envs=24, monitor_dir=None)

    #  ProfilerActivity.CUDA, ProfilerActivity.XPU

    # with profile(activities=[ProfilerActivity.CPU, ProfilerActivity.XPU], record_shapes=True,) as prof:
    #    with record_function("model_inference"):

    net_arch_shared = {"pi": [256, 256, 64], "vf": [256, 256, 64]}

    model = PPO(
        CustomMultiInputPolicy,
        # "MultiInputPolicy",
        env,
        policy_kwargs={"net_arch": net_arch_shared},
        n_steps=80000,
        batch_size=80,
        gamma=0.99,
        gae_lambda=0.95,
        n_epochs=4,
        clip_range=0.1,
        ent_coef=0.05,
        vf_coef=0.5,
        max_grad_norm=0.5,
        clip_range_vf=0.1,
        target_kl=None,
        learning_rate=2.5 * 10**-4,
        verbose=1,
        tensorboard_log="./reports/tb/PPO/BORING/",
        device="auto",
        normalize_advantage=True,
    )

    callback = HParamAndSaveCallback(check_freq=192000, save_path="./models/RL/checkpoints", verbose=1)

    for i in range(32):
        print(i)  # noqa: T201 Intentional interactive/CLI output.
        if i % 4 == 0:
            print("Training: RANDOM")  # noqa: T201 Intentional interactive/CLI output.
            env_kwargs = {"make_players": make_players_rng, "learning_player_pos": 1}
            total_timesteps = 16_000_000
        elif i % 4 == 1:
            print("Training: Tholu")  # noqa: T201 Intentional interactive/CLI output.
            env_kwargs = {"make_players": make_players_tholu, "learning_player_pos": 1}
            total_timesteps = 8_000_000
        elif i % 4 == 2:
            print("Training: Self")  # noqa: T201 Intentional interactive/CLI output.
            env_kwargs = {"make_players": make_players_self, "learning_player_pos": 1}
            total_timesteps = 8_000_000
        elif i % 4 == 3:
            print("Training: Cross")  # noqa: T201 Intentional interactive/CLI output.
            env_kwargs = {"make_players": make_players_self_tholu, "learning_player_pos": 1}
            total_timesteps = 8_000_000

        env = enchant_env(SchafkopfEnv, env_kwargs=env_kwargs)

        path = Path("./models/RL/iter_model")
        if path.exists():
            model = PPO.load(path, env=env)
        else:
            model = PPO(CustomMultiInputPolicy, env, policy_kwargs={"net_arch": net_arch_shared})

        model.learn(total_timesteps=total_timesteps, progress_bar=True, callback=callback)
        model.save(path)


if __name__ == "__main__":
    main()
