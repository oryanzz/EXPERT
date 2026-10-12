"""EXPERT (EXP PER TIME) - a farm timer for MapleStory that reads your EXP off the screen."""
import base64
import ctypes
import ctypes.wintypes as wt
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import winsound
from datetime import datetime
from pathlib import Path

from maple_exp import __version__
from maple_exp.capture import CaptureError, capture, find_game, game_rect, is_covered, make_dpi_aware

make_dpi_aware()  # must happen before any window exists

import webview  # noqa: E402

from maple_exp.layout import compact_rect, covers_monitor, dock_position, fitted_height  # noqa: E402
from maple_exp.update import check_for_update  # noqa: E402
from maple_exp.history import append_session, known_maps, load_recent, replace_last  # noqa: E402
from maple_exp.i18n import system_language  # noqa: E402
from maple_exp.minimap import MapVotes, canonical_name  # noqa: E402
from maple_exp.ocr import BarReader, crop_for_display  # noqa: E402
from maple_exp.parse import Reading  # noqa: E402
from maple_exp.paths import app_dirs  # noqa: E402
from maple_exp.sound import pick_sound  # noqa: E402
from maple_exp.tracker import Summary, Tracker  # noqa: E402
from maple_exp.webcache import clear_web_cache  # noqa: E402

ROOT = Path(__file__).resolve().parent
FROZEN = getattr(sys, "frozen", False)  # running as the single-file EXPERT.exe
RES, DATA = app_dirs(FROZEN, ROOT, getattr(sys, "_MEIPASS", None), os.environ)  # see maple_exp/paths.py
SHOTS = DATA / "shots"
SOUNDS = DATA / "sounds"  # the user's own done.wav; the default chime ships in RES / "sounds"
HISTORY = DATA / "history.csv"
WEB_STORAGE = DATA / ".webview"
REPO_URL = "https://github.com/oryanzz/EXPERT"
ICON = RES / "ui" / "icon.ico"
APP_ID = "ORYANZ.EXPERT"  # taskbar identity; scripts/make_shortcut.ps1 stamps the same ID on the shortcut
SAMPLE_EVERY = 10  # seconds between live readings while the timer runs
WIN_W, WIN_H = 440, 860
MIN_W, MIN_H = 160, 40  # small enough for the compact strip


def fail(code: str) -> dict:
    """A failed API call. Errors travel as short codes; the page words them in the user's
    language (ui/i18n.js: "err.<code>")."""
    return {"ok": False, "error": code}


def read_game(reader: BarReader):
    frame = capture()
    res = reader.read(frame.image)
    w, h = frame.image.size
    if res is None:
        raise CaptureError("covered" if is_covered(frame, (0, h - 60, w, h - 5)) else "unreadable")
    if is_covered(frame, res.box):
        raise CaptureError("covered")
    return frame, res


def detect_map(reader: BarReader, image) -> str:
    """Map name from the minimap, snapped to a name already in the history; "" if not visible."""
    try:
        found = reader.read_map(image)
    except Exception:  # a missing map name must never break a session
        return ""
    return canonical_name(found[1], known_maps(HISTORY)) if found else ""


def summary_dict(s: Summary) -> dict:
    return {k: getattr(s, k) for k in Summary.__dataclass_fields__}


def chime() -> None:
    """sounds/done.wav if the user added one (e.g. recorded from the game), else the bundled chime."""
    path = pick_sound(SOUNDS, RES / "sounds")
    try:
        if path is None:
            raise RuntimeError("no sound file")
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except RuntimeError:  # missing or unplayable file: fall back to a plain beep
        for freq, ms in ((880, 120), (1175, 120), (1568, 260)):
            winsound.Beep(freq, ms)


