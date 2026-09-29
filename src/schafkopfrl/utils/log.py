"""Logging setup for the Schafkopf RL project."""

import logging
from pathlib import Path


def get_logger(name: str = "SchafkopfEnv") -> logging.Logger:
    """Return a configured logger for the given channel name.

    Args:
        name: Name of the logger to create and configure.
    """
    logger = logging.getLogger(name)

    logger.setLevel(logging.WARNING)
    # Create logs/ directory if it doesn't exist
    log_dir = Path("reports/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(fmt="%(asctime)s [%(levelname)s] %(name)s\n%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    # File handler
    file_handler = logging.FileHandler(log_dir / "schafkopf.log")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
