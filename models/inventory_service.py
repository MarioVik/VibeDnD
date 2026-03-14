"""Inventory and wealth helpers for item add/buy flows."""

from __future__ import annotations

from datetime import datetime

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
    character, mode: str, item_name: str, qty: int, total_cost_cp: int
):
    tx = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "item": item_name,
        "qty": int(qty),
        "total_cost_cp": int(total_cost_cp),
    }
    log = list(getattr(character, "inventory_transactions", []))
    log.insert(0, tx)
    character.inventory_transactions = log[:10]


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
    _add_transaction(character, mode, item.get("name", "Item"), qty, logged_cost)
    return True, "Item added."
