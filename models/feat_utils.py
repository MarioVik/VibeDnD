"""Feat-related helpers shared across the app.

This module is GUI-free and safe to import from models, GUI steps, and exporters.
"""

from __future__ import annotations

from typing import Set


def _clean_name(value) -> str:
    text = str(value or "").strip()
    return text


def get_owned_feat_names(character) -> Set[str]:
    """Return a set of normalized feat names already owned by the character.

    The set contains lowercased (casefolded) names so callers can compare
    against feat names in a case-insensitive way.
    """
    owned: set[str] = set()

    # Background feat stored as a feat dict on the character.
    background_feat = getattr(character, "feat", None) or {}
    bg_name = _clean_name(background_feat.get("name"))
    if not bg_name:
        # Fallback to raw background config if present.
        background = getattr(character, "background", None) or {}
        bg_name = _clean_name(background.get("feat"))
    if bg_name:
        owned.add(bg_name.casefold())

    # Species origin feat (e.g., Human extra origin feat).
    species_feat = getattr(character, "species_origin_feat", None) or {}
    sp_name = _clean_name(species_feat.get("name"))
    if sp_name:
        owned.add(sp_name.casefold())

    # Warlock Lessons of the First Ones origin feat choice.
    level1_choices = getattr(character, "level1_class_choices", {}) or {}
    lessons_name = _clean_name(level1_choices.get("warlock_lessons_feat"))
    if lessons_name:
        owned.add(lessons_name.casefold())

    return owned

