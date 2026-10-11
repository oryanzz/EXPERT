"""Is there a newer EXPERT release on GitHub? (The download itself is scripts/update.ps1.)"""
import json
import re
import urllib.request

from . import __version__

REPO = "oryanzz/EXPERT"
LATEST_API = f"https://api.github.com/repos/{REPO}/releases/latest"


def parse_version(text: str) -> tuple[int, ...] | None:
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", (text or "").strip())
    return tuple(int(g) for g in m.groups()) if m else None


def is_newer(latest: str, current: str) -> bool:
    a, b = parse_version(latest), parse_version(current)
    return bool(a and b and a > b)


def release_info(api: dict) -> dict | None:
    """The fields the UI needs from GitHub's 'latest release' response, or None if unusable."""
    tag = api.get("tag_name")
    if not tag or api.get("draft") or api.get("prerelease") or not parse_version(tag):
        return None
    return {"version": tag.lstrip("v"), "tag": tag, "url": api.get("html_url", "")}


def check_for_update(timeout: float = 5.0) -> dict | None:
    """The latest release if it is newer than this copy; None if up to date, offline, or rate-limited."""
    req = urllib.request.Request(LATEST_API, headers={"User-Agent": f"EXPERT/{__version__}",
                                                      "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            info = release_info(json.load(resp))
    except (OSError, ValueError):  # offline, timeout, HTTP error, bad JSON
        return None
    return info if info and is_newer(info["tag"], __version__) else None
