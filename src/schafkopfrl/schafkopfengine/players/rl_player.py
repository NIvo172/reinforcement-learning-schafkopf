"""Reinforcement-learning players wrapping a stable-baselines3 agent."""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING

import gymnasium.spaces as spaces
import numpy as np
from stable_baselines3 import A2C, PPO

from schafkopfrl.schafkopfengine.players.player import Player
from schafkopfrl.schafkopfengine.utils.enums import Color, Game

if TYPE_CHECKING:
    from schafkopfrl.schafkopfengine.cards import Card


class RL(Player):
    """Base class for the reinforcement-learning players."""

    def __init__(self, uid: int) -> None:
        """Initialize the RL player with its unique id.

        Args:
            uid: Unique player id.
        """
        super().__init__(uid)
        self.observation: dict[str, object] = {}

    def choose_gametype(self) -> tuple[Game, Color]:
        """Choose the game type according to the standard rule."""
        return self.choose_gametype_rule(color_threshold=2, trumps_threshold=3)

    def contra(self) -> bool:
        """Skip the Contra declaration."""
        return False

    def retour(self) -> bool:
        """Skip the Retour declaration."""
        return False

    def _reset(self) -> None:
        super()._reset()
        self.observation = {}

    def observe(self) -> dict[str, object]:
        """Update and return the observation dict of this player."""
        # This updates the observation dict.
        self.observation.update(self._observe_basic())
        self.observation.update(self._observe_trick())
        self.observation.update(self._observe_cards())
        self.observation.update(self._observe_player_behavior())
        # for key, value in self.observation.items():
        #    print(key, value)
        return self.observation.copy()

    def _observe_trick(self) -> dict[str, object]:
        assert self._publicgamestate is not None  # noqa: S101 Internal invariant debug check.
        trick_current_cards_id = [card.model_id for card in self._publicgamestate.trick_current_cards]

        trick_current_cards_id = trick_current_cards_id[:4] + [0] * (4 - len(trick_current_cards_id))

        trick_current_owner = (
            self._publicgamestate.players.index(self._publicgamestate.trick_current_owner)
            if isinstance(self._publicgamestate.trick_current_owner, Player)
            else 4
        )

        trick_winning_card = (
            self._publicgamestate.trick_current_highest_card.model_id
            if self._publicgamestate.trick_current_highest_card
            else 0
        )

        observation: dict[str, object] = {
            "trick_current_owner": trick_current_owner,
            "trick_current_cards": np.array(trick_current_cards_id),
            "trick_current_points": self._publicgamestate.trick_current_points,
            "trick_winning_card": trick_winning_card,
            # PublicGameState does not expose player_points yet.
            # Per-player trick points accumulated so far in the game.
            "player_points": [self._publicgamestate.scores[player] for player in self._publicgamestate.players],
            "points_left": self._publicgamestate.points_left,
        }

        # for key, value in observation.items():
        #    print(f"{key}\n{value}\n")

        return observation

    def _observe_cards(self) -> dict[str, object]:
        assert self._publicgamestate is not None  # noqa: S101 Internal invariant debug check.
        assert self._publicgamestate.trumps_left is not None  # noqa: S101 Internal invariant debug check.
        colors_left = self._publicgamestate.colors_left.copy()
        trumps_left = self._publicgamestate.trumps_left.copy()

        for card in self.cards:
            if card.is_trump:
                trumps_left.remove(card)
                continue
            colors_left[card.color] -= 1

        colors_left_counts = list(colors_left.values())
        trumps_left_ids = [card.model_id for card in trumps_left]

        trumps_left_ids = trumps_left_ids[:14] + [0] * (14 - len(trumps_left_ids))

        cards_left = []
        for card in self._publicgamestate.cards_left:
            cards_left.append(card.model_id)
        cards_left = cards_left[:32] + [0] * (32 - len(cards_left))

        trumps_value = 0
        for trump in self._publicgamestate.trumps_left:
            trumps_value += trump.rank

        colors_count = list(self._publicgamestate.colors_count.values())
        observation: dict[str, object] = {
            "colors_left": np.array(colors_left_counts),
            "colors_count": np.array(colors_count),
            "trumps_left": np.sort(np.array(trumps_left_ids)),
            "trumps_value": np.array([trumps_value]),
            "cards_left": np.sort(np.array(cards_left)),
        }

        return observation

    def _observe_player_behavior(self) -> dict[str, object]:
        assert self._publicgamestate is not None  # noqa: S101 Internal invariant debug check.
        observation: dict[str, object] = {}
        for player in self._publicgamestate.players:
            player_pos = self._publicgamestate.players.index(player)
            player_info = [card.model_id for card in self._publicgamestate.played_cards_player[player]]

            player_info = player_info[:8] + [0] * (8 - len(player_info))

            player_info += list(self._publicgamestate.colors_left_player[player].values())

            player_info += [self._publicgamestate.trumps_left_player[player]]

            observation["player_0" + str(player_pos)] = np.array(player_info)

        # for key, value in observation.items():
        #    print(f"{key}\n{value}\n")

        return observation

    def _observe_basic(self) -> dict[str, object]:
        # Invariant: observe() only runs while a game is active.
        assert self._publicgamestate is not None  # noqa: S101 Internal invariant debug check.
        assert self._publicgamestate.playing_order is not None  # noqa: S101 Internal invariant debug check.
        assert self._publicgamestate.calling_player is not None  # noqa: S101 Internal invariant debug check.
        assert self.team is not None  # noqa: S101 Internal invariant debug check.

        # Model ID mapping to cards in numpy.
        played_cards = np.zeros(32, dtype=np.int64)
        left_cards = np.zeros(32, dtype=np.int64)
        for idx, (played_card, left_card) in enumerate(
            # Pairwise truncation is intentional: this mapping only covers the played cards.
            zip(self._publicgamestate.cards_played, self._publicgamestate.cards_left)  # noqa: B905 Intentional truncation of the legacy card mapping.
        ):
            played_cards[idx] = played_card.model_id
            left_cards[idx] = left_card.model_id

        allowed_cards = self._allowed_cards()

        action_ids = [card.model_id for card in allowed_cards]

        action_ids = action_ids[:8] + [0] * (8 - len(action_ids))

        # playing_order =[player.id for player in self._publicgamestate.playing_order]

        observation = {
            "position": self._publicgamestate.players.index(self),
            "playing_order": [player.id for player in self._publicgamestate.playing_order],
            "handcards": np.sort(self._hand_cards_to_model()),
            "allowed_actions": np.array(action_ids),
            "team": self.team.value,
            "team_dist": self._get_team_obs_lstm(),
            "ruf_color": self._publicgamestate.game_color.value,  # This will break in SOLO (future 2028)
            "played_cards": np.array(played_cards),
            "trick_number": self._publicgamestate.trick_number + 1,
            "player_pos": np.array(self._publicgamestate.players.index(self._publicgamestate.calling_player)),
        }
        # print(observation["played_cards"])
        # for key, value in observation.items():
        #    print(f"{key}\n{value}\n")
        # print(f"player_pos\n{np.array(self._publicgamestate.players.index(self._publicgamestate.calling_player))}")
        return observation

    def _hand_cards_to_model(self) -> np.ndarray:
        mapped_cards = []
        for card in self.cards:
            mapped_cards.append(card.model_id)

        mapped_cards = mapped_cards[:8] + [0] * (8 - len(mapped_cards))

        return np.array(mapped_cards)

    def _get_team_obs_lstm(self) -> np.ndarray:
        # Invariant: observe() only runs while a game is active with a calling player.
        assert self._publicgamestate is not None  # noqa: S101 Internal invariant debug check.
        assert self._publicgamestate.calling_player is not None  # noqa: S101 Internal invariant debug check.
        if self.teammember:
            team_dist: list[float] = []
            for player in self._publicgamestate.players:
                if player.team == self.team:
                    team_dist.append(1)
                else:
                    team_dist.append(0)
        else:
            if self == self._publicgamestate.calling_player:
                team_dist = [0.33, 0.33, 0.33, 0.33]
                team_dist[self._publicgamestate.players.index(self)] = 1
            else:
                team_dist = [0.5, 0.5, 0.5, 0.5]
                team_dist[self._publicgamestate.players.index(self)] = 1
                team_dist[self._publicgamestate.players.index(self._publicgamestate.calling_player)] = 0

        # else:
        #    team_dist = self.team_model(self._construct_input_vector_70())
        #    team_dist = team_dist.detach().numpy()[0]
        #    team_dist[self._publicgamestate.players.index(self)] = 1
        #    if self.team == Team.NONPLAYER:
        #        team_dist[self._publicgamestate.players.index(self._publicgamestate.calling_player)] = 0
        #    elif self.team == Team.PLAYER:
        #        team_dist[self._publicgamestate.players.index(self._publicgamestate.calling_player)] = 1
        #
        #    return team_dist

        return np.array(team_dist, dtype=np.float32)

    def _get_team_obs(self) -> np.ndarray:
        assert self._publicgamestate is not None  # noqa: S101 Internal invariant debug check.
        if self.teammember:
            team_dist: list[float] = []
            for player in self._publicgamestate.players:
                if player == self.team:  # type: ignore[comparison-overlap]  # Legacy comparison; always False at runtime.
                    team_dist.append(1)  # type: ignore[unreachable]
                else:
                    team_dist.append(0)
        else:
            team_dist = 4 * [0.0]
            self_pos = self._publicgamestate.players.index(self)
            game_player = self._publicgamestate.calling_player

            team_dist = [0 if player == game_player else 0.5 for player in self._publicgamestate.players]
            team_dist[self_pos] = 1
            if game_player == self:
                team_dist = 4 * [0.33]
                team_dist[self_pos] = 1
                return np.array(team_dist, dtype=np.float32)

        return np.array(team_dist, dtype=np.float32)

    def _check_legal_action(self, action: int) -> bool:
        allowed_cards = self._allowed_cards()
        return action in [card.model_id for card in allowed_cards]

    def _basic_space(self) -> spaces.Dict:
        basic_space = spaces.Dict(
            {
                "position": spaces.Discrete(5),
                "handcards": spaces.MultiDiscrete([33] * 8),
                "allowed_actions": spaces.MultiDiscrete([33] * 8),
                "team": spaces.Discrete(2),
                "team_dist": spaces.Box(low=0, high=1, shape=(4,)),
                "ruf_color": spaces.Discrete(5),
                "played_cards": spaces.MultiDiscrete([33] * 32),
                "trick_number": spaces.Discrete(9),
                "player_pos": spaces.Discrete(5),
                "trick_current_owner": spaces.Discrete(5),
                "trick_current_cards": spaces.MultiDiscrete([33] * 4),
                "trick_current_points": spaces.Discrete(45),
                "trick_winning_card": spaces.Discrete(33),
                "colors_left": spaces.MultiDiscrete([7] * 4),
                "colors_count": spaces.MultiDiscrete([7] * 4),
                "trumps_left": spaces.MultiDiscrete([33] * 14),
                "player_00": spaces.MultiDiscrete([33] * 13),
                "player_01": spaces.MultiDiscrete([33] * 13),
                "player_02": spaces.MultiDiscrete([33] * 13),
                "player_03": spaces.MultiDiscrete([33] * 13),
                "cards_left": spaces.MultiDiscrete([33] * 32),
                "playing_order": spaces.MultiDiscrete([4] * 4),
                "player_points": spaces.MultiDiscrete([121] * 4),
                "points_left": spaces.Discrete(121),
                "trumps_value": spaces.Box(low=0.0, high=156.0, shape=(1,), dtype=np.float32),
            }
        )
        return basic_space


