"""Reusable two-column spell swap panel used by level-up wizard and rest dialog."""

from __future__ import annotations

import tkinter as tk
from itertools import groupby
from tkinter import ttk

from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import ModernSectionedListbox

LEVEL_NAMES = {
    0: "Cantrips",
    1: "1st-Level",
    2: "2nd-Level",
    3: "3rd-Level",
    4: "4th-Level",
    5: "5th-Level",
    6: "6th-Level",
    7: "7th-Level",
    8: "8th-Level",
    9: "9th-Level",
}


def _spell_detail_lines(spell: dict) -> list[str]:
    """Build the detail text lines for a spell dict."""
    lines = [
        spell["name"],
        f"{'Cantrip' if spell['level'] == 0 else 'Level ' + str(spell['level'])} "
        f"{spell['school']}",
        f"Casting Time: {spell.get('casting_time', '?')}"
        f"{'  (Ritual)' if spell.get('ritual') else ''}",
        f"Range: {spell.get('range', '?')}",
        f"Duration: {'Concentration, ' if spell.get('concentration') else ''}"
        f"{spell.get('duration', '?')}",
        "",
        spell.get("description", ""),
    ]
    if spell.get("higher_levels"):
        lines.extend(["", f"At Higher Levels: {spell['higher_levels']}"])
    if spell.get("cantrip_upgrade"):
        lines.extend(["", f"Cantrip Upgrade: {spell['cantrip_upgrade']}"])
    return lines


def _max_detail_height(
    *spell_lists: list[dict], lower: int = 4, upper: int = 20
) -> int:
    """Return the line count needed to fit the longest spell description."""
    max_lines = lower
    for spells in spell_lists:
        for spell in spells:
            max_lines = max(max_lines, len(_spell_detail_lines(spell)))
    return min(max_lines, upper)


