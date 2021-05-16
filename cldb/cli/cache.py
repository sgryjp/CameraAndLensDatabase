"""Command to control download cache."""
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
@click.option("-v", "--verbose", type=int, count=True)
def purge(verbose: bool) -> None:
    """Remove cache data."""

    if cache_root.exists():
        for path in cache_root.glob("**/*"):
            try:
                if verbose:
                    click.secho(str(path.absolute()), dim=True)
                path.unlink()
            except OSError as ex:
                msg = f"cannot remove '{path}': {str(ex)}"
                click.secho(msg, fg="yellow")
