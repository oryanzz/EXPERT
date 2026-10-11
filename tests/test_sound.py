from maple_exp.sound import pick_sound


def test_custom_sound_wins(tmp_path):
    (tmp_path / "default.wav").write_bytes(b"x")
    (tmp_path / "done.wav").write_bytes(b"x")
    assert pick_sound(tmp_path) == tmp_path / "done.wav"


def test_falls_back_to_default(tmp_path):
    (tmp_path / "default.wav").write_bytes(b"x")
    assert pick_sound(tmp_path) == tmp_path / "default.wav"


def test_no_sound_files(tmp_path):
    assert pick_sound(tmp_path) is None


def test_missing_folder(tmp_path):
    assert pick_sound(tmp_path / "nope") is None


def test_custom_sound_in_data_dir_default_in_bundle(tmp_path):
    data, bundle = tmp_path / "data", tmp_path / "bundle"
    data.mkdir(); bundle.mkdir()
    (bundle / "default.wav").write_bytes(b"x")
    assert pick_sound(data, bundle) == bundle / "default.wav"
    (data / "done.wav").write_bytes(b"x")
    assert pick_sound(data, bundle) == data / "done.wav"
