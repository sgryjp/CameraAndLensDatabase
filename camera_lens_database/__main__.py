import logging
import shutil
from enum import Enum

import pandas as pd
import typer

from . import cache_root, lenses, nikon

_logger = logging.getLogger(__name__)
app = typer.Typer()


class CacheAction(str, Enum):
    info = "info"
    purge = "purge"


@app.command()
def fetch():
    """Fetch the newest equipment data from the Web."""
    STR_COLUMNS = (lenses.KEY_BRAND, lenses.KEY_MOUNT, lenses.KEY_NAME)

    try:
        specs = []

        lens_info = list(nikon.enumerate_lenses(True))
        lens_info += list(nikon.enumerate_lenses(False))
        with typer.progressbar(lens_info, label="Nikon Lens") as pbar:
            for name, uri in pbar:
                spec = nikon.read_lens(name, uri)
                if spec is None:
                    continue
                specs.append(spec.dict())

        df = pd.DataFrame(specs)
        df = df.sort_values(
            by=[
                lenses.KEY_BRAND,
                lenses.KEY_MOUNT,
                lenses.KEY_MIN_FOCAL_LENGTH,
                lenses.KEY_MAX_FOCAL_LENGTH,
                lenses.KEY_NAME,
            ],
            kind="mergesort",
            key=lambda c: c.str.lower() if str(c) in STR_COLUMNS else c,
        )
        print(df.to_csv(index=None, float_format="%g"))
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
