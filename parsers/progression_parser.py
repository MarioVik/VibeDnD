"""Parser for full level 1-20 class progression tables from dnd2024_data.json."""

import re
from parsers.class_parser import MAIN_CLASSES, CASTER_TYPES

# Standard spell slot columns
SPELL_SLOT_HEADERS = {"1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th"}

# Known non-feature, non-spell extra columns per class
EXTRA_COLUMNS = {
    "barbarian": ["Rages", "Rage Damage", "Weapon Mastery"],
    "bard": ["Bardic Die"],
    "fighter": ["Second Wind", "Weapon Mastery"],
    "monk": ["Martial Arts", "Focus Points", "Unarmored Movement"],
    "rogue": ["Sneak Attack"],
    "sorcerer": ["Sorcery Points"],
    # Part B extras (non-spell columns after Level)
    "artificer_b": ["Plans Known", "Magic Items"],
    "cleric_b": ["Channel Divinity"],
    "druid_b": ["Wild Shape"],
    "paladin_b": ["Channel Divinity"],
    "ranger_b": ["Favored Enemy"],
    "warlock_b": ["Eldritch Invocations"],
}


def _find_all_level_tables(lines: list[str]) -> list[int]:
    """Find the starting line index of every 'Level' table header."""
    indices = []
    for i, line in enumerate(lines):
        if line.strip() == "Level" and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if nxt and nxt not in ("1",):
                indices.append(i)
    return indices


def _read_table_headers(lines: list[str], header_idx: int) -> tuple[list[str], int]:
    """Read header lines from a table, return (headers, data_start_index)."""
    headers = []
    data_start = None
    for i in range(header_idx, len(lines)):
        stripped = lines[i].strip()
        if stripped.isdigit() and int(stripped) >= 1:
            data_start = i
            break
        if stripped:
            headers.append(stripped)
    return headers, data_start


def _classify_headers(headers: list[str]) -> dict:
    """Classify table headers into categories."""
    result = {
        "has_prof_bonus": "Proficiency Bonus" in headers,
        "has_features": any(h in ("Features", "Class Features") for h in headers),
        "has_cantrips": "Cantrips" in headers,
        "has_prepared": "Prepared Spells" in headers,
        "slot_levels": [h for h in headers if h in SPELL_SLOT_HEADERS],
        "has_pact_slots": "Spell Slots" in headers,
        "has_slot_level": "Slot Level" in headers,
        "extra_cols": [],
    }

    # Identify extra columns (not Level, Prof Bonus, Features, or spell-related)
    skip = {"Level", "Proficiency Bonus", "Features", "Class Features",
            "Cantrips", "Prepared Spells", "Spell Slots", "Slot Level"}
    skip.update(SPELL_SLOT_HEADERS)
    result["extra_cols"] = [h for h in headers if h not in skip]

    return result


def _is_level_marker(lines: list[str], idx: int, expected_level: int) -> bool:
    """Check if lines[idx] is a level marker (bare integer matching expected)."""
    stripped = lines[idx].strip()
    if not stripped.isdigit():
        return False
    level = int(stripped)
    if level != expected_level:
        return False
    # Verify: next non-empty line should be +N (proficiency bonus) or a feature/value
    for j in range(idx + 1, min(idx + 5, len(lines))):
        nxt = lines[j].strip()
        if not nxt or nxt == ",":
            continue
        if nxt.startswith("+"):
            return True
        # For Part B tables without prof bonus, check it's a valid value
        if nxt == "-" or nxt.isdigit():
            return True
        # Feature name - this is likely a row value, not a level marker
        return True
    return False


def _read_all_rows(lines: list[str], data_start: int, header_info: dict,
                    end_idx: int | None = None) -> list[dict]:
    """Read all 20 level rows from a table."""
    if end_idx is None:
        end_idx = len(lines)

    # For tables WITHOUT features (Part B), use fixed column count
    if not header_info["has_features"]:
        return _read_fixed_column_rows(lines, data_start, header_info, end_idx)

    # For tables WITH features, use prof bonus detection for row boundaries
    return _read_feature_rows(lines, data_start, header_info, end_idx)


