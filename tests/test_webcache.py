from maple_exp.webcache import clear_web_cache


def make(path, text="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_clears_http_and_code_cache_but_keeps_local_storage(tmp_path):
    profile = tmp_path / "EBWebView" / "Default"
    make(profile / "Cache" / "Cache_Data" / "f_000003")
    make(profile / "Code Cache" / "js" / "abc")
    make(profile / "Local Storage" / "leveldb" / "000003.log", "minutes=10")
    clear_web_cache(tmp_path)
    assert not (profile / "Cache").exists()
    assert not (profile / "Code Cache").exists()
    assert (profile / "Local Storage" / "leveldb" / "000003.log").read_text() == "minutes=10"


def test_missing_storage_folder_is_fine(tmp_path):
    clear_web_cache(tmp_path / "nope")
