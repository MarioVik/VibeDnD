"""Shared parsing utilities for all category parsers."""

import re


def extract_name_from_url(url: str) -> str:
    """Convert URL slug to display name.

    'http://dnd2024.wikidot.com/spell:acid-splash' -> 'Acid Splash'
    'http://dnd2024.wikidot.com/fighter:main' -> 'Fighter'
    """
    slug = url.rsplit("/", 1)[-1]
    # Remove prefix before colon
    if ":" in slug:
        slug = slug.split(":", 1)[1]
    # Remove 'main' suffix for class pages
    if slug == "main":
        slug = url.rsplit("/", 1)[-1].split(":", 1)[0]
    slug = slug.replace("-", " ")
    return slug.title()


def extract_source(content: str) -> str:
    """Extract 'Source: X' from first line."""
    lines = content.strip().split("\n")
    for line in lines[:3]:
        line = line.strip()
        if line.startswith("Source:"):
            return line[len("Source:"):].strip()
        if line.startswith("Source"):
            # "Source: X" or just "Source\nX"
            rest = line[len("Source"):].strip().lstrip(":")
            if rest:
                return rest.strip()
    # Check if second line is the source value
    if len(lines) >= 2 and lines[0].strip() == "Source:":
        return lines[1].strip()
    if len(lines) >= 2 and lines[0].strip().startswith("Source"):
        return lines[1].strip()
    return "Unknown"


def extract_field(content: str, field_name: str) -> str | None:
    """Extract value after a field label.

    Handles patterns like:
      'Casting Time:\\nAction'
      'Ability Scores:\\nStrength, Dexterity, Intelligence'
      'Speed:\\n30 feet'
    """
    lines = content.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Match "Field Name:" or "Field Name" as a standalone line
        if stripped.rstrip(":").strip().lower() == field_name.lower():
            # Return the next non-empty line
            for j in range(i + 1, min(i + 5, len(lines))):
                val = lines[j].strip()
                if val:
                    return val
        # Match "Field Name: value" on same line
        pattern = re.compile(rf'^{re.escape(field_name)}\s*:\s*(.+)', re.IGNORECASE)
        m = pattern.match(stripped)
        if m:
            return m.group(1).strip()
    return None


def extract_field_multiline(content: str, field_name: str, stop_fields: list[str] | None = None) -> str | None:
    """Extract multi-line value after a field label, stopping at the next known field."""
    lines = content.split("\n")
    collecting = False
    result_lines = []

    if stop_fields is None:
        stop_fields = []
    stop_set = {f.lower().rstrip(":") for f in stop_fields}

    for line in lines:
        stripped = line.strip()
        if collecting:
            # Check if we hit a stop field
            check = stripped.rstrip(":").strip().lower()
            if check in stop_set:
                break
            result_lines.append(stripped)
        elif stripped.rstrip(":").strip().lower() == field_name.lower():
            collecting = True

    if result_lines:
        return "\n".join(result_lines).strip()
    return None


def split_comma_list(text: str) -> list[str]:
    """Split comma-separated list, handling 'and' and 'or' conjunctions.

    'Bard, Sorcerer, Warlock, Wizard' -> ['Bard', 'Sorcerer', 'Warlock', 'Wizard']
    'Insight and Religion' -> ['Insight', 'Religion']
    """
    # Replace conjunctions with commas
    text = re.sub(r'\s+and\s+', ', ', text)
    text = re.sub(r'\s+or\s+', ', ', text)
    return [item.strip() for item in text.split(",") if item.strip()]


def extract_description(content: str, after_source: bool = True) -> str:
    """Extract the flavor/narrative description text.

    Typically the paragraph(s) between Source line and the first traits/mechanics section.
    """
    lines = content.split("\n")
    start = 0

    if after_source:
        for i, line in enumerate(lines):
            if line.strip().startswith("Source"):
                # Skip the source value line too
                start = i + 1
                # If source is on its own line, skip the value on the next line
                if lines[i].strip().rstrip(":").strip() == "Source":
                    start = i + 2
                break

    # Collect lines until we hit a traits/mechanics header
    desc_lines = []
    trait_headers = [
        "core ", "traits", "primary ability", "hit point die",
        "creature type", "ability scores", "prerequisite",
        "you gain the following", "feat:", "skill proficiencies",
    ]

    for i in range(start, len(lines)):
        stripped = lines[i].strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if any(lower.startswith(h) for h in trait_headers):
            break
        # Also stop at labeled field patterns
        if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+:', stripped):
            break
        desc_lines.append(stripped)

    return " ".join(desc_lines).strip()


def is_school_index(entry: dict) -> bool:
    """Check if a spell entry is a school index page (not an individual spell)."""
    return "-school" in entry.get("url", "")


def parse_choose_pattern(text: str) -> dict | None:
    """Parse 'Choose N: X, Y, Z' or 'Choose N from: X, Y, Z' patterns.

    Returns {'count': N, 'options': ['X', 'Y', 'Z']} or None.
    """
    m = re.match(r'Choose\s+(\d+)\s*(?:from\s*)?:\s*(.+)', text, re.IGNORECASE)
    if m:
        count = int(m.group(1))
        options = split_comma_list(m.group(2))
        return {"count": count, "options": options}
    return None
