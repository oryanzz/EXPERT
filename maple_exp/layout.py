"""Window sizing: the frameless window hugs its content instead of leaving empty space."""

MIN_CSS_HEIGHT = 320  # never collapse below a usable window


def fitted_height(content_css: float, dpr: float, max_px: int) -> int:
    """Physical-pixel window height for `content_css` CSS pixels of content, capped at `max_px`."""
    return int(round(min(max(content_css, MIN_CSS_HEIGHT) * dpr, max_px)))


def dock_position(game: tuple, screens: list, win_w: int) -> tuple[int, int]:
    """Where EXPERT opens (physical px) so it never covers the game's EXP bar.

    game: the game's client area (left, top, right, bottom); screens: monitor work areas, the
    game's own monitor first. Windowed game with room: beside it. Full-screen game: on another
    monitor if there is one, else the top-right corner (the EXP bar is at the bottom centre).
    """
    gl, gt, gr, gb = game
    sl, st, sr, sb = screens[0]
    if gr + 24 + win_w <= sr:
        return gr + 24, max(st, gt - 31)  # 31px: the game window's title bar above its client area
    others = screens[1:]
    target = others[0] if others else screens[0]
    return target[2] - win_w - 16, target[1] + 16
