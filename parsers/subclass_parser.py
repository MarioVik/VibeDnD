"""Parser for subclass entries from dnd2024_data.json.

Parses from three sources in priority order:
1) Dedicated class subclass pages (e.g. fighter:banneret)
2) Subclass name tables in class main pages (fallback)
3) UA subclass pages (ua:subclass-*)
"""

import re
from parsers.base_parser import extract_source, extract_description, join_description_lines
from parsers.class_parser import MAIN_CLASSES

# Valid levels at which subclasses grant expanded spells.
_VALID_SPELL_LEVELS = {3, 5, 7, 9, 13, 17}

# Hardcoded expanded spell lists for subclasses whose scraped descriptions
# have garbled HTML table formatting that cannot be reliably parsed.
# Key: subclass slug, Value: {level: [spell_name, ...]}.
_EXPANDED_SPELLS_OVERRIDES: dict[str, dict[int, list[str]]] = {
    "alchemist": {
        3: ["Healing Word", "Ray of Sickness"],
        5: ["Flaming Sphere", "Melf's Acid Arrow"],
        9: ["Gaseous Form", "Mass Healing Word"],
        13: ["Death Ward", "Vitriolic Sphere"],
        17: ["Cloudkill", "Raise Dead"],
    },
    "cartographer": {
        3: ["Faerie Fire", "Guiding Bolt"],
        5: ["Healing Word", "Locate Object", "Mind Spike"],
        9: ["Call Lightning", "Clairvoyance"],
        13: ["Banishment", "Locate Creature"],
        17: ["Scrying", "Teleportation Circle"],
    },
    "knowledge-domain": {
        3: ["Command", "Comprehend Languages", "Detect Magic",
            "Detect Thoughts", "Identify", "Mind Spike"],
        5: ["Dispel Magic", "Nondetection", "Tongues"],
        7: ["Arcane Eye", "Banishment", "Confusion"],
        9: ["Legend Lore", "Scrying", "Synaptic Static"],
    },
    "light-domain": {
        3: ["Burning Hands", "Faerie Fire", "Scorching Ray",
            "See Invisibility"],
        5: ["Daylight", "Fireball"],
        7: ["Arcane Eye", "Wall of Fire"],
        9: ["Flame Strike", "Scrying"],
    },
    "war-domain": {
        3: ["Guiding Bolt", "Magic Weapon", "Shield of Faith",
            "Spiritual Weapon"],
        5: ["Crusader's Mantle", "Spirit Guardians"],
        7: ["Fire Shield", "Freedom of Movement"],
        9: ["Hold Monster", "Steel Wind Strike"],
    },
    "circle-of-the-moon": {
        3: ["Cure Wounds", "Moonbeam", "Starry Wisp"],
        5: ["Conjure Animals"],
        7: ["Fount of Moonlight"],
        9: ["Mass Cure Wounds"],
    },
    "circle-of-the-titan": {
        3: ["Cure Wounds", "Longstrider", "Thaumaturgy"],
        5: ["Fear"],
        7: ["Stoneskin"],
        9: ["Destructive Wave"],
    },
    "circle-of-preservation": {
        3: ["Bless", "Lesser Restoration", "Protection from Poison",
            "Sanctuary"],
        5: ["Beacon of Hope", "Plant Growth"],
        7: ["Aura of Life", "Death Ward"],
        9: ["Greater Restoration", "Hallow"],
    },
    "oath-of-the-ancients": {
        3: ["Ensnaring Strike", "Speak with Animals"],
        5: ["Misty Step", "Moonbeam"],
        9: ["Protection from Energy", "Plant Growth"],
        13: ["Ice Storm", "Stoneskin"],
        17: ["Commune with Nature", "Tree Stride"],
    },
    "oath-of-the-noble-genies": {
        3: ["Chromatic Orb", "Elementalism", "Thunderous Smite"],
        5: ["Mirror Image", "Phantasmal Force"],
        9: ["Fly", "Gaseous Form"],
        13: ["Conjure Minor Elementals", "Summon Elemental"],
        17: ["Banishing Smite", "Contact Other Plane"],
    },
    "oathbreaker": {
        3: ["Hellish Rebuke", "Witch Bolt"],
        5: ["Crown of Madness", "Darkness"],
        9: ["Fear", "Summon Undead"],
        13: ["Blight", "Phantasmal Killer"],
        17: ["Contagion", "Steel Wind Strike"],
    },
    "fey-wanderer": {
        3: ["Charm Person"],
        5: ["Misty Step"],
        9: ["Summon Fey"],
        13: ["Dimension Door"],
        17: ["Mislead"],
    },
    "gloom-stalker": {
        3: ["Disguise Self"],
        5: ["Rope Trick"],
        9: ["Fear"],
        13: ["Greater Invisibility"],
        17: ["Seeming"],
    },
    "winter-walker": {
        3: ["Ice Knife"],
        5: ["Hold Person"],
        9: ["Remove Curse"],
        13: ["Ice Storm"],
        17: ["Cone of Cold"],
    },
    "aberrant-sorcery": {
        3: ["Arms of Hadar", "Calm Emotions", "Detect Thoughts",
            "Dissonant Whispers", "Mind Sliver"],
        5: ["Hunger of Hadar", "Sending"],
        7: ["Evard's Black Tentacles", "Summon Aberration"],
        9: ["Rary's Telepathic Bond", "Telekinesis"],
    },
    "clockwork-sorcery": {
        3: ["Aid", "Alarm", "Lesser Restoration",
            "Protection from Evil and Good"],
        5: ["Dispel Magic", "Protection from Energy"],
        7: ["Freedom of Movement", "Summon Construct"],
        9: ["Greater Restoration", "Wall of Force"],
    },
    "archfey-patron": {
        3: ["Calm Emotions", "Faerie Fire", "Misty Step",
            "Phantasmal Force", "Sleep"],
        5: ["Blink", "Plant Growth"],
        7: ["Dominate Beast", "Greater Invisibility"],
        9: ["Dominate Person", "Seeming"],
    },
    "celestial-patron": {
        3: ["Aid", "Cure Wounds", "Guiding Bolt",
            "Lesser Restoration", "Light", "Sacred Flame"],
        5: ["Daylight", "Revivify"],
        7: ["Guardian of Faith", "Wall of Fire"],
        9: ["Greater Restoration", "Summon Celestial"],
    },
    "reanimator": {
        3: ["False Life", "Spare the Dying", "Witch Bolt"],
        5: ["Blindness/Deafness", "Enhance Ability"],
        9: ["Animate Dead", "Lightning Bolt"],
        13: ["Blight", "Death Ward"],
        17: ["Antilife Shell", "Raise Dead"],
    },
    "grave-domain": {
        3: ["Bane", "Chill Touch", "Detect Evil and Good",
            "Gentle Repose", "Ray of Enfeeblement"],
        5: ["Revivify", "Vampiric Touch"],
        7: ["Blight", "Dispel Evil and Good"],
        9: ["Hold Monster", "Raise Dead"],
    },
    "ancestral-sorcery": {
        3: ["Command", "Guidance", "Locate Object",
            "Protection from Evil and Good", "Resistance",
            "Spiritual Weapon"],
        5: ["Magic Circle", "Spirit Guardians"],
        7: ["Divination", "Locate Creature"],
        9: ["Legend Lore", "Yolande's Regal Presence"],
    },
    "sorcerer-king-patron": {
        3: ["Command", "Compelled Duel", "Hold Person",
            "Mind Spike", "Wrathful Smite"],
        5: ["Fear", "Sending"],
        7: ["Compulsion", "Staggering Smite"],
        9: ["Dominate Person", "Synaptic Static"],
    },
}


