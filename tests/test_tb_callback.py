"""Tests for the training-time hyperparameter and checkpoint callback."""

from pathlib import Path
from unittest.mock import MagicMock

from schafkopfrl.schafkopfgym.tb_callback import HParamAndSaveCallback


def _make_callback(tmp_path: Path, check_freq: int = 1, verbose: int = 0) -> tuple[HParamAndSaveCallback, MagicMock]:
    """Create a callback with a fake model and logger attached."""
    callback = HParamAndSaveCallback(check_freq=check_freq, save_path=str(tmp_path / "checkpoints"), verbose=verbose)
    model = MagicMock(name="PPO")
    model.gamma = 0.99
    model.gae_lambda = 0.95
    model.learning_rate = 3e-4
    model.ep_info_buffer = [{"r": 1.0}]
    model.logger = MagicMock()
    callback.model = model
    callback.num_timesteps = 5
    return callback, model


def test_init_callback_creates_save_dir(tmp_path: Path) -> None:
    """The save path is created before training starts."""
    callback, _model = _make_callback(tmp_path)
    callback._init_callback()
    assert (tmp_path / "checkpoints").is_dir()


def test_on_training_start_logs_hyperparameters(tmp_path: Path) -> None:
    """Hyperparameters are recorded via the logger at training start."""
    callback, model = _make_callback(tmp_path)
    callback._on_training_start()
    assert model.logger.record.called


def test_on_step_saves_when_improving(tmp_path: Path) -> None:
    """An improving mean episode reward updates the best reward and saves."""
    callback, model = _make_callback(tmp_path, check_freq=1)
    model.ep_info_buffer = [{"r": 10.0}, {"r": 20.0}]
    callback.n_calls = 1
    assert callback._on_step() is True
    assert callback.best_mean_reward == 15.0
    model.save.assert_called_once()
    save_file = Path(str(model.save.call_args.args[0]))
    assert save_file.suffix == "" and "checkpoint" in save_file.name
    # Repeated steps never degrade the best reward.
    callback.n_calls = 2
    assert callback._on_step() is True
    assert callback.best_mean_reward == 15.0


def test_on_step_without_episodes_still_saves(tmp_path: Path) -> None:
    """Without finished episodes the callback skips the reward check but saves."""
    import numpy as np

    callback, model = _make_callback(tmp_path, check_freq=1)
    model.ep_info_buffer = []
    callback.n_calls = 1
    assert callback._on_step() is True
    assert np.isneginf(callback.best_mean_reward)
    model.save.assert_called_once()


def test_on_step_respects_check_freq(tmp_path: Path) -> None:
    """Steps not aligned with the frequency do not trigger a save."""
    callback, model = _make_callback(tmp_path, check_freq=3)
    callback.n_calls = 1
    assert callback._on_step() is True
    model.save.assert_not_called()
    callback.n_calls = 3
    assert callback._on_step() is True
    model.save.assert_called_once()
