# Contributing to EXPERT

Thanks for helping! Bug reports, ideas, translations and pull requests are all welcome.

## Ground rules

- **Screen only.** EXPERT must keep working purely from screenshots. Changes that read or
  write game memory, hook or inject into the game process, send input to the game, or automate
  gameplay will not be accepted - they put players' accounts at risk.
- **Privacy.** Never commit real screenshots with other players' names or chat, your `shots/`
  folder, `history.csv` or `app.log`. Blur names before adding a test image (see
  `tests/fixtures/sample_game.png` for an example).
- **No game assets.** Don't add sounds, images or fonts taken from MapleStory.

## Development setup

```bash
python -m venv .venv                      # Python 3.11 or 3.12
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest            # all tests must pass
.venv\Scripts\python -m pyflakes app.py maple_exp dev tests
```

With the game open in windowed mode you can run the end-to-end check, which drives the real
window and saves a screenshot of every screen to `dev/out/`:

```bash
.venv\Scripts\python dev\harness.py 0.5   # a 30-second session
```

## Pull requests

- Keep them focused - one fix or feature per PR.
- Add or update tests for behavior changes; parsing and EXP math live in pure functions
  (`maple_exp/parse.py`, `tracker.py`, `minimap.py`) that are easy to test.
- Describe how you tested it, and attach a screenshot for UI changes.

## Reporting bugs

Open an [issue](https://github.com/oryanzz/EXPERT/issues) with your Windows version, the
game's window size, what you expected and what happened. The last lines of `app.log` help a lot.
If you attach a screenshot, blur other players' names first.

By contributing you agree that your contributions are licensed under the project's
[MIT License](LICENSE).