def _extract_expanded_spells(features_by_level: dict[int, list[dict]], slug: str) -> dict[str, list[str]] | None:
    """Extract expanded/patron spell lists from subclass feature descriptions.

    Returns ``{level_str: [spell_name, ...]}`` or ``None`` if no expanded
    spells feature is found.  The key is a string (e.g. ``"3"``) so it
    matches the JSON convention used elsewhere.

    Strategy:
    1. Use a hardcoded override if available (for garbled HTML scrapes).
    2. Otherwise, parse the clean comma-separated format from the description.
    """
    # Check hardcoded overrides first
    if slug in _EXPANDED_SPELLS_OVERRIDES:
        return {str(k): v for k, v in _EXPANDED_SPELLS_OVERRIDES[slug].items()}

    # Look for the feature that describes expanded spells
    for level, feats in features_by_level.items():
        for feat in feats:
            desc = feat.get("description", "")
            lower = desc.lower()
            if ("always have the listed spells prepared" not in lower
                    and "always have certain spells ready" not in lower):
                continue
            return _parse_clean_expanded_spells(desc)
    return None


def _parse_clean_expanded_spells(desc: str) -> dict[str, list[str]] | None:
    """Parse: '... Level Spells 3 SpellA , SpellB 5 SpellC , ...'"""
    m = re.search(
        r"Level\s+(?:Prepared\s+)?Spells?\s+(\d.+)",
        desc,
        re.IGNORECASE,
    )
    if not m:
        return None
    table_text = m.group(1).strip().split("\n")[0].strip()
    if " , " not in table_text:
        return None

    result: dict[int, list[str]] = {}
    current_level: int | None = None
    level_pattern = "|".join(str(l) for l in sorted(_VALID_SPELL_LEVELS))

    parts = table_text.split(" , ")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Split on embedded level transitions (e.g. "Suggestion 5 Fireball")
        segments = re.split(
            r"\s+(?=(?:" + level_pattern + r")\s)", part
        )
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
            m2 = re.match(r"^(\d+)\s+(.*)", segment)
            if m2 and int(m2.group(1)) in _VALID_SPELL_LEVELS:
                current_level = int(m2.group(1))
                result[current_level] = []
                spell = m2.group(2).strip()
                if spell:
                    result[current_level].append(spell)
            elif current_level is not None:
                result[current_level].append(segment)

    # Clean up: strip trailing commas/whitespace
    for lv in list(result):
        result[lv] = [
            s.strip().rstrip(" ,")
            for s in result[lv]
            if len(s.strip().rstrip(" ,")) > 1
        ]

    if not result or not all(len(v) > 0 for v in result.values()):
        return None
    return {str(k): v for k, v in result.items()}


