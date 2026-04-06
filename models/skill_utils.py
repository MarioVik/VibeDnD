"""D&D 2024 skill proficiency and expertise helpers.

This module is GUI-free and can be imported from anywhere (wizard steps,
character viewer, exporters, rest dialog, etc.).
"""

from __future__ import annotations

from models.enums import ALL_SKILLS

ZHENTARIM_TACTICS = "Zhentarim Tactics"
BOON_OF_TERROR = "Boon Of Terror"

_FEAT_EXPERTISE_KEY = "expertise_skill"
_SKILL_ORDER = {skill.display_name: idx for idx, skill in enumerate(ALL_SKILLS)}


def _skill_sort_key(skill_name: str) -> tuple[int, str]:
    return (_SKILL_ORDER.get(skill_name, len(_SKILL_ORDER)), skill_name.casefold())


def _sorted_skill_names(names) -> list[str]:
    return sorted({name for name in names if name}, key=_skill_sort_key)


def _append_unique_label(labels: list[str], seen: set[str], label: str):
    if label and label not in seen:
        labels.append(label)
        seen.add(label)


def _append_unique_source(
    entries: list[tuple[str, str]],
    seen: set[tuple[str, str]],
    skill_name: str,
    source_label: str,
):
    key = (skill_name, source_label)
    if skill_name and source_label and key not in seen:
        entries.append(key)
        seen.add(key)


def _iter_character_feats(character):
    feat_slots = [
        ("Background Feat", getattr(character, "feat", None)),
        ("Species Feat", getattr(character, "species_origin_feat", None)),
    ]
    for slot_label, feat in feat_slots:
        name = str((feat or {}).get("name", "") or "").strip()
        if name:
            yield slot_label, name


def get_feat_expertise_skill(character, feat_name: str) -> str | None:
    """Return the stored expertise skill for a feat, if present."""
    raw = (getattr(character, "feat_sub_choices", {}) or {}).get(feat_name)
    if isinstance(raw, dict):
        value = raw.get(_FEAT_EXPERTISE_KEY) or raw.get("skill") or raw.get("choice")
    elif isinstance(raw, str):
        value = raw
    else:
        value = None
    value = str(value).strip() if value else ""
    return value or None


def set_feat_expertise_skill(character, feat_name: str, skill_name: str | None):
    """Persist a feat-granted expertise skill using feat_sub_choices."""
    if not isinstance(character.feat_sub_choices, dict):
        character.feat_sub_choices = {}

    skill_name = str(skill_name).strip() if skill_name else ""
    current = character.feat_sub_choices.get(feat_name)

    if not skill_name:
        if isinstance(current, dict):
            updated = dict(current)
            updated.pop(_FEAT_EXPERTISE_KEY, None)
            if updated:
                character.feat_sub_choices[feat_name] = updated
            else:
                character.feat_sub_choices.pop(feat_name, None)
        else:
            character.feat_sub_choices.pop(feat_name, None)
        return

    updated = dict(current) if isinstance(current, dict) else {}
    updated[_FEAT_EXPERTISE_KEY] = skill_name
    character.feat_sub_choices[feat_name] = updated


def get_skill_proficiency_sources(character) -> list[tuple[str, str]]:
    """Return automatic skill proficiencies with their source labels."""
    entries: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    if character.background:
        bg_name = character.background.get("name", "Background")
        for skill in character.background.get("skill_proficiencies", []):
            _append_unique_source(entries, seen, skill, f"Background - {bg_name}")

    for cl in character.class_levels:
        for skill in cl.new_proficiencies:
            _append_unique_source(
                entries,
                seen,
                skill,
                f"Level {cl.class_level} Feature",
            )

    for feat_slot, feat_name in _iter_character_feats(character):
        if feat_name == BOON_OF_TERROR:
            source = f"{feat_slot} - {feat_name}"
            _append_unique_source(entries, seen, "Intimidation", source)

    return entries


