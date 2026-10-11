"""EXPERT (EXP PER TIME) - a farm timer for MapleStory that reads your EXP off the screen."""
import base64
import ctypes
import ctypes.wintypes as wt
import io
import os
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

from maple_exp.history import append_session, known_maps, load_recent, replace_last  # noqa: E402
from maple_exp.minimap import MapVotes, canonical_name  # noqa: E402
from maple_exp.ocr import BarReader, crop_for_display  # noqa: E402
from maple_exp.parse import Reading  # noqa: E402
from maple_exp.sound import pick_sound  # noqa: E402
from maple_exp.tracker import Summary, Tracker  # noqa: E402
from maple_exp.webcache import clear_web_cache  # noqa: E402

ROOT = Path(__file__).resolve().parent
SHOTS = ROOT / "shots"
SOUNDS = ROOT / "sounds"
HISTORY = ROOT / "history.csv"
WEB_STORAGE = ROOT / ".webview"
REPO_URL = "https://github.com/oryanzz/EXPERT"
SAMPLE_EVERY = 10  # seconds between live readings while the timer runs
WIN_W, WIN_H = 440, 860

ERRORS = {
    "not_found": "MapleStory לא פתוח",
    "minimized": "חלון המשחק ממוזער",
    "black": "הצילום יצא שחור. העבר את המשחק למצב חלון",
    "covered": "חלון אחר מכסה את בר ה-EXP",
    "unreadable": "לא הצלחתי לקרוא את ה-EXP מהמסך",
}


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
    path = pick_sound(SOUNDS)
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
        self.error = self.warning = None
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
            self.phase, self.error = "error", ERRORS[e.code]
        except Exception as e:  # keep the UI alive whatever happens
            self.phase, self.error = "error", f"שגיאה לא צפויה: {e}"

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
                self.warning = "קריאת הסיום לא הסתדרה עם הקודמות, אז החישוב הוא עד הקריאה התקינה האחרונה. בדוק את המספרים למטה."
        except CaptureError as e:
            self.warning = f"צילום הסיום נכשל ({ERRORS[e.code]}), אז החישוב הוא עד הקריאה האחרונה שהצליחה."
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
        SHOTS.mkdir(exist_ok=True)
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
                return "המספרים שהזנת לא מסתדרים זה עם זה (בדוק את האחוזים)"
            samples.append((self.end["t"], end))
            self.end.update(exp=end_exp, pct=end_pct, accepted=True)
        self.start.update(exp=start_exp, pct=start_pct)
        self.map_name = " ".join(map_name.split())  # the user's spelling becomes the known name
        self.tracker, self.samples, self.warning = tracker, samples, None
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
            "warning": self.warning,
            "failed_reads": self.failed_reads,
            "samples": len(self.samples),
        }


class Api:
    def __init__(self):
        self._reader = BarReader()
        self._session: Session | None = None
        threading.Thread(target=self._reader.warm_up, daemon=True).start()

    def get_state(self) -> dict:
        hwnd = find_game()
        rect = game_rect(hwnd) if hwnd else None
        game = {"found": bool(hwnd), "minimized": bool(hwnd) and rect is None,
                "size": f"{rect[2] - rect[0]}×{rect[3] - rect[1]}" if rect else None}
        session = self._session.state() if self._session else {"phase": "idle"}
        return {"game": game, **session}

    def test_read(self) -> dict:
        try:
            frame, res = read_game(self._reader)
        except CaptureError as e:
            return {"ok": False, "error": ERRORS[e.code]}
        buf = io.BytesIO()
        crop_for_display(frame.image, res.box).save(buf, "PNG")
        r = res.reading
        return {"ok": True, "exp": r.exp, "pct": r.pct, "level": r.level,
                "map": detect_map(self._reader, frame.image),
                "crop": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}

    def start(self, minutes, delay=3) -> dict:
        if self._session and self._session.phase in ("countdown", "running", "finalizing"):
            return {"ok": False, "error": "טיימר כבר רץ"}
        minutes = float(minutes)
        if not 0 < minutes <= 600:
            return {"ok": False, "error": "בחר בין דקה ל-600 דקות"}
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
            return {"ok": False, "error": "אין סשן לתקן"}
        try:
            err = self._session.recompute(int(start_exp), float(start_pct), int(end_exp), float(end_pct),
                                          str(map_name or ""))
        except (TypeError, ValueError):
            return {"ok": False, "error": "מספר לא תקין"}
        return {"ok": err is None, "error": err}

    def history(self) -> list[dict]:
        return load_recent(HISTORY)

    def app_info(self) -> dict:
        return {"version": __version__, "repo": REPO_URL}

    def open_repo(self) -> None:
        os.startfile(REPO_URL)  # fixed URL, opens in the default browser

    def open_shots(self) -> None:
        SHOTS.mkdir(exist_ok=True)
        os.startfile(SHOTS)

    def set_on_top(self, flag) -> None:
        hwnd = own_window()
        if hwnd:
            user32.SetWindowPos(hwnd, HWND_TOPMOST if flag else HWND_NOTOPMOST, 0, 0, 0, 0, SWP_ASYNC_NOMOVE)

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
        WINDOW_TITLE, str(ROOT / "ui" / "index.html"), js_api=api,
        width=WIN_W, height=WIN_H, x=x, y=y,
        frameless=True, easy_drag=False, on_top=True, background_color="#9fd8ff",
    )
    window.events.shown += lambda: round_corners(own_window())
    return window


def initial_position():
    """Dock beside the game window when there is room, so we never cover the EXP bar."""
    hwnd = find_game()
    rect = game_rect(hwnd) if hwnd else None
    if not rect:
        return None, None
    u = ctypes.windll.user32
    scale = u.GetDpiForSystem() / 96
    screen_right = u.GetSystemMetrics(76) + u.GetSystemMetrics(78)  # virtual screen left + width
    x = rect[2] + 24
    if x + WIN_W * scale <= screen_right:
        return int(x / scale), int(max(0, rect[1] - 31) / scale)
    return None, None


def main():
    if sys.stderr is None:  # started via pythonw (the shortcut): no console, so log to a file
        sys.stdout = sys.stderr = open(ROOT / "app.log", "a", encoding="utf-8", buffering=1)
    clear_web_cache(WEB_STORAGE)  # never run a stale cached app.js after an update
    create_main_window(Api())
    # non-private so the last minutes / pin choice survive restarts
    webview.start(private_mode=False, storage_path=str(WEB_STORAGE))


if __name__ == "__main__":
    main()
