#!/usr/bin/env python3
"""Build a single-file Ubuntu installer (.deb) for VibeDnD.

Run this script on Ubuntu (or Debian-based Linux) to produce one .deb file
that non-technical users can install by double-clicking.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
PKG_ROOT = BUILD / "deb-root"
DEBIAN_DIR = PKG_ROOT / "DEBIAN"
APP_DIR = PKG_ROOT / "opt" / "vibednd"
BIN_DIR = PKG_ROOT / "usr" / "bin"
DESKTOP_DIR = PKG_ROOT / "usr" / "share" / "applications"
ICON_DIR = PKG_ROOT / "usr" / "share" / "icons" / "hicolor" / "256x256" / "apps"
OUT_DIR = DIST / "installer-linux"

PACKAGE_NAME = "vibednd"
PACKAGE_VERSION = "0.1.0"
APP_EXECUTABLE_NAME = "VibeDnD"

ICON_PNG = ROOT / "icon-source.png"

DATA_FILES = [
    "data/spells.json",
    "data/classes.json",
    "data/species.json",
    "data/backgrounds.json",
    "data/feats.json",
    "data/class_progressions.json",
    "data/subclasses.json",
    "data/items.json",
]

EXCLUDES = [
    "dnd2024_scraper",
    "parsers",
    "bs4",
    "beautifulsoup4",
    "requests",
    "urllib3",
    "certifi",
    "charset_normalizer",
    "idna",
    "soupsieve",
]

COLLECT_SUBMODULES = [
    "gui",
]


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd or ROOT)
    if result.returncode != 0:
        sys.exit(result.returncode)


def check_prereqs() -> None:
    if platform.system() != "Linux":
        sys.exit("ERROR: build_ubuntu.py must be run on Ubuntu/Linux.")

    missing = [f for f in DATA_FILES if not (ROOT / f).exists()]
    if missing:
        sys.exit(
            "ERROR: Missing data files:\n"
            + "\n".join(f"  - {m}" for m in missing)
            + "\nRun parsers first."
        )

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        sys.exit("ERROR: PyInstaller not installed. Install with: pip install pyinstaller")

    if shutil.which("dpkg-deb") is None:
        sys.exit("ERROR: dpkg-deb not found. Install with: sudo apt install dpkg-dev")


def deb_arch() -> str:
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        return "amd64"
    if machine in {"aarch64", "arm64"}:
        return "arm64"
    return machine


def build_app() -> Path:
    sep = ":"
    add_data: list[str] = []
    for f in DATA_FILES:
        src = ROOT / f
        add_data += ["--add-data", f"{src}{sep}data"]

    exclude_flags: list[str] = []
    for mod in EXCLUDES:
        exclude_flags += ["--exclude-module", mod]

    collect_flags: list[str] = []
    for pkg in COLLECT_SUBMODULES:
        collect_flags += ["--collect-submodules", pkg]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        APP_EXECUTABLE_NAME,
        "--windowed",
        "--onedir",
    ]

    if ICON_PNG.exists():
        cmd += ["--icon", str(ICON_PNG)]
    else:
        print(f"WARNING: {ICON_PNG} not found. Building without custom icon.")

    cmd += add_data + exclude_flags + collect_flags + [str(ROOT / "main.py")]
    run(cmd)

    app_dist = DIST / APP_EXECUTABLE_NAME
    if not app_dist.exists():
        sys.exit(f"ERROR: Expected PyInstaller output missing: {app_dist}")
    return app_dist


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_launcher() -> None:
    launcher_path = BIN_DIR / "vibednd"
    launcher = "#!/bin/sh\nexec /opt/vibednd/VibeDnD \"$@\"\n"
    _write_text(launcher_path, launcher)
    launcher_path.chmod(0o755)


def _make_desktop_entry() -> None:
    desktop_path = DESKTOP_DIR / "vibednd.desktop"
    desktop = """[Desktop Entry]
Type=Application
Name=VibeDnD
Comment=D&D 2024 Character Creator
Exec=/usr/bin/vibednd
Icon=vibednd
Terminal=false
Categories=Game;Utility;
"""
    _write_text(desktop_path, desktop)


def _copy_icon() -> None:
    if ICON_PNG.exists():
        ICON_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ICON_PNG, ICON_DIR / "vibednd.png")


def _installed_size_kb() -> int:
    result = subprocess.run(
        ["du", "-sk", str(PKG_ROOT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return 0
    first = result.stdout.strip().split()[0]
    try:
        return int(first)
    except (ValueError, IndexError):
        return 0


def _make_control_file() -> None:
    DEBIAN_DIR.mkdir(parents=True, exist_ok=True)
    control_path = DEBIAN_DIR / "control"
    control = "\n".join(
        [
            f"Package: {PACKAGE_NAME}",
            f"Version: {PACKAGE_VERSION}",
            "Section: games",
            "Priority: optional",
            f"Architecture: {deb_arch()}",
            "Maintainer: VibeDnD",
            f"Installed-Size: {_installed_size_kb()}",
            "Depends: libc6, libx11-6, libxext6, libxrender1, libfontconfig1",
            "Description: VibeDnD D&D 2024 Character Creator",
            "",
        ]
    )
    _write_text(control_path, control)


def create_deb(app_dist: Path) -> Path:
    if PKG_ROOT.exists():
        shutil.rmtree(PKG_ROOT)
    PKG_ROOT.mkdir(parents=True, exist_ok=True)

    APP_DIR.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(app_dist, APP_DIR)

    _make_launcher()
    _make_desktop_entry()
    _copy_icon()
    _make_control_file()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_deb = OUT_DIR / f"VibeDnD-Installer-Ubuntu-{deb_arch()}.deb"
    if out_deb.exists():
        out_deb.unlink()

    run(["dpkg-deb", "--build", "--root-owner-group", str(PKG_ROOT), str(out_deb)])
    return out_deb


def main() -> None:
    check_prereqs()
    app_dist = build_app()
    deb_path = create_deb(app_dist)
    print()
    print(f"Done. Send this file to Ubuntu users: {deb_path}")


if __name__ == "__main__":
    main()
