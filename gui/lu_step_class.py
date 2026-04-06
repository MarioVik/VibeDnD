"""Level-up step: Multiclass selector."""

import tkinter as tk
from tkinter import ttk

from gui.lu_base_step import LevelUpStep
from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import (
    CardFrame,
    FormattedDescription,
    GradientHeader,
    PillBadge,
    SectionHeader,
    ScrollableFrame,
)
from models.level_up_logic import validate_class_step


class LuClassStep(LevelUpStep):
    tab_title = "Class"

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
            text="Choose Class",
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

        self._scroll = ScrollableFrame(self.frame, auto_hide_scrollbar=True)
        self._scroll.grid(row=1, column=0, sticky="nsew")

        self._selected_card = None

    def on_enter(self):
        self._rebuild()

    def _rebuild(self):
        for w in self._scroll.inner.winfo_children():
            w.destroy()

        inner = self._scroll.inner
        self._level_label.configure(text=f"Total Level {self.ctx.new_total_level}")

        SectionHeader(inner, text="Select the class to advance in").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["sm"]),
        )

        tk.Label(
            inner,
            text="Choose which class to take your next level in. "
                 "Your primary class is highlighted.",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
            wraplength=700,
            justify=tk.LEFT,
        ).pack(anchor="w", padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        self._prereq_label = tk.Label(
            inner,
            text="",
            font=FONTS["body"],
            fg=COLORS["negative"],
            bg=COLORS["bg"],
        )
        self._prereq_label.pack(anchor="w", padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        # Build a card for each available class
        grid = tk.Frame(inner, bg=COLORS["bg"])
        grid.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["lg"]))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(2, weight=1)

        self._class_cards = {}
        for i, cls in enumerate(sorted(self.data.classes, key=lambda c: c.get("name", ""))):
            slug = cls.get("slug", "")
            name = cls.get("name", slug.title())
            is_primary = slug == self.ctx.primary_class_slug
            is_selected = slug == self.ctx.class_slug
            current_levels = self.character.class_level_in(slug)

            border = COLORS["accent"] if is_selected else COLORS["border_subtle"]
            card = CardFrame(
                grid,
                bg=COLORS["bg_container"] if not is_selected else COLORS["bg_high"],
                border_color=border,
                pad=SPACING["md"],
            )
            card.grid(
                row=i // 3, column=i % 3,
                padx=SPACING["xs"], pady=SPACING["xs"], sticky="nsew",
            )

            header = tk.Frame(card.inner, bg=card.inner.cget("bg"))
            header.pack(fill=tk.X)

            tk.Label(
                header,
                text=name,
                font=FONTS["heading_serif_sm"],
                fg=COLORS["fg"],
                bg=card.inner.cget("bg"),
            ).pack(side=tk.LEFT)

            if is_primary:
                PillBadge(
                    header,
                    text="PRIMARY",
                    bg_color=COLORS["accent"],
                    fg_color=COLORS["accent_text"],
                ).pack(side=tk.RIGHT, padx=(SPACING["xs"], 0))

            if current_levels > 0:
                PillBadge(
                    header,
                    text=f"LVL {current_levels}",
                    bg_color=COLORS["badge_glass_dim"],
                    fg_color=COLORS["gold"],
                ).pack(side=tk.RIGHT)

            desc = cls.get("description", "")
            if desc:
                short_desc = desc[:120] + "..." if len(desc) > 120 else desc
                tk.Label(
                    card.inner,
                    text=short_desc,
                    font=FONTS["body_small"],
                    fg=COLORS["fg_dim"],
                    bg=card.inner.cget("bg"),
                    wraplength=220,
                    justify=tk.LEFT,
                ).pack(anchor="w", pady=(SPACING["xs"], 0))

            hit_die = cls.get("hit_die", "?")
            tk.Label(
                card.inner,
                text=f"Hit Die: d{hit_die}",
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg_dim"],
                bg=card.inner.cget("bg"),
            ).pack(anchor="w", pady=(SPACING["xs"], 0))

            # Make the card clickable
            self._class_cards[slug] = card
            for widget in [card, card.inner] + list(card.inner.winfo_children()):
                widget.bind("<Button-1>", lambda e, s=slug: self._select_class(s))
                if hasattr(widget, "winfo_children"):
                    for child in widget.winfo_children():
                        child.bind("<Button-1>", lambda e, s=slug: self._select_class(s))

    def _select_class(self, slug: str):
        self.ctx.class_slug = slug
        self.ctx.new_class_level = self.character.class_level_in(slug) + 1

        # Check prerequisites
        ok, title, msg = validate_class_step(self.ctx, self.character)
        if not ok:
            self._prereq_label.configure(text=f"\u26a0 {msg}")
        else:
            self._prereq_label.configure(text="")

        # Reset dependent state
        self.ctx.subclass_name = ""
        self.ctx.subclass_slug = None
        self.ctx.feat_name = ""
        self.ctx.asi_selections.clear()

        self._rebuild()
        self.notify_change()

    def is_valid(self) -> bool:
        ok, _, _ = validate_class_step(self.ctx, self.character)
        return ok
