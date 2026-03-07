"""Parser for spell entries from dnd2024_data.json."""

import re
from parsers.base_parser import extract_name_from_url, extract_source, extract_field, is_school_index


def parse_spell_header(content: str) -> dict:
    """Parse the spell header line like 'Evocation Cantrip (Artificer, Sorcerer, Wizard)'
    or 'Level 3 Evocation (Sorcerer, Wizard)'."""
    lines = content.strip().split("\n")

    for line in lines:
        stripped = line.strip()

        # Cantrip pattern: "School Cantrip (Classes)"
        m = re.match(r'^(\w+)\s+Cantrip\s*\(([^)]+)\)', stripped)
        if m:
            return {
                "level": 0,
                "school": m.group(1),
                "classes": [c.strip() for c in m.group(2).split(",")],
            }

        # Leveled spell: "Level N School (Classes)"
        m = re.match(r'^Level\s+(\d+)\s+(\w+)\s*\(([^)]+)\)', stripped)
        if m:
            return {
                "level": int(m.group(1)),
                "school": m.group(2),
                "classes": [c.strip() for c in m.group(3).split(",")],
            }

    return {"level": -1, "school": "Unknown", "classes": []}


def parse_components(text: str) -> dict:
    """Parse components string like 'V, S, M (a ball of bat guano)'.

    Returns {'V': True, 'S': True, 'M': 'a ball of bat guano'} or similar.
    """
    result = {"V": False, "S": False, "M": None}
    if not text:
        return result

    # Check for material component with description
    m_match = re.search(r'M\s*\(([^)]+)\)', text)
    if m_match:
        result["M"] = m_match.group(1).strip()
    elif "M" in text.upper().split(",")[0] if len(text.split(",")) == 1 else "M" in text:
        # Check for bare M
        parts = [p.strip() for p in text.split(",")]
        for p in parts:
            if p.strip().startswith("M"):
                if "(" in p:
                    m2 = re.search(r'M\s*\(([^)]+)\)', p)
                    if m2:
                        result["M"] = m2.group(1).strip()
                else:
                    mat = p.strip()[1:].strip()
                    result["M"] = mat if mat else True

    if "V" in text:
        result["V"] = True
    if "S" in text:
        result["S"] = True

    return result


def parse_duration(text: str) -> tuple[str, bool]:
    """Parse duration, returning (duration_text, is_concentration)."""
    if not text:
        return ("Unknown", False)

    concentration = False
    clean = text

    # Handle concentration markers
    if "Concentration" in text or text.startswith("C\n") or text.startswith("C,"):
        concentration = True
        clean = re.sub(r'^C\s*,?\s*', '', text)
        clean = re.sub(r'^Concentration,?\s*', '', clean)
        clean = clean.strip()
        if clean.startswith("up to "):
            clean = clean  # keep as-is

    if not clean:
        clean = text

    return (clean.strip(), concentration)


def parse_spells(raw_data: list[dict]) -> list[dict]:
    """Parse all spell entries into structured data."""
    spells = []

    for entry in raw_data:
        # Skip school index pages
        if is_school_index(entry):
            continue

        url = entry["url"]
        content = entry["content"]
        name = extract_name_from_url(url)
        source = extract_source(content)

        # Parse header
        header = parse_spell_header(content)
        if header["level"] == -1:
            print(f"  WARNING: Could not parse header for {name} ({url})")
            continue

        # Extract fields
        casting_time_raw = extract_field(content, "Casting Time")
        range_val = extract_field(content, "Range")
        components_raw = extract_field(content, "Components")
        duration_raw = extract_field(content, "Duration")

        # Parse casting time for ritual
        ritual = False
        casting_time = casting_time_raw or "Action"
        if casting_time_raw and "Ritual" in casting_time_raw:
            ritual = True
            casting_time = re.sub(r'\s*or\s*Ritual\s*', '', casting_time).strip()
            casting_time = re.sub(r'\s*or\s*$', '', casting_time).strip()

        # Parse components
        components = parse_components(components_raw or "")

        # Parse duration
        duration_text, concentration = parse_duration(duration_raw or "Instantaneous")

        # Extract description - everything after Duration value until special sections
        lines = content.split("\n")
        desc_start = None
        for i, line in enumerate(lines):
            if line.strip().rstrip(":").lower() == "duration":
                # Skip the duration value line(s)
                desc_start = i + 2
                break

        description = ""
        higher_levels = None
        cantrip_upgrade = None

        if desc_start:
            desc_lines = []
            in_higher = False
            in_cantrip = False

            for i in range(desc_start, len(lines)):
                stripped = lines[i].strip()
                if not stripped:
                    continue

                if stripped.startswith("Using a Higher-Level Spell Slot") or stripped.startswith("At Higher Levels"):
                    in_higher = True
                    in_cantrip = False
                    continue
                elif stripped.startswith("Cantrip Upgrade"):
                    in_cantrip = True
                    in_higher = False
                    continue

                if in_higher:
                    if higher_levels:
                        higher_levels += " " + stripped
                    else:
                        higher_levels = stripped
                elif in_cantrip:
                    if cantrip_upgrade:
                        cantrip_upgrade += " " + stripped
                    else:
                        cantrip_upgrade = stripped
                else:
                    desc_lines.append(stripped)

            description = " ".join(desc_lines)

        spells.append({
            "name": name,
            "level": header["level"],
            "school": header["school"],
            "classes": header["classes"],
            "casting_time": casting_time,
            "ritual": ritual,
            "range": range_val or "Self",
            "components": components,
            "concentration": concentration,
            "duration": duration_text,
            "description": description,
            "higher_levels": higher_levels,
            "cantrip_upgrade": cantrip_upgrade,
            "source": source,
        })

    return spells
