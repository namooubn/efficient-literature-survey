"""Logging configuration helpers."""

import logging


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure root logger level and format."""
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )
