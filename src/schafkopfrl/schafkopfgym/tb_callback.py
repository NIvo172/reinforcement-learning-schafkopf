"""Training callback that logs hyperparameters and checkpoints models."""

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.logger import HParam

from schafkopfrl.utils.log import get_logger

logger = get_logger("HParamAndSaveCallback")

# This sets the global UID for Models once at import
# every model should have a unique timestamp.
TIMESTEMP = datetime.now(UTC).strftime("%Y%m%d%H%M")


class HParamAndSaveCallback(BaseCallback):
    """Log hyperparameters and save the best model during training.

    Every ``check_freq`` calls to _on_step, checks mean episode reward via ep_info_buffer and saves the model if it's a
    new best.
    """

    def __init__(self, check_freq: int, save_path: str, verbose: int = 1) -> None:
        """Store the save-check frequency, save path, and best reward so far.

        Args:
            check_freq: Number of steps between save checks.
            save_path: Directory in which checkpoints are saved.
            verbose: SB3 verbosity flag; values greater than zero enable logging.
        """
        super().__init__(verbose)
        # For saving best model
        self.check_freq = check_freq
        self.save_path = save_path
        self.best_mean_reward = -np.inf

    def _init_callback(self) -> None:
        # Ensure save directory exists
        if self.save_path is not None:
            Path(self.save_path).mkdir(parents=True, exist_ok=True)

    def _on_training_start(self) -> None:
        # Log hyperparameters once at the very beginning
        #        clip_value = self.model.clip_range(1) if callable(self.model.clip_range) else self.model.clip_range
        hparam_dict = {
            "algorithm": self.model.__class__.__name__,
            #            'batch size': self.model.batch_size,
            "gamma": self.model.gamma,  # type: ignore[attr-defined]  # PPO attribute present at runtime, but missing from the BaseAlgorithm static type.
            "gae lambda": self.model.gae_lambda,  # type: ignore[attr-defined]  # PPO attribute present at runtime, but missing from the BaseAlgorithm static type.
            #            'n_epochs': self.model.n_epochs,
            #            'clip range': clip_value,
            "learning rate": self.model.learning_rate,
        }
        metric_dict = {
            "rollout/ep_len_mean": 0,
            "rollout/ep_rew_mean": 0,
            "train/value_loss": 0.0,
        }
        self.logger.record(
            "hparams",
            HParam(hparam_dict, metric_dict),
            exclude=("stdout", "log", "json", "csv"),
        )
        if self.verbose > 0:
            logger.info("Logged hyperparameters for TensorBoard HParams tab.")

    def _on_step(self) -> bool:
        # Only run save-check every `check_freq` calls
        if self.n_calls % self.check_freq == 0:
            # Compute mean reward over episodes finished so far
            if len(self.model.ep_info_buffer) > 0:  # type: ignore[arg-type]  # SB3 types ep_info_buffer as deque | None, but it is populated when episodes end.
                ep_rewards = [ep_info["r"] for ep_info in self.model.ep_info_buffer]  # type: ignore[union-attr]  # SB3 types ep_info_buffer as deque | None, but it is set when an episode ends.
                current_mean = float(np.mean(ep_rewards))
            else:
                current_mean = None

            if current_mean is not None:
                if self.verbose > 0:
                    logger.info(
                        "[Step %s] mean_reward=%.2f  best=%.2f", self.num_timesteps, current_mean, self.best_mean_reward
                    )
                # If we've improved, save!
                if current_mean > self.best_mean_reward:
                    self.best_mean_reward = current_mean
            save_string = f"{TIMESTEMP}_checkpoint"
            save_file = Path(self.save_path) / save_string
            if self.verbose > 0:
                logger.info("New checkpoint! Saving model to %s.zip", save_file)
            self.model.save(save_file)

        return True
