from dataclasses import dataclass
from uuid import UUID

KEY_ID = "ID"
KEY_NAME = "Name"
KEY_BRAND = "Brand"
KEY_MOUNT = "Mount"
KEY_MIN_FOCAL_LENGTH = "Min. Focal Length"
KEY_MAX_FOCAL_LENGTH = "Max. Focal Length"
KEY_MIN_F_VALUE = "Min. F Value"
KEY_MAX_F_VALUE = "Max. F Value"
KEY_MIN_FOCUS_DISTANCE = "Min. Focus Distance"
KEY_COMMENT = "Comment"
IDX_ID = 0
IDX_NAME = 1
IDX_BRAND = 2
IDX_MOUNT = 3
IDX_MIN_FOCAL_LENGTH = 4
IDX_MAX_FOCAL_LENGTH = 5
IDX_MIN_F_VALUE = 6
IDX_MAX_F_VALUE = 7
IDX_MIN_FOCUS_DISTANCE = 8
IDX_COMMENT = 9


@dataclass(order=True)
class Lens(object):
    id: UUID
    name: str
    brand: str
    mount: str
    min_focal_length: float
    max_focal_length: float
    min_f_value: float
    max_f_value: float
    min_focus_distance: float
