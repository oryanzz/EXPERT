"""Repro for the freeze: toggle 'always on top' while the UI polls get_state.

Exits 0 if the window stays responsive, 1 if it hangs.
"""
import ctypes
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402
import webview  # noqa: E402

OUT = ROOT / "dev" / "out"
OUT.mkdir(parents=True, exist_ok=True)
app.HISTORY = OUT / "history.csv"
user32 = ctypes.windll.user32


def watchdog():
    time.sleep(25)
    print("RESULT: HUNG (watchdog fired)", flush=True)
    os._exit(1)


def drive(window):
    threading.Thread(target=watchdog, daemon=True).start()
    time.sleep(4)
    hwnd = app.own_window()
    window.evaluate_js("document.getElementById('pinBtn').addEventListener('click', () => { window.__pinClicks = (window.__pinClicks || 0) + 1 }); 1")
    # click the pin repeatedly (fire-and-forget) while the 400ms poll keeps running
    for _ in range(11):  # odd number of toggles: starts on top, should end NOT on top
        window.evaluate_js("setTimeout(() => document.getElementById('pinBtn').click(), 0); 1")
        time.sleep(0.35)
    time.sleep(3)
    hung = bool(user32.IsHungAppWindow(hwnd))
    topmost = bool(user32.GetWindowLongW(hwnd, -20) & 0x8)  # GWL_EXSTYLE & WS_EX_TOPMOST
    button_on = window.evaluate_js("document.getElementById('pinBtn').classList.contains('active')")
    clicks = window.evaluate_js("window.__pinClicks || 0")
    print("RESULT:", "HUNG" if hung else "OK (responsive)",
          f"| window topmost={topmost} button on={button_on} clicks handled={clicks}", flush=True)
    os._exit(1 if hung or topmost != button_on else 0)


win = app.create_main_window(app.Api())
webview.start(drive, win, private_mode=False, storage_path=str(OUT / ".webview"))
