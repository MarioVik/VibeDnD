"""Level-up step: Hit Point selection."""

import tkinter as tk
from tkinter import ttk

from gui.lu_base_step import LevelUpStep
from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import (
    CardFrame,
    GradientHeader,
    SectionHeader,
    ScrollableFrame,
)
from models.level_up_logic import validate_hp_step


class LuHpStep(LevelUpStep):
    tab_title = "Hit Points"

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # Hero header
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
            text="Hit Points",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        self._level_label = tk.Label(
            hero_row,
            text="",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        )
        self._level_label.pack(side=tk.RIGHT)

        # Scrollable content
        self._scroll = ScrollableFrame(self.frame, auto_hide_scrollbar=True)
        self._scroll.grid(row=1, column=0, sticky="nsew")

    def on_enter(self):
        self._rebuild()

    def _rebuild(self):
        for w in self._scroll.inner.winfo_children():
            w.destroy()

        inner = self._scroll.inner

        # Find class display name
        cls_name = self.ctx.class_slug.title()
        for cls in self.data.classes:
            if cls.get("slug") == self.ctx.class_slug:
                cls_name = cls.get("name", cls_name)
                break

        self._level_label.configure(text=f"{cls_name} Level {self.ctx.new_class_level}")

        self._build_hp_section(inner, cls_name)

    def _build_hp_section(self, parent, cls_name: str):
        SectionHeader(parent, text="Hit Points").pack(
            fill=tk.X,
            padx=SPACING["lg"],
            pady=(SPACING["lg"], SPACING["sm"]),
        )

        selected_class_data = None
        for cls in self.data.classes:
            if cls.get("slug") == self.ctx.class_slug:
                selected_class_data = cls
                break

        hit_die = selected_class_data.get("hit_die", 8) if selected_class_data else 8
        con_mod = self.character.ability_scores.modifier("Constitution")
        average = hit_die // 2 + 1

        card = CardFrame(parent, pad=SPACING["lg"])
        card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))
        inner = card.inner

        tk.Label(
            inner,
            text=f"Hit Die: d{hit_die}  |  CON Modifier: {'+' if con_mod >= 0 else ''}{con_mod}",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", pady=(0, SPACING["sm"]))

        # Average option
        self._hp_mode_var = tk.StringVar(value=self.ctx.hp_mode)
        avg_frame = tk.Frame(inner, bg=COLORS["bg_surface"])
        avg_frame.pack(fill=tk.X, pady=(0, SPACING["xs"]))

        ttk.Radiobutton(
            avg_frame,
            text=f"Take average ({average} + {con_mod} CON = {average + con_mod} HP)",
            variable=self._hp_mode_var,
            value="average",
            style="Card.TRadiobutton",
            command=self._on_hp_change,
        ).pack(anchor="w")

        # Manual option
        manual_frame = tk.Frame(inner, bg=COLORS["bg_surface"])
        manual_frame.pack(fill=tk.X)

        ttk.Radiobutton(
            manual_frame,
            text="Roll manually:",
            variable=self._hp_mode_var,
            value="manual",
            style="Card.TRadiobutton",
            command=self._on_hp_change,
        ).pack(side=tk.LEFT)

        self._hp_manual_var = tk.StringVar(value=self.ctx.hp_manual_value)
        self._manual_entry = ttk.Entry(
            manual_frame,
            textvariable=self._hp_manual_var,
            width=5,
        )
        self._manual_entry.pack(side=tk.LEFT, padx=(SPACING["xs"], SPACING["xs"]))

        self._hp_hint = tk.Label(
            manual_frame,
            text=f"+ {con_mod} CON = ? HP",
            font=FONTS["body_small"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        )
        self._hp_hint.pack(side=tk.LEFT)

        self._hp_manual_var.trace_add("write", self._on_manual_change)
        self._hp_mode_var.trace_add("write", self._on_hp_change)
        self._update_manual_state()

    def _on_hp_change(self, *_):
        self.ctx.hp_mode = self._hp_mode_var.get()
        self._update_manual_state()

    def _on_manual_change(self, *_):
        self.ctx.hp_manual_value = self._hp_manual_var.get()
        self._update_hint()

    def _update_manual_state(self):
        if self._hp_mode_var.get() == "manual":
            self._manual_entry.config(state="normal")
        else:
            self._manual_entry.config(state="disabled")
        self._update_hint()

    def _update_hint(self):
        if self._hp_mode_var.get() != "manual":
            return
        con_mod = self.character.ability_scores.modifier("Constitution")
        val = self._hp_manual_var.get().strip()
        try:
            roll = int(val)
            if roll >= 1:
                self._hp_hint.config(text=f"+ {con_mod} CON = {roll + con_mod} HP")
            else:
                self._hp_hint.config(text="(must be >= 1)")
        except ValueError:
            self._hp_hint.config(text=f"+ {con_mod} CON = ? HP")

    def is_valid(self) -> bool:
        ok, _, _ = validate_hp_step(self.ctx)
        return ok
