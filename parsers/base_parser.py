"""Shared parsing utilities for all category parsers."""

import re


def _is_subheading(line: str) -> bool:
    """Detect sub-headings like 'Plans Known.' or 'Creating an Item.'"""
    return (
        len(line) < 50
        and line.endswith(".")
        and line[0].isupper()
        and line.count(".") == 1
        and len(line.split()) <= 4
        and not line.startswith("See ")
    )


_TABLE_VALUE_PATTERN = re.compile(r"^(Yes|No|Varies)$", re.IGNORECASE)


def _looks_like_table_header(line: str) -> bool:
    """Detect short table header labels."""
    text = line.strip()
    if not text or text.startswith("•"):
        return False
    if len(text) > 32:
        return False
    if re.match(r"^Level\s+\d+\s*:", text):
        return False
    if text.endswith((".", ":", ";", "?", "!")):
        return False
    return True


def _looks_like_table_value(line: str) -> bool:
    """Detect short table cell values (numbers, yes/no, short labels)."""
    text = line.strip()
    if not text or text.startswith("•"):
        return False
    if len(text) > 40:
        return False
    if re.match(r"^Level\s+\d+\s*:", text):
        return False
    if text.endswith((".", ":", ";", "?", "!")):
        return False
    if re.match(r"^(See|You|When|As|For|To|The|If|Once|Whenever|While)\b", text):
        return False
    return True


def _has_table_header_keywords(headers: list[str]) -> bool:
    """Check whether header labels look table-like."""
    header_text = " ".join(h.lower() for h in headers)
    keywords = (
        "level",
        "cost",
        "known",
        "max",
        "min",
        "speed",
        "slot",
        "point",
        "attunement",
        "forms",
        "cr",
        "plan",
    )
    return any(k in header_text for k in keywords)


def _format_subclass_name_lists(lines: list[str]) -> list[str]:
    """Format 'X Subclasses' + Name + items blocks as bullets."""
    result: list[str] = []
    i = 0

    while i < len(lines):
        title = lines[i].strip()

        if re.match(r"^.+\sSubclasses$", title):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1

            if j < len(lines) and lines[j].strip() == "Name":
                k = j + 1
                items: list[str] = []

                while k < len(lines):
                    item = lines[k].strip()
                    if not item:
                        break
                    if item.startswith("•"):
                        break
                    if re.match(r"^Level\s+\d+\s*:", item):
                        break
                    if len(item) > 45:
                        break
                    if item.endswith((".", ":", ";", "?", "!")):
                        break
                    if re.match(
                        r"^(See|You|When|As|For|To|The|If|Once|Whenever|While)\b", item
                    ):
                        break
                    items.append(item)
                    k += 1

                if len(items) >= 3:
                    result.append("")
                    result.append(title)
                    result.append("")
                    for item in items:
                        result.append(f"• {item}")
                    result.append("")
                    i = k
                    continue

        result.append(lines[i])
        i += 1

    return result


