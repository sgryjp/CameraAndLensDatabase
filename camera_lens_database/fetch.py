"""Command to fetch internet resources."""
import io
import itertools
import multiprocessing
import sys
import traceback
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import pandas as pd
import typer

from . import lenses, nikon, utils

_help_target = "Type of the equipment to scarpe"
_help_max_workers = (
    "Number of worker processes to launch."
    " Specifying 0 launches as many processes as CPU cores."
)
_help_lenses_csv = "The lens database file to read for already known equipments' IDs."
_help_output = "The file to store scraped spec data."


class FetchTarget(str, Enum):
    LENS: str = "lens"
    CAMERA: str = "camera"


def init() -> None:
    multiprocessing.freeze_support()


def _read_nikon_lens(args: Tuple[str, str]) -> Optional[Dict[str, Union[float, str]]]:
    name, uri = args

    lens = nikon.read_lens(name, uri)
    if lens is None:
        return  # Converters

    return lens.dict()


def main(
    target: FetchTarget = typer.Argument(..., help=_help_target),
    lenses_csv: Path = typer.Option(Path("lenses.csv"), help=_help_lenses_csv),
    num_workers: int = typer.Option(
        0, "-j", "--max-workers", help=_help_max_workers, metavar="N"
    ),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help=_help_output),
):
    """Fetch the newest equipment data from the Web."""
    STR_COLUMNS = (lenses.KEY_BRAND, lenses.KEY_MOUNT, lenses.KEY_NAME)

    try:
        if target != FetchTarget.LENS:
            raise NotImplementedError()
        else:
            orig_data_path = lenses_csv
            name_uri_pairs = itertools.chain(
                nikon.enumerate_lenses(nikon.EquipmentType.F_LENS_OLD),
                nikon.enumerate_lenses(nikon.EquipmentType.F_LENS),
                nikon.enumerate_lenses(nikon.EquipmentType.Z_LENS),
            )
            sort_keys = [
                lenses.KEY_BRAND,
                lenses.KEY_MOUNT,
                lenses.KEY_MIN_FOCAL_LENGTH,
                lenses.KEY_MAX_FOCAL_LENGTH,
                lenses.KEY_NAME,
            ]
            detail_fetcher = _read_nikon_lens

        # Before fetching the newest data, load already assigned equipment IDs
        orig_data = pd.read_csv(orig_data_path).set_index("Name")["ID"]
        orig_id_map = {k.lower(): v.lower() for k, v in orig_data.to_dict().items()}

        # Query equipments with location of thier spec data.
        ppargs = list(name_uri_pairs)

        # Fetch and analyze equipment specs
        spec_or_nones = utils.parallel_apply(
            ppargs, detail_fetcher, num_workers=num_workers
        )
        specs = [spec for spec in spec_or_nones if spec is not None]

        # Reuse already assigned IDs
        for spec in specs:
            name = spec["name"]
            assert isinstance(name, str)
            already_assigned_id = orig_id_map.get(name.lower())
            if already_assigned_id is not None:
                spec["id"] = already_assigned_id

        # Sort the result
        df = pd.DataFrame(specs).sort_values(
            by=sort_keys,
            kind="mergesort",
            key=lambda c: c.str.lower() if str(c) in STR_COLUMNS else c,
        )

        # Now output it
        write = partial(df.to_csv, index=None, float_format="%g")
        if output is None:
            write(sys.stdout)
        else:
            with open(output, "wb") as f:
                write(f)

    except Exception:
        with io.StringIO() as buf:
            traceback.print_exc(file=buf)
            typer.secho(str(buf.getvalue()), fg=typer.colors.RED)
        raise typer.Exit(1)
