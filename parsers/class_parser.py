"""Parser for class entries from dnd2024_data.json."""

import re
from parsers.base_parser import (
    extract_name_from_url,
    extract_source,
    extract_field,
    extract_description,
    split_comma_list,
    parse_choose_pattern,
)

# Known main classes (by URL slug before :main)
MAIN_CLASSES = {
    "artificer",
    "barbarian",
    "bard",
    "cleric",
    "druid",
    "fighter",
    "monk",
    "paladin",
    "ranger",
    "rogue",
    "sorcerer",
    "warlock",
    "wizard",
}

# Caster type classification
CASTER_TYPES = {
    "bard": "full",
    "cleric": "full",
    "druid": "full",
    "sorcerer": "full",
    "wizard": "full",
    "paladin": "half",
    "ranger": "half",
    "artificer": "half",
    "warlock": "pact",
}

SPELLCASTING_ABILITIES = {
    "bard": "Charisma",
    "cleric": "Wisdom",
    "druid": "Wisdom",
    "sorcerer": "Charisma",
    "wizard": "Intelligence",
    "paladin": "Charisma",
    "ranger": "Wisdom",
    "artificer": "Intelligence",
    "warlock": "Charisma",
}

ALL_SKILLS = [
    "Acrobatics",
    "Animal Handling",
    "Arcana",
    "Athletics",
    "Deception",
    "History",
    "Insight",
    "Intimidation",
    "Investigation",
    "Medicine",
    "Nature",
    "Perception",
    "Performance",
    "Persuasion",
    "Religion",
    "Sleight of Hand",
    "Stealth",
    "Survival",
]


def parse_core_traits(content: str, class_name: str) -> dict:
    """Parse the Core X Traits block."""
    traits = {}

    # Primary Ability
    primary = extract_field(content, "Primary Ability")
    if primary:
        traits["primary_ability"] = split_comma_list(primary)
    else:
        traits["primary_ability"] = []

    # Hit Point Die
    hpd = extract_field(content, "Hit Point Die")
    if hpd:
        m = re.search(r"D(\d+)", hpd, re.IGNORECASE)
        traits["hit_die"] = int(m.group(1)) if m else 8
    else:
        traits["hit_die"] = 8

    # Saving Throw Proficiencies
    saves = extract_field(content, "Saving Throw Proficiencies")
    if saves:
        traits["saving_throws"] = split_comma_list(saves)
    else:
        traits["saving_throws"] = []

    # Skill Proficiencies
    skills_raw = extract_field(content, "Skill Proficiencies")
    if skills_raw:
        choice = parse_choose_pattern(skills_raw)
        if choice:
            traits["skill_choices"] = choice
        else:
            any_skills = re.match(
                r"Choose\s+any\s+(\d+)\s+skills?", skills_raw, re.IGNORECASE
            )
            if any_skills:
                traits["skill_choices"] = {
                    "count": int(any_skills.group(1)),
                    "options": list(ALL_SKILLS),
                }
            else:
                traits["skill_choices"] = {
                    "count": 2,
                    "options": split_comma_list(skills_raw),
                }
    else:
        traits["skill_choices"] = {"count": 0, "options": []}

    # Weapon Proficiencies
    weapons = extract_field(content, "Weapon Proficiencies")
    traits["weapon_proficiencies"] = split_comma_list(weapons) if weapons else []

    # Armor Training
    armor = extract_field(content, "Armor Training")
    if armor and armor.lower() != "none":
        traits["armor_proficiencies"] = split_comma_list(armor)
    else:
        traits["armor_proficiencies"] = []

    # Starting Equipment
    equip = extract_field(content, "Starting Equipment")
    traits["starting_equipment"] = parse_equipment_options(equip) if equip else []

    return traits


