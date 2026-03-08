"""Parser for feat entries from dnd2024_data.json."""

import re
from parsers.base_parser import extract_name_from_url, extract_source


def parse_prerequisites(content: str) -> dict | None:
    """Parse prerequisite line like 'Prerequisite: Level 4+, Strength 13+'."""
    lines = content.split("\n")
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("prerequisite"):
            text = re.sub(r'^prerequisite\s*:\s*', '', stripped, flags=re.IGNORECASE)
            result = {"level": None, "abilities": {}}

            # Level requirement
            level_match = re.search(r'Level\s+(\d+)\+?', text, re.IGNORECASE)
            if level_match:
                result["level"] = int(level_match.group(1))

            # Ability requirements: "Strength 13+", "Dexterity 13+"
            ability_pattern = re.findall(
                r'(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma)\s+(\d+)\+?',
                text, re.IGNORECASE,
            )
            for ability, score in ability_pattern:
                result["abilities"][ability.title()] = int(score)

            # Class requirement
            class_match = re.search(r'(Spellcasting|Pact Magic)\s+feature', text, re.IGNORECASE)
            if class_match:
                result["requires_spellcasting"] = True

            return result if result["level"] or result["abilities"] else result

    return None


def categorize_feat(prereqs: dict | None) -> str:
    """Categorize feat as origin, general, or epic_boon."""
    if prereqs is None:
        return "origin"
    level = prereqs.get("level")
    if level is None:
        return "origin"
    if level >= 19:
        return "epic_boon"
    return "general"


def parse_benefits(feat_name: str, content: str) -> list[dict]:
    """Parse feat benefits.

    Benefits follow the pattern:
        Benefit Name.
        Description text.
    Or there might just be a description for simple feats.
    """
    benefits = []
    lines = content.split("\n")

    # Find start of benefits
    start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if "you gain the following" in stripped.lower():
            start = i + 1
            break
        if stripped.lower().startswith("prerequisite"):
            start = i + 1
            # Skip the "You gain..." line if it follows
            if i + 1 < len(lines) and "you gain the following" in lines[i + 1].strip().lower():
                start = i + 2
            break

    # Also skip source line
    if start == 0:
        for i, line in enumerate(lines):
            if line.strip().startswith("Source"):
                start = i + 1
                if i + 1 < len(lines) and lines[i+1].strip().startswith("Prerequisite"):
                    start = i + 2
                break

    current_name = None
    current_desc_lines = []

    for i in range(start, len(lines)):
        stripped = lines[i].strip()
        if not stripped:
            continue

        # Skip "You gain the following benefits" line
        if "you gain the following" in stripped.lower():
            continue

        # If this is a continuation after a broken header (e.g. \n.)
        if stripped.startswith(".") and current_name and not current_desc_lines:
            stripped = stripped.lstrip(". ").strip()
            if not stripped:
                continue

        is_header = False
        header_text = ""

        # Check if this is a benefit header
        if (stripped.endswith(".") and len(stripped) < 50 and
                not stripped[0].islower() and
                stripped.count(". ") == 0):
            is_header = True
            header_text = stripped.rstrip(".")
        elif (i + 1 < len(lines) and lines[i+1].strip().startswith(".")):
            # Handle markdown quirk where the period ended up on the next line
            if len(stripped) < 50 and not stripped.endswith(".") and not stripped.startswith("."):
                is_header = True
                header_text = stripped

        if is_header:
            if current_name or current_desc_lines:
                benefits.append({
                    "name": current_name or feat_name,
                    "description": " ".join(current_desc_lines).strip(),
                })
            current_name = header_text
            current_desc_lines = []
        else:
            current_desc_lines.append(stripped)

    if current_name or current_desc_lines:
        benefits.append({
            "name": current_name or feat_name,
            "description": " ".join(current_desc_lines).strip(),
        })

    return benefits


def detect_ability_increase(benefits: list[dict]) -> str | None:
    """Detect which ability a feat increases."""
    for b in benefits:
        if "ability score increase" in b["name"].lower():
            desc = b["description"].lower()
            for ability in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
                if ability in desc:
                    return ability.title()
            # Generic "Increase one ability score of your choice"
            if "choice" in desc or "your choice" in desc:
                return "Choice"
    return None


def parse_feats(raw_data: list[dict]) -> list[dict]:
    """Parse all feat entries into structured data."""
    feats = []

    for entry in raw_data:
        url = entry["url"]
        content = entry["content"]

        if "feat:" not in url:
            continue

        name = extract_name_from_url(url)
        source = extract_source(content)

        # Prerequisites
        prereqs = parse_prerequisites(content)

        # Category
        category = categorize_feat(prereqs)

        benefits = parse_benefits(name, content)

        # Ability score increase detection
        ability_increase = detect_ability_increase(benefits)

        feats.append({
            "name": name,
            "source": source,
            "category": category,
            "prerequisites": prereqs,
            "benefits": benefits,
            "ability_score_increase": ability_increase,
        })

    return feats
