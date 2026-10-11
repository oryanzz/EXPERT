"""WebView2 keeps an HTTP cache of the UI files that pywebview serves from 127.0.0.1, and with
no cache headers it may reuse an old app.js after an update. Clearing it on launch keeps the
UI in sync with the code; saved settings (Local Storage) are left alone."""
import shutil
from pathlib import Path

_CACHE_DIRS = ("Cache", "Code Cache")


def clear_web_cache(storage_path: Path) -> None:
    profile = Path(storage_path) / "EBWebView" / "Default"
    for name in _CACHE_DIRS:
        shutil.rmtree(profile / name, ignore_errors=True)
