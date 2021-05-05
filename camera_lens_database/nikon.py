import logging
from typing import Dict, Iterator, Optional, Tuple, Union
from urllib.parse import urljoin, urlparse
from uuid import uuid4

from bs4 import BeautifulSoup, Tag
from bs4.element import ResultSet

from . import config, lenses
from .exceptions import CameraLensDatabaseException
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
        abs_dest = urljoin(abs_dest, "spec.html")

        yield name, abs_dest


def read_lens(name: str, uri: str) -> Optional[lenses.Lens]:
    try:
        html_text = fetch(uri)
        soup = BeautifulSoup(html_text, config["bs_features"])
        selection = soup.select("div#spec ~ table")
        if len(selection) <= 0:
            msg = f"spec table not found: {uri}"
            raise CameraLensDatabaseException(msg)

        # Collect and parse interested th-td pairs from the spec table
        spec_table: Tag = selection[0]
        pairs: Dict[str, Union[float, str]] = {
            lenses.KEY_ID: str(uuid4()),
            lenses.KEY_NAME: name,
            lenses.KEY_BRAND: "Nikon",
            lenses.KEY_COMMENT: "",
        }
        for row in spec_table.select("tr"):
            ths: ResultSet = row.select("th")
            tds: ResultSet = row.select("td")
            if len(ths) != 1 or len(tds) != 1:
                msg = f"spec table does not have 1 by 1 th-td pairs: {uri}"
                raise CameraLensDatabaseException(msg)

            for key, value in recognize_lens_term(key=ths[0].text, value=tds[0].text):
                pairs[key] = value
        if len(pairs) != len(lenses.Lens.__fields__):
            return None

        # Compose a spec object from the table content
        return lenses.Lens(**pairs)
    except Exception as ex:
        msg = f"failed to read spec of '{name}' from {uri}: {str(ex)}"
        raise CameraLensDatabaseException(msg)


def recognize_lens_term(key: str, value: str):
    if "主レンズ" in value:
        return  # Tele-converter

    if key == "型式":
        yield lenses.KEY_MOUNT, _parse_mount_name(value)
    elif key == "焦点距離":
        for min_dist, max_dist in enum_millimeter_ranges(value):
            yield lenses.KEY_MIN_FOCAL_LENGTH, float(min_dist)
            yield lenses.KEY_MAX_FOCAL_LENGTH, float(max_dist)
            return

        msg = f"pattern unmatched: {value!r}"
        raise CameraLensDatabaseException(msg)
    elif key == "最短撮影距離":
        distances = list(enum_millimeter_values(value))
        yield lenses.KEY_MIN_FOCUS_DISTANCE, min(distances)
    elif key == "最小絞り":
        f_values = list(enum_f_numbers(value))
        yield lenses.KEY_MAX_F_VALUE, max(f_values)
    elif key == "最大絞り":
        f_values = list(enum_f_numbers(value))
        yield lenses.KEY_MIN_F_VALUE, min(f_values)


def _parse_mount_name(s: str):
    s = s.replace(" ", "")
    if "ニコンZマウント" in s:
        return "Nikon Z"
    elif "ニコンFマウント" in s:
        return "Nikon F"
    else:
        msg = f"unkown mount description: '{s}'"
        raise CameraLensDatabaseException(msg)
