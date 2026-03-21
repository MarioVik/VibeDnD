"""Centralised path helpers that work both in development and in a frozen
PyInstaller bundle.

When frozen, *read-only* assets (data/*.json) live inside the temp
``sys._MEIPASS`` directory that PyInstaller unpacks.  *Mutable* files
(settings.json, characters/) are stored in a platform-appropriate user
data directory so they persist between runs and are always writable.

  Windows : %APPDATA%\\VibeDnD\\
  macOS   : ~/Library/Application Support/VibeDnD/
  Linux   : $XDG_DATA_HOME/VibeDnD/  (default ~/.local/share/VibeDnD/)
  dev     : project root (unchanged behaviour)
"""

import os
import sys


def is_frozen() -> bool:
    """Return True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def _bundle_dir() -> str:
    """Root of the bundled/unpacked assets (read-only)."""
    if is_frozen():
        return sys._MEIPASS  # type: ignore[attr-defined]
    return os.path.dirname(os.path.abspath(__file__))


def _user_data_dir() -> str:
    """Writable directory for user data (settings, saved characters).

    On macOS, writing next to the executable would target a path inside
    the .app bundle which is read-only when installed to /Applications.
    Use the canonical per-platform user-data location instead.
    """
    if sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    elif sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get(
            "XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share")
        )
    return os.path.join(base, "VibeDnD")


def _exe_dir() -> str:
    """Directory that contains the running executable (writable)."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def data_dir() -> str:
    """Path to the ``data/`` folder with parsed JSON files."""
    return os.path.join(_bundle_dir(), "data")


def settings_path() -> str:
    """Path to the mutable ``settings.json`` file."""
    if is_frozen():
        return os.path.join(_user_data_dir(), "settings.json")
    return os.path.join(_exe_dir(), "settings.json")


def characters_dir() -> str:
    """Path to the ``characters/`` directory for saved characters."""
    if is_frozen():
        return os.path.join(_user_data_dir(), "characters")
    return os.path.join(_exe_dir(), "characters")
