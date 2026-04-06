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

        # ── Determine class groups ────────────────────────────────
        existing_slugs: set[str] = {cl.class_slug for cl in self.character.class_levels}
        class_by_slug: dict[str, dict] = {cls["slug"]: cls for cls in self.data.classes}

        primary_slug = self.ctx.primary_class_slug
        primary_cls = class_by_slug.get(primary_slug, {})
        other_existing = sorted(
            existing_slugs - {primary_slug},
            key=lambda s: class_by_slug.get(s, {}).get("name", s),
        )
        mc_classes = sorted(
            [c for c in self.data.classes if c["slug"] not in existing_slugs],
            key=lambda c: c.get("name", ""),
        )

        self._prereq_label = tk.Label(
            inner,
            text="",
            font=FONTS["body"],
            fg=COLORS["negative"],
            bg=COLORS["bg"],
        )

        # ── Primary class section ─────────────────────────────────
        SectionHeader(inner, text="Continue Your Path").pack(
            fill=tk.X,
            padx=SPACING["lg"],
            pady=(SPACING["lg"], SPACING["sm"]),
        )

        self._class_cards = {}

        # Primary class — full-width prominent card
        self._build_primary_card(inner, primary_cls, primary_slug)

        # Existing multiclass classes (if already multiclassed)
        if other_existing:
            existing_grid = tk.Frame(inner, bg=COLORS["bg"])
            existing_grid.pack(
                fill=tk.X,
                padx=SPACING["lg"],
                pady=(SPACING["xs"], 0),
            )
            for ci in range(3):
                existing_grid.columnconfigure(ci, weight=1)

            for i, slug in enumerate(other_existing):
                cls = class_by_slug.get(slug, {})
                self._build_class_card(
                    existing_grid,
                    cls,
                    slug,
                    row=i // 3,
                    col=i % 3,
                )

        # ── Multiclass section ────────────────────────────────────
        if mc_classes:
            SectionHeader(
                inner,
                text="Multiclass",
                right_text="OPTIONAL",
            ).pack(
                fill=tk.X,
                padx=SPACING["lg"],
                pady=(SPACING["xl"], SPACING["sm"]),
            )

            tk.Label(
                inner,
                text="Take a level in a different class. You must meet the "
                "ability score prerequisites for both your current class "
                "and the new class.",
                font=FONTS["body_small"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg"],
                wraplength=700,
                justify=tk.LEFT,
            ).pack(
                anchor="w",
                padx=SPACING["lg"],
                pady=(0, SPACING["sm"]),
            )

            self._prereq_label.pack(
                anchor="w",
                padx=SPACING["lg"],
                pady=(0, SPACING["sm"]),
            )

            mc_grid = tk.Frame(inner, bg=COLORS["bg"])
            mc_grid.pack(
                fill=tk.X,
                padx=SPACING["lg"],
                pady=(0, SPACING["lg"]),
            )
            for ci in range(3):
                mc_grid.columnconfigure(ci, weight=1)

            for i, cls in enumerate(mc_classes):
                slug = cls.get("slug", "")
                self._build_class_card(
                    mc_grid,
                    cls,
                    slug,
                    row=i // 3,
                    col=i % 3,
                )

    # ── Card builders ─────────────────────────────────────────────

    def _build_primary_card(self, parent, cls: dict, slug: str):
        """Build the prominent full-width card for the primary class."""
        name = cls.get("name", slug.title())
        is_selected = slug == self.ctx.class_slug
        current_levels = self.character.class_level_in(slug)

        border = COLORS["accent"] if is_selected else COLORS["outline_dim"]
        card = CardFrame(
            parent,
            bg=COLORS["bg_high"] if is_selected else COLORS["bg_container"],
            border_color=border,
            pad=SPACING["md"],
        )
        card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["xs"]))

        header = tk.Frame(card.inner, bg=card.inner.cget("bg"))
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text=f"Continue as {name}",
            font=FONTS["heading_serif"],
            fg=COLORS["accent_text"] if is_selected else COLORS["fg"],
            bg=card.inner.cget("bg"),
        ).pack(side=tk.LEFT)

        # Recommended pill
        PillBadge(
            header,
            text="RECOMMENDED",
            bg_color=COLORS["gold_dark"],
            fg_color=COLORS["gold_on_dark"],
        ).pack(side=tk.RIGHT, padx=(SPACING["xs"], 0))

        PillBadge(
            header,
            text=f"LVL {current_levels} \u2192 {current_levels + 1}",
            bg_color=COLORS["badge_glass_dim"],
            fg_color=COLORS["gold"],
        ).pack(side=tk.RIGHT, padx=(SPACING["xs"], 0))

        PillBadge(
            header,
            text="PRIMARY",
            bg_color=COLORS["accent"],
            fg_color=COLORS["accent_text"],
        ).pack(side=tk.RIGHT)

        desc = cls.get("description", "")
        if desc:
            short_desc = desc[:180] + "..." if len(desc) > 180 else desc
            tk.Label(
                card.inner,
                text=short_desc,
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=card.inner.cget("bg"),
                wraplength=700,
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

        self._class_cards[slug] = card
        for widget in [card, card.inner] + list(card.inner.winfo_children()):
            widget.bind("<Button-1>", lambda e, s=slug: self._select_class(s))
            if hasattr(widget, "winfo_children"):
                for child in widget.winfo_children():
                    child.bind(
                        "<Button-1>",
                        lambda e, s=slug: self._select_class(s),
                    )

    def _build_class_card(
        self,
        grid,
        cls: dict,
        slug: str,
        row: int,
        col: int,
    ):
        """Build a standard class card in the grid."""
        name = cls.get("name", slug.title())
        is_primary = slug == self.ctx.primary_class_slug
        is_selected = slug == self.ctx.class_slug
        current_levels = self.character.class_level_in(slug)

        border = COLORS["accent"] if is_selected else COLORS["border_subtle"]
        card = CardFrame(
            grid,
            bg=COLORS["bg_high"] if is_selected else COLORS["bg_container"],
            border_color=border,
            pad=SPACING["md"],
        )
        card.grid(
            row=row,
            column=col,
            padx=SPACING["xs"],
            pady=SPACING["xs"],
            sticky="nsew",
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

        self._class_cards[slug] = card
        for widget in [card, card.inner] + list(card.inner.winfo_children()):
            widget.bind("<Button-1>", lambda e, s=slug: self._select_class(s))
            if hasattr(widget, "winfo_children"):
                for child in widget.winfo_children():
                    child.bind(
                        "<Button-1>",
                        lambda e, s=slug: self._select_class(s),
                    )

    def _select_class(self, slug: str):
        self.ctx.class_slug = slug
        self.ctx.new_class_level = self.character.class_level_in(slug) + 1

        # Check prerequisites (store message for after rebuild)
        ok, title, msg = validate_class_step(self.ctx, self.character)
        prereq_msg = "" if ok else f"\u26a0 {msg}"

        # Reset dependent state
        self.ctx.subclass_name = ""
        self.ctx.subclass_slug = None
        self.ctx.feat_name = ""
        self.ctx.asi_selections.clear()

        self._rebuild()
        if prereq_msg:
            self._prereq_label.configure(text=prereq_msg)
        self.notify_change()

    def is_valid(self) -> bool:
        ok, _, _ = validate_class_step(self.ctx, self.character)
        return ok
