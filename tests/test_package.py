"""Tests verifying that the core ``schafkopfrl`` subpackages can be imported."""

from schafkopfrl import schafkopfengine, schafkopfgym, utils


def test_package_import() -> None:
    """The core subpackages are importable without error."""
    assert schafkopfengine is not None
    assert schafkopfgym is not None
    assert utils is not None
