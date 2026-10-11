"""Find the MapleStory window and screenshot its client area.

PrintWindow is blocked for the (elevated) game process, so this grabs the
window's area of the screen instead - the EXP bar must not be covered.
"""
import ctypes
import ctypes.wintypes as wt
from dataclasses import dataclass

from PIL import Image, ImageGrab

user32 = ctypes.WinDLL("user32")  # private copy: our argtypes must not leak into pywebview's calls
user32.FindWindowW.restype = wt.HWND
user32.WindowFromPoint.argtypes = [wt.POINT]
user32.WindowFromPoint.restype = wt.HWND
user32.GetAncestor.restype = wt.HWND
GA_ROOT = 2


def make_dpi_aware() -> None:
    """Use physical pixels so window rects line up with screenshots."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except OSError:
        user32.SetProcessDPIAware()


class CaptureError(Exception):
    """code is one of: not_found, minimized, black."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass
class Frame:
    image: Image.Image
    left: int  # screen position of the client area's top-left corner
    top: int
    hwnd: int


def find_game() -> int | None:
    return user32.FindWindowW("MapleStoryClass", None) or user32.FindWindowW(None, "MapleStory")


def game_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    """Client area as (left, top, right, bottom) in screen pixels."""
    if user32.IsIconic(hwnd):
        return None
    cr = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(cr))
    origin = wt.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(origin))
    if cr.right <= 0 or cr.bottom <= 0:
        return None
    return origin.x, origin.y, origin.x + cr.right, origin.y + cr.bottom


def capture() -> Frame:
    hwnd = find_game()
    if not hwnd:
        raise CaptureError("not_found")
    rect = game_rect(hwnd)
    if rect is None:
        raise CaptureError("minimized")
    image = ImageGrab.grab(bbox=rect, all_screens=True)
    if image.convert("L").getextrema()[1] < 10:
        raise CaptureError("black")
    return Frame(image=image, left=rect[0], top=rect[1], hwnd=hwnd)


def is_covered(frame: Frame, box: tuple[int, int, int, int]) -> bool:
    """True if another window sits on top of `box` (image coordinates)."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    for x, y in ((x0 + 2, cy), (cx, cy), (x1 - 2, cy), (cx, y0 + 2), (cx, y1 - 2)):
        hit = user32.WindowFromPoint(wt.POINT(frame.left + x, frame.top + y))
        if not hit or user32.GetAncestor(hit, GA_ROOT) != frame.hwnd:
            return True
    return False
