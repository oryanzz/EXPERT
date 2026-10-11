"""Read the EXP text from the bottom status bar of a game screenshot."""
import re
import threading
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter

from .minimap import parse_minimap
from .parse import EXP_LABEL, Reading, parse_status

BAR_HEIGHT = 80  # the classic status bar is ~60px tall regardless of resolution
MAP_CORNER = (600, 160)  # the minimap's header (title + street + map name) sits in this top-left area


@dataclass
class BarResult:
    reading: Reading
    box: tuple[int, int, int, int]  # EXP text, in screenshot coordinates


class BarReader:
    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()

    def _get_engine(self):
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR  # slow import; load on first use
            self._engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
        return self._engine

    def warm_up(self) -> None:
        with self._lock:
            self._get_engine()(np.zeros((40, 200, 3), np.uint8), use_cls=False)

    def read(self, image: Image.Image) -> BarResult | None:
        w, h = image.size
        # fall back to a taller strip in case the UI is scaled up
        for strip_h in dict.fromkeys((min(BAR_HEIGHT, h), h // 5)):
            top = h - strip_h
            strip = np.array(image.crop((0, top, w, h)).convert("RGB"))
            with self._lock:
                boxes, _ = self._get_engine()(strip, use_cls=False)
            boxes = sorted(boxes or [], key=lambda b: min(p[0] for p in b[0]))
            reading = parse_status([b[1] for b in boxes])
            if reading:
                return BarResult(reading, _exp_box(boxes, top))
        return None

    def read_map(self, image: Image.Image) -> tuple[str | None, str] | None:
        """(street, map) from the minimap header in the top-left corner, or None if it isn't showing."""
        w, h = image.size
        corner = image.crop((0, 0, min(MAP_CORNER[0], w), min(MAP_CORNER[1], h))).convert("RGB")
        # the minimap's crisp pixel font OCRs badly ("Moumtainm"); a slight blur reads it right
        corner = np.array(corner.filter(ImageFilter.GaussianBlur(0.9)))
        with self._lock:
            boxes, _ = self._get_engine()(corner, use_cls=False)
        return parse_minimap(boxes or [])


def _exp_box(boxes, top: int) -> tuple[int, int, int, int]:
    """Union of the OCR boxes from the 'EXP' label through the '%' sign."""
    texts = [b[1].upper() for b in boxes]
    i = next(k for k, t in enumerate(texts) if re.search(EXP_LABEL, t))
    j = next((k for k in range(i, len(texts)) if "%" in texts[k]), i)
    pts = [p for b in boxes[i:j + 1] for p in b[0]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return int(min(xs)), int(min(ys)) + top, int(max(xs)), int(max(ys)) + top


def crop_for_display(image: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    x0, y0, x1, y1 = box
    pad = 6
    c = image.crop((max(0, x0 - pad), max(0, y0 - pad), min(image.width, x1 + pad), min(image.height, y1 + pad)))
    return c.resize((c.width * 2, c.height * 2), Image.NEAREST)
