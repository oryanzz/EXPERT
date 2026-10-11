"""A global show/hide key (RegisterHotKey), so EXPERT can be toggled from inside the game.

RegisterHotKey works while the (elevated) game has focus, unlike a keyboard hook. F12 can't be
used: Windows reserves it for the debugger (AeDebug\\UserDebuggerHotKey), so registering it
fails with ERROR_HOTKEY_ALREADY_REGISTERED on most PCs.
"""
import ctypes
import ctypes.wintypes as wt
import threading

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x4000
_MODS = {"ctrl": MOD_CONTROL, "control": MOD_CONTROL, "shift": MOD_SHIFT, "alt": MOD_ALT}
_NAMED = {"pause": 0x13, "scrolllock": 0x91, "insert": 0x2D, "home": 0x24, "end": 0x23,
          "pageup": 0x21, "pagedown": 0x22}
WM_HOTKEY, WM_APP = 0x0312, 0x8000
_HOTKEY_ID = 1


def parse_hotkey(spec: str) -> tuple[int, int] | None:
    """'F11' / 'Pause' / 'Ctrl+Shift+E' -> (modifiers, virtual-key code); None for 'off' or invalid."""
    parts = [p.strip().lower() for p in (spec or "").split("+")]
    if not parts or not parts[-1] or parts[-1] == "off":
        return None
    mods = 0
    for p in parts[:-1]:
        if p not in _MODS:
            return None
        mods |= _MODS[p]
    key = parts[-1].replace(" ", "")
    if key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        return mods, 0x6F + int(key[1:])  # VK_F1 = 0x70
    if key in _NAMED:
        return mods, _NAMED[key]
    if len(key) == 1 and key.isalnum():
        return mods, ord(key.upper())
    return None


class HotkeyListener:
    """Owns one global hotkey on a background thread with its own message loop."""

    def __init__(self, on_press):
        self._on_press = on_press
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
        self._user32.PeekMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT, wt.UINT]
        self._user32.PostThreadMessageW.argtypes = [wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM]
        self._thread_id = 0
        self._ready = threading.Event()
        self._done = threading.Event()
        self._request: tuple[int, int] | None = None
        self._result = False
        threading.Thread(target=self._loop, daemon=True, name="hotkey").start()
        self._ready.wait(2)

    def set_key(self, spec: str) -> bool:
        """Register `spec` ('off' unregisters). False if invalid or taken by another program."""
        self._request = parse_hotkey(spec)
        self._done.clear()
        self._user32.PostThreadMessageW(self._thread_id, WM_APP, 0, 0)
        self._done.wait(2)
        return self._result or self._request is None and (spec or "").strip().lower() == "off"

    def _loop(self):
        u = self._user32
        msg = wt.MSG()
        u.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # create this thread's message queue
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
        self._ready.set()
        while u.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY and msg.wParam == _HOTKEY_ID:
                try:
                    self._on_press()
                except Exception:  # a failing toggle must not end the listener
                    pass
            elif msg.message == WM_APP:
                u.UnregisterHotKey(None, _HOTKEY_ID)  # hotkeys belong to the thread that registered them
                req = self._request
                self._result = bool(req and u.RegisterHotKey(None, _HOTKEY_ID, req[0] | MOD_NOREPEAT, req[1]))
                self._done.set()
