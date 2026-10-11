"""Where EXPERT reads its resources (UI, default sound, icon) and keeps user data.

Run from source, both live in the project folder. The single-file .exe unpacks itself into a
temporary folder on every launch, so there the user's data (history, screenshots, settings,
custom sound, logs) lives in %LOCALAPPDATA%\\EXPERT instead. EXPERT_DATA_DIR overrides it.
"""
from pathlib import Path


def app_dirs(frozen: bool, code_dir: Path, bundle_dir: Path | None, env) -> tuple[Path, Path]:
    """(resource_dir, data_dir)."""
    res = Path(bundle_dir) if frozen and bundle_dir else Path(code_dir)
    if env.get("EXPERT_DATA_DIR"):
        data = Path(env["EXPERT_DATA_DIR"])
    elif frozen:
        data = Path(env.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "EXPERT"
    else:
        data = Path(code_dir)
    return res, data