def get_auto_skill_expertise_sources(character) -> list[tuple[str, str]]:
    """Return automatically granted skill expertise with source labels."""
    entries: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for feat_slot, feat_name in _iter_character_feats(character):
        if feat_name == BOON_OF_TERROR:
            source = f"{feat_slot} - {feat_name}"
            _append_unique_source(entries, seen, "Intimidation", source)

    return entries


def get_all_skill_proficiency_names(character) -> set[str]:
    """Return all skill proficiencies currently granted to the character."""
    proficiencies = set(getattr(character, "selected_skills", []) or [])
    proficiencies.update(skill for skill, _ in get_skill_proficiency_sources(character))
    return proficiencies


def _raw_selectable_expertise_grants(character) -> list[dict]:
    grants: list[dict] = []

    for class_level_index, cl in enumerate(character.class_levels):
        if cl.class_slug == "rogue" and cl.class_level == 1:
            grants.append(
                {
                    "id": f"class-level-{class_level_index}-rogue-expertise",
                    "kind": "class_level",
                    "class_level_index": class_level_index,
                    "label": "Rogue",
                    "count": 2,
                    "temporary": False,
                    "selections": [skill for skill in cl.new_expertise if skill],
                }
            )

    seen_feats: set[str] = set()
    for feat_slot, feat_name in _iter_character_feats(character):
        if feat_name != ZHENTARIM_TACTICS or feat_name in seen_feats:
            continue
        seen_feats.add(feat_name)
        stored = get_feat_expertise_skill(character, feat_name)
        grants.append(
            {
                "id": f"feat-{feat_name.casefold().replace(' ', '-')}-expertise",
                "kind": "feat",
                "feat_name": feat_name,
                "label": f"{feat_slot} - {feat_name}",
                "count": 1,
                "temporary": True,
                "selections": [stored] if stored else [],
            }
        )

    return grants


def _store_grant_selections(character, grant: dict, selections: list[str]) -> bool:
    selections = [skill for skill in selections if skill][: grant["count"]]

    if grant["kind"] == "class_level":
        idx = grant["class_level_index"]
        if not (0 <= idx < len(character.class_levels)):
            return False
        cl = character.class_levels[idx]
        if cl.new_expertise != selections:
            cl.new_expertise = list(selections)
            return True
        return False

    if grant["kind"] == "feat":
        feat_name = grant["feat_name"]
        before = get_feat_expertise_skill(character, feat_name)
        after = selections[0] if selections else None
        if before != after:
            set_feat_expertise_skill(character, feat_name, after)
            return True

    return False


def scrub_expertise_selections(character) -> bool:
    """Remove stale or invalid expertise picks after related choices change."""
    changed = False

    valid_feat_names = {name for _slot, name in _iter_character_feats(character)}
    if ZHENTARIM_TACTICS not in valid_feat_names:
        before = get_feat_expertise_skill(character, ZHENTARIM_TACTICS)
        if before:
            set_feat_expertise_skill(character, ZHENTARIM_TACTICS, None)
            changed = True

    proficient_skills = get_all_skill_proficiency_names(character)
    taken = {skill for skill, _ in get_auto_skill_expertise_sources(character)}

    for grant in _raw_selectable_expertise_grants(character):
        cleaned: list[str] = []
        for skill in grant["selections"][: grant["count"]]:
            if skill and skill in proficient_skills and skill not in taken:
                cleaned.append(skill)
                taken.add(skill)
        changed = _store_grant_selections(character, grant, cleaned) or changed

    return changed


