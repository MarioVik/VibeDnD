"""Entry point: `python -m tui` from the VibeDnD repo root."""
import sys

from .app import run

if __name__ == "__main__":
    run(demo="--demo" in sys.argv)
