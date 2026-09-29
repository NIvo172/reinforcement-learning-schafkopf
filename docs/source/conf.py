"""Sphinx configuration for Schafkopf RL."""

import os
import tomllib
from importlib import metadata
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_project_metadata() -> dict[str, Any]:
    """Load PEP 621 project metadata from the repository's pyproject.toml."""
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)

    project_metadata = pyproject.get("project")
    if not isinstance(project_metadata, dict):
        raise RuntimeError("pyproject.toml does not contain a [project] table.")
    return project_metadata


def format_authors(project_metadata: dict[str, Any]) -> str:
    """Format PEP 621 author entries for Sphinx project metadata."""
    formatted_authors: list[str] = []
    authors = project_metadata.get("authors", [])
    if not isinstance(authors, list):
        return ""

    for author_entry in authors:
        if not isinstance(author_entry, dict):
            continue
        name = str(author_entry.get("name", "")).strip()
        email = str(author_entry.get("email", "")).strip()
        if name and email:
            formatted_authors.append(f"{name} <{email}>")
        elif name or email:
            formatted_authors.append(name or email)

    return ", ".join(formatted_authors)


project_metadata = load_project_metadata()
project = str(project_metadata["name"])
author = format_authors(project_metadata)
project_license = str(project_metadata.get("license", ""))

try:
    release = metadata.version(project)
except metadata.PackageNotFoundError:
    release = "0+unknown"

version = release

extensions = [
    "myst_nb",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "sphinx.ext.duration",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_inline_tabs",
    "sphinxcontrib.mermaid",
]

templates_path = ["_templates"]
autosummary_generate = True
autodoc_typehints = "description"
napoleon_google_docstring = True
napoleon_numpy_docstring = False
coverage_modules = ["schafkopfrl"]
coverage_show_missing_items = True
coverage_statistics_to_stdout = True
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

documentation_builder = os.environ.get("PROJECT_DOCS_BUILDER")

suppress_warnings = [
    # MyST cross-references to not-yet-authored pages (readme, command-reference, ...).
    "myst.xref_missing",
]
if documentation_builder == "coverage":
    exclude_patterns.extend(["auto_examples/**", "diagrams/**", "notebooks/**", "sg_execution_times.rst"])
    suppress_warnings.append("toc.excluded")

html_theme = "furo"
html_context = {"project_license": project_license}
mermaid_output_format = "raw"


nb_execution_mode = "off"
