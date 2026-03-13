"""Helpers for splitting equipment text from starting wealth."""

import re
from decimal import Decimal, ROUND_HALF_UP


_GP_RE = re.compile(r"(\d+(?:[\.,]\d+)?)\s*GP\b", re.IGNORECASE)


def extract_gp(text: str) -> Decimal:
    """Extract total GP amount mentioned in an equipment text snippet."""
    if not text:
        return Decimal("0")

    total = Decimal("0")
    for m in _GP_RE.finditer(text):
        raw = m.group(1).replace(",", ".")
        total += Decimal(raw)
    return total


def gp_to_coins(gp_total: Decimal) -> tuple[int, int, int]:
    """Convert GP amount to (gp, sp, cp) using 10/10 conversion."""
    total_cp = int(
        (gp_total * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    gp = total_cp // 100
    rem = total_cp % 100
    sp = rem // 10
    cp = rem % 10
    return gp, sp, cp


def strip_wealth(text: str) -> str:
    """Remove currency fragments from equipment text.

    Example:
    "Greataxe, 4 Handaxes, Explorer's Pack, and 15 GP; or" ->
    "Greataxe, 4 Handaxes, Explorer's Pack"
    "150 GP" -> ""
    """
    if not text:
        return ""

    clean = text.replace(";", "")
    parts = [p.strip() for p in clean.split(",")]
    keep = []
    for part in parts:
        lower = part.lower()
        if _GP_RE.search(part):
            continue
        if lower in {"or", "and"}:
            continue
        if lower.startswith("and ") and _GP_RE.search(part[4:]):
            continue
        keep.append(part)

    return ", ".join(keep).strip(" ,")
