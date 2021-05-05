import pathlib

import typer

__version__ = "21.5.4"

APP_NAME = "Camera Lens Database"
# KEY_NAME = "Name"
# KEY_BRAND = "Brand"
# KEY_MOUNT = "Mount"
# KEY_MIN_FOCAL_LENGTH = "Min. Focal Length"
# KEY_MAX_FOCAL_LENGTH = "Max. Focal Length"
# KEY_MIN_F_VALUE = "Min. F Value"
# KEY_MAX_F_VALUE = "Max. F Value"
# KEY_MIN_FOCUS_DISTANCE = "Min. Focus Distance"
IDX_NAME = 0
IDX_BRAND = 1
IDX_MOUNT = 2
IDX_MIN_FOCAL_LENGTH = 3
IDX_MAX_FOCAL_LENGTH = 4
IDX_MIN_F_VALUE = 5
IDX_MAX_F_VALUE = 6
IDX_MIN_FOCUS_DISTANCE = 7

app_dir = pathlib.Path(typer.get_app_dir(APP_NAME, roaming=False, force_posix=True))
cache_root = app_dir / "cache"

config = {
    "bs_features": "lxml",
}
