from pathlib import Path

from maple_exp.selftest import run_selftest

SAMPLE = Path(__file__).parent / "fixtures" / "sample_game.png"


def test_selftest_reads_the_sample_screenshot():
    result = run_selftest(SAMPLE)
    assert result["ok"] is True
    assert (result["exp"], result["pct"], result["level"]) == (28524, 98.43, 22)
    assert result["map"] == "Tree Dungeon, Forest Up North IV"


def test_selftest_reports_failure_for_an_image_without_a_bar(tmp_path):
    from PIL import Image
    blank = tmp_path / "blank.png"
    Image.new("RGB", (800, 600), "white").save(blank)
    result = run_selftest(blank)
    assert result["ok"] is False
