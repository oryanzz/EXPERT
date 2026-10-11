"""Is there a newer EXPERT release on GitHub? (Installing it: scripts/update.ps1 for a source
install, scripts/update_exe.ps1 for the .exe.)"""
import json
import re
import urllib.request

from . import __version__

REPO = "oryanzz/EXPERT"
LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"
EXE_ASSET = "EXPERT.exe"


def parse_version(text: str) -> tuple[int, ...] | None:
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", (text or "").strip())
    return tuple(int(g) for g in m.groups()) if m else None


def is_newer(latest: str, current: str) -> bool:
    a, b = parse_version(latest), parse_version(current)
    return bool(a and b and a > b)


def release_info(api: dict) -> dict | None:
    """The fields the app needs from GitHub's 'latest release' response, or None if unusable."""
    tag = api.get("tag_name")
    if not tag or api.get("draft") or api.get("prerelease") or not parse_version(tag):
        return None
    exe = next((a.get("browser_download_url") for a in api.get("assets") or [] if a.get("name") == EXE_ASSET), None)
    return {"version": tag.lstrip("v"), "tag": tag, "url": api.get("html_url", ""), "exe_url": exe}


def update_available(info: dict | None, current: str, need_exe: bool) -> dict | None:
    """`info` if it is newer than `current`. The .exe build only offers releases whose EXPERT.exe
    is attached already (CI builds it a few minutes after a release is published)."""
    if not info or not is_newer(info["tag"], current) or (need_exe and not info["exe_url"]):
        return None
    return info


def check_for_update(need_exe: bool = False, timeout: float = 5.0) -> dict | None:
    """The latest release if this copy should offer it; None if up to date, offline, or rate-limited."""
    req = urllib.request.Request(LATEST_API, headers={"User-Agent": f"EXPERT/{__version__}",
                                                      "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            info = release_info(json.load(resp))
    except (OSError, ValueError):  # offline, timeout, HTTP error, bad JSON
        return None
    return update_available(info, __version__, need_exe)
