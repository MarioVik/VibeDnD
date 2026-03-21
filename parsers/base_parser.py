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
    for i, line in enumerate(lines[:3]):
        line = line.strip()
        if line.startswith("Source:"):
            value = line[len("Source:"):].strip()
            if value:
                return value
            # "Source:" on its own line — value is on the next line
            if i + 1 < len(lines) and lines[i + 1].strip():
                return lines[i + 1].strip()
        if line.startswith("Source"):
            rest = line[len("Source"):].strip().lstrip(":")
            if rest:
                return rest.strip()
            if i + 1 < len(lines) and lines[i + 1].strip():
                return lines[i + 1].strip()
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
    Some entries (e.g. Eberron backgrounds) place the description *after* all
    field headers, so if nothing is found before the headers we fall back to
    collecting trailing text.
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

    field_headers = trait_headers + [
        "tool proficiency", "equipment",
    ]

    first_header_idx = None
    for i in range(start, len(lines)):
        stripped = lines[i].strip()
        if not stripped:
            continue
        lower = stripped.lower()
        if any(lower.startswith(h) for h in trait_headers):
            first_header_idx = i
            break
        # Also stop at labeled field patterns
        if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+:', stripped):
            first_header_idx = i
            break
        desc_lines.append(stripped)

    if desc_lines:
        return " ".join(desc_lines).strip()

    # Fallback: collect trailing text after all known field headers.
    # Walk past header/value pairs (header line + one value line each),
    # then grab whatever remains as the description.
    def _is_header(line: str) -> bool:
        low = line.strip().lower()
        return (
            any(low.startswith(h) for h in field_headers)
            or bool(re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+:', line.strip()))
        )

    i = first_header_idx or start
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue
        if _is_header(stripped):
            i += 1  # skip header line
            # skip the value line(s) until next header or end
            while i < len(lines):
                s = lines[i].strip()
                if not s:
                    i += 1
                    continue
                if _is_header(s):
                    break
                i += 1  # skip value line
                break  # only consume one value line per header
        else:
            break

    tail_lines = []
    for j in range(i, len(lines)):
        stripped = lines[j].strip()
        if stripped:
            tail_lines.append(stripped)

    return " ".join(tail_lines).strip()


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
