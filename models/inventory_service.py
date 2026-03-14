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


def undo_last_transaction(character) -> tuple[bool, str]:
    """Undo the latest inventory transaction (if any)."""
    txs = list(getattr(character, "inventory_transactions", []) or [])
    if not txs:
        return False, "No transaction to undo."

    tx = txs.pop(0)
    item_id = str(tx.get("item_id", ""))
    item_name = str(tx.get("item", "Item"))
    qty = max(1, int(tx.get("qty", 1)))
    mode = str(tx.get("mode", "free"))
    total_cost = int(tx.get("total_cost_cp", 0))

    inv = list(getattr(character, "custom_inventory", []))
    target = None
    if item_id:
        target = next((e for e in inv if e.get("item_id") == item_id), None)
    if target is None:
        target = next((e for e in inv if str(e.get("name", "")) == item_name), None)

    if target is not None:
        target_qty = int(target.get("qty", 0))
        new_qty = max(0, target_qty - qty)
        if new_qty <= 0:
            inv = [e for e in inv if e is not target]
        else:
            target["qty"] = new_qty
    character.custom_inventory = inv

    if mode == "buy" and total_cost > 0:
        character.wealth_adjust_cp = (
            int(getattr(character, "wealth_adjust_cp", 0)) + total_cost
        )

    character.inventory_transactions = txs[:10]
    return True, f"Undid: {mode.upper()} {qty} x {item_name}"
