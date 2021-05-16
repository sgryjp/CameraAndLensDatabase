"""Command to control download cache."""
import shutil

import click

from . import cache_root


@click.group()
def main() -> None:
    """Do cache related operation."""
    pass


@main.command()
def info() -> None:
    click.echo(cache_root.absolute())


@main.command()
def purge() -> None:
    def print_error(func, path, exc_info):  # type: ignore[no-untyped-def]
        _, ex, _ = exc_info
        msg = f"cannot remove '{path}': {str(ex)}"
        click.secho(msg, fg="yellow")

    if cache_root.exists():
        shutil.rmtree(cache_root, onerror=print_error)
