import logging
import shutil
from enum import Enum
from pathlib import Path

import pandas as pd
import typer

from . import cache_root, lenses, nikon

_logger = logging.getLogger(__name__)
app = typer.Typer()


class CacheAction(str, Enum):
    info = "info"
    purge = "purge"


@app.command()
def fetch(
    lenses_csv: Path = typer.Option(Path("lenses.csv")),
    overwrite: bool = typer.Option(False, "--overwrite", "-o"),
):
    """Fetch the newest equipment data from the Web."""
    STR_COLUMNS = (lenses.KEY_BRAND, lenses.KEY_MOUNT, lenses.KEY_NAME)

    try:
        specs = []

        orig_lens_data = pd.read_csv(lenses_csv)
        df = orig_lens_data.loc[:, ["ID", "Name"]]
        df = df.set_index("Name")["ID"]
        orig_id_map = {k.lower(): v.lower() for k, v in df.to_dict().items()}

        lens_info = list(nikon.enumerate_lenses(True))
        lens_info += list(nikon.enumerate_lenses(False))
        with typer.progressbar(lens_info, label="Nikon Lens") as pbar:
            for name, uri in pbar:
                spec = nikon.read_lens(name, uri)
                if spec is None:
                    continue
                orig_id = orig_id_map.get(spec.name.lower())
                if orig_id is not None:
                    attrs = {k: v for k, v in spec.dict().items()}
                    attrs[lenses.KEY_ID] = orig_id
                    spec = lenses.Lens(**attrs)
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
        if overwrite:
            df.to_csv(lenses_csv, index=None, float_format="%g")
        else:
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