class Session:
    def __init__(self, reader: BarReader, minutes: float, delay: int, on_done):
        self.reader = reader
        self.minutes = minutes
        self.map_name = ""  # read from the minimap: start shot, first samples, end shot (majority)
        self._map_votes = MapVotes()
        self._map_tries = 0
        self.on_done = on_done
        self.phase = "countdown"
        self.countdown_until = time.monotonic() + delay
        self.t0 = self.end_at = None
        self.start = self.end = None  # snapshots shown in the summary
        self.samples: list[tuple[float, Reading]] = []  # accepted readings, in order
        self.tracker: Tracker | None = None
        self.result: dict | None = None
        self.error = self.warning = None  # codes, worded by the page ("err.<code>" / "warn.<code>")
        self.error_detail = self.warning_reason = ""
        self.failed_reads = 0
        self.stamp = datetime.now()
        self._stop = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self._stop.set()

    # -- worker thread -------------------------------------------------

    def _run(self):
        try:
            self._loop()
        except CaptureError as e:
            self._fail(e.code)
        except Exception as e:  # keep the UI alive whatever happens
            self._fail("unexpected", str(e))

    def _fail(self, code: str, detail: str = ""):
        self.phase, self.error, self.error_detail = "error", code, detail

    def _warn(self, code: str, reason: str = ""):
        self.warning, self.warning_reason = code, reason

    def _loop(self):
        while time.monotonic() < self.countdown_until:
            if self._stop.wait(0.1):
                self.phase = "cancelled"
                return
        frame, res = self._read_retrying(tries=3)
        self.t0 = time.monotonic()
        self.end_at = self.t0 + self.minutes * 60
        self.start = self._snapshot(frame, res, "start")
        self.tracker = Tracker(self.t0, res.reading)
        self.samples.append((self.t0, res.reading))
        self.phase = "running"
        self._vote_map(frame.image)

        next_sample = self.t0 + SAMPLE_EVERY
        while True:
            wake = min(next_sample, self.end_at)
            if self._stop.wait(max(0.0, wake - time.monotonic())) or time.monotonic() >= self.end_at:
                break
            self._sample()
            next_sample += SAMPLE_EVERY

        self.phase = "finalizing"
        try:
            frame, res = self._read_retrying(tries=3)
            t = time.monotonic()
            self.end = self._snapshot(frame, res, "end")
            self.end["t"] = t
            self._vote_map(frame.image)
            self.end["accepted"] = self.tracker.add(t, res.reading)
            if self.end["accepted"]:
                self.samples.append((t, res.reading))
            else:
                self._warn("end_rejected")
        except CaptureError as e:
            self._warn("end_failed", e.code)
        self._finish()

    def _sample(self):
        try:
            frame, res = read_game(self.reader)
        except CaptureError:
            self.failed_reads += 1
            return
        t = time.monotonic()
        if self._map_tries < 3:
            self._vote_map(frame.image)
        if self.tracker.add(t, res.reading):
            self.samples.append((t, res.reading))
        else:
            self.failed_reads += 1

    def _vote_map(self, image):
        self._map_tries += 1
        self._map_votes.add(detect_map(self.reader, image))
        self.map_name = self._map_votes.best

    def _read_retrying(self, tries: int):
        for attempt in range(tries):
            try:
                return read_game(self.reader)
            except CaptureError:
                if attempt == tries - 1:
                    raise
                time.sleep(1)

    def _snapshot(self, frame, res, label: str) -> dict:
        SHOTS.mkdir(parents=True, exist_ok=True)
        name = f"{self.stamp:%Y-%m-%d_%H-%M-%S}_{label}.jpg"
        frame.image.save(SHOTS / name, quality=90)
        buf = io.BytesIO()
        crop_for_display(frame.image, res.box).save(buf, "PNG")
        r = res.reading
        return {"exp": r.exp, "pct": r.pct, "level": r.level, "shot": name,
                "crop": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}

    def _finish(self, replace=False):
        t_last = self.samples[-1][0]
        self.result = summary_dict(self.tracker.summary(t_last))
        record = {
            "date": f"{self.stamp:%Y-%m-%d %H:%M}", "map": self.map_name,
            "minutes": round(self.result["minutes"], 1), "exp_gained": self.result["exp_gained"],
            "exp_per_min": round(self.result["exp_per_min"]), "exp_per_hour": round(self.result["exp_per_hour"]),
            "pct_gained": round(self.result["pct_gained"], 2), "levels_gained": self.result["levels_gained"],
            "start_level": self.start["level"] or "", "end_level": self.result["level"] or "",
            "start_shot": self.start["shot"], "end_shot": (self.end or {}).get("shot", ""),
        }
        (replace_last if replace else append_session)(HISTORY, record)
        self.phase = "done"
        if not replace:
            self.on_done()

    # -- manual correction ---------------------------------------------

    def recompute(self, start_exp: int, start_pct: float, end_exp: int, end_pct: float, map_name: str) -> str | None:
        """Re-run the math with corrected start/end readings (and map). Returns an error or None."""
        start = Reading(start_exp, start_pct, self.start["level"])
        middle = self.samples[1:-1] if self.end and self.end["accepted"] else self.samples[1:]
        tracker = Tracker(self.t0, start)
        samples = [(self.t0, start)]
        for t, r in middle:
            if tracker.add(t, r):
                samples.append((t, r))
        if self.end:
            end = Reading(end_exp, end_pct, self.end["level"])
            if not tracker.add(self.end["t"], end):
                return "mismatch"  # error code
            samples.append((self.end["t"], end))
            self.end.update(exp=end_exp, pct=end_pct, accepted=True)
        self.start.update(exp=start_exp, pct=start_pct)
        self.map_name = " ".join(map_name.split())  # the user's spelling becomes the known name
        self.tracker, self.samples = tracker, samples
        self._warn(None)
        self._finish(replace=True)
        return None

    # -- state for the UI ------------------------------------------------

    def state(self) -> dict:
        now = time.monotonic()
        live = None
        if self.tracker and self.phase in ("running", "finalizing"):
            live = summary_dict(self.tracker.summary(self.samples[-1][0]))
            live["last_ago"] = now - self.samples[-1][0]
        return {
            "phase": self.phase,
            "countdown": max(0, self.countdown_until - now),
            "total": self.minutes * 60,
            "remaining": max(0, self.end_at - now) if self.end_at else self.minutes * 60,
            "map": self.map_name,
            "live": live,
            "result": self.result,
            "start": self.start,
            "end": self.end,
            "error": self.error,
            "error_detail": self.error_detail,
            "warning": self.warning,
            "warning_reason": self.warning_reason,
            "failed_reads": self.failed_reads,
            "samples": len(self.samples),
        }


