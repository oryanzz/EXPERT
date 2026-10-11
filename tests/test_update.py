from maple_exp.update import is_newer, parse_version, release_info


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
                                 "url": "https://github.com/oryanzz/EXPERT/releases/tag/v1.0.2"}


def test_release_info_ignores_drafts_and_prereleases():
    assert release_info({"tag_name": "v2.0.0", "html_url": "x", "draft": True}) is None
    assert release_info({"tag_name": "v2.0.0", "html_url": "x", "prerelease": True}) is None
    assert release_info({"message": "API rate limit exceeded"}) is None
