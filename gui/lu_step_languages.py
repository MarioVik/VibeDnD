"""Level-up step: Language selection (Deft Explorer)."""

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
from models.language_utils import STANDARD_LANGUAGES
from models.level_up_logic import validate_language_step


class LuLanguagesStep(LevelUpStep):
    tab_title = "Languages"

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
            text="Deft Explorer — Languages",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        self._scroll = ScrollableFrame(self.frame, auto_hide_scrollbar=True)
        self._scroll.grid(row=1, column=0, sticky="nsew")

        self._lang_vars: dict[str, tk.BooleanVar] = {}

    def on_enter(self):
        self._rebuild()

    def _rebuild(self):
        for w in self._scroll.inner.winfo_children():
            w.destroy()
        self._lang_vars.clear()

        inner = self._scroll.inner
        choices_needed = 2

        SectionHeader(inner, text="Choose Languages").pack(
            fill=tk.X, padx=SPACING["lg"],
            pady=(SPACING["lg"], SPACING["sm"]),
        )

        card = CardFrame(inner, pad=SPACING["lg"])
        card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        tk.Label(
            card.inner,
            text="Your Deft Explorer feature grants 2 languages of your choice.",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", pady=(0, SPACING["sm"]))

        chosen = len(self.ctx.language_selections)
        color = COLORS["positive"] if chosen == choices_needed else COLORS["fg_dim"]
        self._counter_label = tk.Label(
            card.inner,
            text=f"{chosen} / {choices_needed} chosen",
            font=FONTS["label_upper_bold"],
            fg=color,
            bg=COLORS["bg_surface"],
        )
        self._counter_label.pack(anchor="w", pady=(0, SPACING["sm"]))

        already_known = set(self.character.chosen_languages)
        already_known.add("Common")
        available = [lang for lang in STANDARD_LANGUAGES if lang not in already_known]

        lang_frame = tk.Frame(card.inner, bg=COLORS["bg_surface"])
        lang_frame.pack(fill=tk.X)

        for lang in available:
            var = tk.BooleanVar(value=lang in self.ctx.language_selections)
            cb = ttk.Checkbutton(
                lang_frame,
                text=lang,
                variable=var,
                style="Card.TCheckbutton",
                command=lambda l=lang, v=var: self._on_toggle(l, v, choices_needed),
            )
            cb.pack(anchor="w", pady=SPACING["xs"])
            self._lang_vars[lang] = var

    def _on_toggle(self, lang: str, var: tk.BooleanVar, choices_needed: int):
        if var.get():
            if len(self.ctx.language_selections) >= choices_needed:
                var.set(False)
                return
            if lang not in self.ctx.language_selections:
                self.ctx.language_selections.append(lang)
        else:
            if lang in self.ctx.language_selections:
                self.ctx.language_selections.remove(lang)

        chosen = len(self.ctx.language_selections)
        color = COLORS["positive"] if chosen == choices_needed else COLORS["fg_dim"]
        self._counter_label.configure(
            text=f"{chosen} / {choices_needed} chosen",
            fg=color,
        )
        self.notify_change()

    def is_valid(self) -> bool:
        ok, _, _ = validate_language_step(self.ctx)
        return ok