# Sources that are considered official (non-UA) even if in the ua section.
# When a subclass from one of these sources duplicates a PHB entry,
# the richer version from this source replaces the PHB name-only entry.
OFFICIAL_SOURCES = {
    "Player's Handbook",
    "Eberron - Forge of the Artificer",
    "Forgotten Realms Subclasses UA (28.01.2025)",
    "Forgotten Realms - Heroes of Faerun",
}

# Map URL class slugs to standard class names
CLASS_SLUG_MAP = {
    "artificer": "artificer",
    "barbarian": "barbarian",
    "bard": "bard",
    "cleric": "cleric",
    "druid": "druid",
    "fighter": "fighter",
    "monk": "monk",
    "paladin": "paladin",
    "ranger": "ranger",
    "rogue": "rogue",
    "sorcerer": "sorcerer",
    "warlock": "warlock",
    "wizard": "wizard",
}

NON_SUBCLASS_SUFFIXES = {
    "main",
    "spell-list",
    "metamagic",
    "eldritch-invocation",
}

# Explicit alias map for known UA/official naming differences.
# Key/value are (class_slug, normalized_name)
ALIAS_CANONICAL = {
    ("fighter", "purple dragon knight"): ("fighter", "banneret"),
}


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _canonical_key(class_slug: str, name: str) -> tuple[str, str]:
    key = (class_slug, _normalize_name(name))
    return ALIAS_CANONICAL.get(key, key)


def _display_name_from_slug(slug: str) -> str:
    return slug.replace("-", " ").title()


def _parse_subclass_features(content: str) -> dict[int, list[dict]]:
    """Parse 'Level N: Feature Name' blocks from subclass content."""
    lines = content.split("\n")
    features_by_level = {}
    current_level = None
    current_name = None
    current_desc_lines = []

    def _save_current():
        if current_level is not None and current_name:
            features_by_level.setdefault(current_level, [])
            features_by_level[current_level].append(
                {
                    "name": current_name,
                    "description": join_description_lines(current_desc_lines),
                }
            )

    for line in lines:
        stripped = line.strip()

        m = re.match(r"^Level\s+(\d+)\s*:\s*(.+)", stripped)
        if m:
            _save_current()
            current_level = int(m.group(1))
            current_name = m.group(2).strip()
            current_desc_lines = []
        elif current_name is not None:
            current_desc_lines.append(stripped)

    _save_current()
    return features_by_level


def _parse_class_subclass_pages(class_subclass_data: list[dict]) -> list[dict]:
    """Parse dedicated subclass pages like fighter:banneret."""
    subclasses = []

    for entry in class_subclass_data:
        url = entry.get("url", "")
        url_part = url.rsplit("/", 1)[-1]
        if ":" not in url_part:
            continue

        class_slug, subclass_slug = url_part.split(":", 1)
        if class_slug not in CLASS_SLUG_MAP:
            continue
        if subclass_slug in NON_SUBCLASS_SUFFIXES:
            continue

        content = entry.get("content", "")
        source = extract_source(content)
        description = extract_description(content)
        features_by_level = _parse_subclass_features(content)

        title = entry.get("title", "").strip()
        if title and title != "Unknown":
            display_name = title
        else:
            display_name = _display_name_from_slug(subclass_slug)

        entry_data = {
            "name": display_name,
            "slug": subclass_slug,
            "class_slug": class_slug,
            "source": source,
            "description": description,
            "feature_levels": sorted(features_by_level.keys()),
            "features": {str(k): v for k, v in features_by_level.items()},
        }
        expanded = _extract_expanded_spells(features_by_level, subclass_slug)
        if expanded:
            entry_data["expanded_spells"] = expanded
        subclasses.append(entry_data)

    return subclasses


