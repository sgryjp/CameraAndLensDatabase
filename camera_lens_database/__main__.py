import logging

import typer

from .nikon_z import enumerate_nikon_z_lens, read_nikon_z_lens

_logger = logging.getLogger(__name__)
app = typer.Typer()


@app.command()
def fetch():
    """Fetch the newest equipment data from the Web."""

    try:
        for name, uri in enumerate_nikon_z_lens():
            spec = read_nikon_z_lens(name, uri)
            if spec is None:
                continue
            print("#", spec)
    except Exception:
        _logger.exception("")


if __name__ == "__main__":
    app()
