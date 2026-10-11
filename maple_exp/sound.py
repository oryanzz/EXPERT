"""Which sound to play when a timer ends: the user's own done.wav, else the bundled chime."""
from pathlib import Path


def pick_sound(folder: Path) -> Path | None:
    for name in ("done.wav", "default.wav"):
        path = Path(folder) / name
        if path.is_file():
            return path
    return None
