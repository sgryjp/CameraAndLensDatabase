import typer

from . import cache, fetch

app = typer.Typer(help="Web scraper for camera and lens data")
app.callback()(fetch.init)
app.command("fetch")(fetch.main)
app.command("cache")(cache.main)


if __name__ == "__main__":
    app()
