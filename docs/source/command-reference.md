# Project command reference

This page is generated for **Schafkopf RL** and contains only commands supported by this project's selected Copier features. Run commands from the repository root unless a section says otherwise.

The template repository's `docs/command-reference.md` is the complete cross-configuration reference. A full data-science showcase can add separate walkthroughs and expected outputs without changing this project-specific command contract.

## Command conventions

- Use `uv run --locked ...` for reproducible validation against `uv.lock`.
- Use unlocked `uv` commands only while intentionally changing dependencies or generated state.
- Tox is the public task interface shared by local development and CI.
- Arguments after `tox run -e <environment> --` are forwarded to that environment's command.

## Set up a checkout

A contributor cloning an established repository runs:

```bash
uv sync --locked
uv run --locked tox
```

The maintainer creating the repository runs the one-time bootstrap before normal development begins:

```bash
uv run scripts/init_project.py \
  --git-name "Your Name" \
  --git-email "you@example.com"
```

Do not rerun `scripts/init_project.py` in an established checkout. Its default initial tag is `v0.0.1`; `MAINTAINING.md` documents its options and recovery behavior.

## Validation tasks

| Goal | Command | What it validates |
| --- | --- | --- |
| Configured default suite | `uv run --locked tox` | The environments selected for this project |
| Every repository hook | `uv run --locked tox run -e pre-commit` | All configured pre-commit hooks against all files |
| CI repository hygiene | `uv run --locked tox run -e repo-checks` | The non-duplicated manual-stage repository checks |
| Lock consistency | `uv run --locked tox run -e lock` | `uv.lock` matches `pyproject.toml` |
| Static validation | `uv run --locked tox run -e lint` | Docstrings, Ruff, formatting, and strict Mypy |
| Tests on Python 3.11 | `uv run --locked tox run -e py311` | The built wheel installed and tested on Python 3.11 |
| Tests on Python 3.12 | `uv run --locked tox run -e py312` | The built wheel installed and tested on Python 3.12 |
| Tests on Python 3.13 | `uv run --locked tox run -e py313` | The built wheel installed and tested on Python 3.13 |
| Tests on Python 3.14 | `uv run --locked tox run -e py314` | The built wheel installed and tested on Python 3.14 |
| Complete Python matrix | `uv run --locked tox run -m test` | Every selected Python test environment |
| Notebook validation | `uv run --locked tox run -e notebooks` | Exploratory notebook outputs, metadata, and Python-cell docstrings |
| UML generation | `uv run --locked tox run -e uml` | Pyreverse/Mermaid diagram sources |
| Documentation | `uv run --locked tox run -e docs` | Strict HTML plus API documentation coverage |
| Distribution validation | `uv run --locked tox run -e package-check` | Fresh sdist/wheel metadata and wheel contents |
| Build distributions | `uv run --locked tox run -e build` | Source and wheel distributions under `dist/` |
| Clean generated output | `uv run --locked tox run -e clean` | Reports, builds, and generated documentation sources |

List the rendered environments and their descriptions with:

```bash
uv run tox list
```

## Focused tests

Use the minimum selected Python environment for a built-wheel test:

```bash
uv run --locked tox run -e py311 -- -k <expression>
uv run --locked tox run -e py311 -- tests/test_module.py::test_name
uv run --locked tox run -e py311 -- --log-cli-level=INFO
```

For faster iteration, `uv run --locked --group test pytest` tests the development environment rather than the built wheel.

## Dependency operations

| Goal | Command |
| --- | --- |
| Synchronise an established checkout | `uv sync --locked` |
| Add a runtime dependency | `uv add <package>` |
| Remove a runtime dependency | `uv remove <package>` |
| Add a test dependency | `uv add --group test <package>` |
| Add a lint or type dependency | `uv add --group lint <package>` |
| Add a documentation dependency | `uv add --group docs <package>` |
| Add a notebook dependency | `uv add --group notebooks <package>` |
| Resolve the lock | `uv lock` |
| Verify the lock without changing it | `uv lock --check` |

Commit `pyproject.toml` and `uv.lock` together after intentional dependency changes.

## Pre-commit

Install hooks once in a development checkout:

```bash
uv run pre-commit install
```

Run the complete configured hook set independently with:

```bash
uv run --locked tox run -e pre-commit
```

## Documentation

| Goal | Command | Output |
| --- | --- | --- |
| Complete strict build | `uv run --locked tox run -e docs` | HTML and API coverage |
| HTML only | `uv run --locked tox run -e docs -- html` | `reports/sphinx/html/` |
| API coverage only | `uv run --locked tox run -e docs -- coverage` | `reports/sphinx/coverage/` |
| Remove documentation output | `uv run --locked tox run -e docs -- clean` | Removes generated Sphinx sources and output |
| Generate UML only | `uv run --locked tox run -e uml` | Mermaid sources under `docs/source/diagrams/` |

Sphinx warnings fail the build. API coverage fails when public symbols are undocumented or modules cannot be imported.

## Notebooks

```bash
uv run --group notebooks jupyter lab
uv run --locked tox run -e notebooks
```

Exploratory notebooks live under `notebooks/`; documentation notebooks live under `docs/source/notebooks/`. Their output policies intentionally differ and are documented in `docs/README.md`.

## Packaging and version diagnostics

```bash
uv run --locked tox run -e package-check
git describe --tags --always --dirty
git tag --points-at HEAD
```

The project derives its version from Git tags. Preserve tags in CI and release checkouts.

## Update from the Copier template

Preview an update before applying it:

```bash
uvx copier update --pretend --vcs-ref=v1.1.0
uvx copier update --vcs-ref=v1.1.0
uv lock
uv sync
uv run --locked tox
```

Use a concrete release tag for reproducible upgrades. `MAINTAINING.md` documents conflict resolution, migrations, and project-owned files.

## Generated outputs

| Output | Produced by |
| --- | --- |
| `reports/pytest/report.html` and `report.jsonl` | Python test environments |
| `reports/coverage/` | pytest coverage |
| `reports/sphinx/html/` | Documentation HTML build |
| `reports/sphinx/coverage/` | API documentation coverage |
| `dist/` | Build and package-check environments |

Remove generated output through `uv run --locked tox run -e clean` rather than deleting individual report paths by hand.
