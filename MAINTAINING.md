# Maintaining Schafkopf RL

This guide is for the initial project owner and long-term maintainers. Daily checkout setup, tests, and coding conventions are documented in `CONTRIBUTING.md`.

## Bootstrap a newly rendered repository

Run this command once, before normal development begins:

```bash
uv run scripts/init_project.py
```

The script is a standalone PEP 723 script, so `uv` runs it before the generated package has Git-derived version metadata.

Override the repository-local Git identity when required:

```bash
uv run scripts/init_project.py \
  --git-name "Your Name" \
  --git-email "you@example.com"
```

Available options:

```text
--git-name NAME       repository-local Git author name
--git-email EMAIL     repository-local Git author email
--tag TAG             initial tag; default v0.0.1
```

Without overrides, initialisation uses the repository-local placeholder `John Doe <john.doe@example.com>`. It does not change global Git configuration.

### Bootstrap lifecycle

The script:

1. verifies `git` and `uv`;
2. initialises a `main` branch and repository-local identity;
3. creates `Initial project` when no Git `HEAD` exists;
4. runs `uv sync`, creating `.venv` and `uv.lock`;
5. reruns pre-commit while automatic fixes keep changing files, up to three attempts;
6. skips DVC because it is not configured;
7. commits lock and generated-state changes when necessary;
8. requires a clean worktree;
9. creates the requested initial tag or verifies that it points to `HEAD`;
10. synchronises the tag-derived installed version; and
11. verifies that the worktree remains clean.

Output is written directly to the terminal. Running the initialisation script does not create a log file.

Initialisation may resume a partial first run, but it is not a contributor-onboarding command. The script refuses to move an existing initial tag from another commit.

Validate the initialised repository as a separate step:

```bash
uv run --locked tox
```

Keeping validation separate makes the one-time repository lifecycle explicit and leaves Tox as the repeatable validation interface used by contributors and CI.

## Dependency and lock policy

`pyproject.toml` is the declaration source and `uv.lock` is the resolved source. Contributors synchronise with:

```bash
uv sync --locked
```

Maintainers intentionally update dependencies with `uv add`, `uv remove`, or direct `pyproject.toml` edits followed by:

```bash
uv lock
uv sync
uv run --locked tox
```

A pip-compatible external view can be exported without replacing the lock:

```bash
uv export --frozen --format requirements.txt --output-file requirements.txt
```

`renovate.json` configures optional automated updates for every dependency manager Renovate detects. This includes PEP 621 dependencies, weekly `uv.lock` maintenance, pre-commit hooks, GitHub Actions, container images, and supported dependency files added later. Routine non-major updates are grouped, while major upgrades remain separate.

Renovate may update dependency references in CI configuration but does not otherwise change CI jobs, permissions, triggers, or validation policy. It remains inactive until the bot is enabled for the repository; every proposed update should pass the normal locked Tox suite before merging.

## Tox and task-script architecture

Tox is the supported task interface. Dependencies are declared once in `pyproject.toml` dependency groups and selected by Tox through `dependency_groups`; they should not normally be repeated under Tox `deps`.

Short declarative commands live in `tox.ini`. Python scripts exist for stateful, multi-step, filesystem-oriented, or cross-platform policy:

| Script | Lifecycle | Responsibility |
| --- | --- | --- |
| `scripts/init_project.py` | One-time bootstrap | Git, dependency lock, generated state, and initial tag |
| `scripts/clean.py` | Recurring maintenance | Cross-platform generated-output cleanup |
| `scripts/check_package.py` | Recurring validation | Fresh sdist/wheel builds, Twine checks, and wheel-content validation |
| `scripts/build_docs.py` | Recurring validation | Strict Sphinx HTML/API coverage, aggregation, and cleanup, including UML generation |
| `scripts/generate_uml.py` | Recurring generation | Pyreverse and Mermaid output |
| `scripts/check_notebooks.py` | Recurring validation | Exploratory notebook output and metadata policy |

Normal Tox and CI tasks do not call `init_project.py`.

## Build and versioning

This project uses **Hatchling with hatch-vcs**. Versions come from Git tags.

Validate source and wheel distributions:

```bash
uv run --locked tox run -e package-check
```

The package-check task removes stale output, builds an sdist and wheel, runs `twine check --strict`, and validates wheel contents.

A build from `v0.0.1` receives version `0.0.1`. Commits after a tag receive a PEP 440 development version derived from repository state. CI must fetch tags and sufficient history.

Before creating a release tag:

```bash
uv lock --check
uv run --locked tox
uv run --locked tox run -m test
git status --short
```

Then tag the clean validated commit using the project's release policy.

## CI

GitHub Actions is configured in `.github/workflows/ci.yml`.

Configured CI provisions Python and `uv`, then invokes named Tox environments for lock checks, lint, the Python matrix, optional capabilities, documentation, and distribution validation. Validation policy belongs in Tox and task scripts rather than provider YAML.

Test and coverage reports, documentation, and distributions are retained as provider artefacts where supported.
## Documentation maintenance

Documentation authoring is documented in `docs/README.md`. Maintainer-level validation uses:

```bash
uv run --locked tox run -e docs
```

The default target builds HTML and API documentation coverage. Sphinx warnings and undocumented public API fail validation.

## Update from the Copier template

Start from a clean worktree and preview:

```bash
copier update --pretend --vcs-ref=:current:
```

Apply the update:

```bash
copier update --vcs-ref=:current:
```

Use a concrete template tag such as `--vcs-ref=v0.2.0` for an intentional version upgrade. Copier compares the old template, new template, and project changes.

After resolving conflicts:

```bash
uv lock
uv sync
uv run --locked tox
```

Review additions and removals before committing. Do not edit `.copier-answers.yml` manually. Treat package-name, project-kind, minimum-Python, and build-backend changes as migrations.

## Generated output and cleanup

Remove reports, documentation output, build artefacts, and generated sources:

```bash
uv run --locked tox run -e clean
```

The cleanup task does not remove source data, authored documentation, the lockfile, or committed DVC metadata.

## Maintainer reference

- [Copier](https://copier.readthedocs.io/)
- [`uv`](https://docs.astral.sh/uv/)
- [Tox](https://tox.wiki/)
- [Hatchling](https://hatch.pypa.io/latest/config/build/)
- [`hatch-vcs`](https://github.com/ofek/hatch-vcs)
- [GitHub Actions](https://docs.github.com/actions)
