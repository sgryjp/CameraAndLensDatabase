from typing import Optional

from pydantic import BaseModel


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
