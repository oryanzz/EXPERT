"""Real OCR on a real screenshot - slower (~2s) but catches model/crop regressions."""
from pathlib import Path

import pytest
from PIL import Image

from maple_exp.minimap import canonical_name
from maple_exp.ocr import BarReader
from maple_exp.parse import Reading

SAMPLE = Path(__file__).parent / "fixtures" / "sample_game.png"


@pytest.fixture(scope="module")
def reader():
    return BarReader()


def test_reads_exp_from_real_screenshot(reader):
    res = reader.read(Image.open(SAMPLE))
    assert res.reading == Reading(exp=28524, pct=98.43, level=22)
    x0, y0, x1, y1 = res.box
    assert 1000 < x0 < x1 < 1220 and 1140 < y0 < y1 < 1185  # the EXP text in the bottom bar


def test_reads_map_from_real_screenshot(reader):
    street, name = reader.read_map(Image.open(SAMPLE))
    assert street == "Victoria Road"
    # the crisp pixel font read "Dumgeon" until the slight blur before OCR
    assert name == "Tree Dungeon, Forest Up North IV"
    assert canonical_name(name, ["Tree Dungeon, Forest Up North IV", "Ant Tunnel I"]) == name
