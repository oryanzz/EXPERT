"""Screenshot the real EXPERT window showing the summary of a real session (02:30, East Rocky
Mountain III), with the real history rows and their maps read from the saved shots.

usage: make_app_shot.py [he|en]   (writes app_summary.png / app_summary_en.png)"""
import base64
import ctypes
import ctypes.wintypes as wt
import io
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402
import webview  # noqa: E402
from PIL import Image, ImageGrab  # noqa: E402

from maple_exp.ocr import crop_for_display  # noqa: E402
from maple_exp.tracker import Tracker  # noqa: E402

SHOTS = ROOT / "shots"
LANG = sys.argv[1] if len(sys.argv) > 1 else "he"
OUT = HERE / ("app_summary.png" if LANG == "he" else f"app_summary_{LANG}.png")
reader = app.BarReader()


def snapshot(path):
    img = Image.open(path).convert("RGB")
    res = reader.read(img)
    buf = io.BytesIO()
    crop_for_display(img, res.box).save(buf, "PNG")
    r = res.reading
    return r, {"exp": r.exp, "pct": r.pct, "level": r.level,
               "crop": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}


start_r, start = snapshot(SHOTS / "2026-10-11_02-30-49_start.jpg")
end_r, end = snapshot(SHOTS / "2026-10-11_02-30-49_end.jpg")
tracker = Tracker(0, start_r)
tracker.add(300.4, end_r)
result = app.summary_dict(tracker.summary(300.4))

# real sessions from history.csv, maps read from each session's start shot
HISTORY = [
    {"date": "2026-10-11 02:30", "map": "East Rocky Mountain III", "minutes": "5.0", "exp_per_min": "351", "levels_gained": "0"},
    {"date": "2026-10-11 02:16", "map": "East Rocky Mountain III", "minutes": "5.0", "exp_per_min": "298", "levels_gained": "0"},
    {"date": "2026-10-11 01:50", "map": "Rocky Road II", "minutes": "3.0", "exp_per_min": "376", "levels_gained": "0"},
    {"date": "2026-10-11 01:41", "map": "Rocky Road II", "minutes": "3.0", "exp_per_min": "301", "levels_gained": "0"},
]


class DemoApi(app.Api):
    def get_state(self):
        return {"game": {"found": True, "minimized": False, "size": "1920×1200"}, "phase": "done",
                "map": "East Rocky Mountain III", "result": result, "start": start, "end": end,
                "warning": None, "error": None, "live": None, "countdown": 0, "total": 300,
                "remaining": 0, "failed_reads": 0, "samples": 31}

    def history(self):
        return HISTORY

    def app_info(self):
        return {**super().app_info(), "lang": LANG}  # as if Windows were in that language


def drive(window):
    time.sleep(4.5)
    r = wt.RECT()
    ctypes.windll.user32.GetWindowRect(app.own_window(), ctypes.byref(r))
    ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom), all_screens=True).save(OUT)
    print("saved", OUT, result, flush=True)
    os._exit(0)


storage = ROOT / "dev" / "out" / f".webview-demo-{LANG}"  # fresh per language: no saved choice
app.clear_web_cache(storage)
win = app.create_main_window(DemoApi())
webview.start(drive, win, private_mode=False, storage_path=str(storage))