def get_selectable_expertise_grants(character) -> list[dict]:
    """Return selectable expertise grants with current values and valid options."""
    proficient_skill_set = get_all_skill_proficiency_names(character)
    proficient_skills = _sorted_skill_names(proficient_skill_set)
    auto_expertise = {skill for skill, _ in get_auto_skill_expertise_sources(character)}
    sanitized_grants: list[dict] = []
    taken = set(auto_expertise)
    for raw_grant in _raw_selectable_expertise_grants(character):
        cleaned: list[str] = []
        for skill in raw_grant["selections"][: raw_grant["count"]]:
            if skill and skill in proficient_skill_set and skill not in taken:
                cleaned.append(skill)
                taken.add(skill)
        grant_data = dict(raw_grant)
        grant_data["current_selections"] = cleaned
        sanitized_grants.append(grant_data)

    all_selected: list[tuple[str, int, str]] = []
    for grant in sanitized_grants:
        for slot_index, skill in enumerate(grant["current_selections"]):
            if skill:
                all_selected.append((grant["id"], slot_index, skill))

    grants: list[dict] = []
    for grant in sanitized_grants:
        slots = []
        current_values = list(grant["current_selections"])
        for slot_index in range(grant["count"]):
            current = (
                current_values[slot_index] if slot_index < len(current_values) else ""
            )
            blocked = set(auto_expertise)
            for other_id, other_slot, other_skill in all_selected:
                if other_id == grant["id"] and other_slot == slot_index:
                    continue
                blocked.add(other_skill)

            options = [
                skill
                for skill in proficient_skills
                if skill == current or skill not in blocked
            ]
            slots.append(
                {
                    "index": slot_index,
                    "current": current,
                    "options": options,
                }
            )

        grant_data = dict(grant)
        grant_data["current_selections"] = current_values
        grant_data["slots"] = slots
        grants.append(grant_data)

    return grants


def get_all_skill_expertise_names(character) -> set[str]:
    """Return all expertise skills currently granted to the character."""
    proficient_skills = get_all_skill_proficiency_names(character)
    expertise = {skill for skill, _ in get_auto_skill_expertise_sources(character)}

    for cl in character.class_levels:
        for skill in cl.new_expertise:
            if skill in proficient_skills:
                expertise.add(skill)

    stored_feat_skill = get_feat_expertise_skill(character, ZHENTARIM_TACTICS)
    if stored_feat_skill and stored_feat_skill in proficient_skills:
        expertise.add(stored_feat_skill)

    return expertise


def get_skill_proficiency_source_labels(character, skill_name: str) -> list[str]:
    """Return human-readable labels for why the character is proficient in a skill."""
    labels: list[str] = []
    seen: set[str] = set()

    if skill_name in (getattr(character, "selected_skills", []) or []):
        _append_unique_label(labels, seen, "Class skill selection")

    for granted_skill, source in get_skill_proficiency_sources(character):
        if granted_skill == skill_name:
            _append_unique_label(labels, seen, source)

    return labels


def get_skill_expertise_source_labels(character, skill_name: str) -> list[str]:
    """Return human-readable labels for why the character has expertise in a skill."""
    labels: list[str] = []
    seen: set[str] = set()

    for granted_skill, source in get_auto_skill_expertise_sources(character):
        if granted_skill == skill_name:
            _append_unique_label(labels, seen, source)

    for cl in getattr(character, "class_levels", []) or []:
        if skill_name not in getattr(cl, "new_expertise", []):
            continue
        if cl.class_slug == "rogue" and cl.class_level == 1:
            label = "Rogue Expertise"
        else:
            label = f"Level {cl.class_level} Expertise"
        _append_unique_label(labels, seen, label)

    for feat_slot, feat_name in _iter_character_feats(character):
        if get_feat_expertise_skill(character, feat_name) == skill_name:
            _append_unique_label(labels, seen, f"{feat_slot} - {feat_name}")

    return labels


# ---------------------------------------------------------------------------
# Skill advantage detection (permanent / unconditional sources only)
# ---------------------------------------------------------------------------

# Item name (lowercase) -> set of skill display names that gain advantage
_ITEM_SKILL_ADVANTAGES: dict[str, set[str]] = {
    "boots of elvenkind": {"Stealth"},
    "cloak of elvenkind": {"Stealth"},
    "cloak of the bat": {"Stealth"},
    "sentinel shield": {"Perception"},
    "rod of alertness": {"Perception"},
    "eyes of the eagle": {"Perception"},
    "robe of eyes": {"Perception"},
    "winter camouflage": {"Stealth"},
}

