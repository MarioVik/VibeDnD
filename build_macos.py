#!/usr/bin/env python3
"""Build a distributable macOS DMG for VibeDnD.

This script must be run on macOS. It builds a native .app with PyInstaller
and wraps it into a single .dmg file suitable for non-technical users.
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
DMG_STAGING = BUILD / "dmg-root"
DMG_OUT_DIR = DIST / "installer-mac"
DMG_NAME = "VibeDnD-Installer-macOS.dmg"
APP_NAME = "VibeDnD.app"
ICON_PNG = ROOT / "icon-source.png"
ICON_ICNS = ROOT / "vibednd.icns"

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

COLLECT_ALL = [
    "gui",
    "models",
    "export",
]


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=cwd or ROOT)
    if result.returncode != 0:
        sys.exit(result.returncode)


def check_prereqs() -> None:
    if platform.system() != "Darwin":
        sys.exit("ERROR: build_macos.py must be run on macOS.")

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

    for tool in ("hdiutil", "sips", "iconutil", "codesign"):
        if shutil.which(tool) is None:
            sys.exit(f"ERROR: Required macOS tool not found: {tool}")


def maybe_make_icns() -> Path | None:
    if ICON_ICNS.exists():
        return ICON_ICNS

    if not ICON_PNG.exists():
        print(f"WARNING: {ICON_PNG} not found. Building without custom app icon.")
        return None

    iconset_dir = BUILD / "vibednd.iconset"
    normalized_png = BUILD / "icon-source-normalized.png"
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir(parents=True, exist_ok=True)

    # Normalize source image to a real PNG first. In CI the source file can be
    # a JPEG with a .png suffix, which makes iconutil reject the iconset.
    run(["sips", "-s", "format", "png", str(ICON_PNG), "--out", str(normalized_png)])

    base_sizes = [16, 32, 128, 256, 512]
    for s in base_sizes:
        out_1x = iconset_dir / f"icon_{s}x{s}.png"
        out_2x = iconset_dir / f"icon_{s}x{s}@2x.png"
        run(["sips", "-z", str(s), str(s), str(normalized_png), "--out", str(out_1x)])
        run(["sips", "-z", str(s * 2), str(s * 2), str(normalized_png), "--out", str(out_2x)])

    run(["iconutil", "-c", "icns", str(iconset_dir), "-o", str(ICON_ICNS)])
    shutil.rmtree(iconset_dir, ignore_errors=True)
    if normalized_png.exists():
        normalized_png.unlink()
    print(f"Created icon: {ICON_ICNS}")
    return ICON_ICNS


def build_app(icon_path: Path | None) -> Path:
    sep = ":"
    add_data: list[str] = []
    for f in DATA_FILES:
        src = ROOT / f
        add_data += ["--add-data", f"{src}{sep}data"]

    exclude_flags: list[str] = []
    for mod in EXCLUDES:
        exclude_flags += ["--exclude-module", mod]

    collect_flags: list[str] = []
    for pkg in COLLECT_ALL:
        collect_flags += ["--collect-all", pkg]

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "VibeDnD",
        "--windowed",
        "--onedir",
        "--osx-bundle-identifier",
        "com.vibednd.app",
    ]

    if icon_path is not None:
        cmd += ["--icon", str(icon_path)]

    cmd += add_data + exclude_flags + collect_flags + [str(ROOT / "main.py")]
    run(cmd)

    app_path = DIST / APP_NAME
    if not app_path.exists():
        sys.exit(f"ERROR: Expected app bundle not found: {app_path}")
    return app_path


def sign_app(app_path: Path) -> None:
    """Ad-hoc sign the app bundle.

    Without any signature, macOS Gatekeeper silently blocks apps downloaded
    from the internet (especially on Apple Silicon). An ad-hoc signature
    (-) is not a Developer ID signature and will not pass notarization, but
    it is enough for Gatekeeper to allow the app to run when the user
    right-clicks → Open (or after approving it in System Settings → Privacy
    & Security).  It also prevents the completely-silent-nothing-happens
    failure that occurs with a fully unsigned bundle on modern macOS.
    """
    print("Ad-hoc signing app bundle...")
    run(
        [
            "codesign",
            "--force",
            "--deep",
            "--sign",
            "-",
            str(app_path),
        ]
    )


def create_dmg(app_path: Path) -> Path:
    DMG_OUT_DIR.mkdir(parents=True, exist_ok=True)
    if DMG_STAGING.exists():
        shutil.rmtree(DMG_STAGING)
    DMG_STAGING.mkdir(parents=True, exist_ok=True)

    staged_app = DMG_STAGING / APP_NAME
    # Use ditto instead of shutil.copytree: ditto preserves symlinks, resource
    # forks, and extended attributes.  shutil.copytree(symlinks=False) follows
    # symlinks and turns them into regular files, which invalidates the
    # code-signature that was just applied (codesign hashes the bundle layout
    # including symlink targets), causing macOS to silently kill the app at
    # launch even after the user approves the Gatekeeper dialog.
    run(["ditto", str(app_path), str(staged_app)])

    apps_link = DMG_STAGING / "Applications"
    if apps_link.exists() or apps_link.is_symlink():
        apps_link.unlink()
    os.symlink("/Applications", apps_link)

    dmg_path = DMG_OUT_DIR / DMG_NAME
    if dmg_path.exists():
        dmg_path.unlink()

    run(
        [
            "hdiutil",
            "create",
            "-volname",
            "VibeDnD Installer",
            "-srcfolder",
            str(DMG_STAGING),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_path),
        ]
    )

    # Ad-hoc sign the DMG container so Gatekeeper doesn't flag the disk image
    # itself as unsigned (separate from the app bundle signature inside it).
    print("Ad-hoc signing DMG...")
    run(["codesign", "--force", "--sign", "-", str(dmg_path)])

    return dmg_path


def main() -> None:
    check_prereqs()
    icon_path = maybe_make_icns()
    app_path = build_app(icon_path)
    sign_app(app_path)
    dmg_path = create_dmg(app_path)
    print()
    print(f"Done. Send this file to Mac users: {dmg_path}")


if __name__ == "__main__":
    main()
