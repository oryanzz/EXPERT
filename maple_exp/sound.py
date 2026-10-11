"""Which sound to play when a timer ends: the user's own done.wav, else the bundled chime."""
from pathlib import Path


def pick_sound(user_dir: Path, bundled_dir: Path | None = None) -> Path | None:
    """user_dir/done.wav if the user added one, else bundled_dir/default.wav (bundled_dir
    defaults to user_dir: a source install keeps both in the same sounds/ folder)."""
    for folder, name in ((user_dir, "done.wav"), (bundled_dir or user_dir, "default.wav")):
        path = Path(folder) / name
        if path.is_file():
            return path
    return None
