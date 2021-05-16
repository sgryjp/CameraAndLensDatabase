from math import isclose

import pytest

import cldb.utils


@pytest.mark.parametrize(
    "s, want",
    [
        ("35.9×23.9mm", (35.9, 23.9)),
    ],
)
def test_enum_square_millimeters(s, want):
    got = list(cldb.utils.enum_square_millimeters(s))
    assert len(got) == 1
    area = got[0]
    assert isclose(area[0], want[0])
    assert isclose(area[1], want[1])
