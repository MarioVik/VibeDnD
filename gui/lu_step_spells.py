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
    ModernSectionedListbox,
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
        self._spells_list: ModernSectionedListbox | None = None

    def on_enter(self):
        self._rebuild()

    def _rebuild(self):
        for w in self._content.winfo_children():
            w.destroy()
        self.cantrip_vars.clear()
        self.spell_vars.clear()

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

        self._spells_list = ModernSectionedListbox(
            left,
            multiselect=True,
            on_hover=self._show_spell_detail,
            on_select=self._on_spell_select_modern,
        )
        self._spells_list.pack(fill=tk.BOTH, expand=True, pady=(SPACING["xs"], 0))

        # ── Data Preparation ──
        class_name = ""
        for cls in self.data.classes:
            if cls.get("slug") == self.ctx.class_slug:
                class_name = cls.get("name", "")
                break

        sections = []
        all_cantrips = []
        available = []
        # Cantrips
        if new_cantrips > 0:
            all_cantrips = self.data.cantrips_for_class(class_name)
            known = set(self.character.selected_cantrips) | set(self.ctx.selected_new_cantrips)
            available_cantrips = [s for s in all_cantrips if s["name"] not in known]
            cantrip_names = [s["name"] for s in sorted(available_cantrips, key=lambda s: s["name"])]
            for s in available_cantrips:
                self.cantrip_vars[s["name"]] = {"var": tk.BooleanVar(value=s["name"] in self.ctx.selected_new_cantrips), "spell": s}
            sections.append(("Cantrips", cantrip_names))

        # Leveled spells
        if new_prepared > 0:
            all_spells = self.data.spells_for_class(class_name, max_level=max_spell_level)
            known = set(self.character.selected_spells) | set(self.ctx.selected_new_spells)
            available = [s for s in all_spells if s["name"] not in known and s.get("level", 0) >= 1]
            available.sort(key=lambda s: (s["level"], s["name"]))
            for lvl, group in groupby(available, key=lambda s: s["level"]):
                group_list = list(group)
                names = [s["name"] for s in group_list]
                for s in group_list:
                    self.spell_vars[s["name"]] = {"var": tk.BooleanVar(value=s["name"] in self.ctx.selected_new_spells), "spell": s}
                sections.append((_LEVEL_NAMES.get(lvl, f"Level {lvl}"), names))

        self._spells_list.set_sectioned_items(sections)
        self._all_spell_objects = {s["name"]: s for s in available + all_cantrips if s["name"] in self.cantrip_vars or s["name"] in self.spell_vars}

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

    def _on_spell_select_modern(self, name: str):
        # Determine if this was a cantrip or leveled spell
        spell = self._all_spell_objects.get(name)
        if not spell:
            return
            
        if spell["level"] == 0:
            # Sync to the ctx via the existing toggle logic
            self._on_cantrip_toggle_manual(name)
        else:
            self._on_spell_toggle_manual(name)

    def _on_cantrip_toggle_manual(self, spell_name: str):
        if self._updating_cantrips:
            return
        self._updating_cantrips = True
        try:
            new_max, _, _ = spell_deltas(self.ctx.class_slug, self.ctx.new_class_level, self.data)
            current = self.ctx.selected_new_cantrips
            if spell_name in current:
                current.remove(spell_name)
            else:
                if len(current) < new_max:
                    current.append(spell_name)
                else:
                    # Deselect in listbox if at cap?
                    # ModernSectionedListbox handles the visual toggle, we just stay in sync.
                    # If we refuse the add, we must deselect it.
                    self._spells_list.deselect_item(spell_name)
                    return
            
            self.ctx.selected_new_cantrips = current
            self._update_counts()
            self.notify_change()
        finally:
            self._updating_cantrips = False

    def _on_spell_toggle_manual(self, spell_name: str):
        if self._updating_spells:
            return
        self._updating_spells = True
        try:
            _, new_max, _ = spell_deltas(self.ctx.class_slug, self.ctx.new_class_level, self.data)
            current = self.ctx.selected_new_spells
            if spell_name in current:
                current.remove(spell_name)
            else:
                if len(current) < new_max:
                    current.append(spell_name)
                else:
                    self._spells_list.deselect_item(spell_name)
                    return
            
            self.ctx.selected_new_spells = current
            self._update_counts()
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


    def _show_spell_detail(self, name_or_spell: str | dict):
        if isinstance(name_or_spell, str):
            spell = self._all_spell_objects.get(name_or_spell)
        else:
            spell = name_or_spell
            
        if not spell:
            return

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
