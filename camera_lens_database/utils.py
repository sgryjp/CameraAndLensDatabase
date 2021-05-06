import re
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Iterator, Tuple

import requests

from . import cache_root

CACHE_TIMEOUT = 8 * 3600


def fetch(uri: str) -> str:
    # Ensure the cache dir exists
    cache_root.mkdir(parents=True, exist_ok=True)

    # Return cached data if its not so old
    uri_bytes = uri.encode("utf-8", errors="replace")
    uri_hash = sha256(uri_bytes)
    cache_file_path = (cache_root / uri_hash.hexdigest()).with_suffix(".html")
    if cache_file_path.is_file():
        cached_time = datetime.utcfromtimestamp(cache_file_path.stat().st_mtime)
        if datetime.utcnow() < cached_time + timedelta(seconds=CACHE_TIMEOUT):
            return cache_file_path.read_text("utf-8", errors="strict")

    # Otherwise, download the resource
    resp = requests.get(uri)
    cache_file_path.write_text(resp.text, encoding="utf-8", errors="replace")
    return resp.text


def enum_millimeter_ranges(s: str) -> Iterator[Tuple[float, float]]:
    pairs = [
        (float(n1), float(n2))
        for n1, n2 in re.findall(r"([\d\.]+)(?:mm)?\s*-\s*([\d\.]+)mm", s)
    ]
    if pairs:
        for n1, n2 in pairs:
            yield n1, n2
        return  # do not try extracting single value if a range found

    singles = [float(n) for n in re.findall(r"([\d\.]+)mm", s)]
    if singles:
        for n in singles:
            yield n, n


def enum_millimeter_values(s: str) -> Iterator[float]:
    for number, unit in re.findall(r"([\d\.]+)\s*(mm?)", s):
        if unit == "mm":
            ratio = 1.0
        elif unit == "m":
            ratio = 1000.0
        else:
            continue

        yield float(number) * ratio


def enum_f_numbers(s: str) -> Iterator[float]:
    f_numbers = re.findall(r"f/([\d\.]+)", s)
    if f_numbers:
        for number in f_numbers:
            yield float(number)

    numbers = re.findall(r"([\d\.]+)", s)
    if numbers:
        for number in numbers:
            yield float(number)