def _read_fixed_column_rows(lines: list[str], data_start: int,
                             header_info: dict, end_idx: int) -> list[dict]:
    """Read rows from a fixed-column table (Part B, no features)."""
    # Count columns: Level + extras + spell columns
    n_cols = 1 + len(header_info["extra_cols"])
    if header_info["has_cantrips"]:
        n_cols += 1
    if header_info["has_prepared"]:
        n_cols += 1
    n_cols += len(header_info["slot_levels"])
    if header_info["has_pact_slots"]:
        n_cols += 1
    if header_info["has_slot_level"]:
        n_cols += 1

    # Collect all non-empty values
    all_values = []
    for i in range(data_start, end_idx):
        stripped = lines[i].strip()
        if not stripped or stripped == ",":
            continue
        if re.match(r'^Level\s+\d+\s*:', stripped):
            break
        if re.match(r'^.+Features\s*\(Part\s+[AB]\)', stripped):
            break
        all_values.append(stripped)

    # Split into rows of n_cols each
    rows = []
    for r in range(0, len(all_values), n_cols):
        chunk = all_values[r:r + n_cols]
        if len(chunk) == n_cols:
            rows.append(_parse_row_values(chunk, header_info))

    return rows


def _read_feature_rows(lines: list[str], data_start: int,
                        header_info: dict, end_idx: int) -> list[dict]:
    """Read rows from a table with variable-length features column."""
    rows = []
    current_level = 1
    current_values = []
    i = data_start

    while i < end_idx and current_level <= 20:
        stripped = lines[i].strip()

        # Skip empty lines and lone commas
        if not stripped or stripped == ",":
            i += 1
            continue

        # Stop if we hit feature descriptions, Part B label, or prose text
        if re.match(r'^Level\s+\d+\s*:', stripped):
            break
        if re.match(r'^.+Features\s*\(Part\s+[AB]\)', stripped):
            break
        # Long lines (>60 chars) are prose, not table data
        if len(stripped) > 60:
            break

        # Check if this is the start of the next level
        # Verify with prof bonus look-ahead
        if (stripped.isdigit() and int(stripped) == current_level + 1
                and len(current_values) > 1):
            # Confirm by checking next non-empty line is +N
            is_level = False
            for j in range(i + 1, min(i + 4, len(lines))):
                nxt = lines[j].strip()
                if not nxt or nxt == ",":
                    continue
                is_level = bool(re.match(r'^\+\d+$', nxt))
                break

            if is_level:
                rows.append(_parse_row_values(current_values, header_info))
                current_level += 1
                current_values = [stripped]
                i += 1
                continue

        current_values.append(stripped)
        i += 1

    # Save last row
    if current_values:
        rows.append(_parse_row_values(current_values, header_info))

    return rows


def _parse_row_values(values: list[str], header_info: dict) -> dict:
    """Parse a list of raw values for a single level row into structured data."""
    row = {}
    idx = 0

    # Level number
    if idx < len(values):
        row["level"] = int(values[idx])
        idx += 1

    # Proficiency bonus (if present in this table)
    if header_info["has_prof_bonus"] and idx < len(values):
        pb = values[idx]
        row["proficiency_bonus"] = int(pb.replace("+", "")) if pb.startswith("+") else 2
        idx += 1

    # Features (if present) - collect until we hit numeric/dash trailing columns
    if header_info["has_features"]:
        features = []
        # Count expected trailing columns
        n_extra = len(header_info["extra_cols"])
        n_spell = (1 if header_info["has_cantrips"] else 0) + \
                  (1 if header_info["has_prepared"] else 0) + \
                  len(header_info["slot_levels"]) + \
                  (1 if header_info["has_pact_slots"] else 0) + \
                  (1 if header_info["has_slot_level"] else 0)
        n_trailing = n_extra + n_spell

        # Everything between prof bonus and trailing columns is features
        remaining = values[idx:]
        if n_trailing > 0 and len(remaining) > n_trailing:
            feature_values = remaining[:-n_trailing]
            trailing = remaining[-n_trailing:]
        else:
            feature_values = remaining
            trailing = []

        # Join feature names (they're separated by commas on separate lines)
        feature_text = ""
        for fv in feature_values:
            if fv == ",":
                feature_text += ", "
            elif feature_text and not feature_text.endswith(", "):
                feature_text += ", " + fv
            else:
                feature_text += fv

        features = [f.strip() for f in feature_text.split(",") if f.strip() and f.strip() != "-"]
        row["features"] = features

        # Parse trailing columns
        _parse_trailing(row, trailing, header_info)
    else:
        # No features column (Part B tables) - everything after level is values
        remaining = values[idx:]
        _parse_trailing_partb(row, remaining, header_info)

    return row


