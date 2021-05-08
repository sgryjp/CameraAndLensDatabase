"""Command to fetch internet resources."""
import io
import traceback
from pathlib import Path

import pandas as pd
import typer
from tqdm import tqdm

from . import lenses, nikon


def main(
    lenses_csv: Path = typer.Option(Path("lenses.csv")),
    overwrite: bool = typer.Option(False, "--overwrite", "-o"),
) -> int:
    """Fetch the newest equipment data from the Web."""
    STR_COLUMNS = (lenses.KEY_BRAND, lenses.KEY_MOUNT, lenses.KEY_NAME)

    try:
        specs = []

        orig_lens_data = pd.read_csv(lenses_csv)
        df = orig_lens_data.loc[:, ["ID", "Name"]]
        df = df.set_index("Name")["ID"]
        orig_id_map = {k.lower(): v.lower() for k, v in df.to_dict().items()}

        lens_info = list(nikon.enumerate_lenses(nikon.EquipmentType.F_LENS_OLD))
        lens_info += list(nikon.enumerate_lenses(nikon.EquipmentType.F_LENS))
        lens_info += list(nikon.enumerate_lenses(nikon.EquipmentType.Z_LENS))
        with tqdm(lens_info, desc="Nikon Lens", unit="models") as pbar:
            for name, uri in pbar:
                spec = nikon.read_lens(name, uri)
                if spec is None:
                    continue  # Converters
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

        return 0
    except Exception:
        with io.StringIO() as buf:
            traceback.print_exc(file=buf)
            typer.secho(str(buf.getvalue()), fg=typer.colors.RED)
        return 1