class Api:
    def __init__(self):
        self._reader = BarReader()
        self._session: Session | None = None
        self._update: dict | None = None  # latest release found by check_update()
        self._full_width = 0  # the full window's width, kept while in compact mode
        threading.Thread(target=self._reader.warm_up, daemon=True).start()

    def get_state(self) -> dict:
        hwnd = find_game()
        rect = game_rect(hwnd) if hwnd else None
        game = {"found": bool(hwnd), "minimized": bool(hwnd) and rect is None,
                "size": f"{rect[2] - rect[0]}×{rect[3] - rect[1]}" if rect else None,
                "overlay": bool(rect) and game_covers_our_screen(hwnd, rect)}
        session = self._session.state() if self._session else {"phase": "idle"}
        return {"game": game, **session}

    def test_read(self) -> dict:
        try:
            frame, res = read_game(self._reader)
        except CaptureError as e:
            return fail(e.code)
        buf = io.BytesIO()
        crop_for_display(frame.image, res.box).save(buf, "PNG")
        r = res.reading
        return {"ok": True, "exp": r.exp, "pct": r.pct, "level": r.level,
                "map": detect_map(self._reader, frame.image),
                "crop": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}

    def start(self, minutes, delay=3) -> dict:
        if self._session and self._session.phase in ("countdown", "running", "finalizing"):
            return fail("busy")
        minutes = float(minutes)
        if not 0 < minutes <= 600:
            return fail("bad_minutes")
        self._session = Session(self._reader, minutes, int(delay), self._on_done)
        return {"ok": True}

    def stop(self) -> None:
        if self._session:
            self._session.stop()

    def reset(self) -> None:
        if self._session and self._session.phase in ("countdown", "running", "finalizing"):
            self._session.stop()
        self._session = None

    def recompute(self, start_exp, start_pct, end_exp, end_pct, map_name="") -> dict:
        if not self._session or self._session.phase != "done":
            return fail("no_session")
        try:
            err = self._session.recompute(int(start_exp), float(start_pct), int(end_exp), float(end_pct),
                                          str(map_name or ""))
        except (TypeError, ValueError):
            return fail("bad_number")
        return {"ok": err is None, "error": err}

    def history(self) -> list[dict]:
        return load_recent(HISTORY)

    def check_update(self) -> dict | None:
        """Newer release on GitHub, or None (up to date / offline). Called once at startup."""
        self._update = check_for_update(need_exe=FROZEN)
        return self._update

    def open_release(self) -> None:
        if self._update and self._update["url"].startswith(REPO_URL + "/"):
            os.startfile(self._update["url"])  # only the official release page from the check

    def start_update(self) -> dict:
        """Hand over to the updater script (it waits for this app to exit), then close."""
        if self._session and self._session.phase in ("countdown", "running", "finalizing"):
            return fail("update_busy")
        ps = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]
        if FROZEN:
            if not (self._update and self._update.get("exe_url")):
                return fail("no_update")
            # the bundle folder (RES) is deleted when the exe exits, so run the script from DATA
            script = DATA / "update_exe.ps1"
            shutil.copyfile(RES / "scripts" / "update_exe.ps1", script)
            args = ps + [str(script), "-ExePath", sys.executable, "-Url", self._update["exe_url"],
                         "-WaitPids", f"{os.getpid()},{os.getppid()}", "-Log", str(DATA / "update.log")]
            cwd = DATA
        else:
            args = ps + [str(ROOT / "scripts" / "update.ps1"), "-WaitPid", str(os.getpid()), "-Restart"]
            cwd = ROOT
        subprocess.Popen(args, cwd=cwd, creationflags=subprocess.CREATE_NEW_CONSOLE)
        self.close()
        return {"ok": True}

    def app_info(self) -> dict:
        return {"version": __version__, "repo": REPO_URL, "lang": system_language()}

    def open_repo(self) -> None:
        os.startfile(REPO_URL)  # fixed URL, opens in the default browser

    def open_shots(self) -> None:
        SHOTS.mkdir(parents=True, exist_ok=True)
        os.startfile(SHOTS)

    def set_on_top(self, flag) -> None:
        hwnd = own_window()
        if hwnd:
            user32.SetWindowPos(hwnd, HWND_TOPMOST if flag else HWND_NOTOPMOST, 0, 0, 0, 0, SWP_ASYNC_NOMOVE)

    def fit_height(self, content_css, dpr=1.0) -> None:
        """Resize the window to hug its content (the UI reports its height on every change)."""
        hwnd = own_window()
        if not hwnd:
            return
        r = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        work = monitor_work_area(hwnd)
        max_px = (work.bottom - r.top - 8) if work else (r.bottom - r.top)
        h = fitted_height(float(content_css), float(dpr or 1), max_px)
        # leaving compact mode queues a width change first; use the remembered width so this
        # height fit (queued right after it) can't narrow the window back
        x, y, w, h = compact_rect((r.left, r.top, r.right, r.bottom), self._full_width or (r.right - r.left), h)
        if (w, h) != (r.right - r.left, r.bottom - r.top):
            user32.SetWindowPos(hwnd, None, x, y, w, h, SWP_ASYNC_MOVE_RESIZE)

    def compact(self, on) -> None:
        """Enter/leave compact mode. Remembers the full window's width to restore it."""
        hwnd = own_window()
        if not hwnd:
            return
        r = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        if on:
            self._full_width = self._full_width or (r.right - r.left)
        else:
            x, y, w, h = compact_rect((r.left, r.top, r.right, r.bottom),
                                      self._full_width or (r.right - r.left), r.bottom - r.top)
            user32.SetWindowPos(hwnd, None, x, y, w, h, SWP_ASYNC_MOVE_RESIZE)

    def fit_compact(self, css_w, css_h, dpr=1.0) -> None:
        """Size the window to the compact strip, top-right corner fixed."""
        hwnd = own_window()
        if not hwnd:
            return
        r = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(r))
        scale = float(dpr or 1)
        # never ask for less than the window's minimum size: Windows would widen it to the minimum
        # and the right edge (which compact_rect keeps fixed) would drift
        w_px, h_px = max(round(css_w * scale), round(MIN_W * scale)), max(round(css_h * scale), round(MIN_H * scale))
        x, y, w, h = compact_rect((r.left, r.top, r.right, r.bottom), w_px, h_px)
        if (w, h) != (r.right - r.left, r.bottom - r.top):
            user32.SetWindowPos(hwnd, None, x, y, w, h, SWP_ASYNC_MOVE_RESIZE)

    def minimize(self) -> None:
        hwnd = own_window()
        if hwnd:
            user32.ShowWindowAsync(hwnd, SW_MINIMIZE)

    def close(self) -> None:
        hwnd = own_window()
        if hwnd:
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)

    def _on_done(self):
        threading.Thread(target=chime, daemon=True).start()
        hwnd = own_window()
        if hwnd and user32.IsIconic(hwnd):
            user32.ShowWindowAsync(hwnd, SW_RESTORE)


