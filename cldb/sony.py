from __future__ import annotations

import enum
from typing import Dict, Iterator, Tuple, Union
from urllib.parse import urljoin
from uuid import uuid4

import bs4
import pydantic

from . import SpecFetcher, config, models, utils
from .exceptions import CameraLensDatabaseException, ParseError


class Mount(str, enum.Enum):
    A = "Sony A"
    E = "Sony E"

    @staticmethod
    def parse(s: str) -> Mount:
        if "Eマウント" in s:
            return Mount.E
        else:
            msg = f"unrecognizable mount description: {s}"
            raise ParseError(msg)


_known_camera_specs: Dict[str, Dict[str, Union[float, str]]] = {}


def enum_cameras() -> Iterator[Tuple[str, str, SpecFetcher]]:
    card: bs4.ResultSet

    base_uri = "https://www.sony.jp/ichigan/lineup/"
    html_text = utils.fetch(base_uri)
    soup = bs4.BeautifulSoup(html_text, features=config["bs_features"])
    for card in soup.select("div[data-s5lineup-pid]"):
        name = card.select(".s5-listItem4__modelName")[0].text.strip()
        anchor = card.select(".s5-listItem4__mainLink")[0]
        yield name, urljoin(base_uri, anchor["href"]), fetch_camera


def fetch_camera(name: str, uri: str) -> models.Camera:
    uri = urljoin(uri, "spec.html")

    html_text = utils.fetch(uri)
    soup = bs4.BeautifulSoup(html_text, config["bs_features"])
    selection = soup.select(".s5-specTable > table")
    if len(selection) <= 0:
        msg = "spec table not found"
        raise ParseError(msg)

    # Set initial values
    pairs: Dict[str, Union[float, str]] = {
        models.KEY_CAMERA_ID: str(uuid4()),
        models.KEY_CAMERA_NAME: name,
        models.KEY_CAMERA_BRAND: "Sony",
        models.KEY_CAMERA_KEYWORDS: "",
    }

    # Collect and parse interested th-td pairs from the spec table
    spec_table: bs4.Tag = selection[0]
    for row in spec_table.select("tr"):
        key_cells: bs4.ResultSet = row.select("th")
        value_cells: bs4.ResultSet = row.select("td")
        if len(key_cells) != 1 or len(value_cells) != 1:
            continue

        key_cell_text = key_cells[0].text.strip()
        value_cell_text = value_cells[0].text.strip()
        for k, v in _recognize_camera_property(key_cell_text, value_cell_text).items():
            pairs[k] = v

    # Force using some spec data which is not available or hard to recognize
    for k, v in _known_camera_specs.get(name, {}).items():
        pairs[k] = v

    # Infer media size name if not set
    if models.KEY_CAMERA_SIZE_NAME not in pairs:
        w = pairs.get(models.KEY_CAMERA_MEDIA_WIDTH)
        h = pairs.get(models.KEY_CAMERA_MEDIA_HEIGHT)
        if w and h:
            assert isinstance(w, float) and isinstance(h, float)
            size_name = models.infer_media_size_name(w, h, for_nikon=False)
            if size_name:
                pairs[models.KEY_CAMERA_SIZE_NAME] = size_name

    # Compose a spec object from the table content
    try:
        return models.Camera(**pairs)
    except pydantic.ValidationError as ex:
        msg = f"unexpected spec: {pairs}, {uri}"
        raise CameraLensDatabaseException(msg) from ex


def _recognize_camera_property(key: str, value: str) -> Dict[str, Union[float, str]]:
    # TODO: This can be merged with nikon._recognize_camera_prop... as a static dict?
    if key == "レンズマウント":
        mount = Mount.parse(value)
        if mount is not None:
            return {models.KEY_CAMERA_MOUNT: mount}

    elif key == "使用レンズ":
        if "ソニーEマウント" in value:
            return {models.KEY_CAMERA_MOUNT: Mount.E}
        elif "ソニーAマウント" in value:
            return {models.KEY_CAMERA_MOUNT: Mount.A}

    elif key == "撮像素子":
        props: Dict[str, Union[float, str]] = {}

        areas = list(utils.enum_square_millimeters(value))
        if len(areas) == 1:
            w, h = areas[0]
            props[models.KEY_CAMERA_MEDIA_WIDTH] = w
            props[models.KEY_CAMERA_MEDIA_HEIGHT] = h

        if props:
            return props

    return {}
