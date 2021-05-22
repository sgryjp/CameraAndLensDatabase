import enum
import re
from typing import Dict, Iterator, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import bs4
import click
import pydantic

from . import SpecFetcher, config, models
from .exceptions import CameraLensDatabaseException, ParseError
from .utils import (
    enum_f_numbers,
    enum_millimeter_ranges,
    enum_millimeter_values,
    enum_square_millimeters,
    fetch,
)


@enum.unique
class EquipmentType(int, enum.Enum):
    F_LENS_OLD = enum.auto()
    F_LENS = enum.auto()
    Z_LENS = enum.auto()
    SLR = enum.auto()
    SLR_OLD = enum.auto()


MOUNT_F = "Nikon F"
MOUNT_Z = "Nikon Z"

_models_to_ignore = [
    # Lenses
    "AF-S TELECONVERTER TC-14E III",
    "AF-S TELECONVERTER TC-20E III",
    "AI AF-I Teleconverter TC-14E",
    "AI AF-I Teleconverter TC-20E",
    "AI AF-S TELECONVERTER TC-14E II",
    "AI AF-S TELECONVERTER TC-17E II",
    "AI AF-S TELECONVERTER TC-20E II",
    "AI TC-14AS",
    "AI TC-14BS",
    "AI TC-201S",
    "AI TC-301S",
    "Z TELECONVERTER TC-1.4x",
    "Z TELECONVERTER TC-2.0x",
    # Cameras
    "E3/E3S",
    "F100",
    "F5",
    "F6",
    "F80D/F80S",
    "FM10",
    "FM3A",
    "Lite Touch Zoom 100W QD",
    "Lite Touch Zoom 120ED QD",
    "Lite Touch Zoom 130ED QD",
    "Lite Touch Zoom 140ED QD",
    "Lite Touch Zoom 150ED QD",
    "Lite Touch Zoom 70Ws QD",
    "NIKONOS-V",
    "Nuvis S",
    "Nuvis S2000",
    "PRONEA S",
    "S3 (限定復刻版)",
    "U",
    "U2",
    "US",
]
_known_lens_specs: Dict[str, Dict[str, Union[float, str]]] = {
    "AI AF Zoom-Nikkor 18-35mm f/3.5-4.5D IF-ED": {
        models.KEY_LENS_MIN_F_VALUE: 3.5,
    },
    "AI AF Zoom Nikkor 24～50mm F3.3～4.5D": {
        models.KEY_LENS_MIN_FOCUS_DISTANCE: 600,
    },
    "AI Micro-Nikkor 55mm f/2.8S": {
        models.KEY_LENS_MIN_FOCUS_DISTANCE: 250,
    },
    "AI Micro-Nikkor 105mm f/2.8S": {
        models.KEY_LENS_MIN_FOCAL_LENGTH: 105,
        models.KEY_LENS_MIN_FOCUS_DISTANCE: 410,
    },
}
_known_camera_specs: Dict[str, Dict[str, Union[float, str]]] = {
    "D1": {
        models.KEY_CAMERA_MOUNT: "Nikon F",
    },
}


def enum_equipments(target: EquipmentType) -> Iterator[Tuple[str, str, SpecFetcher]]:
    fetcher: SpecFetcher
    if target == EquipmentType.F_LENS_OLD:
        base_uri = "https://www.nikon-image.com/products/nikkor/discontinue_fmount/"
        fetcher = read_lens
    elif target == EquipmentType.F_LENS:
        base_uri = "https://www.nikon-image.com/products/nikkor/fmount/index.html"
        fetcher = read_lens
    elif target == EquipmentType.Z_LENS:
        base_uri = "https://www.nikon-image.com/products/nikkor/zmount/index.html"
        fetcher = read_lens
    elif target == EquipmentType.SLR:
        base_uri = "https://www.nikon-image.com/products/slr/"
        fetcher = read_camera
    elif target == EquipmentType.SLR_OLD:
        base_uri = "https://www.nikon-image.com/products/slr/discontinue_lineup/"
        fetcher = read_camera
    else:
        msg = f"unsupported type to enumerate: {target}"
        raise ValueError(msg)

    html_text = fetch(base_uri)
    soup = bs4.BeautifulSoup(html_text, features=config["bs_features"])
    for anchor in soup.select(".mod-goodsList-ul > li > a"):
        # Get the equipment name
        name: str = anchor.select(".mod-goodsList-title")[0].text
        name = _normalize_name(name)
        if name in _models_to_ignore:
            continue

        # Get raw value of href attribute
        raw_dest = anchor["href"]
        if raw_dest.startswith("javascript:"):
            continue

        # Check the destination looks fine
        pr = urlparse(raw_dest)
        if pr.hostname and pr.hostname != base_uri:
            msg = "skipped an item because it's not on the same server"
            msg += f": {anchor['href']!r} <> {base_uri!r}"
            click.secho(msg, fg="yellow")
            continue

        # Construct an absolute URI
        rel_dest = pr.path
        abs_dest = urljoin(base_uri, rel_dest)

        yield name, abs_dest, fetcher