def _format_inline_multi_column_tables(lines: list[str]) -> list[str]:
    """Format compact multi-column inline tables as bullet rows.

    Output format:
      • <first-col> — <Header2>: <val>, <Header3>: <val>
    """
    result: list[str] = []
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        candidates: list[dict] = []

        # Try two variants:
        # A) title line at i, headers start at i+1
        # B) headers start at i (no standalone title)
        for has_title in (True, False):
            for n_cols in (4, 3):
                header_start = i + 1 if has_title else i
                data_start = header_start + n_cols
                if data_start >= len(lines):
                    continue

                if has_title and (
                    not stripped or len(stripped) > 45 or stripped.endswith(".")
                ):
                    continue

                headers = [lines[header_start + c].strip() for c in range(n_cols)]
                if not all(_looks_like_table_header(h) for h in headers):
                    continue
                if not _has_table_header_keywords(headers):
                    continue

                values: list[str] = []
                j = data_start
                while j < len(lines):
                    value = lines[j].strip()
                    if not value:
                        break
                    if not _looks_like_table_value(value):
                        break
                    values.append(value)
                    j += 1

                if len(values) < n_cols * 2 or len(values) % n_cols != 0:
                    continue

                rows = [values[r : r + n_cols] for r in range(0, len(values), n_cols)]
                first_col = [row[0] for row in rows]
                yes_no_in_first = sum(
                    1 for val in first_col if _TABLE_VALUE_PATTERN.match(val)
                )
                numeric_in_first = sum(
                    1 for val in first_col if re.match(r"^\d+(?:/\d+)?$", val)
                )

                score = len(rows) * 10
                score -= yes_no_in_first * 6
                if numeric_in_first == len(first_col):
                    score += 2
                if has_title:
                    score += 1
                    if _has_table_header_keywords([stripped]):
                        score -= 8

                candidates.append(
                    {
                        "score": score,
                        "has_title": has_title,
                        "headers": headers,
                        "rows": rows,
                        "end": j,
                    }
                )

        if candidates:
            best = max(candidates, key=lambda c: c["score"])
            if best["has_title"]:
                result.append("")
                result.append(stripped)
                result.append("")
            for row in best["rows"]:
                first = row[0]
                details = ", ".join(
                    f"{best['headers'][idx]}: {row[idx]}"
                    for idx in range(1, len(best["headers"]))
                )
                bullet = f"• {first} — {details}" if details else f"• {first}"
                result.append(bullet)
            result.append("")
            i = best["end"]
            continue

        result.append(lines[i])
        i += 1

    return result


def _format_inline_tables(lines: list[str]) -> list[str]:
    """Detect 2-column tables in raw lines and format them as readable text.

    Detects patterns like:
        Magic Item Plans (Artificer Level 2+)   <- table title
        Magic Item Plan                          <- col 1 header
        Attunement                               <- col 2 header
        Alchemy Jug                              <- row 1 col 1
        No                                       <- row 1 col 2
        ...

    Formats them as:
        Magic Item Plans (Artificer Level 2+)
        • Alchemy Jug — No
        • Bag of Holding — No
    """
    result: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        # Look for a 2-column table: title line, then two header lines,
        # then alternating name/value pairs where values match Yes/No/Varies.
        if (
            i + 4 < len(lines)
            and stripped  # title line is non-empty
            and lines[i + 1].strip()  # col 1 header
            and lines[i + 2].strip()  # col 2 header
            and lines[i + 3].strip()  # first data value
            and _TABLE_VALUE_PATTERN.match(
                lines[i + 4].strip()
            )  # second line is Yes/No/Varies
        ):
            col1_header = lines[i + 1].strip()
            col2_header = lines[i + 2].strip()
            first_name = lines[i + 3].strip()

            # Guardrails: this formatter is for labeled 2-column tables,
            # not numeric matrix data.
            if re.match(r"^\d+(?:/\d+)?$", col1_header):
                result.append(lines[i])
                i += 1
                continue
            if re.match(r"^\d+(?:/\d+)?$", col2_header):
                result.append(lines[i])
                i += 1
                continue
            if re.match(r"^\d+(?:/\d+)?$", first_name):
                result.append(lines[i])
                i += 1
                continue

            # Verify col2 header is a short label (not a sentence)
            if len(col2_header.split()) <= 3:
                # Blank line before the table title to separate from prose
                result.append("")
                # Emit the table title
                result.append(stripped)
                result.append("")  # blank line after title
                j = i + 3  # skip title + 2 header lines
                while j + 1 < len(lines):
                    name = lines[j].strip()
                    value = lines[j + 1].strip()
                    if not name:
                        break
                    if _TABLE_VALUE_PATTERN.match(value):
                        result.append(f"• {name} — {col2_header}: {value}")
                        j += 2
                    else:
                        # No longer in the table
                        break
                result.append("")  # blank line after table
                i = j
                continue

        result.append(lines[i])
        i += 1

    return result


