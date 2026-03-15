"""Inventory and wealth helpers for item add/buy flows."""

from __future__ import annotations

from datetime import datetime
import re

from gui.equipment_utils import extract_gp


def _selected_equipment_gp(character) -> int:
    total_gp = 0
    if character.character_class:
        for opt in character.character_class.get("starting_equipment", []):
            if opt.get("option") == character.equipment_choice_class:
                total_gp += int(extract_gp(opt.get("items", "")))
                break
    if character.background:
        for opt in character.background.get("equipment", []):
            if opt.get("option") == character.equipment_choice_background:
                total_gp += int(extract_gp(opt.get("items", "")))
                break
    return total_gp


def base_wealth_cp(character) -> int:
    """Starting wealth from selected class/background loadouts, in copper."""
    return _selected_equipment_gp(character) * 100


def current_wealth_cp(character) -> int:
    """Current available wealth in copper."""
    return base_wealth_cp(character) + int(getattr(character, "wealth_adjust_cp", 0))


def cp_to_coins(total_cp: int) -> tuple[int, int, int]:
    total_cp = max(0, int(total_cp))
    gp = total_cp // 100
    rem = total_cp % 100
    sp = rem // 10
    cp = rem % 10
    return gp, sp, cp


def _add_transaction(
    character,
    mode: str,
    item_id: str,
    item_name: str,
    item_category: str,
    qty: int,
    total_cost_cp: int,
):
    tx = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "item_id": item_id,
        "item": item_name,
        "category": item_category,
        "qty": int(qty),
        "total_cost_cp": int(total_cost_cp),
    }
    log = list(getattr(character, "inventory_transactions", []))
    log.insert(0, tx)
    character.inventory_transactions = log[:10]


def normalize_item_key(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip().lower())


def add_item(character, item: dict, qty: int, mode: str) -> tuple[bool, str]:
    """Add item to custom inventory.

    mode: "free" or "buy"
    Returns (ok, message).
    """
    qty = int(max(1, qty))
    cost_cp = int(item.get("cost_cp", 0))
    total_cost = cost_cp * qty

    if mode == "buy":
        if total_cost <= 0:
            return False, "This item has no fixed buy cost."
        if current_wealth_cp(character) < total_cost:
            return False, "Not enough wealth to buy this item."
        character.wealth_adjust_cp = (
            int(getattr(character, "wealth_adjust_cp", 0)) - total_cost
        )

    inv = list(getattr(character, "custom_inventory", []))
    item_id = item.get("id")
    existing = next((e for e in inv if e.get("item_id") == item_id), None)
    if existing:
        existing["qty"] = int(existing.get("qty", 0)) + qty
    else:
        inv.append(
            {
                "item_id": item_id,
                "name": item.get("name", "Unknown Item"),
                "category": item.get("category", "Adventuring Gear"),
                "qty": qty,
            }
        )
    character.custom_inventory = inv

    logged_cost = total_cost if mode == "buy" else 0
    _add_transaction(
        character,
        mode,
        str(item.get("id", "")),
        item.get("name", "Item"),
        item.get("category", "Adventuring Gear"),
        qty,
        logged_cost,
    )
    return True, "Item added."


def remove_item(character, item_name: str, qty: int = 1) -> tuple[bool, str]:
    """Remove item quantity from character inventory/equipment pools.

    Removal consumes custom inventory entries first, then applies an overlay
    against base equipment-derived items via ``character.removed_items``.
    """
    qty = int(max(1, qty))
    target_key = normalize_item_key(item_name)
    if not target_key:
        return False, "Invalid item selection."

    remaining = qty
    inv = list(getattr(character, "custom_inventory", []) or [])
    for ent in inv:
        if remaining <= 0:
            break
        if normalize_item_key(ent.get("name", "")) != target_key:
            continue
        have = int(ent.get("qty", 1))
        take = min(have, remaining)
        ent["qty"] = have - take
        remaining -= take

    inv = [e for e in inv if int(e.get("qty", 0)) > 0]
    character.custom_inventory = inv

    if remaining > 0:
        removed = dict(getattr(character, "removed_items", {}) or {})
        removed[target_key] = int(removed.get(target_key, 0)) + remaining
        character.removed_items = {k: int(v) for k, v in removed.items() if int(v) > 0}

    _add_transaction(
        character,
        "remove",
        "",
        item_name,
        "",
        qty,
        0,
    )
    return True, "Item removed."
