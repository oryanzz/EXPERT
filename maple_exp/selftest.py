"""OCR self-check on a screenshot file. `EXPERT.exe --selftest image.png out.json` runs it, so a
freshly built .exe can prove its bundled OCR models load and read correctly (used by CI)."""
from pathlib import Path

from PIL import Image

from .ocr import BarReader


def run_selftest(image_path: Path) -> dict:
    reader = BarReader()
    image = Image.open(image_path).convert("RGB")
    bar = reader.read(image)
    found = reader.read_map(image)
    if bar is None:
        return {"ok": False, "error": "EXP bar not found", "map": found[1] if found else None}
    r = bar.reading
    return {"ok": True, "exp": r.exp, "pct": r.pct, "level": r.level, "map": found[1] if found else None}
