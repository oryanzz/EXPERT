# Changelog

All notable changes to EXPERT are listed here. The project follows
[Semantic Versioning](https://semver.org/).

## [1.2.0] - 2026-10-11

### Added
- **Compact mode for full-screen play**: a small strip (about 200-310 x 50 px) with the timer,
  live EXP/min, one action button and an expand button, in every state - start, countdown,
  running and the summary line. Toggle it from the title bar; it turns on by itself when a timer
  starts while the game is full screen on the same monitor as EXPERT. The strip keeps the
  window's top-right corner in place and can be dragged anywhere.

## [1.1.1] - 2026-10-11

### Fixed
- **Full screen.** Tested live with the game in full screen at 2560x1440 (letterboxed, UI scaled up):
  - the map is read from a collapsed minimap's title row ("Hidden Street : Free Market <8>");
  - the EXP-bar and minimap crop areas scale with the screen instead of assuming a 1920x1200 window;
  - EXPERT opens on another monitor when the game is full screen (or in the top-right corner of a
    single monitor) instead of in the middle of the game.

## [1.1.0] - 2026-10-11

### Added
- **`EXPERT.exe`** - a single-file download, no Python or setup needed:
  `https://github.com/oryanzz/EXPERT/releases/latest/download/EXPERT.exe`.
  Built and OCR-self-tested by GitHub Actions for every release, with a SHA256 checksum.
- The exe updates itself from the banner, like the source version.
- `EXPERT.exe --selftest image.png out.json` checks the bundled OCR.
- `THIRD_PARTY_LICENSES.txt` with the license texts of everything bundled into the exe.

### Changed
- The exe keeps user data in `%LOCALAPPDATA%\EXPERT` (`EXPERT_DATA_DIR` overrides it);
  a source install still keeps it in the EXPERT folder.

## [1.0.3] - 2026-10-11

### Changed
- The update button is now a single word: `עדכון`.

## [1.0.2] - 2026-10-11

### Added
- **Built-in updater.** At startup EXPERT checks GitHub for a newer release and shows a banner;
  *Update now* closes the app, installs the new version (keeping history, screenshots, custom
  sound and settings) and reopens it. Also available as `update.bat`; a git checkout runs
  `git pull`.

### Changed
- The taskbar and Alt+Tab show the EXPERT stopwatch instead of the Python icon. EXPERT now has its
  own taskbar identity, also stamped on the shortcut, so a pinned EXPERT and the running window
  share one button (re-run `setup.bat` to refresh an existing shortcut).

## [1.0.1] - 2026-10-11

### Changed
- The window now fits its content: no empty space below the credit line, and the full summary
  shows without scrolling (capped at the bottom of the screen).
- The credit line is in English with even spacing: `EXPERT v1.0.1 · by ORYANZ · GitHub`.

## [1.0.0] - 2026-10-11

First public release.

### Added
- Farm timer with preset and custom durations, a 3-second start delay and an end chime.
- EXP reading from the game's status bar with on-device OCR, every 10 seconds.
- Summary: EXP per minute and per hour, EXP gained, percent gained, levels gained, and time to
  the next level.
- Level-ups during a session are counted correctly; misread levels are out-voted.
- Automatic map detection from the minimap header, with OCR clean-up and snapping to maps
  already in your history.
- Session history (`history.csv`), start/end screenshots, and a manual fix for misread values.
- Floating frameless window docked beside the game, with pin, minimize and close.
- Custom end sound via `sounds/done.wav`.
- `setup.bat` installer with desktop shortcut, and `run.bat`.

[1.2.0]: https://github.com/oryanzz/EXPERT/releases/tag/v1.2.0
[1.1.1]: https://github.com/oryanzz/EXPERT/releases/tag/v1.1.1
[1.1.0]: https://github.com/oryanzz/EXPERT/releases/tag/v1.1.0
[1.0.3]: https://github.com/oryanzz/EXPERT/releases/tag/v1.0.3
[1.0.2]: https://github.com/oryanzz/EXPERT/releases/tag/v1.0.2
[1.0.1]: https://github.com/oryanzz/EXPERT/releases/tag/v1.0.1
[1.0.0]: https://github.com/oryanzz/EXPERT/releases/tag/v1.0.0
