"""Which language the UI opens in when the user hasn't picked one (the texts live in ui/i18n.js)."""
import ctypes
from typing import Iterable

LANG_HEBREW = 0x0D  # primary language id: the low 10 bits of a Windows LANGID


def pick_language(ui_langid: int, keyboard_langids: Iterable[int], locale_name: str) -> str:
    """Hebrew for Hebrew Windows, and for English Windows that types Hebrew or uses an
    Israeli region (common in Israel); English for everyone else."""
    if ui_langid & 0x3FF == LANG_HEBREW:
        return "he"
    if any(k & 0x3FF == LANG_HEBREW for k in keyboard_langids):
        return "he"
    if locale_name.lower().startswith("he"):
        return "he"
    return "en"


def system_language() -> str:
    try:
        kernel32, user32 = ctypes.WinDLL("kernel32"), ctypes.WinDLL("user32")
        ui = kernel32.GetUserDefaultUILanguage()
        n = user32.GetKeyboardLayoutList(0, None)
        layouts = (ctypes.c_void_p * max(n, 1))()
        n = user32.GetKeyboardLayoutList(n, layouts)
        keyboards = [(layouts[i] or 0) & 0xFFFF for i in range(n)]  # low word of an HKL = input language
        buf = ctypes.create_unicode_buffer(85)  # LOCALE_NAME_MAX_LENGTH
        locale = buf.value if kernel32.GetUserDefaultLocaleName(buf, len(buf)) else ""
    except (AttributeError, OSError):  # not Windows
        return "en"
    return pick_language(ui, keyboards, locale)
