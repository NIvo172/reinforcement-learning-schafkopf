"""Safe file appending helpers for the Schafkopf RL project."""

from pathlib import Path


def append_to_log(filename: str, content: str) -> None:
    """Append content to a file, creating parent directories as needed.

    The path is resolved relative to the current working directory, so callers running from the repository root write
    into its reports tree.

    Args:
        filename: Path of the file to append to.
        content: Text to append.
    """
    target_dir = Path.cwd()

    path_parts = filename.split("/")

    for path_part in path_parts[:-1]:
        target_dir /= path_part

    target_dir = target_dir.resolve()

    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = (target_dir / path_parts[-1]).resolve()

    with target_path.open("a", encoding="utf-8") as f:
        f.write(content)
