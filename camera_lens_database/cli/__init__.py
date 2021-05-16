import click


@click.group()
def main() -> None:
    """Scrape camera and lens data on the web."""
    pass


# Import subcommand modules after defining main so that they can refer it
from . import cache  # noqa: E402, F401
from . import fetch  # noqa: E402, F401
