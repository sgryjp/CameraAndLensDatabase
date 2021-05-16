"""Command to control download cache."""
import shutil

import click

from .. import cache_root
from . import main


@main.group()
def cache() -> None:
    """Do cache related operation."""
    pass


@cache.command()
def info() -> None:
    """Show information about the cache."""
    click.echo(cache_root.absolute())


@cache.command()
def purge() -> None:
    """Remove cache data."""

    def print_error(func, path, exc_info):  # type: ignore[no-untyped-def]
        _, ex, _ = exc_info
        msg = f"cannot remove '{path}': {str(ex)}"
        click.secho(msg, fg="yellow")

    if cache_root.exists():
        shutil.rmtree(cache_root, onerror=print_error)
