"""Load parsed game data from JSON files."""

import json
import os

from gui.source_config import load_settings
from paths import data_dir

DATA_DIR = data_dir()


class GameData:
    """Container for all parsed game data."""

    def __init__(self):
        self.spells = self._load("spells.json")
        self.classes = self._load("classes.json")
        self.species = self._load("species.json")
        self.backgrounds = self._load("backgrounds.json")
        self.feats = self._load("feats.json")

        # Source filter settings (mutable, shared with steps)
        self.source_filters = load_settings()

        # Build lookup indexes
        self.classes_by_name = {c["name"]: c for c in self.classes}
        self.species_by_name = {s["name"]: s for s in self.species}
        self.backgrounds_by_name = {b["name"]: b for b in self.backgrounds}
        self.feats_by_name = {f["name"]: f for f in self.feats}

        # Group by source
        self.classes_by_source = self._group_by_source(self.classes)
        self.species_by_source = self._group_by_source(self.species)
        self.backgrounds_by_source = self._group_by_source(self.backgrounds)
        self.feats_by_category = {}
        for f in self.feats:
            cat = f.get("category", "general")
            self.feats_by_category.setdefault(cat, []).append(f)

    def _load(self, filename: str) -> list[dict]:
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            print(f"WARNING: {path} not found. Run parsers first.")
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _group_by_source(self, items: list[dict]) -> dict[str, list[dict]]:
        groups = {}
        for item in items:
            source = item.get("source", "Unknown")
            groups.setdefault(source, []).append(item)
        return groups

    def spells_for_class(self, class_name: str, max_level: int = 1) -> list[dict]:
        """Get spells available to a class up to a given level."""
        return [
            s for s in self.spells
            if class_name in s.get("classes", []) and s.get("level", 99) <= max_level
        ]

    def cantrips_for_class(self, class_name: str) -> list[dict]:
        """Get cantrips available to a class."""
        return [
            s for s in self.spells
            if class_name in s.get("classes", []) and s.get("level", 99) == 0
        ]

    def find_feat(self, name: str) -> dict | None:
        """Find a feat by name, handling parenthetical variants like 'Magic Initiate (Cleric)'."""
        # Exact match
        if name in self.feats_by_name:
            return self.feats_by_name[name]
        # Try base name without parenthetical
        base = name.split("(")[0].strip()
        if base in self.feats_by_name:
            return self.feats_by_name[base]
        # Case-insensitive search
        for fname, feat in self.feats_by_name.items():
            if fname.lower() == name.lower() or fname.lower() == base.lower():
                return feat
        return None
