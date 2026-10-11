"""Session log as a CSV that opens cleanly in Excel (UTF-8 with BOM for Hebrew)."""
import csv
from pathlib import Path

FIELDS = ["date", "map", "minutes", "exp_gained", "exp_per_min", "exp_per_hour",
          "pct_gained", "levels_gained", "start_level", "end_level", "start_shot", "end_shot"]


def append_session(path: Path, record: dict) -> None:
    path = Path(path)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8-sig" if new else "utf-8") as f:
        w = csv.DictWriter(f, FIELDS, restval="", extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(record)


def replace_last(path: Path, record: dict) -> None:
    """Overwrite the newest row (after the user corrects a reading)."""
    path = Path(path)
    if not path.exists():
        return append_session(path, record)
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    rows[-1:] = [record]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, FIELDS, restval="", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def known_maps(path: Path) -> list[str]:
    """Distinct map names from past sessions, newest first - what OCR reads get snapped to."""
    return list(dict.fromkeys(r["map"] for r in load_recent(path, limit=10_000) if r.get("map")))


def load_recent(path: Path, limit: int = 20) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return rows[::-1][:limit]
