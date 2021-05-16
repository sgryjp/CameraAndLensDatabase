from math import isclose

import pytest

import cldb.utils


@pytest.mark.parametrize(
    "s, want",
    [
        ("35.9×23.9mm", (35.9, 23.9)),
        ("23.3 × 15.5mm", (23.3, 15.5)),
        ("23.7x15.7mm", (23.7, 15.7)),
        ("23.7(H)×15.6(V)mm", (23.7, 15.6)),
    ],
)
def test_enum_square_millimeters(s, want):
    got = list(cldb.utils.enum_square_millimeters(s))
    assert len(got) == 1
    area = got[0]
    assert isclose(area[0], want[0])
    assert isclose(area[1], want[1])
