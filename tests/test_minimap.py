from maple_exp.minimap import MapVotes, canonical_name, clean_name, parse_minimap


def box(x0, y0, x1, y1, text):
    return [[[x0, y0], [x1, y0], [x1, y1], [x0, y1]], text, 0.9]


# OCR boxes from real screenshots' top-left corner (minimap header)
TREE_DUNGEON = [box(12, 14, 75, 25, "mInImAF"), box(324, 13, 373, 25, "WORLD"),
                box(82, 46, 202, 63, "VictoriaRoad"), box(79, 67, 378, 88, "TreeDungeon,ForestUpNorthIV")]
ROCKY_ROAD = [box(12, 14, 75, 25, "mInImAF"), box(161, 13, 210, 25, "WORLD"),
              box(81, 46, 203, 63, "VictoriaRoad"), box(79, 67, 202, 87, "RockyRoadll"),
              box(5, 270, 150, 285, "Quest Helper (1/5)")]


def test_reads_street_and_map_under_the_header():
    assert parse_minimap(TREE_DUNGEON) == ("Victoria Road", "Tree Dungeon, Forest Up North IV")


def test_glued_roman_numeral_is_split():
    assert parse_minimap(ROCKY_ROAD) == ("Victoria Road", "Rocky Road II")


def test_no_minimap_header_means_no_map():
    assert parse_minimap([box(10, 50, 200, 70, "Some chat text")]) is None


def test_header_without_name_lines():
    assert parse_minimap([box(324, 13, 373, 25, "WORLD")]) is None


def test_clean_name_spacing_and_commas():
    assert clean_name("TreeDungeon,Forest UpNorthIV") == "Tree Dungeon, Forest Up North IV"


def test_clean_name_separate_numeral_token():
    assert clean_name("Ant Tunnel ll") == "Ant Tunnel II"


def test_clean_name_keeps_words_that_really_end_in_l():
    assert clean_name("Ant Tunnel") == "Ant Tunnel"
    assert clean_name("Mushroom Hill") == "Mushroom Hill"


def test_canonical_snaps_ocr_variants_to_a_known_name():
    known = ["Tree Dungeon, Forest Up North IV", "Ant Tunnel I"]
    assert canonical_name("Tree Dumgeon, Forest Up North IV", known) == "Tree Dungeon, Forest Up North IV"
    assert canonical_name("Ant Tunnel l", known) == "Ant Tunnel I"


def test_canonical_keeps_new_names():
    assert canonical_name("Rocky Road II", ["Ant Tunnel I"]) == "Rocky Road II"


def test_canonical_does_not_merge_different_numbers():
    # "Ant Tunnel I" vs "Ant Tunnel II" are different maps
    assert canonical_name("Ant Tunnel II", ["Ant Tunnel I"]) == "Ant Tunnel II"


def test_clean_name_period_misread_for_comma():
    assert clean_name("Tree Dungeon.Forest Up North IV") == "Tree Dungeon, Forest Up North IV"


def test_map_votes_majority_wins():
    v = MapVotes()
    for name in ["East Rocky Mountainl", "East Rocky Mountain III", "East Rocky Mountain III"]:
        v.add(name)
    assert v.best == "East Rocky Mountain III"


def test_map_votes_ignore_empty_reads_and_tie_goes_to_first():
    v = MapVotes()
    assert v.best == ""
    v.add("")
    v.add("Rocky Road II")
    v.add("Rocky Road I")
    assert (v.best, v.count) == ("Rocky Road II", 2)
