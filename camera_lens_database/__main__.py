import typer

from . import cache, fetch

app = typer.Typer()
app.command("fetch")(fetch.main)
app.command("cache")(cache.main)


if __name__ == "__main__":
    app()
