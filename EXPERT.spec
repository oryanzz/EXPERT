# PyInstaller spec for the single-file EXPERT.exe.
# Build with build_exe.bat (locally) or the "Release exe" GitHub workflow.
import re
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo, StringStruct, StringTable,
                                                 VarFileInfo, VarStruct, VSVersionInfo)

version = re.search(r'__version__ = "([\d.]+)"', Path("maple_exp/__init__.py").read_text()).group(1)
numbers = tuple(int(n) for n in version.split(".")) + (0,)

datas = [
    ("ui", "ui"),
    ("sounds/default.wav", "sounds"),
    ("scripts/update_exe.ps1", "scripts"),   # copied out by the app to run the self-update
    ("LICENSE", "."),
    ("THIRD_PARTY_LICENSES.txt", "."),
]
datas += collect_data_files("rapidocr_onnxruntime")  # OCR models + config.yaml

a = Analysis(
    ["app.py"],
    datas=datas,
    excludes=["tkinter", "unittest", "pytest", "IPython", "matplotlib", "pydoc_data"],
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="EXPERT",
    icon="ui/icon.ico",
    console=False,
    upx=False,
    version=VSVersionInfo(
        ffi=FixedFileInfo(filevers=numbers, prodvers=numbers),
        kids=[
            StringFileInfo([StringTable("040904B0", [
                StringStruct("CompanyName", "ORYANZ"),
                StringStruct("FileDescription", "EXPERT - EXP PER TIME"),
                StringStruct("FileVersion", version),
                StringStruct("InternalName", "EXPERT"),
                StringStruct("LegalCopyright", "Copyright (c) 2026 ORYANZ - MIT License"),
                StringStruct("OriginalFilename", "EXPERT.exe"),
                StringStruct("ProductName", "EXPERT"),
                StringStruct("ProductVersion", version),
            ])]),
            VarFileInfo([VarStruct("Translation", [1033, 1200])]),
        ],
    ),
)
