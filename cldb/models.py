from typing import Optional

from pydantic import BaseModel

SIZE_NAME_FX = "FX"
SIZE_NAME_DX = "DX"
SIZE_NAME_35MM = "35mm"
SIZE_NAME_APS_C = "APS-C"


class Lens(BaseModel):
    id: str
    name: str
    brand: str
    mount: str
    min_focal_length: float
    max_focal_length: float
    min_f_value: float
    max_f_value: float
    min_focus_distance: float
    keywords: str


class Camera(BaseModel):
    id: str
    name: str
    brand: str
    mount: str
    media_width: float
    media_height: float
    size_name: str
    name_japan: Optional[str]
    name_us: Optional[str]
    keywords: str


def infer_media_size_name(
    width: float, height: float, *, for_nikon: bool = False
) -> Optional[str]:
    if 35.6 <= width <= 36.0 and 23.8 <= height <= 24.0:
        return SIZE_NAME_FX if for_nikon else SIZE_NAME_35MM
    elif 20.7 <= width <= 23.7 and 13.8 <= height <= 15.8:
        return SIZE_NAME_DX if for_nikon else SIZE_NAME_APS_C
    return None


(
    KEY_LENS_ID,
    KEY_LENS_NAME,
    KEY_LENS_BRAND,
    KEY_LENS_MOUNT,
    KEY_LENS_MIN_FOCAL_LENGTH,
    KEY_LENS_MAX_FOCAL_LENGTH,
    KEY_LENS_MIN_F_VALUE,
    KEY_LENS_MAX_F_VALUE,
    KEY_LENS_MIN_FOCUS_DISTANCE,
    KEY_LENS_KEYWORDS,
) = Lens.__fields__.keys()


(
    KEY_CAMERA_ID,
    KEY_CAMERA_NAME,
    KEY_CAMERA_BRAND,
    KEY_CAMERA_MOUNT,
    KEY_CAMERA_MEDIA_WIDTH,
    KEY_CAMERA_MEDIA_HEIGHT,
    KEY_CAMERA_SIZE_NAME,
    KEY_CAMERA_NAME_JAPAN,
    KEY_CAMERA_NAME_US,
    KEY_CAMERA_KEYWORDS,
) = Camera.__fields__.keys()
