"""Level-up step: Spell swap (optional, for Bard/Sorcerer/Warlock)."""

import tkinter as tk
from tkinter import ttk

from gui.lu_base_step import LevelUpStep
from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import (
    GradientHeader,
    SectionHeader,
    CardFrame,
)
from gui.spell_swap_panel import SpellSwapPanel
from models.level_up_logic import (
    get_max_swap_spell_level,
    validate_swap_step,
)


class LuSwapStep(LevelUpStep):
    tab_title = "Spell Swap"

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
            text="Swap Spells",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        tk.Label(
            hero.inner,
            text="You may replace one known spell or cantrip with a different one from your class list. This is optional.",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
            wraplength=760,
            justify=tk.LEFT,
        ).pack(
            anchor="w",
            padx=SPACING["card_pad"],
            pady=(0, SPACING["xl"]),
        )

        self._content = tk.Frame(self.frame, bg=COLORS["bg"])
        self._content.grid(row=1, column=0, sticky="nsew")
        self._content.columnconfigure(0, weight=1)
        self._content.rowconfigure(0, weight=1)
        self._swap_panel = None

    def on_enter(self):
        self._rebuild()

    def _rebuild(self):
        for w in self._content.winfo_children():
            w.destroy()

        class_name = ""
        for cls in self.data.classes:
            if cls.get("slug") == self.ctx.class_slug:
                class_name = cls.get("name", "")
                break

        max_spell_level = get_max_swap_spell_level(self.ctx, self.data)

        def _find_spell(name):
            for s in self.data.spells_for_class(class_name, max_level=9):
                if s["name"] == name:
                    return s
            for s in self.data.cantrips_for_class(class_name):
                if s["name"] == name:
                    return s
            return None

        forget_cantrips = [d for n in self.character.selected_cantrips if (d := _find_spell(n))]
        forget_spells = [d for n in self.character.selected_spells if (d := _find_spell(n))]

        known_c_set = set(self.character.selected_cantrips) | set(self.ctx.selected_new_cantrips)
        learn_cantrips = [
            s for s in self.data.cantrips_for_class(class_name)
            if s["name"] not in known_c_set
        ]

        known_s_set = set(self.character.selected_spells) | set(self.ctx.selected_new_spells)
        learn_spells = [
            s for s in self.data.spells_for_class(class_name, max_level=max_spell_level)
            if s["name"] not in known_s_set and s.get("level", 0) >= 1
        ]

        self._swap_panel = SpellSwapPanel(
            self._content,
            forget_spells=forget_spells,
            learn_spells=learn_spells,
            forget_cantrips=forget_cantrips,
            learn_cantrips=learn_cantrips,
            allow_cantrips=True,
        )

        def _sync_swap_vars(*_):
            fv = self._swap_panel.forget_var.get()
            lv = self._swap_panel.learn_var.get()
            if not fv:
                self.ctx.swap_out_cantrip = None
                self.ctx.swap_out_spell = None
                self.ctx.swap_in_cantrip = None
                self.ctx.swap_in_spell = None
            elif fv.startswith("C:"):
                self.ctx.swap_out_cantrip = fv[2:]
                self.ctx.swap_out_spell = None
                self.ctx.swap_in_cantrip = lv or None
                self.ctx.swap_in_spell = None
            else:
                self.ctx.swap_out_spell = fv[2:]
                self.ctx.swap_out_cantrip = None
                self.ctx.swap_in_spell = lv or None
                self.ctx.swap_in_cantrip = None

        self._swap_panel.forget_var.trace_add("write", _sync_swap_vars)
        self._swap_panel.learn_var.trace_add("write", _sync_swap_vars)

    def is_valid(self) -> bool:
        ok, _, _ = validate_swap_step(self.ctx)
        return ok
