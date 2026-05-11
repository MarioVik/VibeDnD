"""Reusable two-column spell swap panel used by level-up wizard and rest dialog."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from itertools import groupby
from tkinter import ttk

from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import CardFrame, ModernSectionedListbox, WrappingLabel

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


def _build_swap_mode_tiles(
    parent: tk.Widget,
    *,
    mode_var: tk.StringVar,
    specs: list[tuple[str, str, str | None, Callable[[], None] | None]],
) -> Callable[[], None]:
    """Card-style selectable tiles in one horizontal row (class feature tile visuals).

    Each spec is ``(value, title, subtitle_or_none, after_select_callback_or_none)``.
    ``mode_var`` values ``""``, ``"skip"``, and ``"pick"`` update border/title colors.
    Returns a no-arg function to refresh styling (e.g. after programmatic ``mode_var`` changes).
    """
    tile_map: dict[str, dict] = {}
    row = tk.Frame(parent, bg=COLORS["bg_surface"])
    row.pack(fill=tk.BOTH, expand=True)
    n_specs = len(specs)
    for col in range(n_specs):
        row.columnconfigure(col, weight=1, uniform="swap_mode_tiles")

    def refresh_styles() -> None:
        curr = mode_var.get()
        for v, widgets in tile_map.items():
            is_sel = curr == v
            border_c = COLORS["accent"] if is_sel else COLORS["border_medium"]
            bg_c = COLORS.get("tile_hover", COLORS["bg_highest"]) if is_sel else COLORS["bg_surface"]
            fg_title = COLORS["accent_text"] if is_sel else COLORS["fg"]
            widgets["border"].configure(bg=border_c)
            widgets["tile"].configure(bg=bg_c)
            widgets["title"].configure(bg=bg_c, fg=fg_title)
            desc_lbl = widgets.get("desc")
            if desc_lbl is not None:
                desc_lbl.configure(background=bg_c)

    for col, (value, title, desc, after) in enumerate(specs):
        gap_l = SPACING["xs"] if col > 0 else 0
        gap_r = SPACING["xs"] if col < n_specs - 1 else 0
        tile_border = tk.Frame(row, bg=COLORS["border_medium"], cursor="hand2")
        tile_border.grid(
            row=0,
            column=col,
            sticky="nsew",
            padx=(gap_l, gap_r),
            pady=0,
        )

        bg_hex = COLORS["bg_surface"]
        tile = tk.Frame(tile_border, bg=bg_hex, cursor="hand2")
        tile.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        title_lbl = tk.Label(
            tile,
            text=title,
            font=FONTS["body_bold"],
            fg=COLORS["fg"],
            bg=bg_hex,
            cursor="hand2",
            anchor="w",
        )
        title_lbl.pack(fill=tk.X, padx=SPACING["md"], pady=(SPACING["md"], 0))

        desc_lbl = None
        if desc:
            desc_lbl = WrappingLabel(
                tile,
                text=desc,
                font=FONTS["body_small"],
                foreground=COLORS["fg_dim"],
                background=bg_hex,
                cursor="hand2",
            )
            desc_lbl.pack(fill=tk.X, padx=SPACING["md"], pady=(SPACING["xs"], SPACING["md"]))

        tile_map[value] = {
            "border": tile_border,
            "tile": tile,
            "title": title_lbl,
            "desc": desc_lbl,
        }

        def on_click(_e, v: str = value, fn: Callable[[], None] | None = after) -> None:
            mode_var.set(v)
            if fn:
                fn()
            refresh_styles()

        def on_enter(_e, v: str = value) -> None:
            if mode_var.get() == v:
                return
            widgets = tile_map[v]
            widgets["border"].configure(bg=COLORS["accent"])
            hi = COLORS["bg_high"]
            widgets["tile"].configure(bg=hi)
            widgets["title"].configure(bg=hi)
            dl = widgets.get("desc")
            if dl is not None:
                dl.configure(background=hi)

        def on_leave(_e, v: str = value) -> None:
            if mode_var.get() == v:
                return
            refresh_styles()

        for w in (tile_border, tile, title_lbl, desc_lbl):
            if w:
                w.bind("<Button-1>", on_click)
                w.bind("<Enter>", on_enter)
                w.bind("<Leave>", on_leave)

    refresh_styles()
    return refresh_styles


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
        self._allow_cantrips = allow_cantrips
        self._all_spell_objects: dict[str, dict] = {}
        self.swap_mode_var = tk.StringVar(value="")

        # ── Two-column split ──
        cols = ttk.Frame(parent)
        cols.pack(fill=tk.BOTH, expand=True, pady=4)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)
        cols.rowconfigure(0, weight=1)

        # --- LEFT: mode card + Forget list ---
        left_col = tk.Frame(cols, bg=COLORS["bg"])
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        left_col.rowconfigure(1, weight=1)
        left_col.columnconfigure(0, weight=1)

        mode_card = CardFrame(left_col, pad=SPACING["md"])
        mode_card.grid(row=0, column=0, sticky="ew", pady=(0, SPACING["sm"]))
        pick_label = (
            "Replace a cantrip or spell"
            if allow_cantrips
            else "Replace a spell"
        )
        self._refresh_mode_tiles = _build_swap_mode_tiles(
            mode_card.inner,
            mode_var=self.swap_mode_var,
            specs=[
                (
                    "skip",
                    no_swap_label,
                    "Keep your known spells and cantrips as they are.",
                    self._on_mode_skip,
                ),
                (
                    "pick",
                    pick_label,
                    "Choose what to forget below, then pick a replacement on the right.",
                    None,
                ),
            ],
        )

        left_lf = ttk.LabelFrame(left_col, text=left_label)
        left_lf.grid(row=1, column=0, sticky="nsew")

        self.left_list = ModernSectionedListbox(
            left_lf,
            on_inspect=self._show_detail,
            on_select=self._on_forget_select_modern,
            radioselect=True,
        )
        self.left_list.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # --- RIGHT: Learn ---
        right_lf = ttk.LabelFrame(cols, text=right_label)
        right_lf.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        
        self.right_list = ModernSectionedListbox(
            right_lf,
            on_inspect=self._show_detail,
            on_select=self._on_learn_select_modern,
            radioselect=True,
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
        
        self.left_list.set_sectioned_items(forget_sections)
        
        self._learn_sections = []
        if allow_cantrips and learn_cantrips:
            self._learn_sections.append(("Cantrips", [s["name"] for s in sorted(learn_cantrips, key=lambda s: s["name"])]))
        if learn_spells:
            learn_sorted = sorted(learn_spells, key=lambda s: (s["level"], s["name"]))
            for lvl, group in groupby(learn_sorted, key=lambda s: s["level"]):
                self._learn_sections.append((LEVEL_NAMES.get(lvl, f"Level {lvl}"), [s["name"] for s in group]))
        
        self.right_list.set_sectioned_items(self._learn_sections)

        # --- Shared Detail Panel ---
        all_spells = (
            forget_spells
            + learn_spells
            + (forget_cantrips or [])
            + (learn_cantrips or [])
        )
        self._all_spell_objects = {s["name"]: s for s in all_spells}
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

    def _clear_detail(self) -> None:
        self._detail_text.configure(state=tk.NORMAL)
        self._detail_text.delete("1.0", tk.END)
        self._detail_text.configure(state=tk.DISABLED)

    def _on_mode_skip(self) -> None:
        self.forget_var.set("")
        self.learn_var.set("")
        self.left_list.set_selected_items([])
        self._refresh_right_list_state()
        self._clear_detail()

    # ── Modern Selection Handlers ──

    def _on_forget_select_modern(self, name: str):
        self.swap_mode_var.set("pick")
        spell = self._all_spell_objects.get(name)
        if self._allow_cantrips and spell:
            prefix = "C:" if spell["level"] == 0 else "S:"
            self.forget_var.set(f"{prefix}{name}")
        else:
            self.forget_var.set(name)

        self._refresh_right_list_state()
        self._refresh_mode_tiles()

    def _on_learn_select_modern(self, name: str):
        self.swap_mode_var.set("pick")
        self.learn_var.set(name)
        self._refresh_mode_tiles()

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
        self.swap_mode_var = tk.StringVar(value="")

        mode_card = CardFrame(parent, pad=SPACING["md"])
        mode_card.pack(fill=tk.X, pady=(4, SPACING["sm"]))
        self._refresh_mode_tiles = _build_swap_mode_tiles(
            mode_card.inner,
            mode_var=self.swap_mode_var,
            specs=[
                (
                    "skip",
                    "Leave prepared spells unchanged",
                    "Do not change your prepared list during this rest.",
                    self._on_multi_mode_skip,
                ),
                (
                    "pick",
                    "Adjust preparations below",
                    "Check spells to unprepare on the left and replacements on the right.",
                    None,
                ),
            ],
        )

        # ── Two-column split ──
        cols = ttk.Frame(parent)
        cols.pack(fill=tk.BOTH, expand=True, pady=(0, 4))
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)
        cols.rowconfigure(0, weight=1)

        # --- LEFT: Forget ---
        left_lf = ttk.LabelFrame(cols, text=left_label)
        left_lf.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        
        self.left_list = ModernSectionedListbox(
            left_lf,
            multiselect=True,
            on_inspect=self._show_detail,
            on_select=self._on_change,
        )
        self.left_list.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # --- RIGHT: Learn ---
        right_lf = ttk.LabelFrame(cols, text=right_label)
        right_lf.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        
        self.right_list = ModernSectionedListbox(
            right_lf,
            multiselect=True,
            on_inspect=self._show_detail,
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

    def _on_multi_mode_skip(self) -> None:
        self.left_list.set_selected_items([])
        self.right_list.set_selected_items([])
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

        if n_forget > 0 or n_learn > 0:
            self.swap_mode_var.set("pick")

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

        self._refresh_mode_tiles()
