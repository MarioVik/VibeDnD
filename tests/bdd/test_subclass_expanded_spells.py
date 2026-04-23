"""BDD tests for subclass expanded/patron spell lists.

Verifies that subclass spells (e.g., warlock patron spells, cleric domain
spells, paladin oath spells) appear in the character's spellbook as
always-prepared grant entries at the appropriate class levels.
"""

from __future__ import annotations

import pytest

from gui.data_loader import GameData
from models.character import Character
from models.class_level import ClassLevel
from models.spell_grant_utils import (
    get_active_spell_grant_sources,
    get_spellbook_entries,
)


@pytest.fixture(scope="module")
def game_data() -> GameData:
    return GameData()


def _find_class(game_data: GameData, slug: str) -> dict:
    for cls in game_data.classes:
        if cls["slug"] == slug:
            return cls
    raise ValueError(f"Class {slug} not found")


def _build_character(
    game_data: GameData,
    class_slug: str,
    level: int,
    subclass_slug: str | None = None,
) -> Character:
    """Build a character at the given class level with optional subclass."""
    cls = _find_class(game_data, class_slug)
    character = Character(
        name=f"Test {cls['name']}",
        character_class=cls,
    )
    levels = []
    for i in range(1, level + 1):
        cl = ClassLevel(
            class_slug=class_slug,
            class_level=i,
            hit_die=cls.get("hit_die", 8),
        )
        # Subclass typically chosen at level 3
        if subclass_slug and i == 3:
            cl.subclass_slug = subclass_slug
        levels.append(cl)
    character.class_levels = levels
    return character


def _get_subclass_source(sources: list[dict], subclass_slug: str) -> dict | None:
    """Find the subclass expanded spells source."""
    for source in sources:
        if subclass_slug in source.get("source_id", ""):
            return source
    return None


def _granted_spell_names(source: dict) -> set[str]:
    """Get the set of spell names from a source's granted entries."""
    return {e["spell_name"] for e in source.get("granted_entries", [])}


def _spellbook_spell_names(entries: list[dict]) -> set[str]:
    """Get the set of spell names from spellbook entries."""
    return {e.get("spell_name", "") for e in entries}


# ── Warlock Patron Spells ────────────────────────────────────────────


class TestWarlockPatronSpells:
    """Warlock subclass patron spells should appear at appropriate levels."""

    def test_fiend_patron_level_3_spells(self, game_data):
        """At warlock level 3, Fiend patron grants level-3 spells."""
        char = _build_character(game_data, "warlock", 3, "fiend-patron")
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "fiend-patron")
        assert source is not None, "Fiend patron spell source should exist"
        names = _granted_spell_names(source)
        assert "Burning Hands" in names
        assert "Command" in names
        assert "Scorching Ray" in names
        assert "Suggestion" in names

    def test_fiend_patron_level_5_spells(self, game_data):
        """At warlock level 5, Fiend patron also grants level-5 spells."""
        char = _build_character(game_data, "warlock", 5, "fiend-patron")
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "fiend-patron")
        assert source is not None
        names = _granted_spell_names(source)
        # Level 3 spells still present
        assert "Burning Hands" in names
        # Level 5 spells added
        assert "Fireball" in names
        assert "Stinking Cloud" in names

    def test_fiend_patron_level_9_all_spells(self, game_data):
        """At warlock level 9, all Fiend patron spells are granted."""
        char = _build_character(game_data, "warlock", 9, "fiend-patron")
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "fiend-patron")
        assert source is not None
        names = _granted_spell_names(source)
        expected = {
            "Burning Hands", "Command", "Scorching Ray", "Suggestion",
            "Fireball", "Stinking Cloud",
            "Fire Shield", "Wall of Fire",
            "Geas", "Insect Plague",
        }
        assert expected.issubset(names), f"Missing: {expected - names}"

    def test_no_spells_before_subclass(self, game_data):
        """At warlock level 2 (before subclass), no patron spells."""
        char = _build_character(game_data, "warlock", 2, None)
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "fiend-patron")
        assert source is None

    def test_archfey_patron_spells(self, game_data):
        """Archfey patron grants correct spells at level 3."""
        char = _build_character(game_data, "warlock", 3, "archfey-patron")
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "archfey-patron")
        assert source is not None
        names = _granted_spell_names(source)
        assert "Faerie Fire" in names
        assert "Sleep" in names
        assert "Calm Emotions" in names

    def test_celestial_patron_spells(self, game_data):
        """Celestial patron grants correct spells at level 3."""
        char = _build_character(game_data, "warlock", 3, "celestial-patron")
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "celestial-patron")
        assert source is not None
        names = _granted_spell_names(source)
        assert "Cure Wounds" in names
        assert "Guiding Bolt" in names

    def test_great_old_one_patron_spells(self, game_data):
        """GOO patron grants correct spells at level 3."""
        char = _build_character(game_data, "warlock", 3, "great-old-one-patron")
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "great-old-one-patron")
        assert source is not None
        names = _granted_spell_names(source)
        assert "Dissonant Whispers" in names
        assert "Detect Thoughts" in names

    def test_patron_spells_in_spellbook(self, game_data):
        """Patron spells appear in the spellbook entries."""
        char = _build_character(game_data, "warlock", 3, "fiend-patron")
        entries = get_spellbook_entries(char, game_data)
        names = _spellbook_spell_names(entries)
        assert "Burning Hands" in names
        assert "Command" in names