def read_lens(name: str, uri: str) -> models.Lens:
    mode_values: List[Tuple[str, str, str, Optional[str]]] = [  # TODO: Improve name
        ("table.table-A01-group", "th", "td", None),
        ("a#spec ~ table", "td:first-child", "td:last-child", None),
        ("div#spec ~ table", "th", "td", "spec.html"),
    ]

    errors = []
    for mode, params in enumerate(mode_values):
        try:
            return _read_lens(name, uri, params)
        except ParseError as ex:
            errors.append((mode, ex))

    msglines = [f'cannot read spec of "{name}" from "{uri}"']
    for mode, e in errors:
        msglines.append(f"  mode {mode}: {str(e)}")
    raise CameraLensDatabaseException("\n".join(msglines))


def _read_lens(
    name: str,
    uri: str,
    params: Tuple[str, str, str, Optional[str]],
) -> models.Lens:
    table_selector, key_cell_selector, value_cell_selector, subpath = params

    if subpath is not None:
        uri = urljoin(uri, subpath)

    html_text = fetch(uri)
    soup = bs4.BeautifulSoup(html_text, config["bs_features"])
    selection = soup.select(table_selector)
    if len(selection) <= 0:
        msg = "spec table not found"
        raise ParseError(msg)

    # Set initial values
    pairs: Dict[str, Union[float, str]] = {
        models.KEY_LENS_ID: str(uuid4()),
        models.KEY_LENS_NAME: name,
        models.KEY_LENS_BRAND: "Nikon",
        models.KEY_LENS_KEYWORDS: "",
    }
    if "fmount/" in uri:
        pairs[models.KEY_LENS_MOUNT] = MOUNT_F

    # Collect and parse interested th-td pairs from the spec table
    spec_table: bs4.Tag = selection[0]
    for row in spec_table.select("tr"):
        key_cells: bs4.ResultSet = row.select(key_cell_selector)
        value_cells: bs4.ResultSet = row.select(value_cell_selector)
        if len(key_cells) != 1 or len(value_cells) != 1:
            msg = "spec table does not have 1 by 1 cell pairs"
            raise ParseError(msg)

        key_cell_text = key_cells[0].text.strip()
        value_cell_text = value_cells[0].text.strip()
        for k, v in _recognize_lens_property(key_cell_text, value_cell_text).items():
            pairs[k] = v

    # Try extracting some specs from the model name
    if (
        models.KEY_LENS_MIN_FOCAL_LENGTH not in pairs
        or models.KEY_LENS_MAX_FOCAL_LENGTH not in pairs
    ):
        for k, v in _recognize_lens_property("焦点距離", name).items():
            pairs[k] = v
    if models.KEY_LENS_MIN_F_VALUE not in pairs:
        for k, v in _recognize_lens_property("最大絞り", name).items():
            pairs[k] = v

    # Force using some spec data which is not available or hard to recognize
    for k, v in _known_lens_specs.get(name, {}).items():
        pairs[k] = v

    # Skip if we couldn't get sufficient data
    lacked_keys = set(models.Lens.__fields__.keys()).difference(pairs.keys())
    if lacked_keys:
        msg = f"cannot find {', '.join(lacked_keys)}"
        raise ParseError(msg)

    # Compose a spec object from the table content
    try:
        return models.Lens(**pairs)
    except pydantic.ValidationError as ex:
        raise CameraLensDatabaseException(f"unexpected spec: {pairs}") from ex


def _recognize_lens_property(key: str, value: str) -> Dict[str, Union[float, str]]:
    if key == "型式":
        mount = _parse_mount_name(value)
        if mount is not None:
            return {models.KEY_LENS_MOUNT: mount}
    elif key == "焦点距離":
        value = _remove_parens(value)
        ranges = list(enum_millimeter_ranges(value))
        if ranges:
            return {
                models.KEY_LENS_MIN_FOCAL_LENGTH: min(n for n, _ in ranges),
                models.KEY_LENS_MAX_FOCAL_LENGTH: max(n for _, n in ranges),
            }
    elif key == "最短撮影距離":
        value = _remove_parens(value)
        values = list(enum_millimeter_values(value))
        if values:
            return {models.KEY_LENS_MIN_FOCUS_DISTANCE: min(values)}
    elif key == "最小絞り":
        values = list(enum_f_numbers(value))
        if values:
            return {models.KEY_LENS_MAX_F_VALUE: max(values)}
    elif key == "最大絞り":
        values = list(enum_f_numbers(value))
        if values:
            return {models.KEY_LENS_MIN_F_VALUE: min(values)}

    return {}