class RLPlayerLearning(RL):
    """RL player used during learning to replay given actions."""

    def __init__(self, uid: int) -> None:
        """Initialize the learning RL player with its unique id.

        Args:
            uid: Unique player id.
        """
        super().__init__(uid)

    def _play_card(self, allowed_cards: list[Card]) -> Card:
        """Satisfy the ``Player`` abstract contract; scripted actions play via ``play_card``."""
        raise RuntimeError("RLPlayerLearning plays scripted actions via play_card(action); not the abstract hook.")

    def play_card(self, action: int | None = None) -> Card:
        """Play the card that matches the given action.

        Args:
            action: Model id of the card to replay. Required for this learning player.
        """
        # self.log_player()
        assert action is not None  # noqa: S101 Internal invariant debug check.
        assert self._check_legal_action(action)  # noqa: S101 Internal invariant debug check.

        for idx, card in enumerate(self.cards):
            if card.model_id == action:
                card_to_play = self.cards[idx]
                self._decount_card(card_to_play)
                break

        return card_to_play


class RLPlayer(RL):
    """RL player that acts with a trained stable-baselines3 model."""

    anchor_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    path_to_rl = anchor_dir / "models" / "RL"

    def __init__(
        self, uid: int, model_path: str, stack_size: int = 8, device: str = "cpu", algorithm: str = "PPO"
    ) -> None:
        """Initialize the RL player with the model to load.

        Args:
            uid: Unique player id.
            model_path: Path of the model file relative to the model directory.
            stack_size: Number of observation frames to stack.
            device: Device the model should run on.
            algorithm: Name of the stable-baselines3 algorithm.
        """
        super().__init__(uid)
        for path_part in model_path.split("/"):
            self.path_to_rl /= path_part
        if algorithm == "PPO":
            self.model: PPO | A2C = PPO.load(self.path_to_rl, device=device)
        if algorithm == "A2C":
            self.model = A2C.load(self.path_to_rl, device=device)

        self.k = stack_size
        self.frames: dict[str, deque[object]] | None = None
        self._new_episode = True

    def play_card(self, action: int | None = None) -> Card:
        """Choose and return the card to play with the model.

        Args:
            action: Ignored; the model selects the action from its observation.
        """
        # self.log_player()
        raw_obs = self.observe()

        if self._new_episode:
            self.frames = {key: deque([val] * self.k, maxlen=self.k) for key, val in raw_obs.items()}
            self._new_episode = False
        else:
            assert self.frames is not None  # noqa: S101 Internal invariant debug check.
            for key, val in raw_obs.items():
                self.frames[key].append(val)

        assert self.frames is not None  # noqa: S101 Internal invariant debug check.

        # numpy's stubs cannot see deque[object] values as array-like; they are numeric obs values at runtime.
        stacked_obs: dict[str, np.ndarray] = {
            key: np.stack(self.frames[key], axis=0)  # type: ignore[arg-type]
            for key in self.frames
        }

        model_action, _ = self.model.predict(stacked_obs, deterministic=True)

        # SB3 predict yields a numpy scalar for a Discrete action space at runtime.
        assert self._check_legal_action(int(model_action))  # noqa: S101 Internal invariant debug check.

        for card in self.cards:
            if card.model_id == model_action:
                played_card = card
                break

        self._decount_card(played_card)

        return played_card

    def _play_card(self, allowed_cards: list[Card]) -> Card:
        """Satisfy the ``Player`` abstract contract by delegating to ``play_card``."""
        return self.play_card()

    def _reset(self) -> None:
        super()._reset()
        self._new_episode = True

    def choose_gametype(self) -> tuple[Game, Color]:
        """Choose the game type according to the standard rule."""
        return self.choose_gametype_rule()
