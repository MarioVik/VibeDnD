"""Parser for background entries from dnd2024_data.json."""

import re
from parsers.base_parser import (
    extract_name_from_url, extract_source, extract_field,
    extract_description, split_comma_list,
)


def parse_equipment_options(text: str) -> list[dict]:
    """Parse background equipment: 'Choose A or B: (A) items; or (B) GP'."""
    options = []
    parts = re.split(r'\(([A-C])\)\s*', text)
    current_label = None
    for part in parts:
        part = part.strip()
        if re.match(r'^[A-C]$', part):
            current_label = part
        elif current_label and part:
            clean = re.sub(r'^or\s+', '', part).strip().rstrip(";").strip()
            if clean:
                options.append({"option": current_label, "items": clean})
            current_label = None

    if not options and text:
        options.append({"option": "A", "items": text})

    return options


def parse_backgrounds(raw_data: list[dict]) -> list[dict]:
    """Parse all background entries into structured data."""
    backgrounds = []

    for entry in raw_data:
        url = entry["url"]
        content = entry["content"]

        # Skip non-background entries (e.g., equipment:tool page)
        if "background:" not in url:
            continue

        name = extract_name_from_url(url)
        source = extract_source(content)
        description = extract_description(content)

        # Ability Scores
        ability_raw = extract_field(content, "Ability Scores")
        ability_scores = split_comma_list(ability_raw) if ability_raw else []

        # Feat
        feat = extract_field(content, "Feat")

        # Skill Proficiencies
        skills_raw = extract_field(content, "Skill Proficiencies")
        skill_proficiencies = split_comma_list(skills_raw) if skills_raw else []

        # Tool Proficiency
        tool_proficiency = extract_field(content, "Tool Proficiency")

        # Equipment
        equip_raw = extract_field(content, "Equipment")
        if not equip_raw:
            # Try multi-line extraction
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.strip().lower().startswith("equipment"):
                    equip_parts = []
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if lines[j].strip():
                            equip_parts.append(lines[j].strip())
                        else:
                            break
                    equip_raw = " ".join(equip_parts)
                    break

        equipment = parse_equipment_options(equip_raw) if equip_raw else []

        backgrounds.append({
            "name": name,
            "source": source,
            "description": description,
            "ability_scores": ability_scores,
            "feat": feat,
            "skill_proficiencies": skill_proficiencies,
            "tool_proficiency": tool_proficiency,
            "equipment": equipment,
        })

    return backgrounds
