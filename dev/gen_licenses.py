"""Write THIRD_PARTY_LICENSES.txt: the license texts of every package bundled into EXPERT.exe.

Run after changing requirements.txt:  .venv\\Scripts\\python dev\\gen_licenses.py
"""
import re
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOP_LEVEL = [re.split(r"[<>=!~; ]", line.strip())[0]
             for line in (ROOT / "requirements.txt").read_text().splitlines()
             if line.strip() and not line.startswith("#")]


def canon(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def runtime_closure(names):
    """Every distribution the app needs at runtime (Windows, no extras)."""
    seen, todo = {}, list(names)
    while todo:
        name = canon(todo.pop())
        if name in seen:
            continue
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        seen[name] = dist
        for req in dist.requires or []:
            req_name, _, marker = req.partition(";")
            if "extra" in marker:
                continue
            if marker and ("sys_platform" in marker or "platform_system" in marker or "os_name" in marker):
                if not any(w in marker for w in ('"win32"', "'win32'", '"Windows"', "'Windows'", '"nt"', "'nt'")):
                    continue
            todo.append(re.split(r"[<>=!~\[ (]", req_name.strip())[0])
    return seen


# Packages whose wheels ship no license file: what their license is and where the full text is.
FALLBACK = {
    "flatbuffers": "Apache License 2.0 (Copyright Google Inc.). The full Apache 2.0 text is in this file, "
                   "under 'packaging' (LICENSE.APACHE). https://github.com/google/flatbuffers",
    "rapidocr-onnxruntime": "Apache License 2.0 (Copyright RapidAI). The full Apache 2.0 text is in this "
                            "file, under 'packaging' (LICENSE.APACHE). https://github.com/RapidAI/RapidOCR",
    "proxy-tools": "MIT License. https://github.com/jtushman/proxy_tools",
}


def license_texts(dist):
    """License/notice files from the dist-info folder, or from the top level of the package itself."""
    pattern = r"^(LICEN[CS]E|COPYING|NOTICE|AUTHORS|ThirdPartyNotices)"
    files = [f for f in dist.files or [] if re.search(pattern, f.name, re.I)
             and (".dist-info" in str(f) or len(f.parts) == 2)]
    return [(f.name, Path(f.locate()).read_text(encoding="utf-8", errors="replace")) for f in files]


def main():
    out = ["THIRD-PARTY LICENSES",
           "",
           "EXPERT.exe bundles the open-source packages below (and the PyInstaller bootloader, licensed",
           "GPL-2.0-or-later with an exception that allows distributing bundled programs under any",
           "license). Their license texts follow. EXPERT itself is MIT licensed - see LICENSE.",
           ""]
    for name, dist in sorted(runtime_closure(TOP_LEVEL).items()):
        meta = dist.metadata
        lic = meta.get("License-Expression") or meta.get("License") or ""
        lic = lic if len(lic) < 80 else lic.splitlines()[0][:80]
        out += ["=" * 78, f"{meta['Name']} {dist.version}" + (f"  ({lic})" if lic else ""),
                meta.get("Home-page") or "", "=" * 78]
        texts = license_texts(dist)
        if not texts:
            out.append(FALLBACK.get(name, "(no license file shipped with the package - see the project page above)"))
        for fname, text in texts:
            out += [f"--- {fname} ---", text.rstrip(), ""]
        out.append("")
    (ROOT / "THIRD_PARTY_LICENSES.txt").write_text("\n".join(out), encoding="utf-8")
    print("wrote THIRD_PARTY_LICENSES.txt for", len(runtime_closure(TOP_LEVEL)), "packages")


if __name__ == "__main__":
    main()
