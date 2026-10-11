from maple_exp.update import is_newer, parse_version, release_info, update_available


def test_parse_version_accepts_tags_with_v():
    assert parse_version("v1.0.2") == (1, 0, 2)
    assert parse_version("1.0.2") == (1, 0, 2)


def test_parse_version_rejects_garbage():
    assert parse_version("latest") is None
    assert parse_version("") is None


def test_newer_compares_numbers_not_text():
    assert is_newer("v1.0.10", "1.0.9")
    assert is_newer("v2.0.0", "1.9.9")
    assert not is_newer("v1.0.1", "1.0.1")
    assert not is_newer("v1.0.0", "1.0.1")


def test_unparseable_latest_is_never_newer():
    assert not is_newer("nightly", "1.0.1")


def test_release_info_from_github_api():
    api = {"tag_name": "v1.0.2", "html_url": "https://github.com/oryanzz/EXPERT/releases/tag/v1.0.2",
           "draft": False, "prerelease": False}
    assert release_info(api) == {"version": "1.0.2", "tag": "v1.0.2",
                                 "url": "https://github.com/oryanzz/EXPERT/releases/tag/v1.0.2",
                                 "exe_url": None}


def test_release_info_ignores_drafts_and_prereleases():
    assert release_info({"tag_name": "v2.0.0", "html_url": "x", "draft": True}) is None
    assert release_info({"tag_name": "v2.0.0", "html_url": "x", "prerelease": True}) is None
    assert release_info({"message": "API rate limit exceeded"}) is None


EXE = "https://github.com/oryanzz/EXPERT/releases/download/v1.1.0/EXPERT.exe"


def test_release_info_finds_the_exe_asset():
    api = {"tag_name": "v1.1.0", "html_url": "u", "assets": [
        {"name": "notes.txt", "browser_download_url": "x"},
        {"name": "EXPERT.exe", "browser_download_url": EXE}]}
    assert release_info(api)["exe_url"] == EXE


def test_update_available_for_source_installs_needs_no_exe():
    info = {"version": "1.1.0", "tag": "v1.1.0", "url": "u", "exe_url": None}
    assert update_available(info, current="1.0.3", need_exe=False) == info


def test_exe_installs_wait_until_the_exe_is_attached():
    info = {"version": "1.1.0", "tag": "v1.1.0", "url": "u", "exe_url": None}
    assert update_available(info, current="1.0.3", need_exe=True) is None
    info["exe_url"] = EXE
    assert update_available(info, current="1.0.3", need_exe=True) == info


def test_no_update_when_current_or_unknown():
    info = {"version": "1.1.0", "tag": "v1.1.0", "url": "u", "exe_url": EXE}
    assert update_available(info, current="1.1.0", need_exe=True) is None
    assert update_available(None, current="1.0.0", need_exe=False) is None
