"""Parser for species entries from dnd2024_data.json."""

import re
from parsers.base_parser import (
    extract_name_from_url,
    extract_source,
    extract_field,
    extract_description,
    split_comma_list,
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
            elif (
                not past_base_stats
                and stripped
                and stripped.rstrip(":") not in skip_fields
            ):
                # Check if previous line was a base stat field
                if i > 0 and lines[i - 1].strip().lower().rstrip(":") in skip_fields:
                    continue  # This is the value of the base stat
                past_base_stats = True

    # Re-parse: find where the actual trait descriptions start
    # Look for "As a/an X, you have these special traits." or first trait name
    trait_section_start = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^As (a|an) .+, you have these special traits\.?$", stripped):
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

    # Parse traits: heading line ends with period and is title-like
    current_name = None
    current_desc_lines = []

    def looks_like_trait_heading(line: str) -> bool:
        if not line.endswith("."):
            return False

        core = line.rstrip(".").strip()
        if not core or len(core) > 70:
            return False

        words = re.findall(r"[A-Za-z][A-Za-z'\-]*", core)
        if not words:
            return False

        # Description sentences often start with these words.
        if words[0].lower() in {
            "you",
            "your",
            "as",
            "when",
            "while",
            "if",
            "the",
            "this",
            "that",
        }:
            return False

        allowed_lower = {
            "a",
            "an",
            "and",
            "as",
            "at",
            "by",
            "for",
            "from",
            "in",
            "of",
            "on",
            "or",
            "the",
            "to",
            "with",
        }
        for word in words:
            if word.lower() in allowed_lower:
                continue
            if not word[0].isupper():
                return False

        return True

    # Stop markers
    stop_markers = [
        "elven lineages",
        "draconic ancestry",
        "fiendish legacy",
        "lineage",
        "level 1",
        "level 3",
        "level 5",
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

        if looks_like_trait_heading(stripped):
            # Single-word trait names like "Darkvision."
            if current_name:
                traits.append(
                    {
                        "name": current_name,
                        "description": " ".join(current_desc_lines).strip(),
                    }
                )
            current_name = stripped.rstrip(".")
            current_desc_lines = []
        elif current_name:
            current_desc_lines.append(stripped)

    if current_name:
        traits.append(
            {
                "name": current_name,
                "description": " ".join(current_desc_lines).strip(),
            }
        )

    return traits


_KNOWN_SUB_RACE_NAMES = {
    "Elven Lineages": [
        "Drow",
        "High Elf",
        "Wood Elf",
        "Lorwyn Elf",
        "Shadowmoor Elf",
    ],
    "Fiendish Legacies": [
        "Abyssal",
        "Chthonic",
        "Infernal",
    ],
    "Draconic Ancestry": [
        "Black",
        "Blue",
        "Brass",
        "Bronze",
        "Copper",
        "Gold",
        "Green",
        "Red",
        "Silver",
        "White",
    ],
}


def parse_sub_choices(content: str, species_name: str) -> list[dict] | None:
    """Parse sub-choice tables (elf lineages, dragonborn ancestry, etc.).

    Returns a list of dicts, each with:
        name: sub-race name (e.g. "Drow", "High Elf")
        description: assembled full description text
    """
    lines = content.split("\n")

    table_configs = {
        "Elven Lineages": ["Lineage", "Level 1", "Level 3", "Level 5"],
        "Draconic Ancestry": ["Dragon", "Damage Type", "Breath Weapon"],
        "Fiendish Legacies": ["Legacy", "Level 1", "Level 3", "Level 5"],
    }

    for table_name, col_headers in table_configs.items():
        table_start = None
        for i, line in enumerate(lines):
            if line.strip() == table_name:
                table_start = i
                break

        if table_start is None:
            continue

        known_names = set(_KNOWN_SUB_RACE_NAMES.get(table_name, []))
        if not known_names:
            continue

        # Find start of data after column headers
        col_start = None
        for i in range(table_start + 1, min(table_start + 10, len(lines))):
            if lines[i].strip() == col_headers[0]:
                col_start = i
                break

        if col_start is None:
            continue

        data_start = col_start + len(col_headers)

        # Collect all non-empty lines from data region
        data_lines = []
        for i in range(data_start, len(lines)):
            stripped = lines[i].strip()
            if not stripped:
                continue
            data_lines.append(stripped)

        # Split data_lines into chunks per known sub-race name.
        # Each chunk starts when we see a known name.
        chunks: list[tuple[str, list[str]]] = []
        current_name = None
        current_cells: list[str] = []

        for line in data_lines:
            if line in known_names:
                if current_name is not None:
                    chunks.append((current_name, current_cells))
                current_name = line
                current_cells = []
            elif current_name is not None:
                current_cells.append(line)

        if current_name is not None:
            chunks.append((current_name, current_cells))

        choices = []
        for name, cells in chunks:
            if len(col_headers) == 3:
                # Draconic Ancestry: cells map to Damage Type, Breath Weapon
                dmg = cells[0] if cells else "Unknown"
                breath = " ".join(cells[1:]) if len(cells) > 1 else "Unknown"
                desc = f"Damage Type: {dmg}\nBreath Weapon: {breath}"
            else:
                # Lineage/Legacy tables: 3 data columns (Level 1, 3, 5).
                # Level 3 and Level 5 are always the last 2 cells (single spell names).
                # Everything before those is the Level 1 description.
                if len(cells) >= 3:
                    lvl5 = cells[-1]
                    lvl3 = cells[-2]
                    lvl1 = " ".join(cells[:-2])
                elif len(cells) == 2:
                    lvl1 = cells[0]
                    lvl3 = cells[1]
                    lvl5 = ""
                elif len(cells) == 1:
                    lvl1 = cells[0]
                    lvl3 = ""
                    lvl5 = ""
                else:
                    lvl1 = lvl3 = lvl5 = ""

                parts = [f"Level 1: {lvl1}"]
                if lvl3:
                    parts.append(f"Level 3: {lvl3}")
                if lvl5:
                    parts.append(f"Level 5: {lvl5}")
                desc = "\n".join(parts)

            choices.append({"name": name, "description": desc})

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
        note_match = re.search(r"\(([^)]+)\)", size_raw)
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
        m = re.search(r"(\d+)\s*feet", speed_raw)
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

        species_list.append(
            {
                "name": name,
                "source": source,
                "description": description,
                "creature_type": creature_type,
                "size": size,
                "speed": speed,
                "traits": traits,
                "sub_choices": sub_choices,
            }
        )

    return species_list
