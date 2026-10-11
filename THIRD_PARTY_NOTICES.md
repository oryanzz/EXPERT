# Third-party notices

EXPERT itself is released under the [MIT License](LICENSE). It relies on the
open-source projects below, each under its own license. The source repository
doesn't include them (they come from PyPI / Google Fonts), but **`EXPERT.exe`
bundles them**: the full license texts of every bundled package are in
[THIRD_PARTY_LICENSES.txt](THIRD_PARTY_LICENSES.txt), which also ships inside the
exe and with every release. `EXPERT.exe` is built with
[PyInstaller](https://pyinstaller.org), whose bootloader is GPL-2.0-or-later with
an exception that allows distributing bundled programs under any license.

## Python packages

| Package | Used for | License |
|---|---|---|
| [pywebview](https://github.com/r0x0r/pywebview) | The app window (Microsoft Edge WebView2) | BSD 3-Clause |
| [RapidOCR](https://github.com/RapidAI/RapidOCR) (`rapidocr_onnxruntime`) | Reading the EXP bar and minimap text | Apache 2.0 |
| [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) models (shipped inside RapidOCR) | The OCR models | Apache 2.0 |
| [ONNX Runtime](https://github.com/microsoft/onnxruntime) | Running the OCR models | MIT |
| [OpenCV](https://github.com/opencv/opencv-python) (`opencv-python`) | Image processing for OCR | Apache 2.0 |
| [Pillow](https://github.com/python-pillow/Pillow) | Screenshots and image handling | MIT-CMU (HPND) |
| [NumPy](https://github.com/numpy/numpy) | Image arrays | BSD 3-Clause |
| [pythonnet](https://github.com/pythonnet/pythonnet) | Windows UI bridge used by pywebview | MIT |
| [Bottle](https://github.com/bottlepy/bottle) | Local file server used by pywebview | MIT |

Development only: [pytest](https://github.com/pytest-dev/pytest) (MIT),
[pyflakes](https://github.com/PyCQA/pyflakes) (MIT).

## Fonts

Loaded at runtime from Google Fonts, all under the
[SIL Open Font License 1.1](https://openfontlicense.org/):
[Fredoka](https://fonts.google.com/specimen/Fredoka),
[Nunito](https://fonts.google.com/specimen/Nunito),
[Rubik](https://fonts.google.com/specimen/Rubik).

## Original assets

The logo, the stopwatch icon (`ui/icon.ico`) and the end-of-timer chime
(`sounds/default.wav`, synthesized by `dev/make_sounds.py`) were made for this
project and are covered by its MIT License. EXPERT ships no assets from
MapleStory.

## Trademarks

MapleStory is a registered trademark of NEXON Korea Corporation. EXPERT is an
independent fan project and is not affiliated with, endorsed by, or sponsored by
NEXON. Game screenshots in the documentation are used only to illustrate how the
tool works.
