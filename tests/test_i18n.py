import json
import re
from pathlib import Path

from maple_exp.i18n import pick_language, system_language

ROOT = Path(__file__).resolve().parent.parent
HEBREW_CHAR = re.compile(r"[֐-׿]")

HE_UI, EN_US_UI = 0x040D, 0x0409
HE_KEYBOARD, EN_US_KEYBOARD, RU_KEYBOARD = 0x040D, 0x0409, 0x0419


def strings():
    """ui/i18n.js is `window.STRINGS = {...JSON...};` so both the page and this test can read it."""
    text = (ROOT / "ui" / "i18n.js").read_text(encoding="utf-8")
    body = text[text.index("STRINGS = {") + len("STRINGS = "):text.rindex("}") + 1]
    return json.loads(body)


# -- default language ------------------------------------------------------

def test_hebrew_windows_gets_hebrew():
    assert pick_language(HE_UI, [EN_US_KEYBOARD], "he-IL") == "he"


def test_english_windows_with_a_hebrew_keyboard_gets_hebrew():
    assert pick_language(EN_US_UI, [EN_US_KEYBOARD, HE_KEYBOARD], "en-US") == "he"


def test_english_windows_with_israeli_region_gets_hebrew():
    assert pick_language(EN_US_UI, [EN_US_KEYBOARD], "he-IL") == "he"


def test_english_windows_gets_english():
    assert pick_language(EN_US_UI, [EN_US_KEYBOARD], "en-US") == "en"


def test_other_languages_get_english():
    assert pick_language(0x0419, [RU_KEYBOARD, EN_US_KEYBOARD], "ru-RU") == "en"


def test_system_language_is_supported():
    assert system_language() in ("he", "en")


# -- translations ----------------------------------------------------------

def test_both_languages_have_the_same_keys():
    s = strings()
    assert set(s) == {"he", "en"}
    assert set(s["he"]) == set(s["en"])


def test_no_empty_translations():
    for lang, table in strings().items():
        assert all(v.strip() for v in table.values()), lang


def test_placeholders_match_between_languages():
    s = strings()
    for key in s["he"]:
        assert set(re.findall(r"\{(\w+)\}", s["he"][key])) == set(re.findall(r"\{(\w+)\}", s["en"][key])), key


def test_every_page_key_is_translated():
    html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
    keys = set(re.findall(r'data-i18n(?:-title)?="([\w.]+)"', html))
    assert keys, "index.html has no data-i18n keys"
    assert keys <= set(strings()["en"]), keys - set(strings()["en"])


def test_every_script_key_is_translated():
    js = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    keys = set(re.findall(r'\bt\("([\w.]+)"', js))
    assert keys, "app.js has no t() calls"
    assert keys <= set(strings()["en"]), keys - set(strings()["en"])


def test_every_python_error_code_is_translated():
    """The app sends short codes (covered, busy...) and the page shows them in the user's language."""
    codes, warnings = set(), set()
    for path in (ROOT / "app.py", ROOT / "maple_exp" / "capture.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.search(r"CaptureError\(|fail\(|return \"\w+\"  # error code", line):
                codes.update(re.findall(r'"(\w+)"', line))
            if "self._warn(" in line:
                warnings.update(re.findall(r'"(\w+)"', line))
    assert {"covered", "busy", "unexpected", "mismatch"} <= codes
    assert {"end_rejected", "end_failed"} <= warnings
    en = strings()["en"]
    assert {f"err.{c}" for c in codes} <= set(en), {c for c in codes if f"err.{c}" not in en}
    assert {f"warn.{w}" for w in warnings} <= set(en), {w for w in warnings if f"warn.{w}" not in en}


def test_all_text_lives_in_the_translation_file():
    for path in (ROOT / "ui" / "index.html", ROOT / "ui" / "app.js", ROOT / "app.py"):
        code = [ln for ln in path.read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith(("#", "//"))]
        leftovers = [ln.strip() for ln in code if HEBREW_CHAR.search(ln)]
        assert not leftovers, f"{path.name}: {leftovers[:3]}"
