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
    comment: str


(
    KEY_ID,
    KEY_NAME,
    KEY_BRAND,
    KEY_MOUNT,
    KEY_MIN_FOCAL_LENGTH,
    KEY_MAX_FOCAL_LENGTH,
    KEY_MIN_F_VALUE,
    KEY_MAX_F_VALUE,
    KEY_MIN_FOCUS_DISTANCE,
    KEY_COMMENT,
) = Lens.__fields__.keys()
