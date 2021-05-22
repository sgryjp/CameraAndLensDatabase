"""Command to fetch internet resources."""
import io
import itertools
import multiprocessing
import sys
import traceback
from enum import Enum
from functools import partial
from typing import Optional

import click
import pandas as pd
from joblib.parallel import delayed

from .. import models, nikon, sony, utils
from . import main

_help_num_workers = (
    "Number of worker processes to launch."
    " Specifying 0 launches as many processes as CPU cores."
)
_help_lenses_csv = "The lens database file (source of already known equipment IDs)."
_help_cameras_csv = "The camera database file (source of already known equipment IDs)."
_help_output = "The file to store scraped spec data."


class FetchTarget(str, Enum):
    LENS: str = "lens"
    CAMERA: str = "camera"


@main.command()
@click.argument("target", type=FetchTarget)
@click.option(
    "--lenses-csv",
    type=click.Path(exists=True),
    default="lenses.csv",
    help=_help_lenses_csv,
)
@click.option(
    "--cameras-csv",
    type=click.Path(exists=True),
    default="cameras.csv",
    help=_help_cameras_csv,
)
@click.option(
    "-j", "--num-workers", type=int, default=0, metavar="N", help=_help_num_workers
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help=_help_output,
)
@click.pass_context
def fetch(
    ctx: click.Context,
    target: FetchTarget,
    lenses_csv: str,
    cameras_csv: str,
    num_workers: int,
    output: Optional[str],
) -> None:
    """Fetch the newest equipment data from the Web.

    TARGET must be either 'camera' or 'lens'.
    """
    STR_COLUMNS = (models.KEY_LENS_BRAND, models.KEY_LENS_MOUNT, models.KEY_LENS_NAME)
    multiprocessing.freeze_support()

    try:
        if target == FetchTarget.CAMERA:
            orig_data_path = cameras_csv
            spec_source = itertools.chain(
                sony.enum_cameras(),
                nikon.enum_equipments(nikon.EquipmentType.SLR),
                nikon.enum_equipments(nikon.EquipmentType.SLR_OLD),
            )
            sort_keys = [
                models.KEY_CAMERA_BRAND,
                models.KEY_CAMERA_MOUNT,
                models.KEY_CAMERA_NAME,
            ]
        elif target == FetchTarget.LENS:
            orig_data_path = lenses_csv
            spec_source = itertools.chain(
                nikon.enum_equipments(nikon.EquipmentType.F_LENS_OLD),
                nikon.enum_equipments(nikon.EquipmentType.F_LENS),
                nikon.enum_equipments(nikon.EquipmentType.Z_LENS),
            )
            sort_keys = [
                models.KEY_LENS_BRAND,
                models.KEY_LENS_MOUNT,
                models.KEY_LENS_MIN_FOCAL_LENGTH,
                models.KEY_LENS_MAX_FOCAL_LENGTH,
                models.KEY_LENS_NAME,
            ]
        else:
            msg = f"unexpected fetch target: {target}"
            raise ValueError(msg)

        # Before fetching the newest data, load already assigned equipment IDs
        orig_data = pd.read_csv(orig_data_path).set_index("Name")["ID"]
        orig_id_map = {k.lower(): v.lower() for k, v in orig_data.to_dict().items()}

        # Collect where and how to fetch spec data for each equipment
        name_uri_and_fetchers = list(spec_source)

        # Fetch and analyze equipment specs
        n_jobs = num_workers if 0 < num_workers else multiprocessing.cpu_count()
        total = len(name_uri_and_fetchers)
        with utils.ProgressParallel(total=total, n_jobs=n_jobs) as parallel:
            specs = parallel(
                delayed(f)(name, uri) for name, uri, f in name_uri_and_fetchers
            )

        # Reuse already assigned IDs
        for spec in specs:
            already_assigned_id = orig_id_map.get(spec.name.lower())
            if already_assigned_id is not None:
                spec.id = already_assigned_id

        # Sort the result
        df = pd.DataFrame([s.dict() for s in specs]).sort_values(
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
            click.secho(str(buf.getvalue()), fg="red")
        ctx.exit(1)