def join_description_lines(lines: list[str]) -> str:
    """Join description lines preserving paragraph breaks and sub-headings.

    Blank lines become paragraph breaks (\\n\\n).
    Short title-cased lines ending with '.' are treated as sub-headings
    and get their own paragraph.
    Inline 2-column tables are formatted as bullet lists.
    """
    # Pre-process: detect and format inline structures
    lines = _format_inline_tables(lines)
    lines = _format_subclass_name_lists(lines)
    lines = _format_inline_multi_column_tables(lines)

    paragraphs: list[str] = []
    current: list[str] = []

    def _looks_like_plain_list_item(text: str) -> bool:
        """Heuristic: short noun-phrase style line suitable for bulleting."""
        if not text:
            return False
        if len(text) > 40:
            return False
        if text.endswith((".", ":", ";", "?", "!")):
            return False
        if re.match(r"^(See|You|When|As|For|To|The)\b", text):
            return False
        return True

    def _flush_plain_list(items: list[str]) -> None:
        """Emit list items as bullets if there are enough to be meaningful."""
        if len(items) >= 3:
            bullet_block = "\n".join(f"• {item}" for item in items)
            paragraphs.append(bullet_block)
        elif items:
            current.extend(items)

    in_bullet_list = False
    collecting_plain_list = False
    plain_list_items: list[str] = []

    for line in lines:
        stripped = line.strip()

        if collecting_plain_list:
            if _looks_like_plain_list_item(stripped):
                plain_list_items.append(stripped)
                continue
            _flush_plain_list(plain_list_items)
            plain_list_items = []
            collecting_plain_list = False

        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
            in_bullet_list = False
        elif stripped.lower().endswith("following list:"):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            paragraphs.append(stripped)
            collecting_plain_list = True
            in_bullet_list = False
        elif stripped.startswith("•"):
            # Bullet items: flush current paragraph, then group bullets
            if current:
                paragraphs.append(" ".join(current))
                current = []
            if not in_bullet_list:
                in_bullet_list = True
                paragraphs.append(stripped)
            else:
                # Append to previous bullet block with newline
                paragraphs[-1] += "\n" + stripped
        elif _is_subheading(stripped):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            paragraphs.append(stripped)
            in_bullet_list = False
        else:
            current.append(stripped)
            in_bullet_list = False

    if collecting_plain_list:
        _flush_plain_list(plain_list_items)

    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs)


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
            value = line[len("Source:") :].strip()
            if value:
                return value
            # "Source:" on its own line — value is on the next line
            if i + 1 < len(lines) and lines[i + 1].strip():
                return lines[i + 1].strip()
        if line.startswith("Source"):
            rest = line[len("Source") :].strip().lstrip(":")
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
        pattern = re.compile(rf"^{re.escape(field_name)}\s*:\s*(.+)", re.IGNORECASE)
        m = pattern.match(stripped)
        if m:
            return m.group(1).strip()
    return None


def extract_field_multiline(
    content: str, field_name: str, stop_fields: list[str] | None = None
) -> str | None:
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
    text = re.sub(r"\s+and\s+", ", ", text)
    text = re.sub(r"\s+or\s+", ", ", text)
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
        "core ",
        "traits",
        "primary ability",
        "hit point die",
        "creature type",
        "ability scores",
        "prerequisite",
        "you gain the following",
        "feat:",
        "skill proficiencies",
    ]

    field_headers = trait_headers + [
        "tool proficiency",
        "equipment",
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
        if re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+:", stripped):
            first_header_idx = i
            break
        desc_lines.append(stripped)

    if desc_lines:
        return join_description_lines(desc_lines)

    # Fallback: collect trailing text after all known field headers.
    # Walk past header/value pairs (header line + one value line each),
    # then grab whatever remains as the description.
    def _is_header(line: str) -> bool:
        low = line.strip().lower()
        return any(low.startswith(h) for h in field_headers) or bool(
            re.match(r"^[A-Z][a-z]+ [A-Z][a-z]+:", line.strip())
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

    return join_description_lines(tail_lines)


def is_school_index(entry: dict) -> bool:
    """Check if a spell entry is a school index page (not an individual spell)."""
    return "-school" in entry.get("url", "")


def parse_choose_pattern(text: str) -> dict | None:
    """Parse 'Choose N: X, Y, Z' or 'Choose N from: X, Y, Z' patterns.

    Returns {'count': N, 'options': ['X', 'Y', 'Z']} or None.
    """
    m = re.match(r"Choose\s+(\d+)\s*(?:from\s*)?:\s*(.+)", text, re.IGNORECASE)
    if m:
        count = int(m.group(1))
        options = split_comma_list(m.group(2))
        return {"count": count, "options": options}
    return None
