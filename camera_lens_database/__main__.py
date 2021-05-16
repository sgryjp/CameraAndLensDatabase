import click

from . import cache, fetch


@click.group()
def app() -> None:
    """Scrape camera and lens data on the web."""
    pass


app.add_command(cache.main, "cache")
app.add_command(fetch.main, "fetch")

if __name__ == "__main__":
    app()
