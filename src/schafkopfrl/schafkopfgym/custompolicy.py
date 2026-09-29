"""Custom stable-baselines3 policy that masks out disallowed Schafkopf actions."""

from typing import Any

import numpy as np
import torch as th
from gymnasium import spaces
from stable_baselines3.common.distributions import Distribution
from stable_baselines3.common.policies import MultiInputActorCriticPolicy
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor, CombinedExtractor
from stable_baselines3.common.type_aliases import Schedule
from torch import nn


class CustomMultiInputPolicy(MultiInputActorCriticPolicy):
    """Actor-critic policy that restricts actions to the currently allowed moves."""

    def __init__(
        self,
        observation_space: spaces.Dict,
        action_space: spaces.Space[Any],
        lr_schedule: Schedule,
        net_arch: list[int] | dict[str, list[int]] | None = None,
        activation_fn: type[nn.Module] = nn.Tanh,
        ortho_init: bool = True,
        use_sde: bool = False,
        log_std_init: float = 0.0,
        full_std: bool = True,
        use_expln: bool = False,
        squash_output: bool = False,
        features_extractor_class: type[BaseFeaturesExtractor] = CombinedExtractor,
        features_extractor_kwargs: dict[str, Any] | None = None,
        share_features_extractor: bool = True,
        normalize_images: bool = True,
        optimizer_class: type[th.optim.Optimizer] = th.optim.Adam,
        optimizer_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the policy by forwarding all arguments to the parent policy.

        Args:
            observation_space: Observation space of the environment.
            action_space: Action space of the environment.
            lr_schedule: Learning rate schedule.
            net_arch: Network architecture.
            activation_fn: Activation function class.
            ortho_init: Whether to use orthogonal weight initialization.
            use_sde: Whether to use state-dependent exploration.
            log_std_init: Initial value for the log standard deviation.
            full_std: Whether to use a full covariance.
            use_expln: Whether to use Expln activations.
            squash_output: Whether to squash the network output.
            features_extractor_class: Features extractor class.
            features_extractor_kwargs: Keyword arguments for the features extractor.
            share_features_extractor: Whether to share the features extractor between actor and critic.
            normalize_images: Whether to normalize images.
            optimizer_class: Optimizer class.
            optimizer_kwargs: Keyword arguments for the optimizer.
        """
        super().__init__(
            observation_space=observation_space,
            action_space=action_space,
            lr_schedule=lr_schedule,
            net_arch=net_arch,
            activation_fn=activation_fn,
            ortho_init=ortho_init,
            use_sde=use_sde,
            log_std_init=log_std_init,
            full_std=full_std,
            use_expln=use_expln,
            squash_output=squash_output,
            features_extractor_class=features_extractor_class,
            features_extractor_kwargs=features_extractor_kwargs,
            share_features_extractor=share_features_extractor,
            normalize_images=normalize_images,
            optimizer_class=optimizer_class,
            optimizer_kwargs=optimizer_kwargs,
        )

    def forward(
        self, obs: th.Tensor | dict[str, th.Tensor], deterministic: bool = False
    ) -> tuple[th.Tensor, th.Tensor, th.Tensor]:
        """Compute the policy forward pass, masking disallowed actions.

        Args:
            obs: Observation tensor or structured observation dict.
            deterministic: Whether to return the deterministic (mode) action.
        """
        # If the observation is a dict, extract allowed actions and remove them before feature extraction.
        allowed_actions = None
        if isinstance(obs, dict):
            # Copy the dict so we don't modify the caller's version.
            # obs = obs.copy()
            allowed_actions = obs["allowed_actions"]

        # Handle frame stacking:
        # If allowed_actions has more than 2 dimensions (e.g. [batch, stack, n_allowed]),
        # take the most recent frame.
        if allowed_actions is not None:
            if allowed_actions.ndim > 2:
                allowed_actions = allowed_actions[:, -1, :]
            elif allowed_actions.ndim == 1:
                allowed_actions = allowed_actions.unsqueeze(0)

        # Extract features from the processed observation.
        features = self.extract_features(obs)

        # Process through the MLP extractor.
        if self.share_features_extractor:
            latent_pi, latent_vf = self.mlp_extractor(features)
        else:
            pi_features, vf_features = features
            latent_pi = self.mlp_extractor.forward_actor(pi_features)
            latent_vf = self.mlp_extractor.forward_critic(vf_features)

        # Compute the value from the critic head.
        values = self.value_net(latent_vf)

        # Compute raw logits from the action network.
        logits = self.action_net(latent_pi)

        if allowed_actions is not None:
            # Ensure allowed_actions is on the proper device.
            allowed_actions = allowed_actions.to(logits.device)
            batch_size, num_actions = logits.shape[0], logits.shape[1]

            # Create a binary mask over the possible actions.
            allowed_mask = th.zeros((batch_size, num_actions), dtype=th.bool, device=logits.device)

            # Vectorized filtering: keep only indices > 0 and less than num_actions.
            # allowed_actions shape: [batch_size, n_allowed]
            valid = (allowed_actions > 0) & (allowed_actions < num_actions)
            if valid.any():
                # Get row and column indices of valid entries.
                rows, cols = th.nonzero(valid, as_tuple=True)
                indices_vals = allowed_actions[rows, cols].long()
                # Set the corresponding positions in the allowed_mask to True.
                allowed_mask[rows, indices_vals] = True

            # Set logits for disallowed actions to a large negative value.
            large_negative = -1e8
            masked_logits = th.where(allowed_mask, logits, large_negative * th.ones_like(logits))
            # Build the probability distribution from the masked logits.
            distribution = self.action_dist.proba_distribution(action_logits=masked_logits)
        else:
            distribution = self._get_action_dist_from_latent(latent_pi)

        # Sample the action and compute its log probability.
        actions = distribution.get_actions(deterministic=deterministic)
        log_prob = distribution.log_prob(actions)

        # Reshape actions to match the action space.
        actions = actions.reshape((-1, *self.action_space.shape))  # type: ignore
        return actions, values, log_prob

    def predict(  # type: ignore[override]  # SB3 runtime signature intentionally differs from typed parent (return_dist, (obs, info) guard).
        self,
        observation: np.ndarray | dict[str, np.ndarray] | tuple[np.ndarray, dict[str, object]],
        state: tuple[np.ndarray, ...] | None = None,
        episode_start: np.ndarray | None = None,
        deterministic: bool = False,
        return_dist: bool = False,
    ) -> tuple[np.ndarray | Distribution, tuple[np.ndarray, ...] | None]:
        """Return the action for a single (unbatched) observation.

        Args:
            observation: Observation to act on.
            state: Previous recurrent state, if the policy is stateful.
            episode_start: Flag indicating the start of an episode.
            deterministic: Whether to return the deterministic (mode) action.
            return_dist: Whether to return the probability distribution as well.
        """
        # 1) Eval mode
        self.set_training_mode(False)

        # 2) API guard
        if isinstance(observation, tuple) and len(observation) == 2 and isinstance(observation[1], dict):
            raise ValueError("Passed (obs, info) tuple to predict(). Use vec_env.reset().")

        # 3) Pull out allowed_actions before any feature extraction
        raw_allowed = None
        if isinstance(observation, dict) and "allowed_actions" in observation:
            raw_allowed = observation["allowed_actions"]  # remove so extract_features ignores it

        # 4) Move obs to tensor(s)
        obs_tensor, vectorized_env = self.obs_to_tensor(observation)

        # 5) Rebuild allowed_actions tensor on correct device
        allowed_actions = None
        if raw_allowed is not None:
            allowed_actions = th.tensor(raw_allowed, device=self.device, dtype=th.long)
            # ensure batch-dim
            if allowed_actions.ndim == 2:
                allowed_actions = allowed_actions.unsqueeze(0)
            # pick last frame if stacked
            if allowed_actions.ndim == 3:
                allowed_actions = allowed_actions[:, -1, :]
            elif allowed_actions.ndim == 1:
                allowed_actions = allowed_actions.unsqueeze(0)

        # 6) Extract features & get latent_pi
        features = self.extract_features(obs_tensor)
        if self.share_features_extractor:
            latent_pi, _ = self.mlp_extractor(features)
        else:
            latent_pi = self.mlp_extractor.forward_actor(features[0])

        # 7) Raw logits
        logits = self.action_net(latent_pi)

        # 8) Mask exactly as in forward()
        if allowed_actions is not None:
            _, na = logits.shape
            mask = th.zeros_like(logits, dtype=th.bool, device=self.device)
            valid = (allowed_actions > 0) & (allowed_actions < na)
            rows, cols = valid.nonzero(as_tuple=True)
            if len(rows) == 0:
                # sanity check: warn if we're never masking anything
                import warnings

                warnings.warn(
                    "allowed_actions mask yielded zero valid entries - no actions will be allowed!", stacklevel=2
                )
            else:
                sel = allowed_actions[rows, cols]
                mask[rows, sel] = True
                logits = logits.masked_fill(~mask, -1e8)

        # 9) Build distribution & optionally return it
        dist = self.action_dist.proba_distribution(action_logits=logits)
        if return_dist:
            return dist, state

        # 10) Sample / mode
        with th.no_grad():
            act_tensor = dist.get_actions(deterministic=deterministic)

        # 11) To numpy, reshape, clip/unscale
        action_shape = tuple(self.action_space.shape)  # type: ignore[arg-type]  # SB3 types shape as tuple[int, ...] | None; always set for Discrete/Box here.
        actions = act_tensor.cpu().numpy().reshape((-1, *action_shape))
        if isinstance(self.action_space, spaces.Box):
            if self.squash_output:
                actions = self.unscale_action(actions)
            else:
                actions = np.clip(actions, self.action_space.low, self.action_space.high)

        # 12) Squeeze if needed
        if not vectorized_env and actions.ndim > len(action_shape):
            actions = actions.squeeze(0)

        return actions, state
