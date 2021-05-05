import logging
import shutil
from enum import Enum

import pandas as pd
import typer

from . import cache_root, nikon_z

_logger = logging.getLogger(__name__)
app = typer.Typer()


class CacheAction(str, Enum):
    info = "info"
    purge = "purge"


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


@app.command()
def cache(action: CacheAction = typer.Argument(CacheAction.info)):
    """Do cache related operation."""

    def print_error(func, path, exc_info):
        _, ex, _ = exc_info
        msg = f"cannot remove '{path}': {str(ex)}"
        _logger.warning(msg)

    if action == CacheAction.info:
        print(cache_root.absolute())
    elif action == CacheAction.purge:
        if cache_root.exists():
            shutil.rmtree(cache_root, onerror=print_error)


if __name__ == "__main__":
    app()
