"""Turn OCR text from MapleStory's bottom status bar into numbers."""
import re
from dataclasses import dataclass

# The "EXP" label as OCR actually reads it ("EXR" seen live: P and R look alike in the game font).
EXP_LABEL = r"E\s*X\s*[PRF]"
# "EXP28.524[98.43%]" / "EXP. 1,234,567 [12.5%]" - dots and commas in the EXP
# number are thousand separators; the percent uses either as the decimal mark.
_EXP_RE = re.compile(EXP_LABEL + r"\.?\s*(\d[\d.,\s]*?)\s*[\[(]\s*(\d{1,3}(?:[.,]\d+)?)\s*%", re.I)
_LEVEL_RE = re.compile(r"LV\.?\s*(\d{1,3})", re.I)


@dataclass(frozen=True)
class Reading:
    exp: int
    pct: float
    level: int | None = None


def parse_status(texts: list[str]) -> Reading | None:
    joined = " ".join(texts)
    m = _EXP_RE.search(joined)
    if not m:
        return None
    pct = float(m.group(2).replace(",", "."))
    if pct > 100:
        return None
    exp = int(re.sub(r"\D", "", m.group(1)))
    lv = _LEVEL_RE.search(joined)
    level = int(lv.group(1)) if lv and int(lv.group(1)) > 0 else None
    return Reading(exp=exp, pct=pct, level=level)
