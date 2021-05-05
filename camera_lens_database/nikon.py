import logging
from typing import Dict, Iterator, Tuple, Union
from urllib.parse import urljoin, urlparse
from uuid import uuid4

from bs4 import BeautifulSoup, Tag
from bs4.element import ResultSet

from . import config, lenses
from .exceptions import CameraLensDatabaseException, ParseError
from .utils import enum_f_numbers, enum_millimeter_ranges, enum_millimeter_values, fetch

_logger = logging.getLogger(__name__)


def enumerate_lenses(zmount: bool = True) -> Iterator[Tuple[str, str]]:
    if zmount:
        base_uri = "https://www.nikon-image.com/products/nikkor/zmount/index.html"
    else:
        base_uri = "https://www.nikon-image.com/products/nikkor/fmount/index.html"
    html_text = fetch(base_uri)
    soup = BeautifulSoup(html_text, features=config["bs_features"])
    for anchor in soup.select(".mod-goodsList-ul > li > a"):
        # Get the equipment name
        name: str = anchor.select(".mod-goodsList-title")[0].text
        name = name.rstrip(" 旧製品")

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
    mode_values = [  # TODO: Improve name
        ("table.table-A01-group", "th", "td", None),
        ("a#spec ~ table", "td:first-child", "td:last-child", None),
        ("div#spec ~ table", "th", "td", "spec.html"),
    ]

    errors = []
    for mode, selectors in enumerate(mode_values):
        try:
            return _read_lens(name, uri, selectors)
        except ParseError as ex:
            errors.append((mode, ex))

    msg = f'cannot read spec of "{name}" from "{uri}"'
    _logger.error(msg)
    for mode, e in errors:
        _logger.error("  mode %d: %s", mode, str(e))
    raise CameraLensDatabaseException(msg)


def _read_lens(name: str, uri: str, selectors) -> lenses.Lens:
    table_selector, key_cell_selector, value_cell_selector, subpath = selectors

    if subpath is not None:
        uri = urljoin(uri, subpath)

    html_text = fetch(uri)
    soup = BeautifulSoup(html_text, config["bs_features"])
    selection = soup.select(table_selector)
    if len(selection) <= 0:
        msg = "spec table not found"
        raise ParseError(msg)

    # Collect and parse interested th-td pairs from the spec table
    spec_table: Tag = selection[0]
    pairs: Dict[str, Union[float, str]] = {
        lenses.KEY_ID: str(uuid4()),
        lenses.KEY_NAME: name,
        lenses.KEY_BRAND: "Nikon",
        lenses.KEY_COMMENT: "",
    }
    for row in spec_table.select("tr"):
        key_cells: ResultSet = row.select(key_cell_selector)
        value_cells: ResultSet = row.select(value_cell_selector)
        if len(key_cells) != 1 or len(value_cells) != 1:
            msg = "spec table does not have 1 by 1 cell pairs"
            raise ParseError(msg)

        for key, value in recognize_lens_term(key_cells[0].text, value_cells[0].text):
            pairs[key] = value

    # Try extracting some specs from the model name
    if lenses.KEY_MIN_FOCAL_LENGTH not in pairs:
        distances = list(recognize_lens_term("焦点距離", name))
        if len(distances) == 2:
            pairs[lenses.KEY_MIN_FOCAL_LENGTH] = distances[0]
    if lenses.KEY_MAX_FOCAL_LENGTH not in pairs:
        distances = list(recognize_lens_term("焦点距離", name))
        if len(distances) == 2:
            pairs[lenses.KEY_MAX_FOCAL_LENGTH] = distances[1]
    if lenses.KEY_MIN_F_VALUE not in pairs:
        distances = list(recognize_lens_term("最大絞り", name))
        if len(distances) == 2:
            pairs[lenses.KEY_MAX_FOCAL_LENGTH] = distances[1]

    # Skip if we couldn't get sufficient data
    lacked_keys = set(lenses.Lens.__fields__.keys()).difference(pairs.keys())
    if lacked_keys:
        msg = f"cannot find {', '.join(lacked_keys)}"
        raise ParseError(msg)

    # Compose a spec object from the table content
    return lenses.Lens(**pairs)


def recognize_lens_term(key: str, value: str):
    if "主レンズ" in value:
        return  # Tele-converter

    if key == "型式":
        mount = _parse_mount_name(value)
        if mount is not None:
            yield lenses.KEY_MOUNT, mount
    elif key == "焦点距離":
        for min_dist, max_dist in enum_millimeter_ranges(value):
            yield lenses.KEY_MIN_FOCAL_LENGTH, float(min_dist)
            yield lenses.KEY_MAX_FOCAL_LENGTH, float(max_dist)
    elif key == "最短撮影距離":
        distances = list(enum_millimeter_values(value))
        if 0 < len(distances):
            yield lenses.KEY_MIN_FOCUS_DISTANCE, min(distances)
    elif key == "最小絞り":
        f_values = list(enum_f_numbers(value))
        if 0 < len(f_values):
            yield lenses.KEY_MAX_F_VALUE, max(f_values)
    elif key == "最大絞り":
        f_values = list(enum_f_numbers(value))
        if 0 < len(f_values):
            yield lenses.KEY_MIN_F_VALUE, min(f_values)


def _parse_mount_name(s: str) -> str:
    s = s.replace(" ", "")
    if "ニコンZマウント" in s:
        return "Nikon Z"
    elif "ニコンFマウント" in s:
        return "Nikon F"
    else:
        msg = f"unrecognizable mount description: {s}"
        raise ParseError(msg)