def _parse_trailing(row: dict, trailing: list[str], header_info: dict) -> None:
    """Parse trailing numeric columns from a features table row."""
    idx = 0

    # Extra columns (class-specific like Rages, Bardic Die, etc.)
    extras = {}
    for col_name in header_info["extra_cols"]:
        if idx < len(trailing):
            val = trailing[idx]
            extras[col_name] = _parse_numeric(val)
            idx += 1
    if extras:
        row["extra"] = extras

    # Spell columns
    _parse_spell_cols(row, trailing[idx:], header_info)


def _parse_trailing_partb(row: dict, remaining: list[str], header_info: dict) -> None:
    """Parse Part B table row (no features, all numeric columns)."""
    idx = 0

    # Extra columns
    extras = {}
    for col_name in header_info["extra_cols"]:
        if idx < len(remaining):
            extras[col_name] = _parse_numeric(remaining[idx])
            idx += 1
    if extras:
        row["extra"] = extras

    # Spell columns
    _parse_spell_cols(row, remaining[idx:], header_info)


def _parse_spell_cols(row: dict, values: list[str], header_info: dict) -> None:
    """Parse spell-related columns (cantrips, prepared, slots)."""
    idx = 0

    if header_info["has_cantrips"]:
        if idx < len(values):
            row["cantrips"] = _parse_numeric(values[idx])
            idx += 1

    if header_info["has_prepared"]:
        if idx < len(values):
            row["prepared_spells"] = _parse_numeric(values[idx])
            idx += 1

    if header_info["slot_levels"]:
        slots = {}
        for level_name in header_info["slot_levels"]:
            if idx < len(values):
                val = _parse_numeric(values[idx])
                if val is not None and isinstance(val, int) and val > 0:
                    slots[level_name] = val
                idx += 1
        if slots:
            row["spell_slots"] = slots

    # Warlock pact magic
    if header_info["has_pact_slots"]:
        if idx < len(values):
            row["pact_slots"] = _parse_numeric(values[idx])
            idx += 1

    if header_info["has_slot_level"]:
        if idx < len(values):
            row["pact_slot_level"] = _parse_numeric(values[idx])
            idx += 1


def _parse_numeric(val: str) -> int | None:
    """Parse a numeric value, treating '-' as None."""
    val = val.strip()
    if val == "-" or not val:
        return None
    # Handle values like "1d6", "1d8" etc. for dice columns
    if "d" in val.lower():
        return val
    try:
        return int(val)
    except ValueError:
        return val


def _parse_feature_descriptions(content: str) -> dict[int, list[dict]]:
    """Parse 'Level N: Feature Name' description blocks for all levels."""
    lines = content.split("\n")
    features_by_level = {}
    current_level = None
    current_name = None
    current_desc_lines = []

    # Find the start of feature descriptions (after the table)
    desc_start = None
    for i, line in enumerate(lines):
        m = re.match(r'^Level\s+(\d+)\s*:\s*(.+)', line.strip())
        if m:
            desc_start = i
            break

    if desc_start is None:
        return features_by_level

    def _save_current():
        if current_level is not None and current_name:
            features_by_level.setdefault(current_level, [])
            features_by_level[current_level].append({
                "name": current_name,
                "description": " ".join(current_desc_lines).strip(),
            })

    for i in range(desc_start, len(lines)):
        stripped = lines[i].strip()
        if not stripped:
            continue

        m = re.match(r'^Level\s+(\d+)\s*:\s*(.+)', stripped)
        if m:
            _save_current()
            current_level = int(m.group(1))
            current_name = m.group(2).strip()
            current_desc_lines = []
        elif current_name is not None:
            current_desc_lines.append(stripped)

    _save_current()
    return features_by_level


