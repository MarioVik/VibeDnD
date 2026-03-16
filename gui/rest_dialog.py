"""Dialog for taking a Short or Long Rest, allowing feature and spell swaps."""

from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import ttk

from gui.theme import COLORS, FONTS
from gui.widgets import ScrollableFrame, AlertDialog

# Load class choices data (same file as level_up_wizard)
_CHOICES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "class_choices.json")
try:
    with open(_CHOICES_PATH, encoding="utf-8") as _f:
        _CLASS_CHOICES: dict = json.load(_f)
except Exception:
    _CLASS_CHOICES = {}

# Classes whose spells are prepared (changeable on Long Rest)
_PREPARED_CASTER_CLASSES = {
    "artificer", "cleric", "druid", "paladin", "ranger", "wizard",
}


def _get_all_known_choices(character, key: str) -> list[str]:
    """Aggregate all choices the character has selected for a given class/subclass key."""
    result: list[str] = []
    for cl in character.class_levels:
        if cl.class_slug == key or cl.subclass_slug == key:
            result.extend(cl.new_choices)
            if cl.replaced_choice and cl.replaced_choice in result:
                result.remove(cl.replaced_choice)
    return result


def _has_swappable_features(character, rest_type: str) -> bool:
    """Return True if the character has any features swappable on this rest type."""
    all_keys = set()
    for cl in character.class_levels:
        all_keys.add(cl.class_slug)
        if cl.subclass_slug:
            all_keys.add(cl.subclass_slug)

    for key in all_keys:
        config = _CLASS_CHOICES.get(key)
        if not config or not config.get("can_swap_on_rest"):
            continue
        swap_type = config.get("swap_rest_type", "long")
        if rest_type == "short" and swap_type not in ("short", "short_or_long"):
            continue
        known = _get_all_known_choices(character, key)
        if known:
            return True
    return False


def _is_prepared_caster(character) -> bool:
    """Return True if the character has at least one prepared-spellcasting class."""
    for cl in character.class_levels:
        if cl.class_slug in _PREPARED_CASTER_CLASSES:
            return True
    return False


def can_short_rest(character) -> bool:
    """Return True if this character has anything to do on a Short Rest."""
    return _has_swappable_features(character, "short")


def can_long_rest(character) -> bool:
    """Return True if this character has anything to do on a Long Rest."""
    if _has_swappable_features(character, "long"):
        return True
    if _is_prepared_caster(character) and character.selected_spells:
        return True
    return False


