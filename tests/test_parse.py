from maple_exp.parse import Reading, parse_status

# OCR boxes from a real 1920x1200 MapleStory screenshot, ordered left to right.
REAL_BAR = ["LV.", "22", "Archer", "Player1", "HP[256/708]", "MP[42/567]",
            "EXP28.524[98.43%]", "CASH SHOP", "MENU", "SHORT-CUT"]


def test_reads_exp_percent_and_level_from_real_bar():
    assert parse_status(REAL_BAR) == Reading(exp=28524, pct=98.43, level=22)


def test_reads_exp_split_across_boxes():
    r = parse_status(["EXP.", "1,234,567", "[", "12.5%]"])
    assert (r.exp, r.pct) == (1234567, 12.5)


def test_dots_are_thousand_separators_in_exp():
    r = parse_status(["EXP. 1.234.567 [0.05%]"])
    assert (r.exp, r.pct) == (1234567, 0.05)


def test_comma_decimal_percent():
    assert parse_status(["EXP 28,524 [98,43%]"]).pct == 98.43


def test_zero_exp_is_valid():
    r = parse_status(["EXP.0[0.00%]"])
    assert (r.exp, r.pct) == (0, 0.0)


def test_level_merged_with_label():
    assert parse_status(["LV.22", "EXP28.524[98.43%]"]).level == 22


def test_level_missing_gives_none():
    assert parse_status(["EXP28.524[98.43%]"]).level is None


def test_no_exp_text_returns_none():
    assert parse_status(["HP[256/708]", "MP[42/567]"]) is None


def test_percent_over_100_is_rejected():
    assert parse_status(["EXP28.524[984.3%]"]) is None


def test_empty_input_returns_none():
    assert parse_status([]) is None


def test_exp_label_misread_as_exr():
    # live 2026-10-11: OCR read the label "EXP" as "EXR"; the strict match fell back to a slow, worse pass
    bar = ["LV.", "23", "Player1", "Archer", "HP[326/730]", "MP[229/584]", "EXR17.420[50.76%]", "CASH SHOP"]
    assert parse_status(bar) == Reading(exp=17420, pct=50.76, level=23)
