"""Level-up step: Feat / Ability Score Improvement with split-detail layout."""

import tkinter as tk
from tkinter import ttk

from gui.lu_base_step import LevelUpStep
from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import (
    CardFrame,
    FormattedDescription,
    GradientHeader,
    SectionHeader,
    ModernSectionedListbox,
    ScrollableFrame,
    WrappingLabel,
    register_mousewheel_target,
)
from gui.source_config import (
    SECTION_ORDER,
    UA_CATEGORY,
    group_by_category,
)
from models.level_up_logic import (
    ALL_ABILITIES,
    parse_asi_options,
    validate_asi_step,
)


class LuAsiStep(LevelUpStep):
    tab_title = "Feat / ASI"

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # Hero header
        hero = GradientHeader(self.frame, min_height=60)
        hero.grid(row=0, column=0, sticky="ew")

        hero_inner = tk.Frame(hero.inner, bg=COLORS["bg_hero"])
        hero_inner.pack(
            fill=tk.X,
            padx=SPACING["card_pad"],
            pady=(SPACING["xl"], 0),
        )

        tk.Label(
            hero_inner,
            text="Ability Score Improvement",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        tk.Label(
            hero.inner,
            text="Choose a feat. The Ability Score Improvement feat lets you increase two scores.",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
            wraplength=760,
            justify=tk.LEFT,
        ).pack(
            anchor="w",
            padx=SPACING["card_pad"],
            pady=(SPACING["xs"], SPACING["xl"]),
        )

        # Split content: list (left) + detail (right)
        content = tk.Frame(self.frame, bg=COLORS["bg"])
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, minsize=280)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(1, weight=1)



        # Left: feat list
        list_frame = tk.Frame(content, bg=COLORS["bg"], width=280)
        list_frame.grid(
            row=1, column=0, sticky="nsew",
            padx=(SPACING["lg"], SPACING["xs"]),
            pady=(SPACING["sm"], SPACING["lg"]),
        )
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self._feat_list = ModernSectionedListbox(
            list_frame,
            radioselect=True,
            on_inspect=self._show_feat_detail,
            on_select=self._on_feat_select,
        )
        self._feat_list.grid(row=0, column=0, rowspan=2, sticky="nsew")

        # Right: detail panel
        detail_outer = tk.Frame(content, bg=COLORS["bg"])
        detail_outer.grid(
            row=1, column=1, sticky="nsew",
            padx=(SPACING["xs"], SPACING["lg"]),
            pady=(SPACING["sm"], SPACING["lg"]),
        )
        detail_outer.columnconfigure(0, weight=1)
        detail_outer.rowconfigure(1, weight=1)

        SectionHeader(detail_outer, text="Feat Details").grid(
            row=0, column=0, sticky="ew", pady=(0, SPACING["sm"]),
        )

        self._detail_scroll = ScrollableFrame(detail_outer, auto_hide_scrollbar=True)
        self._detail_scroll.grid(row=1, column=0, sticky="nsew")

    def on_enter(self):
        self._populate_feats()
        # Restore previous selection
        if self.ctx.feat_name:
            self._feat_list.select_item(self.ctx.feat_name)
            self._show_feat_detail(self.ctx.feat_name)



    def _populate_feats(self):
        filters = self.data.source_filters.get("feats", {})
        enabled = {cat for cat, on in filters.items() if on}

        # Get general feats + epic boons if level >= 19
        feat_options = []
        for feat in self.data.feats:
            cat = feat.get("category", "general")
            if cat == "general":
                feat_options.append(feat)
            elif cat == "epic_boon" and self.ctx.new_total_level >= 19:
                feat_options.append(feat)

        grouped = group_by_category(feat_options, "feats")
        sections = [
            (cat, [f["name"] for f in items])
            for cat, items in grouped
            if cat in enabled
        ]
        self._feat_list.set_sectioned_items(sections)

    def _on_feat_select(self, name: str):
        self.ctx.feat_name = name
        self.ctx.asi_selections.clear()
        self._show_feat_detail(name)
        self.notify_change()

    def _show_feat_detail(self, name: str):
        for w in self._detail_scroll.inner.winfo_children():
            w.destroy()

        inner = self._detail_scroll.inner
        feat = self.data.find_feat(name)
        if not feat:
            tk.Label(
                inner,
                text="Select a feat from the list.",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg"],
            ).pack(anchor="w", padx=SPACING["lg"], pady=SPACING["lg"])
            return

        # Feat info card
        card = CardFrame(inner, pad=SPACING["lg"])
        card.pack(fill=tk.X, padx=0, pady=(0, SPACING["sm"]))

        tk.Label(
            card.inner,
            text=name,
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w")

        source = feat.get("source", "Unknown")
        tk.Label(
            card.inner,
            text=source,
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", pady=(0, SPACING["xs"]))

        # Prerequisites
        prereqs = feat.get("prerequisites")
        if prereqs:
            prereq_text = str(prereqs.get("text", "") or "").strip()
            if not prereq_text:
                parts = []
                if prereqs.get("level"):
                    parts.append(f"Level {prereqs['level']}+")
                for ab, val in prereqs.get("abilities", {}).items():
                    parts.append(f"{ab} {val}+")
                prereq_text = ", ".join(parts)
            if prereq_text:
                tk.Label(
                    card.inner,
                    text=f"Prerequisites: {prereq_text}",
                    font=FONTS["body_small"],
                    fg=COLORS["fg_dim"],
                    bg=COLORS["bg_surface"],
                ).pack(anchor="w", pady=(0, SPACING["xs"]))

        # Benefits
        for benefit in feat.get("benefits", []):
            bf = tk.Frame(card.inner, bg=COLORS["bg_surface"])
            bf.pack(fill=tk.X, pady=(SPACING["xs"], 0))
            tk.Label(
                bf,
                text=benefit.get("name", ""),
                font=FONTS["body_bold"],
                fg=COLORS["accent_text"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w")
            desc = benefit.get("description", "")
            if desc:
                WrappingLabel(
                    bf,
                    text=desc,
                    font=FONTS["body_small"],
                    foreground=COLORS["fg_dim"],
                    background=COLORS["bg_surface"],
                ).pack(fill=tk.X, anchor="w", padx=(SPACING["lg"], 0))

        # ASI UI
        self._build_asi_ui(inner, feat)

    def _build_asi_ui(self, parent, feat: dict):
        asi_field = feat.get("ability_score_increase")
        name = feat.get("name", "")

        if name == "Ability Score Improvement":
            self._build_asi_full_choice(parent)
        elif asi_field:
            asi_options = parse_asi_options(feat)
            if len(asi_options) == 1:
                self._build_asi_fixed(parent, asi_options[0])
            elif asi_options:
                self._build_asi_choice_one(parent, asi_options)
            else:
                if asi_field == "Choice":
                    self._build_asi_choice_one(parent, ALL_ABILITIES)
                else:
                    self._build_asi_fixed(parent, asi_field)

    def _build_asi_full_choice(self, parent):
        card = CardFrame(parent, pad=SPACING["lg"])
        card.pack(fill=tk.X, pady=(SPACING["sm"], 0))

        tk.Label(
            card.inner,
            text="Ability Score Increase",
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w")

        self._asi_mode_var = tk.StringVar(value=self.ctx.asi_mode)
        mode_frame = tk.Frame(card.inner, bg=COLORS["bg_surface"])
        mode_frame.pack(fill=tk.X, pady=(SPACING["xs"], SPACING["xs"]))

        tk.Label(
            mode_frame,
            text="Mode:",
            font=FONTS["body"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(side=tk.LEFT)

        mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self._asi_mode_var,
            values=["+2 to one ability", "+1 to two abilities"],
            state="readonly",
            width=22,
        )
        mode_combo.pack(side=tk.LEFT, padx=(SPACING["sm"], 0))
        mode_combo.bind("<<ComboboxSelected>>", lambda *_: self._rebuild_asi_dropdowns(card.inner))

        self._asi_dropdowns_frame = tk.Frame(card.inner, bg=COLORS["bg_surface"])
        self._asi_dropdowns_frame.pack(fill=tk.X, pady=(0, SPACING["xs"]))

        self._asi_ability1_var = tk.StringVar(value=self.ctx.asi_ability1)
        self._asi_ability2_var = tk.StringVar(value=self.ctx.asi_ability2)

        self._rebuild_asi_dropdowns(card.inner)

    def _rebuild_asi_dropdowns(self, parent_card):
        for w in self._asi_dropdowns_frame.winfo_children():
            w.destroy()

        mode = self._asi_mode_var.get()
        self.ctx.asi_mode = mode
        self.ctx.asi_selections.clear()

        def ability_label(ab):
            score = self.character.ability_scores.total(ab)
            return f"{ab} ({score})"

        if mode == "+2 to one ability":
            row = tk.Frame(self._asi_dropdowns_frame, bg=COLORS["bg_surface"])
            row.pack(fill=tk.X, pady=SPACING["xs"])
            tk.Label(
                row, text="+2 to:", font=FONTS["body"],
                fg=COLORS["fg"], bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT)
            opts = [
                ability_label(ab) for ab in ALL_ABILITIES
                if self.character.ability_scores.total(ab) <= 18
            ]
            self._asi_ability1_var.set(self.ctx.asi_ability1)
            c1 = ttk.Combobox(
                row, textvariable=self._asi_ability1_var,
                values=opts, state="readonly", width=24,
            )
            c1.pack(side=tk.LEFT, padx=(SPACING["sm"], 0))
            c1.bind("<<ComboboxSelected>>", lambda *_: self._update_asi_selections())
        else:
            row1 = tk.Frame(self._asi_dropdowns_frame, bg=COLORS["bg_surface"])
            row1.pack(fill=tk.X, pady=SPACING["xs"])
            tk.Label(
                row1, text="First +1:", font=FONTS["body"],
                fg=COLORS["fg"], bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT)
            opts = [
                ability_label(ab) for ab in ALL_ABILITIES
                if self.character.ability_scores.total(ab) < 20
            ]
            self._asi_ability1_var.set(self.ctx.asi_ability1)
            c1 = ttk.Combobox(
                row1, textvariable=self._asi_ability1_var,
                values=opts, state="readonly", width=24,
            )
            c1.pack(side=tk.LEFT, padx=(SPACING["sm"], 0))
            c1.bind("<<ComboboxSelected>>", lambda *_: self._update_asi_selections())

            row2 = tk.Frame(self._asi_dropdowns_frame, bg=COLORS["bg_surface"])
            row2.pack(fill=tk.X, pady=SPACING["xs"])
            tk.Label(
                row2, text="Second +1:", font=FONTS["body"],
                fg=COLORS["fg"], bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT)
            self._asi_ability2_var.set(self.ctx.asi_ability2)
            c2 = ttk.Combobox(
                row2, textvariable=self._asi_ability2_var,
                values=opts, state="readonly", width=24,
            )
            c2.pack(side=tk.LEFT, padx=(SPACING["sm"], 0))
            c2.bind("<<ComboboxSelected>>", lambda *_: self._update_asi_selections())

    def _build_asi_choice_one(self, parent, abilities: list[str]):
        card = CardFrame(parent, pad=SPACING["lg"])
        card.pack(fill=tk.X, pady=(SPACING["sm"], 0))

        tk.Label(
            card.inner,
            text="Ability Score Increase",
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w")

        row = tk.Frame(card.inner, bg=COLORS["bg_surface"])
        row.pack(fill=tk.X, pady=(SPACING["xs"], 0))

        tk.Label(
            row, text="Ability +1:", font=FONTS["body"],
            fg=COLORS["fg"], bg=COLORS["bg_surface"],
        ).pack(side=tk.LEFT)

        self._asi_choice_var = tk.StringVar(value=self.ctx.asi_choice)
        opts = [
            f"{ab} ({self.character.ability_scores.total(ab)})"
            for ab in abilities
            if self.character.ability_scores.total(ab) < 20
        ]
        c = ttk.Combobox(
            row, textvariable=self._asi_choice_var,
            values=opts, state="readonly", width=24,
        )
        c.pack(side=tk.LEFT, padx=(SPACING["sm"], 0))
        c.bind("<<ComboboxSelected>>", lambda *_: self._update_asi_selections())

    def _build_asi_fixed(self, parent, ability: str):
        card = CardFrame(parent, pad=SPACING["lg"])
        card.pack(fill=tk.X, pady=(SPACING["sm"], 0))

        current = self.character.ability_scores.total(ability)
        tk.Label(
            card.inner,
            text=f"Ability Score Increase: {ability} +1  (current: {current} \u2192 {min(current + 1, 20)})",
            font=FONTS["body"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w")
        self.ctx.asi_selections = {ability: 1}

    def _extract_ability(self, label: str) -> str | None:
        if not label:
            return None
        return label.split(" (")[0]

    def _update_asi_selections(self):
        self.ctx.asi_selections.clear()
        feat = self.data.find_feat(self.ctx.feat_name) if self.ctx.feat_name else None
        asi_field = feat.get("ability_score_increase") if feat else None

        if self.ctx.feat_name == "Ability Score Improvement":
            mode = self._asi_mode_var.get()
            self.ctx.asi_mode = mode
            if mode == "+2 to one ability":
                ab = self._extract_ability(self._asi_ability1_var.get())
                self.ctx.asi_ability1 = self._asi_ability1_var.get()
                if ab:
                    self.ctx.asi_selections = {ab: 2}
            else:
                ab1 = self._extract_ability(self._asi_ability1_var.get())
                ab2 = self._extract_ability(self._asi_ability2_var.get())
                self.ctx.asi_ability1 = self._asi_ability1_var.get()
                self.ctx.asi_ability2 = self._asi_ability2_var.get()
                if ab1:
                    self.ctx.asi_selections[ab1] = self.ctx.asi_selections.get(ab1, 0) + 1
                if ab2:
                    self.ctx.asi_selections[ab2] = self.ctx.asi_selections.get(ab2, 0) + 1
        elif asi_field:
            ab = self._extract_ability(getattr(self, "_asi_choice_var", tk.StringVar()).get())
            self.ctx.asi_choice = getattr(self, "_asi_choice_var", tk.StringVar()).get()
            if ab:
                self.ctx.asi_selections = {ab: 1}

        self.notify_change()

    def is_valid(self) -> bool:
        ok, _, _ = validate_asi_step(self.ctx, self.character, self.data)
        return ok