class SpellSwapPanel:
    """Builds a two-column spell swap UI with level headers, scrollable lists,
    and a shared spell-detail panel.

    After the user interacts, read ``forget_var`` and ``learn_var`` to get the
    current selections.  Values are plain spell names for spells; cantrips are
    prefixed with ``C:`` and spells with ``S:`` when *allow_cantrips* is True.
    """

    def __init__(
        self,
        parent: tk.Widget,
        *,
        forget_spells: list[dict],
        learn_spells: list[dict],
        forget_cantrips: list[dict] | None = None,
        learn_cantrips: list[dict] | None = None,
        allow_cantrips: bool = False,
        left_label: str = "Forget",
        right_label: str = "Learn",
        no_swap_label: str = "Don\u2019t swap",
    ):
        self.forget_var = tk.StringVar(value="")
        self.learn_var = tk.StringVar(value="")
        self._cantrip_rbs: list[tuple[ttk.Radiobutton, dict]] = []
        self._spell_rbs: list[tuple[ttk.Radiobutton, dict]] = []
        self._allow_cantrips = allow_cantrips

        # ── Two-column split ──
        cols = ttk.Frame(parent)
        cols.pack(fill=tk.BOTH, expand=True, pady=4)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)
        cols.rowconfigure(0, weight=1)

        # --- LEFT: Forget ---
        left_lf = ttk.LabelFrame(cols, text=left_label)
        left_lf.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        
        self.left_list = ModernSectionedListbox(
            left_lf,
            on_hover=self._show_detail,
            on_select=self._on_forget_select_modern,
        )
        self.left_list.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # --- RIGHT: Learn ---
        right_lf = ttk.LabelFrame(cols, text=right_label)
        right_lf.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        
        self.right_list = ModernSectionedListbox(
            right_lf,
            on_hover=self._show_detail,
            on_select=self._on_learn_select_modern,
        )
        self.right_list.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # ── Data Preparation ──
        forget_sections = []
        if allow_cantrips and forget_cantrips:
            forget_sections.append(("Cantrips", [s["name"] for s in sorted(forget_cantrips, key=lambda s: s["name"])]))
        if forget_spells:
            forget_sorted = sorted(forget_spells, key=lambda s: (s["level"], s["name"]))
            for lvl, group in groupby(forget_sorted, key=lambda s: s["level"]):
                forget_sections.append((LEVEL_NAMES.get(lvl, f"Level {lvl}"), [s["name"] for s in group]))
        
        self.left_list.set_sectioned_items(forget_sections + [("Action", [no_swap_label])])
        
        self._learn_sections = []
        if allow_cantrips and learn_cantrips:
            self._learn_sections.append(("Cantrips", [s["name"] for s in sorted(learn_cantrips, key=lambda s: s["name"])]))
        if learn_spells:
            learn_sorted = sorted(learn_spells, key=lambda s: (s["level"], s["name"]))
            for lvl, group in groupby(learn_sorted, key=lambda s: s["level"]):
                self._learn_sections.append((LEVEL_NAMES.get(lvl, f"Level {lvl}"), [s["name"] for s in group]))
        
        self.right_list.set_sectioned_items(self._learn_sections)

        self._all_spell_objects = {s["name"]: s for s in all_spells}
        self._no_swap_label = no_swap_label

        # --- Shared Detail Panel ---
        all_spells = (
            forget_spells
            + learn_spells
            + (forget_cantrips or [])
            + (learn_cantrips or [])
        )
        detail_h = _max_detail_height(all_spells)
        detail_lf = ttk.LabelFrame(parent, text="Spell Details")
        detail_lf.pack(fill=tk.X, pady=(4, 0))
        self._detail_text = tk.Text(
            detail_lf,
            wrap=tk.WORD,
            height=detail_h,
            bg=COLORS["bg_light"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            state=tk.DISABLED,
        )
        self._detail_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    # ── Modern Selection Handlers ──

    def _on_forget_select_modern(self, name: str):
        if name == self._no_swap_label:
            self.forget_var.set("")
        else:
            spell = self._all_spell_objects.get(name)
            if self._allow_cantrips and spell:
                prefix = "C:" if spell["level"] == 0 else "S:"
                self.forget_var.set(f"{prefix}{name}")
            else:
                self.forget_var.set(name)
        
        self._refresh_right_list_state()

    def _on_learn_select_modern(self, name: str):
        self.learn_var.set(name)

    def _refresh_right_list_state(self):
        val = self.forget_var.get()
        if not val:
            self.learn_var.set("")
            self.right_list.set_sectioned_items([])
        elif val.startswith("C:"):
            # Only cantrips
            cantrip_only = [self._learn_sections[0]] if self._learn_sections and self._learn_sections[0][0] == "Cantrips" else []
            self.right_list.set_sectioned_items(cantrip_only)
        elif val.startswith("S:"):
            spells_only = [s for s in self._learn_sections if s[0] != "Cantrips"]
            self.right_list.set_sectioned_items(spells_only)
        else:
            self.right_list.set_sectioned_items(self._learn_sections)

    # ── Detail panel ──

    def _show_detail(self, name_or_spell: str | dict):
        if isinstance(name_or_spell, str):
            if name_or_spell == self._no_swap_label:
                return
            spell = self._all_spell_objects.get(name_or_spell)
        else:
            spell = name_or_spell
            
        if not spell:
            return

        self._detail_text.configure(state=tk.NORMAL)
        self._detail_text.delete("1.0", tk.END)
        self._detail_text.insert("1.0", "\n".join(_spell_detail_lines(spell)))
        self._detail_text.configure(state=tk.DISABLED)


class MultiSpellSwapPanel:
    """Checkbox-based panel for swapping multiple prepared spells at once.

    Used by prepared casters (Cleric, Druid, Wizard, Artificer) who can
    re-prepare their entire spell list on a Long Rest.

    Read ``forget_names`` and ``learn_names`` for the current selections.
    """

    def __init__(
        self,
        parent: tk.Widget,
        *,
        forget_spells: list[dict],
        learn_spells: list[dict],
        left_label: str = "Unprepare",
        right_label: str = "Prepare instead",
    ):
        # ── Two-column split ──
        cols = ttk.Frame(parent)
        cols.pack(fill=tk.BOTH, expand=True, pady=4)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)
        cols.rowconfigure(0, weight=1)

        # --- LEFT: Forget ---
        left_lf = ttk.LabelFrame(cols, text=left_label)
        left_lf.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        
        self.left_list = ModernSectionedListbox(
            left_lf,
            on_hover=self._show_detail,
            on_select=self._on_change,
        )
        self.left_list.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # --- RIGHT: Learn ---
        right_lf = ttk.LabelFrame(cols, text=right_label)
        right_lf.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        
        self.right_list = ModernSectionedListbox(
            right_lf,
            on_hover=self._show_detail,
            on_select=self._on_change,
        )
        self.right_list.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # ── Counter label ──
        self._counter = ttk.Label(
            parent,
            text="",
            foreground=COLORS["fg_dim"],
        )
        self._counter.pack(anchor="w", padx=4, pady=(0, 2))

        forget_sections = []
        if forget_spells:
            forget_sorted = sorted(forget_spells, key=lambda s: (s["level"], s["name"]))
            for lvl, group in groupby(forget_sorted, key=lambda s: s["level"]):
                forget_sections.append((LEVEL_NAMES.get(lvl, f"Level {lvl}"), [s["name"] for s in group]))
        self.left_list.set_sectioned_items(forget_sections)

        learn_sections = []
        if learn_spells:
            learn_sorted = sorted(learn_spells, key=lambda s: (s["level"], s["name"]))
            for lvl, group in groupby(learn_sorted, key=lambda s: s["level"]):
                learn_sections.append((LEVEL_NAMES.get(lvl, f"Level {lvl}"), [s["name"] for s in group]))
        self.right_list.set_sectioned_items(learn_sections)

        self._all_spell_objects = {s["name"]: s for s in forget_spells + learn_spells}

        # --- Shared Detail Panel ---
        detail_h = _max_detail_height(forget_spells, learn_spells)
        detail_lf = ttk.LabelFrame(parent, text="Spell Details")
        detail_lf.pack(fill=tk.X, pady=(4, 0))
        self._detail_text = tk.Text(
            detail_lf,
            wrap=tk.WORD,
            height=detail_h,
            bg=COLORS["bg_light"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            state=tk.DISABLED,
        )
        self._detail_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._on_change()

    # ── Public properties ──

    @property
    def forget_names(self) -> list[str]:
        return self.left_list.get_selected_names()

    @property
    def learn_names(self) -> list[str]:
        return self.right_list.get_selected_names()

    # ── Detail panel ──

    def _show_detail(self, name: str):
        spell = self._all_spell_objects.get(name)
        if not spell:
            return
        self._detail_text.configure(state=tk.NORMAL)
        self._detail_text.delete("1.0", tk.END)
        self._detail_text.insert("1.0", "\n".join(_spell_detail_lines(spell)))
        self._detail_text.configure(state=tk.DISABLED)

    # ── Logic ──

    def _on_change(self, *_):
        n_forget = len(self.forget_names)
        n_learn = len(self.learn_names)

        # Update counter
        if n_forget == 0 and n_learn == 0:
            self._counter.configure(
                text="Check spells on the left to unprepare, then check replacements on the right.",
                foreground=COLORS["fg_dim"],
            )
        elif n_forget == n_learn:
            self._counter.configure(
                text=f"Swapping {n_forget} spell{'s' if n_forget != 1 else ''}.",
                foreground=COLORS["fg"],
            )
        else:
            diff = n_forget - n_learn
            if diff > 0:
                self._counter.configure(
                    text=f"Unpreparing {n_forget}, preparing {n_learn} — select {diff} more on the right.",
                    foreground=COLORS["accent"],
                )
            else:
                self._counter.configure(
                    text=f"Unpreparing {n_forget}, preparing {n_learn} — deselect {-diff} on the right or select more on the left.",
                    foreground=COLORS["accent"],
                )
