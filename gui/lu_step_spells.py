"""Level-up step: Spell selection with split-detail layout."""

import tkinter as tk
from tkinter import ttk
from itertools import groupby

from gui.lu_base_step import LevelUpStep
from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import (
    CardFrame,
    GradientHeader,
    SectionHeader,
    register_mousewheel_target,
)
from models.level_up_logic import spell_deltas, validate_spell_step

_LEVEL_NAMES = {
    1: "1st-Level", 2: "2nd-Level", 3: "3rd-Level", 4: "4th-Level",
    5: "5th-Level", 6: "6th-Level", 7: "7th-Level", 8: "8th-Level",
    9: "9th-Level",
}


class LuSpellsStep(LevelUpStep):
    tab_title = "Spells"

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        hero = GradientHeader(self.frame, min_height=60)
        hero.grid(row=0, column=0, sticky="ew")

        hero_row = tk.Frame(hero.inner, bg=COLORS["bg_hero"])
        hero_row.pack(
            fill=tk.X,
            padx=SPACING["card_pad"],
            pady=(SPACING["xl"], SPACING["xl"]),
        )

        tk.Label(
            hero_row,
            text="Select New Spells",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        self._info_label = tk.Label(
            hero_row,
            text="",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        )
        self._info_label.pack(side=tk.RIGHT)

        self._content = tk.Frame(self.frame, bg=COLORS["bg"])
        self._content.grid(row=1, column=0, sticky="nsew")
        self._content.columnconfigure(0, weight=1)
        self._content.columnconfigure(1, weight=1)
        self._content.rowconfigure(0, weight=1)

        self._updating_cantrips = False
        self._updating_spells = False
        self.cantrip_vars: dict[str, dict] = {}
        self.spell_vars: dict[str, dict] = {}
        self.cantrip_checkbuttons: dict[str, ttk.Checkbutton] = {}
        self.spell_checkbuttons: dict[str, ttk.Checkbutton] = {}

    def on_enter(self):
        self._rebuild()

    def _rebuild(self):
        for w in self._content.winfo_children():
            w.destroy()
        self.cantrip_vars.clear()
        self.spell_vars.clear()
        self.cantrip_checkbuttons.clear()
        self.spell_checkbuttons.clear()

        new_cantrips, new_prepared, max_spell_level = spell_deltas(
            self.ctx.class_slug, self.ctx.new_class_level, self.data
        )

        class_name = ""
        for cls in self.data.classes:
            if cls.get("slug") == self.ctx.class_slug:
                class_name = cls.get("name", "")
                break

        parts = []
        if new_cantrips > 0:
            parts.append(f"{new_cantrips} cantrip(s)")
        if new_prepared > 0:
            parts.append(f"{new_prepared} spell(s)")
        self._info_label.configure(text="  |  ".join(parts) if parts else "")

        # ── LEFT: spell list ──
        left = tk.Frame(self._content, bg=COLORS["bg"])
        left.grid(
            row=0, column=0, sticky="nsew",
            padx=(SPACING["lg"], SPACING["xs"]),
            pady=(SPACING["sm"], SPACING["lg"]),
        )
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)

        # Count labels
        if new_cantrips > 0:
            self._cantrip_count = tk.Label(
                left,
                text=f"0 / {new_cantrips} cantrips selected",
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg"],
            )
            self._cantrip_count.pack(anchor="w", padx=SPACING["xs"], pady=(0, 1))
        else:
            self._cantrip_count = None

        if new_prepared > 0:
            self._spell_count = tk.Label(
                left,
                text=f"0 / {new_prepared} spells selected",
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg"],
            )
            self._spell_count.pack(anchor="w", padx=SPACING["xs"], pady=(0, 1))
        else:
            self._spell_count = None

        list_outer = tk.Frame(left, bg=COLORS["bg"])
        list_outer.pack(fill=tk.BOTH, expand=True, pady=(SPACING["xs"], 0))
        canvas, inner = self._make_scrollable_list(list_outer)

        # Cantrips
        if new_cantrips > 0:
            self._section_header(inner, "Cantrips")
            all_cantrips = self.data.cantrips_for_class(class_name)
            known = set(self.character.selected_cantrips) | set(self.ctx.selected_new_cantrips)
            available = [s for s in all_cantrips if s["name"] not in known]

            for spell in sorted(available, key=lambda s: s["name"]):
                var = tk.BooleanVar(value=spell["name"] in self.ctx.selected_new_cantrips)
                var.trace_add("write", lambda *a, s=spell: self._on_cantrip_toggle(s))
                self.cantrip_vars[spell["name"]] = {"var": var, "spell": spell}
                cb = ttk.Checkbutton(inner, text=spell["name"], variable=var)
                cb.pack(anchor="w", pady=1, padx=(SPACING["sm"], 0))
                cb.bind("<Enter>", lambda e, s=spell: self._show_spell_detail(s))
                self.cantrip_checkbuttons[spell["name"]] = cb

        # Leveled spells
        if new_prepared > 0:
            all_spells = self.data.spells_for_class(class_name, max_level=max_spell_level)
            known = set(self.character.selected_spells) | set(self.ctx.selected_new_spells)
            available = [
                s for s in all_spells
                if s["name"] not in known and s.get("level", 0) >= 1
            ]
            available.sort(key=lambda s: (s["level"], s["name"]))

            for lvl, group in groupby(available, key=lambda s: s["level"]):
                self._section_header(inner, _LEVEL_NAMES.get(lvl, f"Level {lvl}"))
                for spell in group:
                    var = tk.BooleanVar(value=spell["name"] in self.ctx.selected_new_spells)
                    var.trace_add("write", lambda *a, s=spell: self._on_spell_toggle(s))
                    self.spell_vars[spell["name"]] = {"var": var, "spell": spell}
                    cb = ttk.Checkbutton(inner, text=spell["name"], variable=var)
                    cb.pack(anchor="w", pady=1, padx=(SPACING["sm"], 0))
                    cb.bind("<Enter>", lambda e, s=spell: self._show_spell_detail(s))
                    self.spell_checkbuttons[spell["name"]] = cb

        # ── RIGHT: spell detail ──
        right = tk.Frame(self._content, bg=COLORS["bg"])
        right.grid(
            row=0, column=1, sticky="nsew",
            padx=(SPACING["xs"], SPACING["lg"]),
            pady=(SPACING["sm"], SPACING["lg"]),
        )
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        SectionHeader(right, text="Spell Details").pack(
            fill=tk.X, pady=(0, SPACING["sm"]),
        )

        detail_card = CardFrame(right, pad=SPACING["lg"])
        detail_card.pack(fill=tk.BOTH, expand=True)

        self._spell_detail_text = tk.Text(
            detail_card.inner,
            wrap=tk.WORD,
            bg=COLORS["bg_surface"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            state=tk.DISABLED,
        )
        self._spell_detail_text.pack(fill=tk.BOTH, expand=True)

        # Restore count labels
        self._update_counts()

    def _section_header(self, parent, title):
        tk.Label(
            parent,
            text=f"\u2500\u2500 {title} \u2500\u2500",
            font=FONTS["body"],
            fg=COLORS["accent"],
            bg=COLORS["bg"],
        ).pack(anchor="w", pady=(SPACING["sm"], SPACING["xs"]))

    def _make_scrollable_list(self, parent_frame):
        canvas = tk.Canvas(
            parent_frame, bg=COLORS["bg"], highlightthickness=0, borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(parent_frame, orient=tk.VERTICAL, command=canvas.yview)
        inner = tk.Frame(canvas, bg=COLORS["bg"])

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        cw = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e, _cw=cw: canvas.itemconfig(_cw, width=e.width))

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        register_mousewheel_target(parent_frame, canvas)
        register_mousewheel_target(canvas, canvas)
        register_mousewheel_target(inner, canvas)

        return canvas, inner

    def _on_cantrip_toggle(self, spell):
        if self._updating_cantrips:
            return
        self._updating_cantrips = True
        try:
            new_max, _, _ = spell_deltas(self.ctx.class_slug, self.ctx.new_class_level, self.data)
            selected = [n for n, d in self.cantrip_vars.items() if d["var"].get()]
            if len(selected) > new_max:
                self.cantrip_vars[spell["name"]]["var"].set(False)
                selected = [n for n, d in self.cantrip_vars.items() if d["var"].get()]
            self.ctx.selected_new_cantrips = selected
            self._update_counts()
            self._update_cantrip_states(new_max, selected)
            self.notify_change()
        finally:
            self._updating_cantrips = False

    def _on_spell_toggle(self, spell):
        if self._updating_spells:
            return
        self._updating_spells = True
        try:
            _, new_max, _ = spell_deltas(self.ctx.class_slug, self.ctx.new_class_level, self.data)
            selected = [n for n, d in self.spell_vars.items() if d["var"].get()]
            if len(selected) > new_max:
                self.spell_vars[spell["name"]]["var"].set(False)
                selected = [n for n, d in self.spell_vars.items() if d["var"].get()]
            self.ctx.selected_new_spells = selected
            self._update_counts()
            self._update_spell_states(new_max, selected)
            self.notify_change()
        finally:
            self._updating_spells = False

    def _update_counts(self):
        new_cantrips, new_prepared, _ = spell_deltas(
            self.ctx.class_slug, self.ctx.new_class_level, self.data
        )
        if self._cantrip_count:
            self._cantrip_count.configure(
                text=f"{len(self.ctx.selected_new_cantrips)} / {new_cantrips} cantrips selected"
            )
        if self._spell_count:
            self._spell_count.configure(
                text=f"{len(self.ctx.selected_new_spells)} / {new_prepared} spells selected"
            )

    def _update_cantrip_states(self, max_count, selected):
        at_max = len(selected) >= max_count
        for name, cb in self.cantrip_checkbuttons.items():
            cb.configure(state=tk.DISABLED if at_max and name not in selected else tk.NORMAL)

    def _update_spell_states(self, max_count, selected):
        at_max = len(selected) >= max_count
        for name, cb in self.spell_checkbuttons.items():
            cb.configure(state=tk.DISABLED if at_max and name not in selected else tk.NORMAL)

    def _show_spell_detail(self, spell):
        self._spell_detail_text.configure(state=tk.NORMAL)
        self._spell_detail_text.delete("1.0", tk.END)
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
        self._spell_detail_text.insert("1.0", "\n".join(lines))
        self._spell_detail_text.configure(state=tk.DISABLED)

    def is_valid(self) -> bool:
        ok, _, _ = validate_spell_step(self.ctx, self.data)
        return ok