class RestDialog(tk.Toplevel):
    """Modal dialog for taking a rest and optionally swapping features/spells."""

    def __init__(self, parent, character, game_data, rest_type: str, on_changed=None):
        """
        rest_type: "short" or "long"
        on_changed: callback called if any changes were saved
        """
        super().__init__(parent)
        self.character = character
        self.data = game_data
        self.rest_type = rest_type
        self.on_changed = on_changed

        title = "Short Rest" if rest_type == "short" else "Long Rest"
        self.title(title)
        self.geometry("700x520")
        self.transient(parent)
        self.grab_set()
        self.resizable(True, True)

        # State: maps choice_key -> {new_choice: str, old_choice: str}
        self._swaps: dict[str, dict] = {}
        # State: spell swap selection vars
        self._spell_remove_var = tk.StringVar(value="")
        self._spell_add_var = tk.StringVar(value="")

        self._build_ui(title)

    def _build_ui(self, title: str):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ── Header ─────────────────────────────────────────────────
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 4))

        ttk.Label(
            header,
            text=title,
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="Optionally swap features or prepared spells before completing this rest.",
            foreground=COLORS["fg_dim"],
        ).pack(anchor="w")

        # ── Scrollable content area ─────────────────────────────────
        scroll = ScrollableFrame(self)
        scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=4)
        inner = scroll.inner

        any_section = False

        # ── Feature swap sections ────────────────────────────────────
        all_keys: set[str] = set()
        for cl in self.character.class_levels:
            all_keys.add(cl.class_slug)
            if cl.subclass_slug:
                all_keys.add(cl.subclass_slug)

        for key in sorted(all_keys):
            config = _CLASS_CHOICES.get(key)
            if not config or not config.get("can_swap_on_rest"):
                continue
            swap_type = config.get("swap_rest_type", "long")
            if self.rest_type == "short" and swap_type not in ("short", "short_or_long"):
                continue

            known = _get_all_known_choices(self.character, key)
            if not known:
                continue

            any_section = True
            self._build_feature_section(inner, key, config, known)

        # ── Prepared spell swap section (Long Rest only) ─────────────
        if self.rest_type == "long" and _is_prepared_caster(self.character) and self.character.selected_spells:
            any_section = True
            self._build_spell_section(inner)

        if not any_section:
            ttk.Label(
                inner,
                text="Nothing to swap on this rest.",
                foreground=COLORS["fg_dim"],
            ).pack(pady=20)

        # ── Footer ──────────────────────────────────────────────────
        footer = ttk.Frame(self)
        footer.grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 12))

        ttk.Button(
            footer,
            text="Finish Rest",
            style="Accent.TButton",
            command=self._on_confirm,
        ).pack(side=tk.RIGHT, padx=(4, 0))

        ttk.Button(
            footer,
            text="Cancel",
            command=self.destroy,
        ).pack(side=tk.RIGHT)

    def _build_feature_section(self, parent, key: str, config: dict, known: list[str]):
        choice_plural = config.get("choice_plural", "Choices")
        choice_label = config.get("choice_label", "Choice")
        options = config.get("options", [])

        frame = ttk.LabelFrame(parent, text=f"Swap {choice_plural}")
        frame.pack(fill=tk.X, pady=(8, 0), padx=4)

        ttk.Label(
            frame,
            text=f"You may replace one {choice_label} with a different one.",
            foreground=COLORS["fg_dim"],
        ).pack(anchor="w", padx=8, pady=(4, 8))

        cols = ttk.Frame(frame)
        cols.pack(fill=tk.X, padx=8, pady=(0, 8))
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        remove_var = tk.StringVar(value="")
        replace_var = tk.StringVar(value="")
        self._swaps[key] = {"remove_var": remove_var, "replace_var": replace_var, "config": config}

        # Left: Remove
        remove_lf = ttk.LabelFrame(cols, text="Remove")
        remove_lf.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        ttk.Radiobutton(
            remove_lf,
            text="Don\u2019t replace",
            variable=remove_var,
            value="",
        ).pack(anchor="w", padx=8, pady=2)

        for name in sorted(known):
            ttk.Radiobutton(
                remove_lf,
                text=name,
                variable=remove_var,
                value=name,
            ).pack(anchor="w", padx=(16, 8), pady=1)

        # Right: Replace with
        add_lf = ttk.LabelFrame(cols, text="Replace with")
        add_lf.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        ttk.Radiobutton(
            add_lf,
            text="\u2014",
            variable=replace_var,
            value="",
        ).pack(anchor="w", padx=8, pady=2)

        # All options minus currently known
        available = [o for o in options if o["name"] not in known]

        # Pool-aware filtering: if pools exist, show all valid options (reshuffling freely)
        # No pool restriction on rest swaps — they can pick from any pool they've unlocked
        pools_cfg = config.get("pools", {})
        if pools_cfg:
            # Determine which pools the character has unlocked
            unlocked_pools: set[str] = set()
            for cl in self.character.class_levels:
                if cl.class_slug == key or cl.subclass_slug == key:
                    lvl_str = str(cl.class_level)
                    pool = pools_cfg.get(lvl_str)
                    if pool:
                        unlocked_pools.add(pool)
            available = [o for o in options if o.get("pool") in unlocked_pools and o["name"] not in known]

        for opt in sorted(available, key=lambda o: o["name"]):
            ttk.Radiobutton(
                add_lf,
                text=opt["name"],
                variable=replace_var,
                value=opt["name"],
            ).pack(anchor="w", padx=(16, 8), pady=1)

        if not available:
            ttk.Label(
                add_lf,
                text="No other options available.",
                foreground=COLORS["fg_dim"],
            ).pack(anchor="w", padx=8, pady=4)

    def _build_spell_section(self, parent):
        frame = ttk.LabelFrame(parent, text="Change Prepared Spells")
        frame.pack(fill=tk.X, pady=(8, 0), padx=4)

        ttk.Label(
            frame,
            text="You may replace one prepared spell with another from your class spell list.",
            foreground=COLORS["fg_dim"],
        ).pack(anchor="w", padx=8, pady=(4, 8))

        cols = ttk.Frame(frame)
        cols.pack(fill=tk.X, padx=8, pady=(0, 8))
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        # Left: Remove a prepared spell
        remove_lf = ttk.LabelFrame(cols, text="Unprepare")
        remove_lf.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        ttk.Radiobutton(
            remove_lf,
            text="Don\u2019t change",
            variable=self._spell_remove_var,
            value="",
        ).pack(anchor="w", padx=8, pady=2)

        for spell in sorted(self.character.selected_spells):
            ttk.Radiobutton(
                remove_lf,
                text=spell,
                variable=self._spell_remove_var,
                value=spell,
            ).pack(anchor="w", padx=(16, 8), pady=1)

        # Right: Prepare a new spell from class spell list
        add_lf = ttk.LabelFrame(cols, text="Prepare instead")
        add_lf.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        ttk.Radiobutton(
            add_lf,
            text="\u2014",
            variable=self._spell_add_var,
            value="",
        ).pack(anchor="w", padx=8, pady=2)

        # Collect available spells from class spell list not already prepared
        known_set = set(self.character.selected_spells)
        available_spells = self._get_available_spells(known_set)

        for spell_name in sorted(available_spells):
            ttk.Radiobutton(
                add_lf,
                text=spell_name,
                variable=self._spell_add_var,
                value=spell_name,
            ).pack(anchor="w", padx=(16, 8), pady=1)

        if not available_spells:
            ttk.Label(
                add_lf,
                text="No additional spells available.",
                foreground=COLORS["fg_dim"],
            ).pack(anchor="w", padx=8, pady=4)

    def _get_available_spells(self, known_set: set[str]) -> list[str]:
        """Return spells from class spell lists not already prepared."""
        available: set[str] = set()
        primary_slugs = {cl.class_slug for cl in self.character.class_levels
                         if cl.class_slug in _PREPARED_CASTER_CLASSES}

        for spell in self.data.spells:
            if spell.get("name") in known_set:
                continue
            spell_classes = {c.lower() for c in spell.get("classes", [])}
            if spell_classes & primary_slugs:
                available.add(spell.get("name", ""))

        return [s for s in available if s]

    def _on_confirm(self):
        changed = False

        # Apply feature swaps
        for key, swap_data in self._swaps.items():
            remove_var: tk.StringVar = swap_data["remove_var"]
            replace_var: tk.StringVar = swap_data["replace_var"]
            remove_name = remove_var.get()
            replace_name = replace_var.get()

            if not remove_name:
                continue
            if not replace_name:
                AlertDialog(
                    self,
                    "Incomplete Swap",
                    f"You selected a {swap_data['config'].get('choice_label', 'choice')} to remove "
                    f"but didn\u2019t pick a replacement. Either select a replacement or choose "
                    f"\u201cDon\u2019t replace\u201d.",
                )
                return

            # Apply to character: find the ClassLevel entry that holds this choice and update it
            _apply_choice_swap(self.character, key, remove_name, replace_name)
            changed = True

        # Apply spell swap
        remove_spell = self._spell_remove_var.get()
        add_spell = self._spell_add_var.get()
        if remove_spell:
            if not add_spell:
                AlertDialog(
                    self,
                    "Incomplete Swap",
                    "You selected a spell to unprepare but didn\u2019t pick a replacement. "
                    "Either select a replacement or choose \u201cDon\u2019t change\u201d.",
                )
                return
            if remove_spell in self.character.selected_spells:
                self.character.selected_spells.remove(remove_spell)
            self.character.selected_spells.append(add_spell)
            changed = True

        if changed and self.on_changed:
            self.on_changed()

        self.destroy()


def _apply_choice_swap(character, key: str, remove_name: str, replace_name: str):
    """Update the character's class_levels to swap one choice for another."""
    # Find the ClassLevel that owns remove_name for this key
    for cl in character.class_levels:
        if (cl.class_slug == key or cl.subclass_slug == key) and remove_name in cl.new_choices:
            cl.new_choices.remove(remove_name)
            cl.new_choices.append(replace_name)
            # Track the replacement (use replaced_choice field for most recent swap)
            cl.replaced_choice = remove_name
            return
    # Fallback: not found in any specific ClassLevel — do nothing (shouldn't happen)
