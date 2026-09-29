# Schafkopf RL

Reinforcement learning for **Schafkopf**, the German four-player trick-taking card game — with a game engine, a Gymnasium environment, and stable-baselines3 (PPO) training utilities.

## Features

- Complete Schafkopf rule engine: game search, Ramsch / Wenz / Sauspiel / Farbwenz / Solo, contra & retour, laufende, schneider
- Gymnasium-compatible environment (dictionary observations, integer card actions)
- Pluggable players: dummy, random, interactive human (console), and RL players backed by stable-baselines3 models
- PPO training loop with tensorboard logging, hparam tracking, and automatic best-model saving
- Play it yourself from the terminal — one human player against three random players by default

## Quick start

```bash
uv sync --locked        # set up the locked environment
uv run schafkopf        # play: you vs. three random players
```

```bash
uv run schafkopf --humans 2 --games 5   # two human seats, five games
uv run schafkopf --humans 0             # watch random players play
```

### Training

Start PPO training from the command line:

```bash
uv run src/schafkopfrl/schafkopfgym/training/rl_training.py
```

## Python API

```python
from schafkopfrl.schafkopfgym.schafkopfgym import SchafkopfEnv
from schafkopfrl.schafkopfgym.training.rl_training import make_players_rng

env = SchafkopfEnv(make_players=make_players_rng)  # 1 learning player + 3 random rivals
obs, info = env.reset()
# ... your agent picks an action from obs ...
obs, reward, terminated, truncated, info = env.step(action)
```

## Repository layout

| Path | Contents |
| --- | --- |
| `src/schafkopfrl/schafkopfengine` | Rules, deck, game state, and the player classes |
| `src/schafkopfrl/schafkopfgym` | Gymnasium env, vectorizer, custom policy, PPO training loop |
| `notebooks/` | Arena evaluation and analysis notebooks |
| `docs/` | Sphinx API documentation (built via `tox -e docs`) |
| `tests/` | 129 tests |

## Development

```bash
uv sync --locked
uv run --locked tox   # lint, types, tests, docs, package checks
```

See `AGENTS.md` (task → command catalog), `CONTRIBUTING.md`, and `MAINTAINING.md` for the full workflow.

## License

MIT — see [LICENSE](LICENSE).

## Disclaimer

This project is part of work originally done in collaboration with Isar Active GmbH. For that reason it does not include some models, datasets, and evaluations that remain tied to the company and are not distributed here.
