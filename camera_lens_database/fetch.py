"""Command to fetch internet resources."""
import io
import multiprocessing
import sys
import traceback
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
import typer
from tqdm.contrib.concurrent import process_map
from tqdm.std import tqdm

from . import lenses, nikon

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


def _read_nikon_lens(
    args: Tuple[str, str, Dict[str, str]]
) -> Optional[Dict[str, Union[float, str]]]:
    name, uri, orig_id_map = args

    lens = nikon.read_lens(name, uri)
    if lens is None:
        return  # Converters

    orig_id = orig_id_map.get(lens.name.lower())
    if orig_id is not None:
        lens.id = orig_id
    return lens.dict()


def main(
    target: FetchTarget = typer.Argument(..., help=_help_target),
    lenses_csv: Path = typer.Option(Path("lenses.csv"), help=_help_lenses_csv),
    num_workers: int = typer.Option(
        0, "-j", "--max-workers", help=_help_max_workers, metavar="N"
    ),
    output: Optional[Path] = typer.Option(None, "-o", "--output", help=_help_output),
) -> int:
    """Fetch the newest equipment data from the Web."""
    global _orig_id_map
    STR_COLUMNS = (lenses.KEY_BRAND, lenses.KEY_MOUNT, lenses.KEY_NAME)

    try:
        if target != FetchTarget.LENS:
            raise NotImplementedError()

        # Before fetching newest data, load already assigned equipment IDs
        orig_lens_data = pd.read_csv(lenses_csv)
        df = orig_lens_data.loc[:, ["ID", "Name"]]
        df = df.set_index("Name")["ID"]
        orig_id_map = {k.lower(): v.lower() for k, v in df.to_dict().items()}

        # Gather where to find spec data
        lens_info = list(nikon.enumerate_lenses(nikon.EquipmentType.F_LENS_OLD))
        lens_info += list(nikon.enumerate_lenses(nikon.EquipmentType.F_LENS))
        lens_info += list(nikon.enumerate_lenses(nikon.EquipmentType.Z_LENS))

        # Resolve parallel processing parameters
        common_ppp: Dict[str, Union[int, str]] = {"unit": "models"}
        if num_workers <= 0:
            common_ppp["max_workers"] = multiprocessing.cpu_count()
        elif num_workers != 1:
            common_ppp["max_workers"] = num_workers

        # Add a common parameter to arguments for paralell processing function
        ppargs = [(name, uri, orig_id_map) for name, uri in lens_info]

        # Fetch and analyze equipment specs
        ppp = dict(common_ppp, desc="Nikon Lens")  # see PEP 584
        specs: List[Dict[str, Union[float, str]]]
        if num_workers == 1:
            with tqdm(ppargs, **ppp) as pbar:
                spec_or_nones = [_read_nikon_lens(ppargs) for ppargs in pbar]
        else:
            pbar = process_map(_read_nikon_lens, ppargs, **ppp)
            spec_or_nones = [spec for spec in pbar]
        specs = [spec for spec in spec_or_nones if spec is not None]

        # Sort the result
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

        # Now output it
        write = partial(df.to_csv, index=None, float_format="%g")
        if output is None:
            write(sys.stdout)
        else:
            with open(output, "wb") as f:
                write(f)

        return 0
    except Exception:
        with io.StringIO() as buf:
            traceback.print_exc(file=buf)
            typer.secho(str(buf.getvalue()), fg=typer.colors.RED)
        return 1
