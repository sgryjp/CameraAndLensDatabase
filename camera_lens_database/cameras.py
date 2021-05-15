from typing import Optional

from pydantic import BaseModel


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
    KEY_ID,
    KEY_NAME,
    KEY_BRAND,
    KEY_MOUNT,
    KEY_MEDIA_WIDTH,
    KEY_MEDIA_HEIGHT,
    KEY_SIZE_NAME,
    KEY_NAME_JAPAN,
    KEY_NAME_US,
    KEY_KEYWORDS,
) = Camera.__fields__.keys()
