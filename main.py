"""D&D 2024 Character Creator - Entry Point."""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paths import data_dir, characters_dir, is_frozen
from gui.app import CharacterCreatorApp


def main():
    # Check that parsed data exists
    dd = data_dir()
    required_files = [
        "spells.json",
        "classes.json",
        "species.json",
        "backgrounds.json",
        "feats.json",
        "class_progressions.json",
        "subclasses.json",
        "items.json",
    ]

    missing = [f for f in required_files if not os.path.exists(os.path.join(dd, f))]
    if missing and not is_frozen():
        print("Parsed data files missing. Running parsers first...")
        from parsers.run_all_parsers import main as run_parsers
        run_parsers()
        print()
    elif missing:
        print(f"ERROR: Data files missing from {dd}: {missing}")
        sys.exit(1)

    # Ensure characters directory exists
    os.makedirs(characters_dir(), exist_ok=True)

    app = CharacterCreatorApp()
    app.run()


if __name__ == "__main__":
    main()
