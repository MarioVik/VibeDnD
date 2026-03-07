"""Centralised path helpers that work both in development and in a frozen
PyInstaller bundle.

When frozen, *read-only* assets (data/*.json) live inside the temp
``sys._MEIPASS`` directory that PyInstaller unpacks.  *Mutable* files
(settings.json) are stored next to the executable so they persist
between runs.
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


def _exe_dir() -> str:
    """Directory that contains the running executable (writable)."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def data_dir() -> str:
    """Path to the ``data/`` folder with parsed JSON files."""
    return os.path.join(_bundle_dir(), "data")


def settings_path() -> str:
    """Path to the mutable ``settings.json`` file.

    When frozen the file lives next to the .exe so user preferences
    survive application restarts.
    """
    return os.path.join(_exe_dir(), "settings.json")
