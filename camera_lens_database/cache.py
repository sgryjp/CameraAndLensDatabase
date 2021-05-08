"""Command to control download cache."""
import logging
import shutil
from enum import Enum

import typer

from . import cache_root

_logger = logging.getLogger(__name__)


class CacheAction(str, Enum):
    info = "info"
    purge = "purge"


def main(action: CacheAction = typer.Argument(CacheAction.info)) -> None:
    """Do cache related operation."""

    def print_error(func, path, exc_info):  # type: ignore[no-untyped-def]
        _, ex, _ = exc_info
        msg = f"cannot remove '{path}': {str(ex)}"
        _logger.warning(msg)

    if action == CacheAction.info:
        print(cache_root.absolute())
    elif action == CacheAction.purge:
        if cache_root.exists():
            shutil.rmtree(cache_root, onerror=print_error)