def _extract_subclass_list(content: str, class_name: str) -> list[str]:
    """Extract the list of subclass names from the class page content."""
    lines = content.split("\n")
    subclasses = []

    # Look for "X Subclasses" section with a Name header
    in_subclass_list = False
    past_name_header = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Detect subclass list section
        if re.match(rf'{class_name}\s+Subclass(es)?$', stripped, re.IGNORECASE):
            in_subclass_list = True
            continue

        if in_subclass_list:
            if stripped == "Name":
                past_name_header = True
                continue
            if past_name_header:
                # Stop at next section (Level X:, long prose, or non-name patterns)
                if re.match(r'^Level\s+\d+', stripped):
                    break
                if len(stripped) > 40:
                    break
                # Subclass names typically start with title-cased words
                if stripped and not stripped.startswith("Source") and len(stripped) > 1:
                    # Skip if it looks like a section header rather than a name
                    if stripped.startswith("Breaking") or stripped.startswith("A "):
                        break
                    subclasses.append(stripped)

    return subclasses


def parse_progressions(raw_data: list[dict]) -> list[dict]:
    """Parse full 1-20 level progression for all main classes."""
    progressions = []

    for entry in raw_data:
        url = entry["url"]

        if ":main" not in url:
            continue

        slug = url.rsplit("/", 1)[-1].split(":")[0].lower()
        if slug not in MAIN_CLASSES:
            continue

        content = entry["content"]
        lines = content.split("\n")

        # Extract class name
        name_match = re.search(r'Core\s+(\w+)\s+Traits', content)
        name = name_match.group(1) if name_match else slug.title()

        # Find all level tables
        table_starts = _find_all_level_tables(lines)
        if not table_starts:
            continue

        # Parse each table
        tables = []
        for t_idx, header_idx in enumerate(table_starts):
            headers, data_start = _read_table_headers(lines, header_idx)
            if data_start is None:
                continue

            header_info = _classify_headers(headers)

            # Determine table label (Part A, Part B, or single)
            label = "main"
            if len(table_starts) > 1:
                label = "part_a" if t_idx == 0 else "part_b"

            # End boundary: next table start or end of content
            end_idx = table_starts[t_idx + 1] if t_idx + 1 < len(table_starts) else None
            rows = _read_all_rows(lines, data_start, header_info, end_idx)
            tables.append({
                "label": label,
                "headers": headers,
                "rows": rows,
            })

        # Parse feature descriptions for all levels
        feature_descriptions = _parse_feature_descriptions(content)

        # Extract subclass list
        subclass_names = _extract_subclass_list(content, name)

        # Merge tables into unified level progression
        levels = _merge_tables(tables)

        # Attach feature descriptions
        for level_data in levels:
            lvl = level_data["level"]
            if lvl in feature_descriptions:
                level_data["feature_details"] = feature_descriptions[lvl]

        progressions.append({
            "name": name,
            "slug": slug,
            "caster_type": CASTER_TYPES.get(slug),
            "levels": levels,
            "subclass_names": subclass_names,
        })

    return progressions


def _merge_tables(tables: list[dict]) -> list[dict]:
    """Merge Part A and Part B tables (or single table) into unified level list."""
    if len(tables) == 1:
        return tables[0]["rows"]

    # Multiple tables: Part A has features, Part B has spell/numeric data
    part_a_rows = {}
    for t in tables:
        if t["label"] == "part_a":
            for row in t["rows"]:
                part_a_rows[row.get("level")] = row

    # Merge Part B data into Part A rows
    for t in tables:
        if t["label"] == "part_b":
            for row in t["rows"]:
                lvl = row.get("level")
                if lvl in part_a_rows:
                    # Merge spell data and extras from Part B
                    for key in ("cantrips", "prepared_spells", "spell_slots",
                                "pact_slots", "pact_slot_level"):
                        if key in row:
                            part_a_rows[lvl][key] = row[key]
                    # Merge extra columns
                    if "extra" in row:
                        part_a_rows[lvl].setdefault("extra", {}).update(row["extra"])
                else:
                    part_a_rows[lvl] = row

    return [part_a_rows[lvl] for lvl in sorted(part_a_rows.keys())]