# ── Cleric Domain Spells ─────────────────────────────────────────────


class TestClericDomainSpells:
    """Cleric domain spells should appear at appropriate levels."""

    def test_life_domain_level_3(self, game_data):
        char = _build_character(game_data, "cleric", 3, "life-domain")
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "life-domain")
        assert source is not None
        names = _granted_spell_names(source)
        assert "Aid" in names
        assert "Bless" in names
        assert "Cure Wounds" in names
        assert "Lesser Restoration" in names

    def test_life_domain_level_5(self, game_data):
        char = _build_character(game_data, "cleric", 5, "life-domain")
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "life-domain")
        assert source is not None
        names = _granted_spell_names(source)
        assert "Mass Healing Word" in names
        assert "Revivify" in names
        # Level 3 spells still there
        assert "Aid" in names


# ── Paladin Oath Spells ──────────────────────────────────────────────


class TestPaladinOathSpells:
    """Paladin oath spells should appear at appropriate levels."""

    def test_devotion_level_3(self, game_data):
        char = _build_character(game_data, "paladin", 3, "oath-of-devotion")
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "oath-of-devotion")
        assert source is not None
        names = _granted_spell_names(source)
        assert "Protection from Evil and Good" in names
        assert "Shield of Faith" in names

    def test_devotion_level_5(self, game_data):
        char = _build_character(game_data, "paladin", 5, "oath-of-devotion")
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "oath-of-devotion")
        assert source is not None
        names = _granted_spell_names(source)
        assert "Aid" in names
        assert "Zone of Truth" in names


# ── Ranger Subclass Spells ───────────────────────────────────────────


class TestRangerSubclassSpells:
    """Ranger subclass spells should appear at appropriate levels."""

    def test_gloom_stalker_level_3(self, game_data):
        char = _build_character(game_data, "ranger", 3, "gloom-stalker")
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "gloom-stalker")
        assert source is not None
        names = _granted_spell_names(source)
        assert "Disguise Self" in names


# ── Sorcerer Subclass Spells ─────────────────────────────────────────


class TestSorcererSubclassSpells:
    """Sorcerer subclass spells should appear at appropriate levels."""

    def test_draconic_sorcery_level_3(self, game_data):
        char = _build_character(game_data, "sorcerer", 3, "draconic-sorcery")
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "draconic-sorcery")
        assert source is not None
        names = _granted_spell_names(source)
        assert "Chromatic Orb" in names
        assert "Command" in names


# ── Level Gating ─────────────────────────────────────────────────────


class TestLevelGating:
    """Expanded spells should only be granted at or above the specified level."""

    def test_no_level_5_spells_at_level_3(self, game_data):
        """Level 5 patron spells should NOT appear at warlock level 3."""
        char = _build_character(game_data, "warlock", 3, "fiend-patron")
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "fiend-patron")
        assert source is not None
        names = _granted_spell_names(source)
        assert "Fireball" not in names
        assert "Stinking Cloud" not in names

    def test_no_level_7_spells_at_level_5(self, game_data):
        """Level 7 patron spells should NOT appear at warlock level 5."""
        char = _build_character(game_data, "warlock", 5, "fiend-patron")
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "fiend-patron")
        assert source is not None
        names = _granted_spell_names(source)
        assert "Fire Shield" not in names
        assert "Wall of Fire" not in names

    def test_progressive_unlock(self, game_data):
        """Each level threshold unlocks additional spells."""
        for level, expected_new in [
            (3, {"Burning Hands", "Command", "Scorching Ray", "Suggestion"}),
            (5, {"Fireball", "Stinking Cloud"}),
            (7, {"Fire Shield", "Wall of Fire"}),
            (9, {"Geas", "Insect Plague"}),
        ]:
            char = _build_character(game_data, "warlock", level, "fiend-patron")
            sources = get_active_spell_grant_sources(char, game_data)
            source = _get_subclass_source(sources, "fiend-patron")
            names = _granted_spell_names(source)
            assert expected_new.issubset(names), (
                f"At level {level}, missing: {expected_new - names}"
            )


# ── Source Label ─────────────────────────────────────────────────────


class TestSourceLabeling:
    """Expanded spell sources should have descriptive labels."""

    def test_source_label_contains_subclass_name(self, game_data):
        char = _build_character(game_data, "warlock", 3, "fiend-patron")
        sources = get_active_spell_grant_sources(char, game_data)
        source = _get_subclass_source(sources, "fiend-patron")
        assert source is not None
        assert "Fiend" in source["source_label"]
        assert "Spells" in source["source_label"]