def parse_equipment_options(text: str) -> list[dict]:
    """Parse equipment options like 'Choose A or B: (A) items; or (B) GP'."""
    options = []
    # Pattern: (A) items; or (B) items; or (C) items
    parts = re.split(r"\(([A-C])\)\s*", text)
    current_label = None
    for part in parts:
        part = part.strip().rstrip(";").strip()
        if not part:
            continue
        if re.match(r"^[A-C]$", part):
            current_label = part
        elif current_label:
            clean = re.sub(r"^or\s+", "", part).strip()
            clean = re.sub(r"\s*;?\s*$", "", clean)
            if clean:
                options.append({"option": current_label, "items": clean})
            current_label = None

    if not options and text:
        options.append({"option": "A", "items": text})

    return options


def _find_all_level_tables(lines: list[str]) -> list[int]:
    """Find the starting line index of every 'Level' table header."""
    indices = []
    for i, line in enumerate(lines):
        if line.strip() == "Level" and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if "Proficiency" in nxt or "Channel" in nxt or "Cantrips" in nxt:
                indices.append(i)
    return indices


def _read_table_header_and_row1(
    lines: list[str], header_idx: int
) -> tuple[list[str], list[str]]:
    """Read header lines and level 1 row values from a table starting at header_idx."""
    header_lines = []
    data_start = None
    for i in range(header_idx, len(lines)):
        stripped = lines[i].strip()
        if stripped == "1":
            data_start = i
            break
        header_lines.append(stripped)

    if data_start is None:
        return header_lines, []

    # Read values until level 2 row.
    # Level 2 marker: "2" followed by "+2" within next few non-empty lines.
    row_values = []
    for i in range(data_start, len(lines)):
        stripped = lines[i].strip()
        if not stripped or stripped == ",":
            continue
        if stripped == "2" and len(row_values) > 2:
            is_level_marker = False
            for j in range(i + 1, min(i + 5, len(lines))):
                nxt = lines[j].strip()
                if not nxt or nxt == ",":
                    continue
                if nxt == "+2":
                    is_level_marker = True
                break
            if is_level_marker:
                break
        row_values.append(stripped)

    return header_lines, row_values


