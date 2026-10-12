"""End-to-end check: drive the real app window against the live game and screenshot each phase.

Also exercises the frameless shell: title-bar drag, minimize and close buttons.
Writes history/screenshots into dev/out instead of the real folders.
"""
import ctypes
import ctypes.wintypes as wt
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app  # noqa: E402  (sets DPI awareness)
import webview  # noqa: E402
from PIL import ImageGrab  # noqa: E402

OUT = ROOT / "dev" / "out"
OUT.mkdir(parents=True, exist_ok=True)
app.SHOTS = OUT / "shots"
app.HISTORY = OUT / "history.csv"
MINUTES = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
user32 = ctypes.windll.user32


def rect():
    r = wt.RECT()
    user32.GetWindowRect(app.own_window(), ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def shot(name):
    ImageGrab.grab(bbox=rect(), all_screens=True).save(OUT / f"{name}.png")
    print("shot", name, rect(), flush=True)


def js(window, code):
    return window.evaluate_js(code)


def drag_titlebar(window, dx, dy):
    """Synthetic mousedown on the title bar + mousemove, the events pywebview's drag handler listens to."""
    js(window, f"""
        const bar = document.querySelector('.titlebar');
        bar.dispatchEvent(new MouseEvent('mousedown', {{bubbles: true, clientX: 60, clientY: 20}}));
        const x = window.screenX + 60 + {dx}, y = window.screenY + 20 + {dy};
        window.dispatchEvent(new MouseEvent('mousemove', {{screenX: x, screenY: y}}));
        window.dispatchEvent(new MouseEvent('mouseup', {{}}));
        1""")


def drive(window):
    time.sleep(4)  # page + fonts + first poll
    shot("1_idle")

    before = rect()
    drag_titlebar(window, -60, 40)
    time.sleep(0.6)
    after = rect()
    print("drag moved window by", (after[0] - before[0], after[1] - before[1]), flush=True)
    drag_titlebar(window, 60, -40)
    time.sleep(0.6)

    js(window, "document.getElementById('minBtn').click()")
    time.sleep(1)
    print("minimized after button:", bool(user32.IsIconic(app.own_window())), flush=True)
    user32.ShowWindowAsync(app.own_window(), 9)
    time.sleep(1.2)

    js(window, "document.getElementById('testBtn').click()")
    for _ in range(40):  # wait for the read (bar + minimap OCR) instead of a fixed sleep
        time.sleep(0.25)
        if js(window, "document.getElementById('testResult').innerText"):
            break
    time.sleep(0.3)
    shot("2_test_read")
    print("test:", js(window, "document.getElementById('testResult').innerText"), flush=True)
    js(window, "window.pywebview.api.start(%s, 3)" % MINUTES)
    time.sleep(1.2)
    shot("2b_countdown")
    time.sleep(3.5)
    shot("3_running_start")
    time.sleep(min(25, MINUTES * 60 * 0.6))
    shot("4_running_mid")
    deadline = time.time() + MINUTES * 60 + 30
    while time.time() < deadline:
        if js(window, "document.getElementById('phaseBadge').className") in ("badge done", "badge err"):  # any language
            break
        time.sleep(1)
    time.sleep(1.5)
    shot("5_done")
    print("session map:", js(window, "document.getElementById('mapVal').innerText"), flush=True)
    js(window, "document.getElementById('editBtn').click(); document.querySelector('.scroll').scrollTop = 1e6")
    time.sleep(0.8)
    shot("6_done_edit_scrolled")
    print("closing via the X button", flush=True)
    js(window, "document.getElementById('closeBtn').click()")


app.clear_web_cache(OUT / ".webview")
win = app.create_main_window(app.Api())
webview.start(drive, win, private_mode=False, storage_path=str(OUT / ".webview"))
print("window closed, webview.start returned", flush=True)
