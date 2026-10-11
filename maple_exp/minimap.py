"""The current map's name, from OCR of the minimap header (top-left: street line, then map line)."""
import difflib
import re

# English words that really end in "ll" - everything else ending in ll/II after a
# lowercase letter is a glued roman numeral ("RockyRoadll" -> "Rocky Road II").
_REAL_LL = {"hill", "hall", "mall", "well", "wall", "mill", "bell", "shell", "skull", "spell", "small", "doll",
            "troll", "bull", "hell", "fall", "ball", "tall", "cell", "dell", "full", "gull", "till", "still", "will"}
_ROMAN = re.compile(r"(?:I{1,3}|IV|VI{0,3}|IX|X)")
_SIMILAR = 0.85  # difflib ratio of OCR-folded names to treat them as the same map


def clean_name(text: str) -> str:
    s = re.sub(r"(?<=[a-z])\.(?=\s*[A-Z])", ",", text)  # comma misread as a period: "Dungeon.Forest"
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)  # OCR drops spaces: "TreeDungeon" -> "Tree Dungeon"
    s = re.sub(r"(?<=[a-z])(?=\d)", " ", s)     # "Market8>" -> "Market 8>"
    s = re.sub(r"\s*,\s*", ", ", s)
    s = re.sub(r"\s*<?\s*(\d{1,2})\s*>$", r" <\1>", s)  # room numbers: "Free Market 8>" -> "Free Market <8>"
    s = re.sub(r"\s+", " ", s).strip(" ,")
    words = s.split(" ")
    last = words[-1]
    if len(words) > 1 and re.fullmatch(r"[lI1|!]{1,3}", last):  # "Tunnel ll" -> "Tunnel II"
        words[-1] = "I" * len(last)
    elif (m := re.fullmatch(r"(.*[a-z])([lI1|!]{2,3})", last)) and last.lower() not in _REAL_LL:
        words[-1:] = [m.group(1), "I" * len(m.group(2))]
    return " ".join(words)


def parse_minimap(boxes) -> tuple[str | None, str] | None:
    """(street, map) from OCR boxes [(points, text, score)] of the screen's top-left corner, or None."""
    header = next((b for b in boxes if "WORLD" in b[1].upper()), None)  # the minimap's WORLD button
    if header is None:
        return None
    right = max(p[0] for p in header[0])
    bottom = max(p[1] for p in header[0])
    top_of = lambda b: min(p[1] for p in b[0])
    # Collapsed minimap (common in full screen): the title row itself reads "Street : Map".
    header_top = min(p[1] for p in header[0])
    for b in boxes:
        ys = [p[1] for p in b[0]]
        if b is not header and ":" in b[1] and max(p[0] for p in b[0]) < right and min(ys) < bottom and max(ys) > header_top:
            street, _, name = b[1].partition(":")
            if sum(c.isalpha() for c in name) >= 3:
                return clean_name(street), clean_name(name)
    lines = sorted((b for b in boxes if bottom < top_of(b) < bottom + 90 and min(p[0] for p in b[0]) < right),
                   key=top_of)
    texts = [clean_name(b[1]) for b in lines if sum(c.isalpha() for c in b[1]) >= 3]
    if not texts:
        return None
    return (texts[0], texts[1]) if len(texts) > 1 else (None, texts[0])


class MapVotes:
    """The minimap OCR wobbles between frames ("Mountainl" once in a few); the most common read wins."""

    def __init__(self):
        self._votes: dict[str, int] = {}  # insertion-ordered, so ties go to the earliest read

    def add(self, name: str) -> None:
        if name:
            self._votes[name] = self._votes.get(name, 0) + 1

    @property
    def count(self) -> int:
        return sum(self._votes.values())

    @property
    def best(self) -> str:
        return max(self._votes, key=self._votes.get) if self._votes else ""


def _split_numeral(name: str) -> tuple[str, str]:
    words = name.split(" ")
    return (" ".join(words[:-1]), words[-1]) if len(words) > 1 and _ROMAN.fullmatch(words[-1]) else (name, "")


def _fold(text: str) -> str:
    """Flatten OCR's usual confusions (l/I/1, O/0, spacing, punctuation) for comparison."""
    return re.sub(r"[^a-z0-9]", "", text.lower().translate(str.maketrans("l1|!0", "iiiio")))


def canonical_name(name: str, known: list[str]) -> str:
    """The known map this OCR read most likely is (same roman numeral, similar text), else the read itself."""
    name = clean_name(name)
    base, numeral = _split_numeral(name)
    best, best_ratio = name, _SIMILAR
    for k in known:
        k_base, k_numeral = _split_numeral(k)
        if k_numeral != numeral:  # "Ant Tunnel I" and "Ant Tunnel II" are different maps
            continue
        ratio = difflib.SequenceMatcher(None, _fold(base), _fold(k_base)).ratio()
        if ratio >= best_ratio:
            best, best_ratio = k, ratio
    return best
