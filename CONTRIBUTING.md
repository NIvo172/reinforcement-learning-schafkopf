# Contributing to Schafkopf RL

This guide is for developers working in an established repository. Initial repository creation, Git tagging, and Copier updates are maintainer operations documented in `MAINTAINING.md`.

## Requirements

- Python 3.11 or newer
- [`uv`](https://docs.astral.sh/uv/)
- Git

The full test matrix represents Python 3.11, 3.12, 3.13, 3.14. The default suite uses Python 3.11.

## Set up a checkout

Synchronise exactly the committed dependency state:

```bash
uv sync --locked
```

`pyproject.toml` declares dependencies and `uv.lock` records the resolved environment. `--locked` fails when those files disagree instead of changing the lock.

Install the Git hook:

```bash
uv run pre-commit install
```

The hook applies repository checks, docstring formatting, and Ruff fixes before a commit.
If `uv.lock` is absent because the project was just rendered, stop and follow the one-time bootstrap in `MAINTAINING.md`.

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/schafkopfrl/` | Installable typed package |
| `tests/` | Behavioural tests and fixtures |
| `scripts/` | Portable task implementations used by Tox |
| `pyproject.toml` | Package metadata, dependencies, and Python-tool policy |
| `uv.lock` | Resolved dependency state |
| `tox.ini` | Supported validation-task interface |
| `configs/` | Versioned experiment/model configuration |
| `data/` | External, raw, interim, and processed data boundaries |
| `models/` | Model artefacts or model metadata |
| `references/` | Data dictionaries and supporting references |
| `reports/` | Figures and generated analysis output |
| `notebooks/` | Exploratory notebooks subject to output hygiene checks |
| `docs/` | Sphinx source and documentation-author guide |

## Change dependencies

Runtime dependencies:

```bash
uv add <package>
uv remove <package>
```

Development-only dependencies belong in the group that consumes them:

```bash
uv add --group test <package>
uv add --group lint <package>
uv add --group docs <package>
uv add --group notebooks <package>
```

After editing dependency declarations:

```bash
uv lock
uv sync
uv run --locked tox run -e lock
```

Commit `pyproject.toml` and `uv.lock` together.

## Run validation

Tox is the preferred project-level task interface used locally and in CI.

| Task | Preferred Tox command | Direct command |
| --- | --- | --- |
| Default configured suite | `uv run --locked tox` | Run each applicable command below |
| Every pre-commit hook | `uv run --locked tox run -e pre-commit` | `uv run --locked --group lint pre-commit run --all-files --show-diff-on-failure` |
| CI repository hygiene | `uv run --locked tox run -e repo-checks` | `uv run --locked --group lint pre-commit run --hook-stage manual --all-files --show-diff-on-failure` |
| Lock consistency | `uv run --locked tox run -e lock` | `uv lock --check` |
| Static validation | `uv run --locked tox run -e lint` | `uv run --locked --group lint ruff check .`<br>`uv run --locked --group lint ruff format --check .`<br>`uv run --locked --group lint mypy src tests scripts` |
| Tests on Python 3.11 | `uv run --locked tox run -e py311` | `uv run --locked --group test pytest` |
| Complete Python matrix | `uv run --locked tox run -m test` | Run pytest with every selected interpreter |
| Notebook validation | `uv run --locked tox run -e notebooks` | `uv run --locked --group lint python scripts/check_notebooks.py` |
| UML generation | `uv run --locked tox run -e uml` | `uv run --locked --group docs python scripts/generate_uml.py` |
| Complete documentation | `uv run --locked tox run -e docs` | `uv run --locked --group docs python scripts/build_docs.py all` |
| HTML documentation | `uv run --locked tox run -e docs -- html` | `uv run --locked --group docs python scripts/build_docs.py html` |
| API documentation coverage | `uv run --locked tox run -e docs -- coverage` | `uv run --locked --group docs python scripts/build_docs.py coverage` |
| Clean documentation output | `uv run --locked tox run -e docs -- clean` | `uv run --locked --group docs python scripts/build_docs.py clean` |
| Distribution validation | `uv run --locked tox run -e package-check` | `uv run --locked --group package-check python scripts/check_package.py` |
| Build distributions | `uv run --locked tox run -e build` | `uv build` |
| Clean generated output | `uv run --locked tox run -e clean` | `uv run python scripts/clean.py` |

The `pyXY` environments build and test the installed wheel. Direct pytest uses the synchronised development environment and is useful for fast iteration, but it does not test the same packaging boundary.

Arguments after `--` are forwarded to pytest:

```bash
uv run --locked tox run -e py311 -- -k <expression>
uv run --locked tox run -e py311 -- --log-cli-level=INFO
```

## Test and coverage reports

Pytest uses branch coverage and fails below 80%. It writes:

- `reports/pytest/report.html`
- `reports/pytest/report.jsonl`
- `reports/pytest/logs/pytest.log`
- `reports/coverage/html/index.html`
- `reports/coverage/coverage.xml`
- `reports/coverage/coverage.json`

Live console logging is disabled by default; use `--log-cli-level=INFO` for one run.

## Pre-commit

Run the complete hook set:

```bash
uv run --locked tox run -e pre-commit
```

`repo-checks` is the narrower manual-stage subset used by CI. Ruff, Mypy, and notebook validation have dedicated Tox environments to keep CI failures focused.

## Notebooks

Start JupyterLab:

```bash
uv run --group notebooks jupyter lab
```

Ruff and `format-docstring-jupyter` validate Python cells. Exploratory notebooks under `notebooks/` must not retain removable output or volatile execution metadata. The pre-commit `nbstripout` hook enforces this when enabled.

Add the `keep_output` tag or `{"keep_output": true}` cell metadata only when an exploratory output must be retained. Documentation notebooks under `docs/source/notebooks/` are governed separately and are not automatically stripped.

## Documentation

The complete documentation-author workflow is in `docs/README.md`.

```bash
uv run --locked tox run -e docs
```

The default target builds strict HTML and API documentation coverage. Generated output is written under `reports/sphinx/`.

## Code conventions

- Docstrings use the **Google** convention.
- Ruff owns Python formatting and linting.
- Mypy runs in strict mode.
- Public functions, classes, modules, and methods require complete docstrings.
- Tests belong under `tests/` and should describe observable behavior.
- Keep imports lightweight; documentation and package validation import the built wheel.

## Tool reference

| Tool | Documentation |
| --- | --- |
| `uv` | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| Tox | [tox.wiki](https://tox.wiki/) |
| Ruff | [docs.astral.sh/ruff](https://docs.astral.sh/ruff/) |
| Mypy | [mypy.readthedocs.io](https://mypy.readthedocs.io/) |
| pytest | [docs.pytest.org](https://docs.pytest.org/) |
| pre-commit | [pre-commit.com](https://pre-commit.com/) |
| JupyterLab | [jupyterlab.readthedocs.io](https://jupyterlab.readthedocs.io/en/stable/) |
| Sphinx | [sphinx-doc.org](https://www.sphinx-doc.org/en/master/) |
