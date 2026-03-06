"""D&D 2024 Character Creator - Entry Point."""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gui.app import CharacterCreatorApp


def main():
    # Check that parsed data exists
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    required_files = ["spells.json", "classes.json", "species.json", "backgrounds.json", "feats.json"]

    missing = [f for f in required_files if not os.path.exists(os.path.join(data_dir, f))]
    if missing:
        print("Parsed data files missing. Running parsers first...")
        from parsers.run_all_parsers import main as run_parsers
        run_parsers()
        print()

    app = CharacterCreatorApp()
    app.run()


if __name__ == "__main__":
    main()