def parse_features_table(content: str, class_name_lower: str) -> dict:
    """Parse the class features table(s) to extract level 1 data.

    Some classes (Wizard, Sorcerer) have spell columns in the main table.
    Others (Cleric, Bard, Druid, etc.) have a separate Part B table with
    spell slots, cantrips, and prepared spell counts.
    """
    lines = content.split("\n")
    result = {
        "cantrips_known": None,
        "spells_prepared": None,
        "spell_slots": None,
        "level_1_features_names": [],
    }

    table_starts = _find_all_level_tables(lines)
    if not table_starts:
        return result

    # Process each table looking for spell data
    for t_idx, header_idx in enumerate(table_starts):
        header_lines, row_values = _read_table_header_and_row1(lines, header_idx)
        header_text = "\n".join(header_lines)

        has_cantrips = "Cantrips" in header_text
        has_prepared = "Prepared Spells" in header_text

        slot_levels = []
        for hl in header_lines:
            if re.match(r"^(1st|2nd|3rd|[4-9]th)$", hl.strip()):
                slot_levels.append(hl.strip())

        is_spell_table = has_cantrips or has_prepared or len(slot_levels) > 0
        is_first_table = t_idx == 0

        if len(row_values) < 2:
            continue

        # For the first table: extract feature names
        if is_first_table:
            # Skip level ("1") and prof bonus ("+2")
            rest = row_values[2:]

            # Count trailing numeric/spell columns in this table
            num_extra_cols = 0
            # Count non-spell extra columns (like Bardic Die, Rages, etc.)
            for hl in header_lines:
                if hl in ("Level", "Proficiency Bonus", "Features", "Class Features"):
                    continue
                if hl in ("Cantrips", "Prepared Spells") or re.match(
                    r"^(1st|2nd|3rd|[4-9]th)$", hl
                ):
                    continue
                num_extra_cols += 1

            num_spell_cols = (
                (1 if has_cantrips else 0)
                + (1 if has_prepared else 0)
                + len(slot_levels)
            )
            total_trailing = num_extra_cols + num_spell_cols

            if total_trailing > 0 and len(rest) >= total_trailing:
                trailing = rest[-total_trailing:]
                feature_names = rest[:-total_trailing]

                # Parse spell data from trailing columns (skip non-spell extras)
                spell_trailing = trailing[num_extra_cols:]
                s_idx = 0
                if has_cantrips and s_idx < len(spell_trailing):
                    val = spell_trailing[s_idx]
                    result["cantrips_known"] = int(val) if val.isdigit() else None
                    s_idx += 1
                if has_prepared and s_idx < len(spell_trailing):
                    val = spell_trailing[s_idx]
                    result["spells_prepared"] = int(val) if val.isdigit() else None
                    s_idx += 1
                slots = {}
                for j, level_name in enumerate(slot_levels):
                    if s_idx + j < len(spell_trailing):
                        val = spell_trailing[s_idx + j]
                        if val != "-" and val.isdigit() and int(val) > 0:
                            slots[level_name] = int(val)
                result["spell_slots"] = slots if slots else None
            else:
                feature_names = rest

            result["level_1_features_names"] = [f for f in feature_names if f != "-"]

        # For subsequent tables (Part B): extract spell data
        elif is_spell_table:
            # Part B tables: Level, [extra cols], Cantrips, Prepared, 1st-9th
            # Row starts with "1" (level) then values
            rest = row_values[1:]  # skip level number, no prof bonus in Part B

            num_extra_b = 0
            for hl in header_lines:
                if hl in ("Level",):
                    continue
                if hl in ("Cantrips", "Prepared Spells") or re.match(
                    r"^(1st|2nd|3rd|[4-9]th)$", hl
                ):
                    continue
                num_extra_b += 1

            num_spell_cols = (
                (1 if has_cantrips else 0)
                + (1 if has_prepared else 0)
                + len(slot_levels)
            )

            if num_extra_b + num_spell_cols <= len(rest):
                spell_data = rest[num_extra_b:]

                idx = 0
                if has_cantrips and idx < len(spell_data):
                    val = spell_data[idx]
                    result["cantrips_known"] = int(val) if val.isdigit() else None
                    idx += 1
                if has_prepared and idx < len(spell_data):
                    val = spell_data[idx]
                    result["spells_prepared"] = int(val) if val.isdigit() else None
                    idx += 1

                slots = {}
                for j, level_name in enumerate(slot_levels):
                    if idx + j < len(spell_data):
                        val = spell_data[idx + j]
                        if val != "-" and val.isdigit() and int(val) > 0:
                            slots[level_name] = int(val)
                result["spell_slots"] = slots if slots else None

    return result


def parse_level_1_features(content: str, feature_names: list[str]) -> list[dict]:
    """Extract level 1 feature descriptions from the content."""
    features = []
    lines = content.split("\n")

    # Find "Level 1:" section
    level1_start = None
    level2_start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("Level 1:") or stripped == "Level 1":
            level1_start = i + 1
        elif stripped.startswith("Level 2:") or stripped == "Level 2":
            level2_start = i
            break

    if level1_start is None:
        return features

    end = level2_start if level2_start else len(lines)
    section = "\n".join(lines[level1_start:end])

    # Parse features within the Level 1 section
    # Features are typically: "Feature Name.\nDescription text..."
    # or "Feature Name\nDescription text..."
    current_name = None
    current_desc_lines = []

    for line in section.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # Check if this line is a feature header (ends with period, short, title case)
        if (
            stripped.endswith(".")
            and len(stripped) < 60
            and not stripped[0].islower()
            and stripped[:-1].replace("'", "").replace(" ", "").isalpha()
        ):
            # Save previous feature
            if current_name:
                features.append(
                    {
                        "name": current_name,
                        "description": " ".join(current_desc_lines).strip(),
                    }
                )
            current_name = stripped.rstrip(".")
            current_desc_lines = []
        elif current_name:
            current_desc_lines.append(stripped)
        # Also check for "Feature Name" without period as header
        elif any(
            stripped.lower().startswith(
                fn.lower().split(",")[0].strip().split("(")[0].strip()
            )
            for fn in feature_names
            if fn != "-"
        ):
            if current_name:
                features.append(
                    {
                        "name": current_name,
                        "description": " ".join(current_desc_lines).strip(),
                    }
                )
            current_name = stripped.rstrip(".")
            current_desc_lines = []

    # Save last feature
    if current_name:
        features.append(
            {
                "name": current_name,
                "description": " ".join(current_desc_lines).strip(),
            }
        )

    return features


