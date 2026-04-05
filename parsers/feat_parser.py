"""Parser for feat entries from dnd2024_data.json."""

import re

from parsers.base_parser import extract_name_from_url, extract_source, join_description_lines

FEAT_CATEGORY_BY_FAMILY_HEADING = {
    "origin feats": "origin",
    "general feats": "general",
    "fighting style feats": "fighting_style",
    "epic boon feats": "epic_boon",
    "dragonmark feats": "dragonmark",
    "greater dragonmark feats": "greater_dragonmark",
}


def _normalize_heading(text: str) -> str:
    return " ".join(str(text or "").strip().rstrip(":").split()).lower()


def _normalize_tag(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())


def _category_from_page_tag(tag: str) -> str | None:
    normalized = _normalize_tag(tag)
    if normalized.endswith("greaterdragonmarkfeat"):
        return "greater_dragonmark"
    if normalized.endswith("dragonmarkfeat"):
        return "dragonmark"
    if normalized.endswith("epicboonfeat"):
        return "epic_boon"
    if normalized.endswith("fightingstylefeat"):
        return "fighting_style"
    if normalized.endswith("originfeat"):
        return "origin"
    if normalized.endswith("generalfeat"):
        return "general"
    return None


def _extract_prerequisite_text(content: str) -> str | None:
    match = re.search(r"Prerequisite\s*:\s*([^\n)]+)", content, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def parse_prerequisites(content: str) -> dict | None:
    """Parse prerequisite text like 'Level 4+, Strength 13+'."""
    text = _extract_prerequisite_text(content)
    if not text:
        return None

    result = {
        "text": text,
        "level": None,
        "abilities": {},
    }

    # Level requirement
    level_match = re.search(r"Level\s+(\d+)\+?", text, re.IGNORECASE)
    if level_match:
        result["level"] = int(level_match.group(1))

    # Ability requirements: "Strength 13+", "Dexterity 13+"
    ability_pattern = re.findall(
        r"(Strength|Dexterity|Constitution|Intelligence|Wisdom|Charisma)\s+(\d+)\+?",
        text,
        re.IGNORECASE,
    )
    for ability, score in ability_pattern:
        result["abilities"][ability.title()] = int(score)

    # Class requirement
    class_match = re.search(r"(Spellcasting|Pact Magic)\s+feature", text, re.IGNORECASE)
    if class_match:
        result["requires_spellcasting"] = True

    return result


def resolve_feat_category(entry: dict, feat_name: str) -> str:
    """Resolve the feat category from explicit scraped metadata."""
    family_heading = str(entry.get("feat_family_heading", "") or "").strip()
    if not family_heading:
        raise ValueError(
            f"Feat '{feat_name}' is missing feat_family_heading metadata in dnd2024_data.json."
        )

    heading_category = FEAT_CATEGORY_BY_FAMILY_HEADING.get(_normalize_heading(family_heading))
    if not heading_category:
        raise ValueError(
            f"Feat '{feat_name}' has unknown feat_family_heading '{family_heading}'."
        )

    page_tags = entry.get("page_tags")
    if not isinstance(page_tags, list) or not page_tags:
        raise ValueError(
            f"Feat '{feat_name}' is missing page_tags metadata in dnd2024_data.json."
        )

    tag_categories = {
        category
        for category in (_category_from_page_tag(tag) for tag in page_tags)
        if category
    }
    if not tag_categories:
        raise ValueError(
            f"Feat '{feat_name}' has no recognized feat category tag in page_tags={page_tags!r}."
        )
    if len(tag_categories) > 1:
        raise ValueError(
            f"Feat '{feat_name}' has conflicting feat category tags in page_tags={page_tags!r}."
        )

    tag_category = next(iter(tag_categories))
    if tag_category != heading_category:
        # The wiki index page groups all dragonmark feats under one "Dragonmark Feats"
        # heading, but page tags distinguish dragonmark vs greater_dragonmark.
        # Trust the more specific page tag in this known hierarchy.
        if heading_category == "dragonmark" and tag_category == "greater_dragonmark":
            return tag_category
        raise ValueError(
            f"Feat '{feat_name}' category mismatch: "
            f"feat_family_heading '{family_heading}' -> '{heading_category}', "
            f"page_tags {page_tags!r} -> '{tag_category}'."
        )
    return heading_category


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
                    "description": join_description_lines(current_desc_lines),
                })
            current_name = header_text
            current_desc_lines = []
        else:
            current_desc_lines.append(stripped)

    if current_name or current_desc_lines:
        benefits.append({
            "name": current_name or feat_name,
            "description": join_description_lines(current_desc_lines),
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

        # Category comes from explicit feat-index family metadata plus page tags.
        category = resolve_feat_category(entry, name)

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
