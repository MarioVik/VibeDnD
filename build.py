#!/usr/bin/env python
"""Cross-platform build script for VibeDnD.

Usage
-----
    python build.py            # default onedir build
    python build.py --onefile  # single-file executable

Requirements
------------
    pip install pyinstaller fpdf2

The script works on Windows, macOS and Linux.  Run it on each target
platform to produce a native executable (PyInstaller does not
cross-compile).
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
BUILD = os.path.join(ROOT, "build")
ICON_FILE = os.path.join(ROOT, "vibednd.ico")

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

# Modules only needed for scraping / parsing, not at runtime
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

# PyInstaller can occasionally miss package submodules in CI builds.
# Collecting the whole gui package avoids runtime ModuleNotFound errors.
COLLECT_SUBMODULES = [
    "gui",
]


def check_prerequisites():
    """Make sure data files and PyInstaller are available."""
    missing = [f for f in DATA_FILES if not os.path.exists(os.path.join(ROOT, f))]
    if missing:
        sys.exit(f"ERROR: Missing data files: {missing}\n"
                 f"Run the parsers first:  python parsers/run_all_parsers.py")

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        sys.exit("ERROR: PyInstaller is not installed.\n"
                 "Install it:  pip install pyinstaller")


def build(onefile: bool = False):
    """Run the PyInstaller build."""
    check_prerequisites()

    # Build the --add-data flags (separator is ; on Windows, : elsewhere)
    sep = ";" if platform.system() == "Windows" else ":"
    add_data = []
    for f in DATA_FILES:
        src = os.path.join(ROOT, f)
        add_data += ["--add-data", f"{src}{sep}data"]

    exclude_flags = []
    for mod in EXCLUDES:
        exclude_flags += ["--exclude-module", mod]

    collect_flags = []
    for pkg in COLLECT_SUBMODULES:
        collect_flags += ["--collect-submodules", pkg]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name", "VibeDnD",
        "--windowed",          # no console window
    ]

    if os.path.exists(ICON_FILE):
        cmd += ["--icon", ICON_FILE]
    else:
        print(f"WARNING: Icon file not found, building without icon: {ICON_FILE}")

    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    cmd += add_data + exclude_flags + collect_flags
    cmd.append(os.path.join(ROOT, "main.py"))

    print(f"{'='*60}")
    print(f"  Building VibeDnD for {platform.system()} ({platform.machine()})")
    print(f"  Mode: {'single file' if onefile else 'directory bundle'}")
    print(f"  Python: {sys.version}")
    print(f"{'='*60}")
    print()
    print("Running:", " ".join(cmd))
    print()

    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        sys.exit(f"Build failed with exit code {result.returncode}")

    # Report output location
    if onefile:
        if platform.system() == "Windows":
            exe = os.path.join(DIST, "VibeDnD.exe")
        elif platform.system() == "Darwin":
            exe = os.path.join(DIST, "VibeDnD")
        else:
            exe = os.path.join(DIST, "VibeDnD")
        print(f"\nBuild complete!  Executable: {exe}")
    else:
        bundle = os.path.join(DIST, "VibeDnD")
        print(f"\nBuild complete!  Bundle directory: {bundle}")
        if platform.system() == "Windows":
            print(f"  Run with: {os.path.join(bundle, 'VibeDnD.exe')}")
        else:
            print(f"  Run with: {os.path.join(bundle, 'VibeDnD')}")


def main():
    parser = argparse.ArgumentParser(description="Build VibeDnD executable")
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Create a single-file executable (slower startup, easier to distribute)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove build/ and dist/ directories before building",
    )
    args = parser.parse_args()

    if args.clean:
        for d in (BUILD, DIST):
            if os.path.exists(d):
                print(f"Removing {d}")
                shutil.rmtree(d, ignore_errors=True)

    build(onefile=args.onefile)


if __name__ == "__main__":
    main()