def _parse_phb_subclasses(class_data: list[dict]) -> list[dict]:
    """Extract PHB subclass names from class main pages.

    These pages list subclass names in a table after '{Class} Subclasses' header,
    but don't include detailed feature descriptions.
    """
    subclasses = []

    for entry in class_data:
        url = entry.get("url", "")
        if ":main" not in url:
            continue

        class_slug = url.rsplit("/", 1)[-1].split(":")[0]
        if class_slug not in CLASS_SLUG_MAP:
            continue

        content = entry["content"]
        source = extract_source(content)
        lines = content.split("\n")

        # Find '{Class} Subclasses' section header
        class_title = class_slug.title()
        in_section = False
        for i, line in enumerate(lines):
            stripped = line.strip()

            if stripped == f"{class_title} Subclasses":
                in_section = True
                continue

            if in_section:
                # Skip the "Name" column header
                if stripped == "Name":
                    continue
                # Stop at next section (Level lines, empty, or long text >60 chars)
                if not stripped or stripped.startswith("Level ") or len(stripped) > 60:
                    break
                # Skip if next line is a long sentence (flavor text heading, not table)
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                if len(next_line) > 60:
                    break
                subclasses.append(
                    {
                        "name": stripped,
                        "slug": stripped.lower().replace(" ", "-"),
                        "class_slug": class_slug,
                        "source": source,
                        "description": "",
                        "feature_levels": [],
                        "features": {},
                    }
                )

    return subclasses


def parse_subclasses(
    ua_data: list[dict],
    class_data: list[dict] | None = None,
    class_subclass_data: list[dict] | None = None,
) -> list[dict]:
    """Parse subclass entries from both PHB class pages and UA data.

    PHB subclasses (from class_data) provide names only.
    UA subclasses (from ua_data) have full feature details.
    When both exist for the same subclass, the official (PHB/Eberron) version
    is kept and the UA version is discarded.
    """
    seen: dict[tuple[str, str], dict] = {}
    seen_priority: dict[tuple[str, str], int] = {}

    # 1. Dedicated class subclass pages (official, detailed)
    if class_subclass_data:
        for sc in _parse_class_subclass_pages(class_subclass_data):
            key = _canonical_key(sc["class_slug"], sc["name"])
            seen[key] = sc
            seen_priority[key] = 3

    # 2. PHB/main page subclass names (fallback, name-only)
    if class_data:
        for sc in _parse_phb_subclasses(class_data):
            key = _canonical_key(sc["class_slug"], sc["name"])
            if key not in seen:
                seen[key] = sc
                seen_priority[key] = 1

    # 3. UA subclasses (detailed)
    for entry in ua_data:
        url = entry["url"]

        if "subclass-" not in url:
            continue

        # Parse URL: ua:subclass-{class}-{slug}
        url_part = url.rsplit("/", 1)[-1]
        remainder = url_part.replace("ua:subclass-", "")
        parts = remainder.split("-", 1)
        if len(parts) < 2:
            continue

        class_slug = parts[0]
        subclass_slug = parts[1]

        # Skip non-standard classes (psion, magic-stealer, etc.)
        if class_slug not in CLASS_SLUG_MAP:
            continue

        content = entry["content"]
        source = extract_source(content)
        description = extract_description(content)

        # Parse features by level
        features_by_level = _parse_subclass_features(content)
        feature_levels = sorted(features_by_level.keys())

        # Build display name from slug
        display_name = _display_name_from_slug(subclass_slug.rstrip("0123456789"))

        entry_data = {
            "name": display_name,
            "slug": subclass_slug,
            "class_slug": class_slug,
            "source": source,
            "description": description,
            "feature_levels": feature_levels,
            "features": {str(k): v for k, v in features_by_level.items()},
        }
        expanded = _extract_expanded_spells(features_by_level, subclass_slug)
        if expanded:
            entry_data["expanded_spells"] = expanded

        key = _canonical_key(class_slug, display_name)
        existing_prio = seen_priority.get(key, 0)

        if existing_prio >= 2:
            # Already have an official entry (detailed or promoted).
            continue

        if existing_prio == 1:
            # Replace name-only fallback if this UA source is considered official.
            if source in OFFICIAL_SOURCES:
                seen[key] = entry_data
                seen_priority[key] = 2
            continue

        # No existing entry; include UA entry.
        seen[key] = entry_data
        seen_priority[key] = 0

    return list(seen.values())
