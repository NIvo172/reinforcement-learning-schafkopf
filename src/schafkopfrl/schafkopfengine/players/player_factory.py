"""Factory functions that create players for the Schafkopf engine."""

from __future__ import annotations

from schafkopfrl.schafkopfengine.players.dummy_player import DummyPlayer
from schafkopfrl.schafkopfengine.players.human_player import HumanPlayer
from schafkopfrl.schafkopfengine.players.player import Player
from schafkopfrl.schafkopfengine.players.random_player import RandomPlayer, RandomSauPlayer
from schafkopfrl.schafkopfengine.players.rl_player import RLPlayer


def create_players(name: str, starting_uid: int = 0, end_uid: int = 4, load_best: bool = False) -> list[Player] | int:
    """Create a list of players of the given type.

    Args:
        name: Short name of the player type.
        starting_uid: First player id included.
        end_uid: Last player id (not included).
        load_best: Whether to load the best model.
    """
    if name == "DP":
        return [DummyPlayer(i) for i in range(starting_uid, end_uid)]

    if name == "Human":
        return [HumanPlayer(i) for i in range(starting_uid, end_uid)]

    if name == "RP":
        return [RandomPlayer(i) for i in range(starting_uid, end_uid)]

    if name == "RSP":
        return [RandomSauPlayer(i) for i in range(starting_uid, end_uid)]

    if name == "RL_BASIC":
        return [RLPlayer(i, "01_BASIC.zip") for i in range(starting_uid, end_uid)]

    return -1


"""
def create_players(name, starting_uid=1, end_uid=4, load_best=False, prob_trash=None):

    if name == 'DP':
        return [DummyPlayer(i) for i in range(starting_uid, end_uid)]

    if name == 'RSP':
        return [RandomSauPlayer(i) for i in range(starting_uid, end_uid)]

    if name.startswith('bc'):
        return [BCPlayer(i, model_path=name, prob_trash=prob_trash) for i in range(starting_uid, end_uid)]

    if name == 'RL_BASIC':
        return [RLPlayer(i, "01_BASIC.zip") for i in range(starting_uid, end_uid)]

    if name == 'RL_BASIC_v2':
        return [RLPlayer(i, "01_BASIC_v2.zip") for i in range(starting_uid, end_uid)]

    if name == 'RL_10M':
        return [RLPlayer(i, '202504251340_BASIC.zip') for i in range(starting_uid, end_uid)]

    if name == 'Ext_Obs':
        if load_best:
            return [RLPlayer(i, "202505132347_HYPER_EXTENDED_OBS.zip",) for i in range(starting_uid, end_uid)]
        return [RLPlayer(i, "202505132347_HYPER_EXTENDED_OBS.zip",) for i in range(starting_uid, end_uid)]

    if name == 'Reward_RL':
        if load_best:
            return [RLPlayer(i, "checkpoints/202505161803_best_model.zip",) for i in range(starting_uid, end_uid)]
        return [RLPlayer(i, "202505161803_HYPER_EXTENDED_OBS.zip",) for i in range(starting_uid, end_uid)]

    if name == 'Reward_RL_A3C':
        if load_best:
            return [RLPlayer(i, "checkpoints/202505181314_best_model.zip", algorithm='A2C') for i in range(starting_uid, end_uid)]
        return [RLPlayer(i, "202505181314_HYPER_EXTENDED_OBS.zip", algorithm='A2C') for i in range(starting_uid, end_uid)]

    if name == 'RL_TEAMPRED':
        return [RLPlayer(i, 'iter_model.zip') for i in range(starting_uid, end_uid)]

    if name == 'Human':
        return [HumanPlayer(i) for i in range(starting_uid, end_uid)]

    if name == 'TeamBase':
        return [ThoLuPlayer(i, 'schafkopf_ppo.zip') for i in range(starting_uid, end_uid)]

    if name == 'TeamHybrid':
        return [ThoLuPlayer(i, 'schafkopf_ppo_against_himself_and_random_20mio.zip') for i in range(starting_uid, end_uid)]

    if name == 'TeamTransfer':
        return [ThoLuPlayer(i, 'schafkopf_ppo_against_himself.zip') for i in range(starting_uid, end_uid)]

    return -1
"""