def _parse_mount_name(s: str) -> str:
    s = s.replace(" ", "")
    if "ニコンZマウント" in s:
        return MOUNT_Z
    elif "ニコンFマウント" in s:
        return MOUNT_F
    else:
        msg = f"unrecognizable mount description: {s}"
        raise ParseError(msg)


def _to_half_width(s: str) -> str:
    s = re.sub(r"（([^）]+)）", r"(\g<1>)", s)
    s = re.sub(r"(?<=\d)～(?=[\dF])", "-", s)
    return s


def _remove_parens(s: str) -> str:
    s = _to_half_width(s)
    s = re.sub(r"（[^）]+）", "", s)
    s = re.sub(r"\([^\)]+\)", "", s)
    s = re.sub(
        r"\[([\d\.m]+)\s*[：:]\s*[^\]]+\]", r" \g<1>", s
    )  # [0.21m：85mmマクロ時] --> 0.21m
    return s


def _normalize_name(name: str) -> str:
    name = _to_half_width(name)
    name = re.sub(r"\s*(旧製品|＜NEW＞)$", "", name)
    name = re.sub(r"NIKKOR", "Nikkor", name, re.IGNORECASE)
    name = re.sub(r"(?<=[^\s])\(", " (", name)  # Insert space before an opening paren
    return name


def read_camera(name: str, uri: str) -> models.Camera:
    mode_values: List[Tuple[str, str, str, Optional[str]]] = [  # TODO: Improve name
        ("div#spec ~ table", "th", "td", "spec.html"),
        ("table.table-A01-group", "th", "td", "spec.html"),
        ("table", "td:first-child", "td:last-child", "spec.html"),
    ]

    errors = []
    for mode, params in enumerate(mode_values):
        try:
            return _read_camera(name, uri, params)
        except ParseError as ex:
            errors.append((mode, ex))

    msglines = [f'cannot read spec of "{name}" from "{uri}"']
    for mode, e in errors:
        msglines.append(f"  mode {mode}: {str(e)}")
    raise CameraLensDatabaseException("\n".join(msglines))


def _read_camera(
    name: str, uri: str, params: Tuple[str, str, str, Optional[str]]
) -> models.Camera:
    table_selector, key_cell_selector, value_cell_selector, subpath = params

    if subpath is not None:
        uri = urljoin(uri, subpath)

    html_text = fetch(uri)
    soup = bs4.BeautifulSoup(html_text, config["bs_features"])
    selection = soup.select(table_selector)
    if len(selection) <= 0:
        msg = "spec table not found"
        raise ParseError(msg)

    # Set initial values
    pairs: Dict[str, Union[float, str]] = {
        models.KEY_CAMERA_ID: str(uuid4()),
        models.KEY_CAMERA_NAME: name,
        models.KEY_CAMERA_BRAND: "Nikon",
        models.KEY_CAMERA_KEYWORDS: "",
    }

    # Collect and parse interested th-td pairs from the spec table
    spec_table: bs4.Tag = selection[0]
    for row in spec_table.select("tr"):
        key_cells: bs4.ResultSet = row.select(key_cell_selector)
        value_cells: bs4.ResultSet = row.select(value_cell_selector)
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
            size_name = models.infer_media_size_name(w, h, for_nikon=True)
            if size_name:
                pairs[models.KEY_CAMERA_SIZE_NAME] = size_name

    # Compose a spec object from the table content
    try:
        return models.Camera(**pairs)
    except pydantic.ValidationError as ex:
        msg = f"unexpected spec: {pairs}, {uri}"
        raise CameraLensDatabaseException(msg) from ex


def _recognize_camera_property(key: str, value: str) -> Dict[str, Union[float, str]]:
    if key == "レンズマウント":
        mount = _parse_mount_name(value)
        if mount is not None:
            return {models.KEY_CAMERA_MOUNT: mount}

    elif key in ("撮像素子", "撮像素子方式", "方式"):
        props: Dict[str, Union[float, str]] = {}

        areas = list(enum_square_millimeters(value))
        if len(areas) == 1:
            w, h = areas[0]
            props[models.KEY_CAMERA_MEDIA_WIDTH] = w
            props[models.KEY_CAMERA_MEDIA_HEIGHT] = h

        if props:
            return props

    return {}