def parse_classes(raw_data: list[dict]) -> list[dict]:
    """Parse all class entries into structured data."""
    classes = []

    for entry in raw_data:
        url = entry["url"]

        # Only parse :main entries for standard classes
        if ":main" not in url:
            continue

        slug = url.rsplit("/", 1)[-1].split(":")[0].lower()
        if slug not in MAIN_CLASSES:
            continue

        content = entry["content"]

        # Extract class name from Core X Traits
        name_match = re.search(r"Core\s+(\w+)\s+Traits", content)
        name = name_match.group(1) if name_match else slug.title()

        source = extract_source(content)
        description = extract_description(content)

        # Parse core traits
        traits = parse_core_traits(content, slug)

        # Parse features table for level 1 data
        table_data = parse_features_table(content, slug)

        # Caster info
        caster_type = CASTER_TYPES.get(slug)
        spellcasting_ability = SPELLCASTING_ABILITIES.get(slug)

        # Parse level 1 feature descriptions
        level_1_features = parse_level_1_features(
            content, table_data["level_1_features_names"]
        )

        classes.append(
            {
                "name": name,
                "slug": slug,
                "source": source,
                "description": description,
                "primary_ability": traits["primary_ability"],
                "hit_die": traits["hit_die"],
                "saving_throws": traits["saving_throws"],
                "skill_choices": traits["skill_choices"],
                "weapon_proficiencies": traits["weapon_proficiencies"],
                "armor_proficiencies": traits["armor_proficiencies"],
                "starting_equipment": traits["starting_equipment"],
                "caster_type": caster_type,
                "spellcasting_ability": spellcasting_ability,
                "cantrips_known": table_data["cantrips_known"],
                "spells_prepared": table_data["spells_prepared"],
                "spell_slots": table_data["spell_slots"],
                "level_1_features": level_1_features,
            }
        )

    # Apply fallback spell data for casters where parsing didn't extract it
    SPELL_FALLBACKS = {
        "druid": {"cantrips_known": 2, "spells_prepared": 4, "spell_slots": {"1st": 2}},
        "ranger": {
            "cantrips_known": None,
            "spells_prepared": 2,
            "spell_slots": {"1st": 2},
        },
        "artificer": {
            "cantrips_known": 2,
            "spells_prepared": 2,
            "spell_slots": {"1st": 2},
        },
        "warlock": {
            "cantrips_known": 2,
            "spells_prepared": 2,
            "spell_slots": {"1st": 1},
        },
        "paladin": {
            "cantrips_known": None,
            "spells_prepared": 2,
            "spell_slots": {"1st": 2},
        },
    }
    for cls in classes:
        slug = cls["slug"]
        if (
            slug in SPELL_FALLBACKS
            and cls["cantrips_known"] is None
            and cls["spells_prepared"] is None
        ):
            fb = SPELL_FALLBACKS[slug]
            cls["cantrips_known"] = fb["cantrips_known"]
            cls["spells_prepared"] = fb["spells_prepared"]
            cls["spell_slots"] = fb["spell_slots"]

    return classes
