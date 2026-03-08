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
        self.class_progressions = self._load("class_progressions.json")
        self.subclasses = self._load("subclasses.json")

        # Source filter settings (mutable, shared with steps)
        self.source_filters = load_settings()

        # Build lookup indexes
        self.classes_by_name = {c["name"]: c for c in self.classes}
        self.species_by_name = {s["name"]: s for s in self.species}
        self.backgrounds_by_name = {b["name"]: b for b in self.backgrounds}
        self.feats_by_name = {f["name"]: f for f in self.feats}
        self.progressions_by_slug = {p["slug"]: p for p in self.class_progressions}

        # Group subclasses by class
        self.subclasses_by_class = {}
        for sc in self.subclasses:
            cls = sc.get("class_slug", "")
            self.subclasses_by_class.setdefault(cls, []).append(sc)

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

    def get_progression(self, class_slug: str) -> dict | None:
        """Get the full 1-20 level progression for a class."""
        return self.progressions_by_slug.get(class_slug)

    def get_level_data(self, class_slug: str, level: int) -> dict | None:
        """Get data for a specific class level."""
        prog = self.get_progression(class_slug)
        if not prog:
            return None
        for lvl_data in prog["levels"]:
            if lvl_data.get("level") == level:
                return lvl_data
        return None

    def get_subclasses_for_class(self, class_slug: str) -> list[dict]:
        """Get all available subclasses for a class."""
        return self.subclasses_by_class.get(class_slug, [])

    def get_subclass(self, class_slug: str, subclass_slug: str) -> dict | None:
        """Get a specific subclass by class and subclass slug."""
        for sc in self.get_subclasses_for_class(class_slug):
            if sc["slug"] == subclass_slug:
                return sc
        return None

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
