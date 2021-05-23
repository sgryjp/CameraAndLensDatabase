from __future__ import annotations

import dataclasses
import enum
import logging
import re
from typing import Dict, Iterator, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import bs4
import pydantic

from . import SpecFetcher, config, models, utils
from .exceptions import CameraLensDatabaseException, ParseError

_logger = logging.getLogger(__name__)


@enum.unique
class EquipmentType(int, enum.Enum):
    NEW_CAMERA = enum.auto()
    OLD_CAMERA = enum.auto()


class Mount(str, enum.Enum):
    A = "Sony A"
    E = "Sony E"

    @staticmethod
    def parse(s: str) -> Mount:
        if "Eマウント" in s or "Ｅマウント" in s:
            return Mount.E
        elif "Aマウント" in s or "ソニー製αレンズ" in s:
            return Mount.A
        else:
            msg = f"unrecognizable mount description: {s}"
            raise ParseError(msg)


@dataclasses.dataclass
class SpecParseParams(object):
    subpath: Optional[str]
    table_selector: str
    key_cell_selector: str
    value_cell_selector: str


_models_to_ignore: List[str] = []
_known_lens_specs: Dict[str, Dict[str, Union[float, str]]] = {}
_known_camera_specs: Dict[str, Dict[str, Union[float, str]]] = {
    "DSLR-A900": {models.KEY_CAMERA_MOUNT: Mount.A},
}


def enum_cameras(target: EquipmentType) -> Iterator[Tuple[str, str, SpecFetcher]]:
    card: bs4.ResultSet

    if target == EquipmentType.NEW_CAMERA:
        base_uri = "https://www.sony.jp/ichigan/lineup/"
        item_selector = "div[data-s5lineup-pid]"
        name_selector = ".s5-listItem4__modelName"
        anchor_selector = ".s5-listItem4__mainLink"
    elif target == EquipmentType.OLD_CAMERA:
        # TODO: Generalize the pattern using JSONP with HTML scraping
        import json

        base_uri = "https://www.sony.jp/ichigan/lineup/past.html"
        jsonp_uri = "https://www.sony.jp/webapi/past_product/previous_product.php?callback=PreviousProduct&categoryId=2508,3729,4588&startDate=20010101&flag=3&sort=2"  # noqa: E501
        html_text = utils.fetch(jsonp_uri)
        obj = json.loads(re.findall(r"PreviousProduct\((.*)\)", html_text)[0])
        eval_name = lambda obj: [x["modelName"] for x in obj["product"]]
        eval_href = lambda obj: [x["productLink"] for x in obj["product"]]
        for name, href in zip(eval_name(obj), eval_href(obj)):
            yield name, urljoin(base_uri, href), fetch_camera
        return
    else:
        msg = f"unsupported type to enumerate: {target}"
        raise ValueError(msg)

    html_text = utils.fetch(base_uri)
    soup = bs4.BeautifulSoup(html_text, features=config["bs_features"])
    for card in soup.select(item_selector):
        name = card.select(name_selector)[0].text.strip()
        anchor = card.select(anchor_selector)[0]

        # Get raw value of href attribute
        raw_dest = anchor["href"]
        if raw_dest.startswith("javascript:"):
            continue

        # Check the destination looks fine
        pr = urlparse(raw_dest)
        if pr.hostname and pr.hostname != base_uri:
            msg = "skipped an item because it's not on the same server"
            msg += f": {anchor['href']!r} <> {base_uri!r}"
            _logger.warning(msg)
            continue

        # Construct an absolute URI
        rel_dest = pr.path
        abs_dest = urljoin(base_uri, rel_dest)

        yield name, abs_dest, fetch_camera


def fetch_camera(name: str, uri: str) -> models.Camera:
    parse_params: List[SpecParseParams] = [
        SpecParseParams("spec.html", ".s5-specTable > table", "th", "td"),
        SpecParseParams("spec.html", ".mod-specTable", "table th", "table th ~ td"),
    ]

    errors = []
    for idx, params in enumerate(parse_params):
        try:
            return _fetch_camera(name, uri, params)
        except ParseError as ex:
            errors.append((idx, ex))

    msglines = [f'cannot read spec of "{name}" from "{uri}"']
    for idx, e in errors:
        msglines.append(f"  mode {idx}: {str(e)}")
    raise CameraLensDatabaseException("\n".join(msglines))


def _fetch_camera(name: str, uri: str, pp: SpecParseParams) -> models.Camera:
    if pp.subpath is not None:
        uri = urljoin(uri, pp.subpath)

    html_text = utils.fetch(uri)
    soup = bs4.BeautifulSoup(html_text, config["bs_features"])
    selection = soup.select(pp.table_selector)
    if len(selection) <= 0:
        msg = f"spec table not found: {uri}"
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
        key_cells: bs4.ResultSet = row.select(pp.key_cell_selector)
        value_cells: bs4.ResultSet = row.select(pp.value_cell_selector)
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
    if key in ("レンズマウント", "使用レンズ"):
        mount = Mount.parse(value)
        if mount is not None:
            return {models.KEY_CAMERA_MOUNT: mount}

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
