"""Window sizing: the frameless window hugs its content instead of leaving empty space."""

MIN_CSS_HEIGHT = 320  # never collapse below a usable window


def fitted_height(content_css: float, dpr: float, max_px: int) -> int:
    """Physical-pixel window height for `content_css` CSS pixels of content, capped at `max_px`."""
    return int(round(min(max(content_css, MIN_CSS_HEIGHT) * dpr, max_px)))
