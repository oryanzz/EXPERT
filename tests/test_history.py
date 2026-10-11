from maple_exp.history import append_session, known_maps, load_recent, replace_last


def test_missing_file_has_no_history(tmp_path):
    assert load_recent(tmp_path / "h.csv") == []


def test_sessions_come_back_newest_first(tmp_path):
    path = tmp_path / "h.csv"
    append_session(path, {"map": "Ant Tunnel", "exp_gained": 1000})
    append_session(path, {"map": "עץ הנשמות", "exp_gained": 2000})
    rows = load_recent(path)
    assert [r["map"] for r in rows] == ["עץ הנשמות", "Ant Tunnel"]
    assert rows[0]["exp_gained"] == "2000"


def test_limit(tmp_path):
    path = tmp_path / "h.csv"
    for i in range(5):
        append_session(path, {"exp_gained": i})
    assert [r["exp_gained"] for r in load_recent(path, limit=2)] == ["4", "3"]


def test_replace_last_rewrites_only_the_newest_row(tmp_path):
    path = tmp_path / "h.csv"
    append_session(path, {"map": "A", "exp_gained": 1})
    append_session(path, {"map": "B", "exp_gained": 2})
    replace_last(path, {"map": "B", "exp_gained": 99})
    rows = load_recent(path)
    assert [(r["map"], r["exp_gained"]) for r in rows] == [("B", "99"), ("A", "1")]


def test_replace_last_on_missing_file_appends(tmp_path):
    path = tmp_path / "h.csv"
    replace_last(path, {"exp_gained": 5})
    assert load_recent(path)[0]["exp_gained"] == "5"


def test_known_maps_newest_first_without_blanks_or_repeats(tmp_path):
    path = tmp_path / "h.csv"
    for m in ["Ant Tunnel I", "", "Rocky Road II", "Ant Tunnel I"]:
        append_session(path, {"map": m})
    assert known_maps(path) == ["Ant Tunnel I", "Rocky Road II"]


def test_known_maps_missing_file(tmp_path):
    assert known_maps(tmp_path / "h.csv") == []
