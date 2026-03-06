"""Parser for species entries from dnd2024_data.json."""

import re
from parsers.base_parser import (
    extract_name_from_url, extract_source, extract_field,
    extract_description, split_comma_list,
)


def parse_traits(content: str) -> list[dict]:
    """Parse special traits from the traits section.

    Traits follow the pattern:
        Trait Name.
        Description text that may span multiple lines.
    """
    traits = []
    lines = content.split("\n")

    # Find the traits section (after "X Traits" header and the base stats)
    traits_start = None
    skip_fields = {"creature type", "size", "speed"}
    past_base_stats = False

    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if "traits" in stripped and not stripped.startswith("creature"):
            traits_start = i + 1
            continue

        if traits_start is not None and i >= traits_start:
            if stripped.rstrip(":") in skip_fields:
                # Skip this field and its value
                past_base_stats = False
                continue
            elif not past_base_stats and stripped and stripped.rstrip(":") not in skip_fields:
                # Check if previous line was a base stat field
                if i > 0 and lines[i - 1].strip().lower().rstrip(":") in skip_fields:
                    continue  # This is the value of the base stat
                past_base_stats = True

    # Re-parse: find where the actual trait descriptions start
    # Look for "As a/an X, you have these special traits." or first trait name
    trait_section_start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r'^As (a|an) .+, you have these special traits\.?$', stripped):
            trait_section_start = i + 1
            break

    # Fallback: find after Speed value
    if trait_section_start is None:
        for i, line in enumerate(lines):
            if line.strip().lower().startswith("speed"):
                # Next non-empty line after speed value is traits
                for j in range(i + 1, len(lines)):
                    if lines[j].strip() and "feet" in lines[j].strip().lower():
                        trait_section_start = j + 1
                        break
                    elif lines[j].strip():
                        trait_section_start = j
                        break
                break

    if trait_section_start is None:
        return traits

    # Parse traits: name ends with period, is short and title-case
    current_name = None
    current_desc_lines = []

    # Stop markers
    stop_markers = [
        "elven lineages", "draconic ancestry", "fiendish legacy",
        "lineage", "level 1", "level 3", "level 5",
    ]

    for i in range(trait_section_start, len(lines)):
        stripped = lines[i].strip()
        if not stripped:
            continue

        lower = stripped.lower()

        # Stop at sub-choice tables
        if any(lower.startswith(m) or lower == m for m in stop_markers):
            # Check if this is a trait name that happens to match
            if stripped.endswith(".") and len(stripped) < 40:
                # It's a trait, not a table header
                pass
            else:
                break

        # Check if this is a trait name (ends with period, short, not a sentence)
        if (stripped.endswith(".") and len(stripped) < 50 and
                " " in stripped and not stripped[0].islower() and
                stripped.count(".") == 1):
            # Save previous
            if current_name:
                traits.append({
                    "name": current_name,
                    "description": " ".join(current_desc_lines).strip(),
                })
            current_name = stripped.rstrip(".")
            current_desc_lines = []
        elif stripped.endswith(".") and len(stripped) < 30 and not stripped[0].islower():
            # Single-word trait names like "Darkvision."
            if current_name:
                traits.append({
                    "name": current_name,
                    "description": " ".join(current_desc_lines).strip(),
                })
            current_name = stripped.rstrip(".")
            current_desc_lines = []
        elif current_name:
            current_desc_lines.append(stripped)

    if current_name:
        traits.append({
            "name": current_name,
            "description": " ".join(current_desc_lines).strip(),
        })

    return traits


def parse_sub_choices(content: str, species_name: str) -> list[dict] | None:
    """Parse sub-choice tables (elf lineages, dragonborn ancestry, etc.)."""
    lines = content.split("\n")

    # Look for known sub-choice table patterns
    table_headers = {
        "Elven Lineages": ["Lineage", "Level 1", "Level 3", "Level 5"],
        "Draconic Ancestry": ["Dragon", "Damage Type", "Breath Weapon"],
        "Fiendish Legacies": ["Legacy", "Level 1", "Level 3", "Level 5"],
    }

    for table_name, expected_cols in table_headers.items():
        table_start = None
        for i, line in enumerate(lines):
            if line.strip() == table_name:
                table_start = i
                break

        if table_start is None:
            continue

        # Find column headers
        col_start = None
        for i in range(table_start + 1, min(table_start + 10, len(lines))):
            if lines[i].strip() == expected_cols[0]:
                col_start = i
                break

        if col_start is None:
            continue

        # Count actual columns (each header is on its own line)
        num_cols = 0
        col_names = []
        for i in range(col_start, min(col_start + 10, len(lines))):
            stripped = lines[i].strip()
            if not stripped:
                break
            # Check if it looks like a column header
            if stripped[0].isupper() and len(stripped) < 30:
                num_cols += 1
                col_names.append(stripped)
            else:
                break

        if num_cols < 2:
            continue

        # Read data rows
        data_start = col_start + num_cols
        choices = []
        row = []

        for i in range(data_start, len(lines)):
            stripped = lines[i].strip()
            if not stripped:
                if row:
                    # Might be end of table
                    continue
                continue

            row.append(stripped)

            if len(row) >= num_cols:
                choice = {}
                for j, col_name in enumerate(col_names):
                    if j < len(row):
                        choice[col_name] = row[j]
                choices.append(choice)
                row = []

        # Handle last partial row
        if row and len(row) >= 2:
            choice = {}
            for j, col_name in enumerate(col_names):
                if j < len(row):
                    choice[col_name] = row[j]
            choices.append(choice)

        if choices:
            return choices

    return None


def parse_size(content: str) -> dict:
    """Parse size field which may offer a choice."""
    size_raw = extract_field(content, "Size")
    if not size_raw:
        return {"options": ["Medium"], "note": None}

    if "or Small" in size_raw or "or Medium" in size_raw:
        options = []
        if "Medium" in size_raw:
            options.append("Medium")
        if "Small" in size_raw:
            options.append("Small")
        note_match = re.search(r'\(([^)]+)\)', size_raw)
        return {
            "options": options if options else ["Medium"],
            "note": note_match.group(1) if note_match else None,
        }

    if "Small" in size_raw:
        return {"options": ["Small"], "note": None}
    return {"options": ["Medium"], "note": None}


def parse_speed(content: str) -> int:
    """Parse speed in feet."""
    speed_raw = extract_field(content, "Speed")
    if speed_raw:
        m = re.search(r'(\d+)\s*feet', speed_raw)
        if m:
            return int(m.group(1))
    return 30


def parse_species(raw_data: list[dict]) -> list[dict]:
    """Parse all species entries into structured data."""
    species_list = []

    for entry in raw_data:
        url = entry["url"]
        content = entry["content"]
        name = extract_name_from_url(url)
        source = extract_source(content)

        # Extract description
        description = extract_description(content)

        # Creature type
        creature_type = extract_field(content, "Creature Type") or "Humanoid"

        # Size
        size = parse_size(content)

        # Speed
        speed = parse_speed(content)

        # Traits
        traits = parse_traits(content)

        # Sub-choices (lineages, ancestry, legacy)
        sub_choices = parse_sub_choices(content, name)

        species_list.append({
            "name": name,
            "source": source,
            "description": description,
            "creature_type": creature_type,
            "size": size,
            "speed": speed,
            "traits": traits,
            "sub_choices": sub_choices,
        })

    return species_list