# Window tweaks go through async Win32 calls on purpose. pywebview's own setters
# (window.on_top / restore) touch WinForms from this worker thread while holding
# the GIL; if the UI thread is mid-way through a JS->Python call (the 400ms poll)
# it needs the GIL too, and the whole app deadlocks.
# A private WinDLL: argtypes set on the shared ctypes.windll.user32 would also apply
# to pywebview's own calls (its drag passes None for SetWindowPos' size and broke).
user32 = ctypes.WinDLL("user32")
user32.FindWindowExW.argtypes = [wt.HWND, wt.HWND, wt.LPCWSTR, wt.LPCWSTR]
user32.FindWindowExW.restype = wt.HWND
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
user32.ShowWindowAsync.argtypes = [wt.HWND, ctypes.c_int]
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
SWP_ASYNC_NOMOVE = 0x0001 | 0x0002 | 0x0010 | 0x4000  # NOSIZE | NOMOVE | NOACTIVATE | ASYNCWINDOWPOS
SWP_ASYNC_MOVE_RESIZE = 0x0004 | 0x0010 | 0x4000  # NOZORDER | NOACTIVATE | ASYNCWINDOWPOS
SW_MINIMIZE, SW_RESTORE = 6, 9
WM_CLOSE = 0x0010
WINDOW_TITLE = "EXPERT"
DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_ROUND = 33, 2
DWMWA_BORDER_COLOR = 34
WOOD_COLORREF = 0x000C3B7A  # #7a3b0c as 0x00BBGGRR


