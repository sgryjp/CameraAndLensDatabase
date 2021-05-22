import pathlib
from typing import Callable, Union

import click

__version__ = "21.5.16"

APP_NAME = "cldb"

app_dir = pathlib.Path(click.get_app_dir(APP_NAME, roaming=False, force_posix=True))
cache_root = app_dir / "cache"

config = {
    "bs_features": "lxml",
}

from . import models  # noqa: E402

SpecFetcher = Callable[[str, str], Union[models.Lens, models.Camera]]
