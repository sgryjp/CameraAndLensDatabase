import logging
from typing import Dict, Iterator, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import pydantic
from bs4 import BeautifulSoup, Tag
from bs4.element import ResultSet

from . import config, lenses
from .exceptions import CameraLensDatabaseException, ParseError
from .utils import enum_f_numbers, enum_millimeter_ranges, enum_millimeter_values, fetch

MOUNT_F = "Nikon F"
MOUNT_Z = "Nikon Z"

_logger = logging.getLogger(__name__)
_lenses_to_ignore = [
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
]
_known_lens_specs: Dict[str, Dict[str, Union[float, str]]] = {
    "AI AF Zoom-Nikkor 18-35mm f/3.5-4.5D IF-ED": {
        lenses.KEY_MIN_F_VALUE: 3.5,
    },
    "AI AF Zoom Nikkor 24～50mm F3.3～4.5D": {
        lenses.KEY_MIN_FOCUS_DISTANCE: 600,
    },
}


def enumerate_lenses(typ: int = 0) -> Iterator[Tuple[str, str]]:
    if typ == 0:
        base_uri = "https://www.nikon-image.com/products/nikkor/discontinue_fmount/"
    elif typ == 1:
        base_uri = "https://www.nikon-image.com/products/nikkor/fmount/index.html"
    else:
        base_uri = "https://www.nikon-image.com/products/nikkor/zmount/index.html"
    html_text = fetch(base_uri)
    soup = BeautifulSoup(html_text, features=config["bs_features"])
    for anchor in soup.select(".mod-goodsList-ul > li > a"):
        # Get the equipment name
        name: str = anchor.select(".mod-goodsList-title")[0].text
        name = name.rstrip(" 旧製品")
        if name in _lenses_to_ignore:
            continue

        # Get raw value of href attribute
        raw_dest = anchor["href"]
        if raw_dest.startswith("javascript:"):
            continue

        # Check the destination looks fine
        pr = urlparse(raw_dest)
        if pr.hostname and pr.hostname != base_uri:
            _logger.warning(
                "skipped an item because it's not on the same server: %r",
                anchor["href"],
                base_uri,
            )
            continue

        # Construct an absolute URI
        rel_dest = pr.path
        abs_dest = urljoin(base_uri, rel_dest)

        yield name, abs_dest


def read_lens(name: str, uri: str) -> lenses.Lens:
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

    msg = f'cannot read spec of "{name}" from "{uri}"'
    _logger.error(msg)
    for mode, e in errors:
        _logger.error("  mode %d: %s", mode, str(e))
    raise CameraLensDatabaseException(msg)


def _read_lens(
    name: str,
    uri: str,
    params: Tuple[str, str, str, Optional[str]],
) -> lenses.Lens:
    table_selector, key_cell_selector, value_cell_selector, subpath = params

    if subpath is not None:
        uri = urljoin(uri, subpath)

    html_text = fetch(uri)
    soup = BeautifulSoup(html_text, config["bs_features"])
    selection = soup.select(table_selector)
    if len(selection) <= 0:
        msg = "spec table not found"
        raise ParseError(msg)

    # Set initial values
    pairs: Dict[str, Union[float, str]] = {
        lenses.KEY_ID: str(uuid4()),
        lenses.KEY_NAME: name,
        lenses.KEY_BRAND: "Nikon",
        lenses.KEY_COMMENT: "",
    }
    if "fmount/" in uri:
        pairs[lenses.KEY_MOUNT] = MOUNT_F

    # Collect and parse interested th-td pairs from the spec table
    spec_table: Tag = selection[0]
    for row in spec_table.select("tr"):
        key_cells: ResultSet = row.select(key_cell_selector)
        value_cells: ResultSet = row.select(value_cell_selector)
        if len(key_cells) != 1 or len(value_cells) != 1:
            msg = "spec table does not have 1 by 1 cell pairs"
            raise ParseError(msg)

        key_cell_text = key_cells[0].text.strip()
        value_cell_text = value_cells[0].text.strip()
        for k, v in recognize_lens_term(key_cell_text, value_cell_text).items():
            pairs[k] = v

    # Try extracting some specs from the model name
    if (
        lenses.KEY_MIN_FOCAL_LENGTH not in pairs
        or lenses.KEY_MAX_FOCAL_LENGTH not in pairs
    ):
        for k, v in recognize_lens_term("焦点距離", name).items():
            pairs[k] = v
    if lenses.KEY_MIN_F_VALUE not in pairs:
        for k, v in recognize_lens_term("最大絞り", name).items():
            pairs[k] = v

    # Force using some spec data which is not available or hard to recognize
    for k, v in _known_lens_specs.get(name, {}).items():
        pairs[k] = v

    # Skip if we couldn't get sufficient data
    lacked_keys = set(lenses.Lens.__fields__.keys()).difference(pairs.keys())
    if lacked_keys:
        msg = f"cannot find {', '.join(lacked_keys)}"
        raise ParseError(msg)

    # Compose a spec object from the table content
    try:
        return lenses.Lens(**pairs)
    except pydantic.ValidationError as ex:
        raise CameraLensDatabaseException(f"unexpected spec: {pairs}") from ex


def recognize_lens_term(key: str, value: str) -> Dict[str, Union[float, str]]:
    if key == "型式":
        mount = _parse_mount_name(value)
        if mount is not None:
            return {lenses.KEY_MOUNT: mount}
    elif key == "焦点距離":
        ranges = list(enum_millimeter_ranges(value))
        if ranges:
            return {
                lenses.KEY_MIN_FOCAL_LENGTH: min(n for n, _ in ranges),
                lenses.KEY_MAX_FOCAL_LENGTH: max(n for _, n in ranges),
            }
    elif key == "最短撮影距離":
        values = list(enum_millimeter_values(value))
        if values:
            return {lenses.KEY_MIN_FOCUS_DISTANCE: min(values)}
    elif key == "最小絞り":
        values = list(enum_f_numbers(value))
        if values:
            return {lenses.KEY_MAX_F_VALUE: max(values)}
    elif key == "最大絞り":
        values = list(enum_f_numbers(value))
        if values:
            return {lenses.KEY_MIN_F_VALUE: min(values)}

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