def own_window() -> int | None:
    """This process's main window handle."""
    pid = os.getpid()
    hwnd = None
    while hwnd := user32.FindWindowExW(None, hwnd, None, WINDOW_TITLE):
        owner = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid:
            return hwnd
    return None


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT), ("rcWork", wt.RECT), ("dwFlags", wt.DWORD)]


user32.MonitorFromWindow.argtypes = [wt.HWND, wt.DWORD]
user32.MonitorFromWindow.restype = wt.HMONITOR
user32.GetMonitorInfoW.argtypes = [wt.HMONITOR, ctypes.POINTER(MONITORINFO)]
user32.EnumDisplayMonitors.argtypes = [wt.HDC, ctypes.POINTER(wt.RECT), ctypes.c_void_p, wt.LPARAM]


def monitor_work_area(hwnd: int) -> wt.RECT | None:
    """The usable area (minus the taskbar) of the monitor the window is on."""
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    hmon = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
    return mi.rcWork if hmon and user32.GetMonitorInfoW(hmon, ctypes.byref(mi)) else None


def game_covers_our_screen(game_hwnd: int, client: tuple) -> bool:
    """The game is full screen on the same monitor as EXPERT, so EXPERT sits on top of it."""
    mine = own_window()
    if not mine:
        return False
    game_mon = user32.MonitorFromWindow(game_hwnd, 2)
    if game_mon != user32.MonitorFromWindow(mine, 2):
        return False
    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(MONITORINFO)
    if not user32.GetMonitorInfoW(game_mon, ctypes.byref(mi)):
        return False
    m = mi.rcMonitor
    return covers_monitor(client, (m.left, m.top, m.right, m.bottom))


