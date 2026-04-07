"""Level-up step: Subclass selection with tile grid + detail view."""

import re
import tkinter as tk
from tkinter import ttk

from gui.lu_base_step import LevelUpStep
from gui.source_config import (
    SECTION_ORDER,
    UA_CATEGORY,
    group_by_category,
    handle_ua_toggle,
    save_settings,
)
from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import (
    CardFrame,
    Chip,
    FormattedDescription,
    GradientHeader,
    PillBadge,
    ScrollableFrame,
    SectionHeader,
    TileGrid,
    WrappingLabel,
)
from models.level_up_logic import validate_subclass_step


class LuSubclassStep(LevelUpStep):
    tab_title = "Subclass"

    def __init__(self, parent, character, game_data, *, level_up_ctx):
        self._current_substep = 0
        self._selected_subclass_data = None
        super().__init__(parent, character, game_data, level_up_ctx=level_up_ctx)

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)

        # Grid view (substep 0)
        self._grid_view = tk.Frame(self.frame, bg=COLORS["bg"])
        self._grid_view.columnconfigure(0, weight=1)
        self._grid_view.rowconfigure(2, weight=1)

        grid_hero = GradientHeader(self._grid_view, min_height=60)
        grid_hero.grid(row=0, column=0, sticky="ew")

        grid_hero_row = tk.Frame(grid_hero.inner, bg=COLORS["bg_hero"])
        grid_hero_row.pack(
            fill=tk.X,
            padx=SPACING["card_pad"],
            pady=(SPACING["xl"], SPACING["xl"]),
        )

        tk.Label(
            grid_hero_row,
            text="Choose Subclass",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        tk.Label(
            grid_hero.inner,
            text="Select a subclass specialization for your character.",
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

        # Source filter toggles
        self._grid_toggle_frame = tk.Frame(self._grid_view, bg=COLORS["bg"])
        self._grid_toggle_frame.grid(row=1, column=0, sticky="ew", padx=SPACING["xl"], pady=(SPACING["md"], 0))
        self.toggle_vars: dict[str, tk.BooleanVar] = {}
        self._ua_prev_enabled = False

        self._tile_grid = TileGrid(
            self._grid_view,
            on_select=self._on_tile_click,
            preferred_cols=4,
            tile_width=250,
            tile_height=180,
            min_tile_width=200,
            expand_tiles_to_fill=True,
            expand_gap_with_tile=True,
            responsive_tile_height=True,
            content_side_padding=SPACING["xl"],
        )
        self._tile_grid.grid(row=2, column=0, sticky="nsew")

        # Detail view (substep 1)
        self._detail_view = tk.Frame(self.frame, bg=COLORS["bg"])
        self._detail_view.columnconfigure(0, weight=1)
        self._detail_view.rowconfigure(1, weight=1)

        self._detail_hero = GradientHeader(self._detail_view, min_height=80)
        self._detail_hero.grid(row=0, column=0, sticky="ew")

        self._detail_scroll = ScrollableFrame(self._detail_view, auto_hide_scrollbar=True)
        self._detail_scroll.grid(row=1, column=0, sticky="nsew")

    # ── Substep protocol ──

    def has_substeps(self) -> bool:
        return True

    def get_current_substep(self) -> int:
        return self._current_substep

    def get_substep_count(self) -> int:
        return 2

    def go_to_substep(self, index: int):
        new_index = max(0, min(1, index))
        if new_index == self._current_substep:
            return
        self._current_substep = new_index
        self._show_current_substep()
        self.notify_substep_change()

    def is_primary_action_visible(self) -> bool:
        return self._current_substep == 1

    def is_primary_action_enabled(self) -> bool:
        return self.is_valid()

    def is_current_substep_valid(self) -> bool:
        if self._current_substep == 0:
            return False  # Must select a tile to advance
        return self.is_valid()

    def _show_current_substep(self):
        self._grid_view.pack_forget()
        self._detail_view.pack_forget()
        if self._current_substep == 0:
            self._grid_view.pack(fill=tk.BOTH, expand=True)
        else:
            self._detail_view.pack(fill=tk.BOTH, expand=True)
            self._build_detail()

    # ── Lifecycle ──

    def on_enter(self):
        self._build_toggles()
        self._populate_tiles()
        self._show_current_substep()

    def _build_toggles(self):
        """Build source filter checkboxes for subclass sources."""
        for w in self._grid_toggle_frame.winfo_children():
            w.destroy()
        self.toggle_vars.clear()

        filters = self.data.source_filters.get("subclasses", {})
        sections = SECTION_ORDER.get("subclasses", [])
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
        self.data.source_filters["subclasses"] = filters
        self._ua_prev_enabled = filters.get(UA_CATEGORY, False)
        save_settings(self.data.source_filters)
        self._populate_tiles()

    def _populate_tiles(self):
        subclasses = self.data.get_subclasses_for_class(self.ctx.class_slug)

        # Merge duplicate entries by slug: some subclasses have a named entry
        # with empty features and an "Unknown" entry with the actual features.
        merged: dict[str, dict] = {}
        for sc in subclasses:
            slug = sc.get("slug", "")
            if slug not in merged:
                merged[slug] = dict(sc)
            else:
                existing = merged[slug]
                # Prefer a real name over "Unknown"
                if existing.get("name") == "Unknown" and sc.get("name") != "Unknown":
                    existing["name"] = sc["name"]
                elif sc.get("name") == "Unknown" and existing.get("name") != "Unknown":
                    pass  # keep existing name
                # Merge features: keep whichever has data
                if not existing.get("features") and sc.get("features"):
                    existing["features"] = sc["features"]
                    existing["feature_levels"] = sc.get("feature_levels", [])
                # Prefer longer description
                if len(sc.get("description") or "") > len(existing.get("description") or ""):
                    existing["description"] = sc["description"]

        subclass_list = list(merged.values())

        # Also include PHB core subclass names
        prog = self.data.get_progression(self.ctx.class_slug)
        phb_names = set()
        if prog:
            for name in prog.get("subclass_names", []):
                phb_names.add(name)

        existing_names = {sc["name"].lower() for sc in subclass_list if sc.get("name") != "Unknown"}

        # Build PHB stub entries for names not in detailed data
        phb_stubs = []
        for name in sorted(phb_names):
            if name.lower() not in existing_names:
                phb_stubs.append({
                    "name": f"{name} (PHB)",
                    "source": "Player's Handbook",
                    "description": "Core subclass — detailed feature data not available.",
                    "features": {},
                })

        # Drop any still-unnamed entries after merge
        all_subclasses = [
            sc for sc in subclass_list if sc.get("name") != "Unknown"
        ] + phb_stubs

        filters = self.data.source_filters.get("subclasses", {})
        enabled = {cat for cat, on in filters.items() if on}

        grouped = group_by_category(all_subclasses, "subclasses")
        sections = []
        for cat, items in grouped:
            if cat not in enabled:
                continue
            cat_tiles = []
            for sc in items:
                traits = self._collect_all_feature_names(sc)
                cat_tiles.append({
                    "name": sc["name"],
                    "description": (sc.get("description") or "")[:150],
                    "traits": traits,
                    "image_path": None,
                    "variant": "lore",
                })
            if cat_tiles:
                sections.append((cat, cat_tiles))
        self._tile_grid.set_sectioned_tiles(sections)

    @staticmethod
    def _collect_all_feature_names(sc: dict) -> list[str]:
        """Collect feature names from all levels for badge display."""
        features_by_level = sc.get("features", {})
        if not features_by_level:
            return []

        def _lvl_key(level_str: str) -> int:
            try:
                return int(level_str)
            except (TypeError, ValueError):
                return 99

        traits: list[str] = []
        for lvl in sorted(features_by_level.keys(), key=_lvl_key):
            for feat in features_by_level[lvl]:
                name = feat.get("name", "")
                if name:
                    traits.append(name)
        return traits

    def _on_tile_click(self, name: str):
        clean_name = name.replace(" (PHB)", "")
        self.ctx.subclass_name = name

        # Resolve slug
        self.ctx.subclass_slug = None
        for sc in self.data.get_subclasses_for_class(self.ctx.class_slug):
            if sc["name"] == clean_name:
                self.ctx.subclass_slug = sc["slug"]
                self._selected_subclass_data = sc
                break

        if not self.ctx.subclass_slug:
            self.ctx.subclass_slug = clean_name.lower().replace(" ", "-")
            self._selected_subclass_data = None

        self.go_to_substep(1)
        self.notify_change()

    def _build_detail(self):
        # Hero header
        for w in self._detail_hero.inner.winfo_children():
            w.destroy()

        name = self.ctx.subclass_name.replace(" (PHB)", "")
        hero_inner = tk.Frame(self._detail_hero.inner, bg=COLORS["bg_hero"])
        hero_inner.pack(
            fill=tk.X,
            padx=SPACING["card_pad"],
            pady=(SPACING["xl"], SPACING["lg"]),
        )

        tk.Label(
            hero_inner,
            text=name,
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        sc = self._selected_subclass_data
        if sc:
            source = sc.get("source", "")
            if source:
                tk.Label(
                    hero_inner,
                    text=source,
                    font=FONTS["label_upper_bold"],
                    fg=COLORS["fg_dim"],
                    bg=COLORS["bg_hero"],
                ).pack(side=tk.RIGHT)

        # Detail content
        for w in self._detail_scroll.inner.winfo_children():
            w.destroy()

        inner = self._detail_scroll.inner

        if not sc:
            card = CardFrame(inner, pad=SPACING["lg"])
            card.pack(fill=tk.X, padx=SPACING["lg"], pady=SPACING["lg"])
            tk.Label(
                card.inner,
                text="Core subclass — detailed feature data not available.",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w")
            return

        # Intro text
        desc = (sc.get("description") or "").strip()
        if desc:
            parts = re.split(r"\bLevel\s+\d+\s*:", desc, maxsplit=1)
            intro = parts[0].strip()
            if intro:
                card = CardFrame(inner, pad=SPACING["lg"])
                card.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["sm"]))
                WrappingLabel(
                    card.inner,
                    text=intro,
                    font=FONTS["body"],
                    foreground=COLORS["fg_dim"],
                    background=COLORS["bg_surface"],
                ).pack(fill=tk.X)

        # Features by level
        features_by_level = sc.get("features", {})
        if features_by_level:
            def _lvl_key(level_str: str):
                try:
                    return int(level_str)
                except (TypeError, ValueError):
                    return 99

            for lvl in sorted(features_by_level.keys(), key=_lvl_key):
                lvl_int = _lvl_key(lvl)
                is_current_level = lvl_int == self.ctx.new_class_level

                header_text = f"Level {lvl} Features"
                header = SectionHeader(inner, text=header_text)
                header.pack(
                    fill=tk.X, padx=SPACING["lg"],
                    pady=(SPACING["lg"], SPACING["sm"]),
                )

                for feat in features_by_level.get(lvl, []):
                    feat_name = feat.get("name", "Feature")
                    feat_desc = feat.get("description", "")

                    bg = COLORS["bg_container"] if is_current_level else COLORS["bg_surface"]
                    border = COLORS["accent"] if is_current_level else COLORS["border_subtle"]

                    card = CardFrame(
                        inner,
                        bg=bg,
                        border_color=border,
                        accent_left=is_current_level,
                        pad=SPACING["lg"],
                    )
                    card.pack(
                        fill=tk.X, padx=SPACING["lg"],
                        pady=(0, SPACING["xs"]),
                    )

                    feat_header = tk.Frame(card.inner, bg=bg)
                    feat_header.pack(fill=tk.X)

                    tk.Label(
                        feat_header,
                        text=feat_name,
                        font=FONTS["heading_serif_sm"],
                        fg=COLORS["fg"],
                        bg=bg,
                    ).pack(side=tk.LEFT)

                    if is_current_level:
                        PillBadge(
                            feat_header,
                            text="GAINED NOW",
                            bg_color=COLORS["accent"],
                            fg_color=COLORS["accent_text"],
                        ).pack(side=tk.RIGHT)
                    else:
                        PillBadge(
                            feat_header,
                            text=f"LEVEL {lvl}",
                            bg_color=COLORS["badge_glass_dim"],
                            fg_color=COLORS["fg_dim"],
                        ).pack(side=tk.RIGHT)

                    if feat_desc:
                        FormattedDescription(
                            card.inner,
                            text=feat_desc,
                            font=FONTS["body_small"],
                            foreground=COLORS["fg_dim"] if not is_current_level else COLORS["fg"],
                            background=bg,
                        ).pack(fill=tk.X, pady=(SPACING["xs"], 0))

    def is_valid(self) -> bool:
        ok, _, _ = validate_subclass_step(self.ctx)
        return ok
