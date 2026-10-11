"""Render a local HTML page in WebView2 and save a screenshot of it (for design previews).

usage: render_page.py page.html out.png [width height]
Opens at the right edge of the screen, beside the game, so it doesn't cover it.
"""
import ctypes
import ctypes.wintypes as wt
import os
import sys
import time
from pathlib import Path

ctypes.windll.shcore.SetProcessDpiAwareness(2)
import webview  # noqa: E402
from PIL import ImageGrab  # noqa: E402

page, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
W, H = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (572, 1340)
user32 = ctypes.windll.user32
screen_w = user32.GetSystemMetrics(0)


def drive(window):
    time.sleep(1.0)
    window.evaluate_js("document.fonts.ready.then(() => { window.__fonts = true }); 1")
    for _ in range(40):
        if window.evaluate_js("!!window.__fonts"):
            break
        time.sleep(0.25)
    time.sleep(0.8)
    hwnd = user32.FindWindowW(None, "render-preview")
    r = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    ImageGrab.grab(bbox=(r.left, r.top, r.right, r.bottom), all_screens=True).save(out)
    print("saved", out, (r.right - r.left, r.bottom - r.top), flush=True)
    os._exit(0)


win = webview.create_window("render-preview", str(page), width=W, height=H, x=screen_w - W - 4, y=40,
                            frameless=True, on_top=True)
webview.start(drive, win)
