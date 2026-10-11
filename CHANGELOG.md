# Changelog

All notable changes to EXPERT are listed here. The project follows
[Semantic Versioning](https://semver.org/).

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

[1.0.0]: https://github.com/oryancohen/EXPERT/releases/tag/v1.0.0
