"""Level-up step: Subclass selection with tile grid + detail view."""

import re
import tkinter as tk
from tkinter import ttk

from gui.lu_base_step import LevelUpStep
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
        self._grid_view.rowconfigure(1, weight=1)

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

        self._tile_grid = TileGrid(
            self._grid_view,
            on_select=self._on_tile_click,
            preferred_cols=3,
            tile_width=280,
            tile_height=300,
            expand_tiles_to_fill=True,
            responsive_tile_height=True,
        )
        self._tile_grid.grid(row=1, column=0, sticky="nsew")

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
        self._populate_tiles()
        self._show_current_substep()

    def _populate_tiles(self):
        subclasses = self.data.get_subclasses_for_class(self.ctx.class_slug)

        # Also include PHB core subclass names
        prog = self.data.get_progression(self.ctx.class_slug)
        phb_names = set()
        if prog:
            for name in prog.get("subclass_names", []):
                phb_names.add(name)

        existing_names = {sc["name"].lower() for sc in subclasses}
        tiles = []

        for sc in sorted(subclasses, key=lambda s: s.get("name", "")):
            features_at_level = sc.get("features", {}).get(str(self.ctx.new_class_level), [])
            traits = [f.get("name", "") for f in features_at_level if f.get("name")]

            tiles.append({
                "name": sc["name"],
                "description": (sc.get("description") or "")[:150],
                "traits": traits,
                "image_path": None,
                "variant": "lore",
            })

        # PHB names not in UA data
        for name in sorted(phb_names):
            if name.lower() not in existing_names:
                tiles.append({
                    "name": f"{name} (PHB)",
                    "description": "Core subclass — detailed feature data not available.",
                    "traits": [],
                    "image_path": None,
                    "variant": "lore",
                })

        self._tile_grid.set_tiles(tiles)

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
