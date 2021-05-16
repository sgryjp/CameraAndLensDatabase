import pathlib

import click

__version__ = "21.5.5"

APP_NAME = "Camera Lens Database"

app_dir = pathlib.Path(click.get_app_dir(APP_NAME, roaming=False, force_posix=True))
cache_root = app_dir / "cache"

config = {
    "bs_features": "lxml",
}
