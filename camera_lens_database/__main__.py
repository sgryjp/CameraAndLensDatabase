import logging

import pandas as pd
import typer

from . import nikon_z

_logger = logging.getLogger(__name__)
app = typer.Typer()


@app.command()
def fetch():
    """Fetch the newest equipment data from the Web."""

    try:
        specs = []
        for name, uri in nikon_z.enumerate_lenses():
            spec = nikon_z.read_lens(name, uri)
            if spec is None:
                continue
            specs.append(spec.dict())

        df = pd.DataFrame(specs)
        print(df)
    except Exception:
        _logger.exception("")


if __name__ == "__main__":
    app()
