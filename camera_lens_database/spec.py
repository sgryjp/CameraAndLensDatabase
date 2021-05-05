from dataclasses import dataclass


@dataclass
class LensSpec(object):
    name: str
    brand: str
    mount: str
    min_focal_length: float
    max_focal_length: float
    min_f_value: float
    max_f_value: float
    min_focus_distance: float
