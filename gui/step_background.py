"""Step 3: Background selection with grid tile view and detail substep."""

import re
import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import (
    ScrollableFrame,
    WrappingLabel,
    FormattedDescription,
    GradientHeader,
    SectionHeader,
    CardFrame,
    TileGrid,
)
from gui.theme import COLORS, FONTS, SPACING
from gui.source_config import (
    SECTION_ORDER,
    UA_CATEGORY,
    group_by_category,
    handle_ua_toggle,
    save_settings,
)


def _first_sentence(text: str) -> str:
    if not text:
        return ""
    for end in (".", "!", "?"):
        idx = text.find(end)
        if idx != -1:
            return text[: idx + 1]
    return text[:120] + ("..." if len(text) > 120 else "")


class BackgroundStep(WizardStep):
    tab_title = "Background"

    def build_ui(self):
        self._edit_initialized = False
        self._current_substep = 0

        # Two containers: grid view (substep 0) and detail view (substep 1)
        self._grid_frame = tk.Frame(self.frame, bg=COLORS["bg"])
        self._detail_frame = tk.Frame(self.frame, bg=COLORS["bg"])

        self._build_grid_view()
        self._build_detail_view()

        # Start on grid
        self._grid_frame.pack(fill=tk.BOTH, expand=True)

    # ── Substep protocol ──────────────────────────────────────────

    def has_substeps(self) -> bool:
        return True

    def get_current_substep(self) -> int:
        return self._current_substep

    def get_substep_count(self) -> int:
        return 2

    def go_to_substep(self, index: int):
        if index == self._current_substep:
            return
        self._current_substep = index
        if index == 0:
            self._detail_frame.pack_forget()
            self._grid_frame.pack(fill=tk.BOTH, expand=True)
        else:
            self._grid_frame.pack_forget()
            self._detail_frame.pack(fill=tk.BOTH, expand=True)
        self.notify_substep_change()

    def get_next_label(self) -> str | None:
        if self._current_substep == 1 and self.is_valid():
            return "Next: Choose Feat  \u25b6"
        return None

    # ── Grid View (substep 0) ─────────────────────────────────────

    def _build_grid_view(self):
        header = tk.Frame(self._grid_frame, bg=COLORS["bg"])
        header.pack(fill=tk.X, padx=SPACING["xl"], pady=(SPACING["xl"], 0))

        tk.Label(
            header,
            text="Choose Your Background",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Your background represents your character\u2019s life before adventuring. "
            "It grants skill proficiencies, a feat, and helps shape your identity.",
            font=FONTS["body_large"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
            wraplength=800,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(SPACING["sm"], 0))

        # Source filter toggles
        self._grid_toggle_frame = tk.Frame(self._grid_frame, bg=COLORS["bg"])
        self._grid_toggle_frame.pack(fill=tk.X, padx=SPACING["xl"], pady=(SPACING["md"], 0))
        self.toggle_vars: dict[str, tk.BooleanVar] = {}
        self._ua_prev_enabled = False
        self._build_toggles()

        # Tile grid (no images for backgrounds, narrower tiles)
        self._tile_grid = TileGrid(
            self._grid_frame, on_select=self._on_tile_click, tile_width=220,
        )
        self._tile_grid.pack(fill=tk.BOTH, expand=True, padx=SPACING["sm"], pady=SPACING["sm"])

        self._populate_tiles()

    def _build_toggles(self):
        """Build source filter checkboxes."""
        for w in self._grid_toggle_frame.winfo_children():
            w.destroy()
        self.toggle_vars.clear()

        filters = self.data.source_filters.get("backgrounds", {})
        sections = SECTION_ORDER["backgrounds"]
        self._ua_prev_enabled = filters.get(UA_CATEGORY, False)

        for cat in sections:
            label = "UA" if cat == UA_CATEGORY else cat
            var = tk.BooleanVar(value=filters.get(cat, cat != UA_CATEGORY))
            cb = ttk.Checkbutton(
                self._grid_toggle_frame,
                text=label,
                variable=var,
                command=self._on_toggle_change,
            )
            cb.pack(side=tk.LEFT, padx=(0, 6))
            self.toggle_vars[cat] = var

    def _on_toggle_change(self):
        ua_var = self.toggle_vars.get(UA_CATEGORY)
        proceed, _ = handle_ua_toggle(self.frame, ua_var, self._ua_prev_enabled)
        if not proceed:
            return

        filters = {cat: var.get() for cat, var in self.toggle_vars.items()}
        self.data.source_filters["backgrounds"] = filters
        self._ua_prev_enabled = filters.get(UA_CATEGORY, False)
        save_settings(self.data.source_filters)
        self._populate_tiles()

    def _populate_tiles(self):
        filters = self.data.source_filters.get("backgrounds", {})
        enabled = {cat for cat, on in filters.items() if on}

        grouped = group_by_category(self.data.backgrounds, "backgrounds")
        sections = []
        for cat, items in grouped:
            if cat not in enabled:
                continue
            cat_tiles = []
            for bg in items:
                traits = []
                feat = bg.get("feat", "")
                if feat:
                    traits.append(f"Feat: {feat}")
                skills = bg.get("skill_proficiencies", [])
                if skills:
                    traits.append(f"Skills: {', '.join(skills)}")
                tool = bg.get("tool_proficiency", "")
                if tool:
                    traits.append(f"Tool: {tool}")

                cat_tiles.append({
                    "name": bg["name"],
                    "description": _first_sentence(bg.get("description", "")),
                    "traits": traits,
                    "image_path": None,  # No images for backgrounds
                })
            if cat_tiles:
                sections.append((cat, cat_tiles))
        self._tile_grid.set_sectioned_tiles(sections)

    def _on_tile_click(self, name: str):
        """Handle tile click: select background and switch to detail view."""
        bg = self.data.backgrounds_by_name.get(name)
        if not bg:
            return
        self._on_select(name)
        self.go_to_substep(1)

    # ── Detail View (substep 1) — existing layout ─────────────────

    def _build_detail_view(self):
        self._detail_frame.columnconfigure(0, weight=1)
        self._detail_frame.rowconfigure(0, weight=1)

        right = ScrollableFrame(self._detail_frame)
        right.grid(row=0, column=0, sticky="nsew", padx=SPACING["sm"], pady=0)
        self.detail = right.inner

        # Hero header
        self._hero = GradientHeader(self.detail, min_height=60)
        self._hero.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))

        self.detail_name = tk.Label(
            self._hero.inner,
            text="Select a background",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        )
        self.detail_name.pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xl"], 0))

        self.detail_source = tk.Label(
            self._hero.inner,
            text="",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        )
        self.detail_source.pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xs"], SPACING["xl"]))

        self.detail_desc = WrappingLabel(
            self.detail, text="", foreground=COLORS["fg_dim"]
        )
        self.detail_desc.pack(fill=tk.X, anchor="w", padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        self.info_frame = tk.Frame(self.detail, bg=COLORS["bg"])
        self.info_frame.pack(fill=tk.X, padx=SPACING["lg"])

        # Ability bonus assignment
        self.bonus_frame = tk.Frame(self.detail, bg=COLORS["bg"])
        self.bonus_frame.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], 0))

        # Background feat details
        self.feat_frame = tk.Frame(self.detail, bg=COLORS["bg"])
        self.feat_frame.pack(
            fill=tk.X,
            padx=SPACING["lg"],
            pady=(SPACING["sm"], SPACING["lg"]),
        )

    def on_enter(self):
        """Pre-select background and bonus assignments when editing."""
        if not self._edit_initialized and self.character.background:
            self._edit_initialized = True
            name = self.character.background.get("name", "")
            saved_mode = self.character.ability_bonus_mode
            saved_bonuses = dict(self.character.ability_scores.bonuses)
            self._on_select(name)
            if hasattr(self, "bonus_mode"):
                self.bonus_mode.set(saved_mode)
                self._update_bonus_ui()
                if saved_mode == "2/1":
                    for ab, val in saved_bonuses.items():
                        if val == 2 and "+2" in self.bonus_combos:
                            self.bonus_combos["+2"].set(ab)
                        elif val == 1 and "+1" in self.bonus_combos:
                            self.bonus_combos["+1"].set(ab)
            self.go_to_substep(1)

    def _on_select(self, name: str):
        bg = self.data.backgrounds_by_name.get(name)
        if not bg:
            return

        self.character.background = bg
        self.detail_name.configure(text=bg["name"])
        self.detail_source.configure(text=f"Source: {bg.get('source', 'Unknown')}")
        self.detail_desc.configure(text=bg.get("description", ""))

        # Info section
        for w in self.info_frame.winfo_children():
            w.destroy()

        SectionHeader(self.info_frame, text="Details").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        info_card = CardFrame(self.info_frame, pad=SPACING["lg"])
        info_card.pack(fill=tk.X)

        info = [
            ("Skills", ", ".join(bg.get("skill_proficiencies", []))),
            ("Tool", bg.get("tool_proficiency", "None")),
        ]

        equip = bg.get("equipment", [])
        if equip:
            equip_text = " / ".join(f"({e['option']}) {e['items']}" for e in equip)
            info.append(("Equipment", equip_text))

        _bg = COLORS["bg_surface"]
        for label, value in info:
            row = tk.Frame(info_card.inner, bg=_bg)
            row.pack(fill=tk.X, pady=1)
            tk.Label(
                row,
                text=f"{label}:",
                font=FONTS["body_bold"],
                fg=COLORS["accent_text"],
                bg=_bg,
                width=12,
                anchor="e",
            ).pack(side=tk.LEFT)
            WrappingLabel(
                row, text=f"  {value}", background=_bg
            ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        # Ability bonus assignment
        for w in self.bonus_frame.winfo_children():
            w.destroy()

        abilities = bg.get("ability_scores", [])
        if abilities:
            SectionHeader(self.bonus_frame, text="Ability Score Bonuses").pack(
                fill=tk.X, pady=(SPACING["sm"], SPACING["sm"])
            )

            bonus_card = CardFrame(self.bonus_frame, pad=SPACING["lg"])
            bonus_card.pack(fill=tk.X)
            bonus_inner = bonus_card.inner

            tk.Label(
                bonus_inner,
                text=f"Distribute bonuses among: {', '.join(abilities)}",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w", pady=(0, SPACING["xs"]))

            mode_frame = tk.Frame(bonus_inner, bg=COLORS["bg_surface"])
            mode_frame.pack(fill=tk.X)
            self.bonus_mode = tk.StringVar(value="2/1")
            ttk.Radiobutton(
                mode_frame,
                text="+2 / +1",
                variable=self.bonus_mode,
                value="2/1",
                command=self._update_bonus_ui,
            ).pack(side=tk.LEFT, padx=SPACING["sm"])
            ttk.Radiobutton(
                mode_frame,
                text="+1 / +1 / +1",
                variable=self.bonus_mode,
                value="1/1/1",
                command=self._update_bonus_ui,
            ).pack(side=tk.LEFT, padx=SPACING["sm"])

            self.assign_frame = tk.Frame(bonus_inner, bg=COLORS["bg_surface"])
            self.assign_frame.pack(fill=tk.X, pady=(SPACING["xs"], 0))
            self.bonus_combos = {}
            self.bonus_widgets = {}
            self.current_abilities = abilities

            self._update_bonus_ui()

        # Set feat from background
        feat_name = bg.get("feat")
        feat = self.data.find_feat(feat_name) if feat_name else None
        self.character.feat = feat
        self._render_background_feat(feat_name, feat)

        self.notify_change()

    def _render_background_feat(self, feat_name: str, feat: dict | None):
        for w in self.feat_frame.winfo_children():
            w.destroy()

        if not feat_name:
            return

        SectionHeader(self.feat_frame, text="Background Feat").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        feat_card = CardFrame(self.feat_frame, pad=SPACING["lg"])
        feat_card.pack(fill=tk.X)

        tk.Label(
            feat_card.inner,
            text=feat_name,
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w")

        source_text = (
            f"Source: {feat.get('source', 'Unknown')}"
            if feat
            else "(Feat data not found)"
        )
        tk.Label(
            feat_card.inner,
            text=source_text,
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w")

        benefits_frame = tk.Frame(feat_card.inner, bg=COLORS["bg_surface"])
        benefits_frame.pack(fill=tk.X, pady=(SPACING["xs"], 0))

        if feat:
            self._render_feat_benefits(feat, benefits_frame)

        if "Magic Initiate" in feat_name:
            match = re.search(r"\(([^)]+)\)", feat_name)
            if match:
                spell_class = match.group(1)
                tk.Label(
                    feat_card.inner,
                    text=(
                        f"This grants 2 cantrips and 1 level 1 spell from the "
                        f"{spell_class} list. Select them in the Spells tab."
                    ),
                    font=FONTS["body"],
                    fg=COLORS["accent_text"],
                    bg=COLORS["bg_surface"],
                    wraplength=700,
                    justify=tk.LEFT,
                ).pack(fill=tk.X, anchor="w", pady=(SPACING["xs"], 0))

    def _render_feat_benefits(self, feat: dict, parent):
        """Render feat benefits into a frame."""
        _bg = parent.cget("bg") if hasattr(parent, "cget") else COLORS["bg_surface"]
        for benefit in feat.get("benefits", []):
            bf = tk.Frame(parent, bg=_bg)
            bf.pack(fill=tk.X, pady=2)
            tk.Label(
                bf,
                text=benefit.get("name", ""),
                font=FONTS["body_bold"],
                fg=COLORS["accent_text"],
                bg=_bg,
            ).pack(anchor="w")
            desc = benefit.get("description", "")
            if desc:
                FormattedDescription(
                    bf,
                    text=desc,
                    font=FONTS["body_small"],
                    foreground=COLORS["fg_dim"],
                    background=_bg,
                ).pack(fill=tk.X, anchor="w", padx=(SPACING["lg"], 0))

    def _update_bonus_ui(self):
        for w in self.assign_frame.winfo_children():
            w.destroy()
        self.bonus_combos.clear()
        self.bonus_widgets.clear()

        mode = self.bonus_mode.get()
        self.character.ability_bonus_mode = mode
        abilities = self.current_abilities
        _bg = COLORS["bg_surface"]

        if mode == "2/1":
            row1 = tk.Frame(self.assign_frame, bg=_bg)
            row1.pack(fill=tk.X, pady=2)
            tk.Label(row1, text="+2 to:", font=FONTS["body_bold"], fg=COLORS["fg"], bg=_bg, width=8).pack(side=tk.LEFT)
            var2 = tk.StringVar(value=abilities[0] if abilities else "")
            combo2 = ttk.Combobox(
                row1, textvariable=var2, values=abilities, state="readonly", width=15
            )
            combo2.pack(side=tk.LEFT, padx=4)
            self.bonus_combos["+2"] = var2
            self.bonus_widgets["+2"] = combo2

            row2 = tk.Frame(self.assign_frame, bg=_bg)
            row2.pack(fill=tk.X, pady=2)
            tk.Label(row2, text="+1 to:", font=FONTS["body_bold"], fg=COLORS["fg"], bg=_bg, width=8).pack(side=tk.LEFT)
            remaining = [a for a in abilities if a != abilities[0]] if abilities else []
            var1 = tk.StringVar(value=remaining[0] if remaining else "")
            combo1 = ttk.Combobox(
                row2, textvariable=var1, values=[a for a in abilities if a != abilities[0]] if abilities else [], state="readonly", width=15
            )
            combo1.pack(side=tk.LEFT, padx=4)
            self.bonus_combos["+1"] = var1
            self.bonus_widgets["+1"] = combo1

            var2.trace_add("write", self._on_bonus_change)
            var1.trace_add("write", self._on_bonus_change)

        else:
            for ab in abilities:
                row = tk.Frame(self.assign_frame, bg=_bg)
                row.pack(fill=tk.X, pady=2)
                tk.Label(row, text="+1 to:", font=FONTS["body_bold"], fg=COLORS["fg"], bg=_bg, width=8).pack(side=tk.LEFT)
                tk.Label(
                    row, text=ab, font=FONTS["body"], fg=COLORS["accent_text"], bg=_bg,
                ).pack(side=tk.LEFT, padx=4)

        self._on_bonus_change()

    def is_valid(self) -> bool:
        return self.character.background is not None

    def _on_bonus_change(self, *args):
        self.character.ability_scores.clear_bonuses()

        mode = self.bonus_mode.get()
        if mode == "2/1":
            plus2_var = self.bonus_combos.get("+2")
            plus1_var = self.bonus_combos.get("+1")
            ab2 = plus2_var.get() if plus2_var else ""
            ab1 = plus1_var.get() if plus1_var else ""
            abilities = self.current_abilities

            combo2_w = self.bonus_widgets.get("+2")
            combo1_w = self.bonus_widgets.get("+1")

            if combo1_w and ab2:
                allowed = [a for a in abilities if a != ab2]
                combo1_w["values"] = allowed
                if ab1 == ab2 and allowed:
                    plus1_var.set(allowed[0])
                    return
            elif combo1_w:
                combo1_w["values"] = abilities

            if combo2_w and ab1:
                combo2_w["values"] = [a for a in abilities if a != ab1]
            elif combo2_w:
                combo2_w["values"] = abilities

            if ab2:
                self.character.ability_scores.set_bonus(ab2, 2)
            if ab1 and ab1 != ab2:
                self.character.ability_scores.set_bonus(ab1, 1)
        else:
            for ab in self.current_abilities:
                self.character.ability_scores.set_bonus(ab, 1)

        self.character.ability_bonus_mode = mode
        self.notify_change()