def round_corners(hwnd: int) -> None:
    """Windows 11 rounded corners + a wood-colored native border for the frameless window.
    Older Windows ignores these attributes and keeps square corners."""
    dwm = ctypes.windll.dwmapi
    for attr, value in ((DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.c_int(DWMWCP_ROUND)),
                        (DWMWA_BORDER_COLOR, ctypes.c_uint(WOOD_COLORREF))):
        dwm.DwmSetWindowAttribute(wt.HWND(hwnd), attr, ctypes.byref(value), ctypes.sizeof(value))


def create_main_window(api: "Api"):
    """Frameless floating window; the page draws its own title bar (drag region + buttons)."""
    x, y = initial_position()
    window = webview.create_window(
        WINDOW_TITLE, str(RES / "ui" / "index.html"), js_api=api,
        width=WIN_W, height=WIN_H, x=x, y=y,
        frameless=True, easy_drag=False, on_top=True, background_color="#9fd8ff", min_size=(MIN_W, MIN_H),
    )
    window.events.shown += lambda: round_corners(own_window())
    return window


def monitor_work_areas(hwnd: int) -> list[tuple[int, int, int, int]]:
    """Work areas of all monitors (taskbar excluded), the one showing `hwnd` first."""
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HMONITOR, wt.HDC, ctypes.POINTER(wt.RECT), wt.LPARAM)
    def collect(hmon, _dc, _rect, _lp):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            w = mi.rcWork
            found.append((hmon, (w.left, w.top, w.right, w.bottom)))
        return True

    user32.EnumDisplayMonitors(None, None, collect, 0)
    own = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
    found.sort(key=lambda m: m[0] != own)
    return [area for _, area in found]


def initial_position():
    """Open where we never cover the game's EXP bar: beside a windowed game, or on another
    monitor / in the top-right corner when the game is full screen (see maple_exp/layout.py)."""
    hwnd = find_game()
    rect = game_rect(hwnd) if hwnd else None
    if not rect:
        return None, None
    scale = ctypes.windll.user32.GetDpiForSystem() / 96
    x, y = dock_position(rect, monitor_work_areas(hwnd), int(WIN_W * scale))
    return int(x / scale), int(y / scale)
    u = ctypes.windll.user32
    scale = u.GetDpiForSystem() / 96
    screen_right = u.GetSystemMetrics(76) + u.GetSystemMetrics(78)  # virtual screen left + width
    x = rect[2] + 24
    if x + WIN_W * scale <= screen_right:
        return int(x / scale), int(max(0, rect[1] - 31) / scale)
    return None, None


def selftest(image: str, out: str) -> int:
    """`EXPERT.exe --selftest shot.png result.json`: prove the bundled OCR works (used by CI)."""
    from maple_exp.selftest import run_selftest
    result = run_selftest(Path(image))
    Path(out).write_text(json.dumps(result), encoding="utf-8")
    return 0 if result["ok"] else 1


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--selftest":
        sys.exit(selftest(sys.argv[2], sys.argv[3]))
    DATA.mkdir(parents=True, exist_ok=True)
    if sys.stderr is None:  # started without a console (shortcut / the .exe): log to a file
        sys.stdout = sys.stderr = open(DATA / "app.log", "a", encoding="utf-8", buffering=1)
    clear_web_cache(WEB_STORAGE)  # never run a stale cached app.js after an update
    # Own taskbar identity: without it Windows groups the window under pythonw.exe and shows
    # Python's icon. Must be set before the window exists.
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    create_main_window(Api())
    # non-private so the last minutes / pin choice survive restarts
    webview.start(icon=str(ICON), private_mode=False, storage_path=str(WEB_STORAGE))


if __name__ == "__main__":
    main()