# Species name (lowercase) -> set of skill display names that gain advantage
_SPECIES_SKILL_ADVANTAGES: dict[str, set[str]] = {
    "changeling": {"Deception", "Intimidation", "Performance", "Persuasion"},
}


def get_all_skill_advantage_names(character) -> set[str]:
    """Return all skills the character has advantage on from permanent sources."""
    advantages: set[str] = set()

    # Species-granted advantages
    species = getattr(character, "species", None)
    if species:
        species_key = (species.get("name") or "").strip().lower()
        if species_key in _SPECIES_SKILL_ADVANTAGES:
            advantages.update(_SPECIES_SKILL_ADVANTAGES[species_key])

    # Custom inventory items (non-weapon / non-armor items are always "active")
    for item in getattr(character, "custom_inventory", []) or []:
        item_key = (item.get("name") or "").strip().lower()
        if item_key in _ITEM_SKILL_ADVANTAGES:
            advantages.update(_ITEM_SKILL_ADVANTAGES[item_key])

    # Equipped weapons
    for key in getattr(character, "equipped_weapons", []) or []:
        if key in _ITEM_SKILL_ADVANTAGES:
            advantages.update(_ITEM_SKILL_ADVANTAGES[key])

    # Equipped armor / shield
    for key in getattr(character, "equipped_armor", []) or []:
        if key in _ITEM_SKILL_ADVANTAGES:
            advantages.update(_ITEM_SKILL_ADVANTAGES[key])

    return advantages


def get_skill_advantage_source_labels(character, skill_name: str) -> list[str]:
    """Return human-readable labels for why the character has advantage on a skill."""
    labels: list[str] = []
    seen: set[str] = set()

    species = getattr(character, "species", None)
    if species:
        species_key = (species.get("name") or "").strip().lower()
        if species_key in _SPECIES_SKILL_ADVANTAGES:
            if skill_name in _SPECIES_SKILL_ADVANTAGES[species_key]:
                _append_unique_label(
                    labels, seen, f"Species - {species.get('name', 'Unknown')}"
                )

    for item in getattr(character, "custom_inventory", []) or []:
        item_name = (item.get("name") or "").strip()
        item_key = item_name.lower()
        if item_key in _ITEM_SKILL_ADVANTAGES:
            if skill_name in _ITEM_SKILL_ADVANTAGES[item_key]:
                _append_unique_label(labels, seen, item_name)

    for key in list(getattr(character, "equipped_weapons", []) or []) + list(
        getattr(character, "equipped_armor", []) or []
    ):
        if key in _ITEM_SKILL_ADVANTAGES and skill_name in _ITEM_SKILL_ADVANTAGES[key]:
            _append_unique_label(labels, seen, key.title())

    return labels


def compute_skill_sources(character) -> dict:
    """Return skill and expertise grant information derived from choices."""
    auto = get_skill_proficiency_sources(character)
    auto_expertise = get_auto_skill_expertise_sources(character)

    class_options: list[str] = []
    choose_count = 0
    if character.character_class:
        skill_choices = character.character_class.get("skill_choices", {})
        choose_count = skill_choices.get("count", 0)
        class_options = list(skill_choices.get("options", []))

    selectable_expertise = get_selectable_expertise_grants(character)
    expertise_choose_count = sum(grant["count"] for grant in selectable_expertise)
    expertise_chosen_count = sum(
        1
        for grant in selectable_expertise
        for slot in grant["slots"]
        if slot["current"]
    )

    return {
        "auto": auto,
        "class_options": class_options,
        "choose_count": choose_count,
        "expertise_auto": auto_expertise,
        "expertise_selectable": selectable_expertise,
        "expertise_choose_count": expertise_choose_count,
        "expertise_chosen_count": expertise_chosen_count,
        "expertise_missing_count": max(
            0, expertise_choose_count - expertise_chosen_count
        ),
    }
