"""Level-up step: Features display (informational)."""

import tkinter as tk

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
from models.level_up_logic import (
    get_spell_summary,
    has_new_spell_options,
)


class LuFeaturesStep(LevelUpStep):
    tab_title = "Features"

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

        self._title_label = tk.Label(
            hero_row,
            text="New Features",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        )
        self._title_label.pack(side=tk.LEFT)

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
        level_data = self.data.get_level_data(
            self.ctx.class_slug, self.ctx.new_class_level
        )

        # Find class display name
        cls_name = self.ctx.class_slug.title()
        for cls in self.data.classes:
            if cls.get("slug") == self.ctx.class_slug:
                cls_name = cls.get("name", cls_name)
                break

        self._level_label.configure(text=f"{cls_name} Level {self.ctx.new_class_level}")

        # ── Features section ──
        self._build_features_section(inner, level_data)

        # ── Spell summary (informational) ──
        if has_new_spell_options(
            self.ctx.class_slug, self.ctx.new_class_level, self.data
        ):
            self._build_spell_summary(inner)

    def _build_features_section(self, parent, level_data):
        if not level_data:
            card = CardFrame(parent, pad=SPACING["lg"])
            card.pack(fill=tk.X, padx=SPACING["lg"], pady=SPACING["sm"])
            tk.Label(
                card.inner,
                text="No progression data available for this class/level.",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w")
            return

        features = level_data.get("features", [])
        details = level_data.get("feature_details", [])

        # Filter out ASI and subclass (handled by their own steps)
        display_features = [
            f
            for f in features
            if f not in ("-", "Ability Score Improvement")
            and not (
                f == "Subclass" or (f.startswith("Subclass") and "Feature" not in f)
            )
        ]

        if not display_features and not level_data.get("extra"):
            return

        SectionHeader(parent, text="New Features").pack(
            fill=tk.X,
            padx=SPACING["lg"],
            pady=(SPACING["lg"], SPACING["sm"]),
        )

        # Two-column grid for feature cards
        grid = tk.Frame(parent, bg=COLORS["bg"])
        grid.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        card_idx = 0

        for feat_name in display_features:
            # Subclass feature — show subclass features
            sub_slug = self.character.subclass_for_class(self.ctx.class_slug)
            if feat_name == "Subclass Feature" and sub_slug:
                card_idx = self._show_subclass_features(grid, card_idx)
                continue

            desc = self._find_feature_description(feat_name, details)

            card = CardFrame(
                grid,
                bg=COLORS["bg_container"],
                border_color=COLORS["border_subtle"],
                pad=SPACING["lg"],
            )
            card.grid(
                row=card_idx // 2,
                column=card_idx % 2,
                padx=SPACING["xs"],
                pady=SPACING["xs"],
                sticky="nsew",
            )
            header = tk.Frame(card.inner, bg=COLORS["bg_container"])
            header.pack(fill=tk.X)
            tk.Label(
                header,
                text=feat_name,
                font=FONTS["heading_serif_sm"],
                fg=COLORS["fg"],
                bg=COLORS["bg_container"],
            ).pack(side=tk.LEFT)
            PillBadge(
                header,
                text=f"LEVEL {self.ctx.new_class_level}",
                bg_color=COLORS["badge_glass_dim"],
                fg_color=COLORS["gold"],
            ).pack(side=tk.RIGHT)
            if desc:
                FormattedDescription(
                    card.inner,
                    text=desc,
                    font=FONTS["body_small"],
                    foreground=COLORS["fg_dim"],
                    background=COLORS["bg_container"],
                ).pack(fill=tk.X, pady=(SPACING["xs"], 0))
            card_idx += 1

        # Extra columns (e.g. Rage Damage, Martial Arts Die)
        extra = level_data.get("extra", {})
        if extra:
            for col_name, val in extra.items():
                if val is not None:
                    extra_card = CardFrame(
                        parent,
                        bg=COLORS["bg_container"],
                        border_color=COLORS["border_subtle"],
                        pad=SPACING["md"],
                    )
                    extra_card.pack(
                        fill=tk.X,
                        padx=SPACING["lg"],
                        pady=(0, SPACING["xs"]),
                    )
                    tk.Label(
                        extra_card.inner,
                        text=f"{col_name}: {val}",
                        font=FONTS["body"],
                        fg=COLORS["fg"],
                        bg=COLORS["bg_container"],
                    ).pack(anchor="w")

    def _find_feature_description(self, feat_name: str, details: list[dict]) -> str:
        feat_lower = feat_name.lower().replace("\u2019", "'")
        for d in details:
            d_lower = d["name"].lower().replace("\u2019", "'")
            if d_lower == feat_lower or feat_lower.startswith(d_lower + " ("):
                return d["description"]

        # Fallback: search all levels for the base feature description
        base_name = feat_name.split(" (")[0].lower().replace("\u2019", "'")
        prog = self.data.get_progression(self.ctx.class_slug)
        if prog:
            for lvl_data in prog.get("levels", []):
                for d in lvl_data.get("feature_details", []):
                    if d["name"].lower().replace("\u2019", "'") == base_name:
                        return d["description"]
        return ""

    def _show_subclass_features(self, grid, card_idx):
        sub_slug = self.character.subclass_for_class(self.ctx.class_slug)
        subclass = self.data.get_subclass(self.ctx.class_slug, sub_slug)
        if not subclass:
            return card_idx

        sub_features = subclass.get("features", {}).get(
            str(self.ctx.new_class_level), []
        )
        if not sub_features:
            return card_idx

        for feat in sub_features:
            card = CardFrame(
                grid,
                bg=COLORS["bg_container"],
                border_color=COLORS["border_subtle"],
                pad=SPACING["lg"],
            )
            card.grid(
                row=card_idx // 2,
                column=card_idx % 2,
                padx=SPACING["xs"],
                pady=SPACING["xs"],
                sticky="nsew",
            )
            header = tk.Frame(card.inner, bg=COLORS["bg_container"])
            header.pack(fill=tk.X)
            tk.Label(
                header,
                text=f"{feat['name']} (Subclass)",
                font=FONTS["heading_serif_sm"],
                fg=COLORS["fg"],
                bg=COLORS["bg_container"],
            ).pack(side=tk.LEFT)
            PillBadge(
                header,
                text=f"LEVEL {self.ctx.new_class_level}",
                bg_color=COLORS["badge_glass_dim"],
                fg_color=COLORS["gold"],
            ).pack(side=tk.RIGHT)
            desc = feat.get("description", "")
            if desc:
                FormattedDescription(
                    card.inner,
                    text=desc,
                    font=FONTS["body_small"],
                    foreground=COLORS["fg_dim"],
                    background=COLORS["bg_container"],
                ).pack(fill=tk.X, pady=(SPACING["xs"], 0))
            card_idx += 1
        return card_idx

    def _build_spell_summary(self, parent):
        parts = get_spell_summary(self.ctx, self.data)
        if not parts:
            return

        SectionHeader(parent, text="Spellcasting Changes").pack(
            fill=tk.X,
            padx=SPACING["lg"],
            pady=(SPACING["lg"], SPACING["sm"]),
        )

        card = CardFrame(parent, pad=SPACING["lg"])
        card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        for p in parts:
            tk.Label(
                card.inner,
                text=p,
                font=FONTS["body"],
                fg=COLORS["fg"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w", pady=1)

        tk.Label(
            card.inner,
            text="(Choose your new spells on the Spells step)",
            font=FONTS["body_small"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", pady=(SPACING["xs"], 0))

    def is_valid(self) -> bool:
        # Features step is informational — always valid
        return True
