"""Step 6: Level-1 class feature choices."""

import tkinter as tk
from tkinter import ttk

from gui.base_step import WizardStep
from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import (
    CardFrame,
    FormattedDescription,
    GradientHeader,
    ScrollableFrame,
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
from models.level1_class_rules import (
    get_available_fighting_styles,
    get_available_order_options,
    get_available_warlock_invocations,
    get_selected_weapon_mastery_details,
    get_tome_cantrip_options,
    get_tome_ritual_options,
    get_unmet_level1_class_feature_phase_requirements,
    get_unmet_level1_class_requirements,
    get_warlock_invocation_binding_options,
    get_warlock_invocation_followup_kind,
    get_weapon_mastery_count,
    get_weapon_mastery_options,
    requires_level1_class_features_step,
    scrub_level1_class_choices,
)
from models.feat_utils import get_owned_feat_names


class ClassFeaturesStep(WizardStep):
    tab_title = "Class Features"

    def __init__(self, parent_notebook, character, game_data):
        self._binding_var = tk.StringVar(value="")
        self._current_substep = 0
        self._rendered_split_active = False
        self._invocation_vars: dict[str, dict] = {}
        self._invocation_checkbuttons: dict[str, ttk.Checkbutton] = {}
        self._invocation_detail_text: tk.Text | None = None

        self._invocation_feat_list: ModernSectionedListbox | None = None
        self._invocation_feat_label: tk.Label | None = None
        self._invocation_feat_source: tk.Label | None = None
        self._invocation_feat_benefits_frame: tk.Frame | None = None
        self._warlock_feat_tiles: dict[str, dict] = {}
        self._updating_invocations = False
        super().__init__(parent_notebook, character, game_data)

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        hero = GradientHeader(self.frame, min_height=60)
        hero.grid(row=0, column=0, sticky="ew")

        hero_inner = tk.Frame(hero.inner, bg=COLORS["bg_hero"])
        hero_inner.pack(fill=tk.X, padx=SPACING["card_pad"], pady=(SPACING["xl"], 0))

        tk.Label(
            hero_inner,
            text="Class Features",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        tk.Label(
            hero.inner,
            text=(
                "Resolve every required level-1 class feature choice before "
                "continuing to the rest of character creation."
            ),
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xs"], SPACING["xl"]))

        scroll = ScrollableFrame(self.frame)
        scroll.grid(row=1, column=0, sticky="nsew")
        self._content = scroll.inner

    def has_substeps(self) -> bool:
        return self.get_substep_count() > 1

    def get_current_substep(self) -> int:
        return self._current_substep

    def get_substep_count(self) -> int:
        slug = self._class_slug()
        if slug == "fighter":
            return 2
        if slug == "warlock" and self._warlock_followup_kind() is not None:
            return 2
        return 1

    def go_to_substep(self, index: int):
        max_index = max(0, self.get_substep_count() - 1)
        next_index = max(0, min(index, max_index))
        if next_index == self._current_substep:
            return

        self._current_substep = next_index
        self._rebuild()
        self.notify_substep_change()

    def is_primary_action_visible(self) -> bool:
        return True

    def is_primary_action_enabled(self) -> bool:
        return self.is_current_substep_valid()

    def is_current_substep_valid(self) -> bool:
        return not self.get_current_substep_requirements()

    def get_sidebar_title(self) -> str | None:
        if not self.has_substeps():
            return None
        return f"Class Features ({min(self._current_substep, 1) + 1}/2)"

    def get_current_substep_requirements(self) -> list[dict]:
        if not self.has_substeps():
            return get_unmet_level1_class_requirements(
                self.character,
                self.data,
                step_key="class_features",
            )
        return get_unmet_level1_class_feature_phase_requirements(
            self.character,
            self.data,
            self._current_substep,
        )

    def on_enter(self):
        scrub_level1_class_choices(self.character, self.data)
        self._rebuild()

    def _class_slug(self) -> str:
        return str((self.character.character_class or {}).get("slug", "") or "")

    def _choice_map(self) -> dict:
        choices = getattr(self.character, "level1_class_choices", {})
        return choices if isinstance(choices, dict) else {}

    def _choice_value(self, key: str, default=None):
        return self._choice_map().get(key, default)

    def _warlock_followup_kind(self) -> str | None:
        if self._class_slug() != "warlock":
            return None
        invocation = str(self._choice_value("warlock_invocation", "") or "").strip()
        return get_warlock_invocation_followup_kind(invocation)

    def _set_choice(self, key: str, value):
        if not isinstance(self.character.level1_class_choices, dict):
            self.character.level1_class_choices = {}
        if value in (None, "", [], {}):
            self.character.level1_class_choices.pop(key, None)
        else:
            self.character.level1_class_choices[key] = value
        scrub_level1_class_choices(self.character, self.data)
        self._rebuild()
        self.notify_change()

    def _set_slotted_choice(self, key: str, index: int, total: int, value: str):
        current = list(self._choice_value(key, []))
        while len(current) < total:
            current.append("")
        current[index] = value.strip()
        cleaned = [entry for entry in current if entry.strip()]
        self._set_choice(key, cleaned)

    def _clear_content(self):
        for widget in self._content.winfo_children():
            widget.destroy()

    def _sync_substep_state(self) -> bool:
        split_active = self.get_substep_count() > 1
        substep_changed = False
        if split_active != self._rendered_split_active:
            self._rendered_split_active = split_active
            substep_changed = True
        if not split_active and self._current_substep != 0:
            self._current_substep = 0
            substep_changed = True
        max_index = max(0, self.get_substep_count() - 1)
        if self._current_substep > max_index:
            self._current_substep = max_index
            substep_changed = True
        return substep_changed

    def _card(
        self,
        title: str,
        description: str = "",
        *,
        parent=None,
        header_parent=None,
    ) -> CardFrame:
        content_parent = parent or self._content
        section_parent = header_parent or content_parent
        SectionHeader(section_parent, text=title).pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )
        card = CardFrame(content_parent, pad=SPACING["lg"])
        card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))
        if description:
            WrappingLabel(
                card.inner,
                text=description,
                background=COLORS["bg_surface"],
                foreground=COLORS["fg_dim"],
            ).pack(fill=tk.X, anchor="w", pady=(0, SPACING["sm"]))
        return card

    def _build_empty_state(self, text: str):
        card = self._card("No Class Feature Choices", "")
        tk.Label(
            card.inner,
            text=text,
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w")

    def _build_radio_group(self, key: str, title: str, options: list[dict]):
        current = str(self._choice_value(key, "") or "")
        SectionHeader(self._content, text=title).pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )

        tile_map = {}
        var = tk.StringVar(value=current)

        for option in options:
            name = str(option.get("name", "")).strip()
            if not name:
                continue
            
            bg_hex = COLORS["bg_surface"]
            tile_border = tk.Frame(self._content, bg=COLORS["border_medium"], cursor="hand2")
            tile_border.pack(fill=tk.X, padx=SPACING["lg"], pady=SPACING["xs"])
            
            tile = tk.Frame(tile_border, bg=bg_hex, cursor="hand2")
            tile.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

            title_lbl = tk.Label(
                tile,
                text=name,
                font=FONTS["body_bold"],
                fg=COLORS["fg"],
                bg=bg_hex,
                cursor="hand2",
                anchor="w"
            )
            title_lbl.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["md"], 0))

            desc_lbl = None
            desc = str(option.get("description", "") or "").strip()
            if desc:
                desc_lbl = FormattedDescription(
                    tile,
                    text=desc,
                    font=FONTS["body_small"],
                    foreground=COLORS["fg_dim"],
                    background=bg_hex,
                    cursor="hand2"
                )
                desc_lbl.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["xs"], SPACING["md"]))

            tile_map[name] = {
                "border": tile_border,
                "tile": tile,
                "title": title_lbl,
                "desc": desc_lbl
            }

            # Binds
            def on_click(_e, n=name):
                var.set(n)
                self._set_choice(key, n)

            def on_enter(_e, n=name):
                if var.get() != n:
                    tile_border.configure(bg=COLORS["accent"])
                    tile.configure(bg=COLORS["bg_high"])
                    title_lbl.configure(bg=COLORS["bg_high"])
                    if desc_lbl: desc_lbl.configure(background=COLORS["bg_high"])

            def on_leave(_e, n=name):
                if var.get() != n:
                    _update_styles()

            for w in [tile_border, tile, title_lbl, desc_lbl]:
                if w:
                    w.bind("<Button-1>", on_click)
                    w.bind("<Enter>", on_enter)
                    w.bind("<Leave>", on_leave)

        def _update_styles():
            curr = var.get()
            for n, widgets in tile_map.items():
                is_sel = (curr == n)
                border_c = COLORS["accent"] if is_sel else COLORS["border_medium"]
                bg_c = COLORS["bg_high"] if is_sel else COLORS["bg_surface"]
                fg_title = COLORS["accent_text"] if is_sel else COLORS["fg"]
                
                widgets["border"].configure(bg=border_c)
                widgets["tile"].configure(bg=bg_c)
                widgets["title"].configure(bg=bg_c, fg=fg_title)
                if widgets["desc"]:
                    widgets["desc"].configure(background=bg_c)

        _update_styles()

    def _build_combo_slots(
        self,
        key: str,
        title: str,
        options: list[str],
        count: int,
        label_prefix: str,
        description: str = "",
    ):
        current = list(self._choice_value(key, []))
        card = self._card(title, description)

        for idx in range(count):
            row = tk.Frame(card.inner, bg=COLORS["bg_surface"])
            row.pack(fill=tk.X, pady=(0, SPACING["xs"]))
            tk.Label(
                row,
                text=f"{label_prefix} {idx + 1}",
                font=FONTS["body_bold"],
                fg=COLORS["fg"],
                bg=COLORS["bg_surface"],
                width=16,
                anchor="w",
            ).pack(side=tk.LEFT)
            var = tk.StringVar(value=current[idx] if idx < len(current) else "")
            combo = ttk.Combobox(
                row,
                textvariable=var,
                values=options,
                state="readonly",
                width=36,
            )
            combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
            combo.bind(
                "<<ComboboxSelected>>",
                lambda _event, i=idx, v=var: self._set_slotted_choice(
                    key, i, count, v.get()
                ),
            )

    def _build_weapon_mastery_section(self):
        count = get_weapon_mastery_count(self.character)
        if not count:
            return

        current = list(self._choice_value("weapon_mastery", []))
        options = get_weapon_mastery_options(self.character, self.data)

        header_lbl = SectionHeader(self._content, text=f"Weapon Mastery ({len(current)} / {count})")
        header_lbl.pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )

        WrappingLabel(
            self._content,
            text=(
                f"Choose {count} weapons whose mastery properties you can use at level 1. "
                "Each mastered weapon gives you its listed mastery effect when you "
                "attack with it."
            ),
            background=COLORS["bg"],
            foreground=COLORS["fg_dim"],
        ).pack(fill=tk.X, anchor="w", padx=SPACING["lg"], pady=(0, SPACING["md"]))

        grid_frame = tk.Frame(self._content, bg=COLORS["bg"])
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        columns = 2
        for i in range(columns):
            grid_frame.columnconfigure(i, weight=1)

        tile_refs = {}

        def update_tiles(current_selection: list[str]):
            for wp_name, widgets in tile_refs.items():
                is_sel = wp_name in current_selection
                border_c = COLORS["accent"] if is_sel else COLORS["border_medium"]
                bg_hex = COLORS.get("tile_hover", COLORS["bg_highest"]) if is_sel else COLORS.get("tile_bg", COLORS["bg_surface"])
                fg_title = COLORS["accent_text"] if is_sel else COLORS["fg"]
                
                widgets["border"].configure(bg=border_c)
                widgets["tile"].configure(bg=bg_hex)
                widgets["title"].configure(bg=bg_hex, fg=fg_title)
                
                if widgets.get("stats"):
                    widgets["stats"].configure(background=bg_hex)
                if widgets.get("sep"):
                    widgets["sep"].configure(bg=COLORS["border_subtle"])
                if widgets.get("mastery_title"):
                    widgets["mastery_title"].configure(bg=bg_hex)
                if widgets.get("mastery_lbl"):
                    widgets["mastery_lbl"].configure(background=bg_hex)

        def on_enter_tile(wp_name: str):
            widgets = tile_refs.get(wp_name)
            if not widgets:
                return
            is_sel = wp_name in list(self._choice_value("weapon_mastery", []))
            
            # Use darker accent highlight from the header
            widgets["border"].configure(bg=COLORS["accent"])
            widgets["tile"].configure(bg=COLORS["bg_high"])
            widgets["title"].configure(bg=COLORS["bg_high"])
            if widgets.get("stats"):
                widgets["stats"].configure(background=COLORS["bg_high"])
            if widgets.get("mastery_title"):
                widgets["mastery_title"].configure(bg=COLORS["bg_high"])
            if widgets.get("mastery_lbl"):
                widgets["mastery_lbl"].configure(background=COLORS["bg_high"])

        def on_leave_tile(wp_name: str):
            widgets = tile_refs.get(wp_name)
            if not widgets:
                return
            update_tiles(list(self._choice_value("weapon_mastery", [])))

        def on_toggle(weapon_name: str):
            curr = list(self._choice_value("weapon_mastery", []))
            if weapon_name in curr:
                curr.remove(weapon_name)
            else:
                curr.append(weapon_name)

            if len(curr) > count:
                curr.pop(0)

            # Manually update state without triggering full rebuild
            if not isinstance(self.character.level1_class_choices, dict):
                self.character.level1_class_choices = {}
                
            if curr:
                self.character.level1_class_choices["weapon_mastery"] = curr
            else:
                self.character.level1_class_choices.pop("weapon_mastery", None)

            # Update count label naturally if possible
            for child in header_lbl.winfo_children():
                if isinstance(child, tk.Label) or isinstance(child, ttk.Label):
                    child.configure(text=f"Weapon Mastery ({len(curr)} / {count})")
                    break

            update_tiles(curr)
            self.notify_change()

        import re
        from models.level1_class_rules import get_weapon_mastery_detail

        for idx, weapon_name in enumerate(options):
            is_selected = weapon_name in current
            weapon_item = self.data.items_by_name.get(weapon_name, {})
            desc = str(weapon_item.get("description", "")).strip()

            mastery_detail = get_weapon_mastery_detail(self.data, weapon_name)
            mastery_desc = mastery_detail.get("description", "")
            mastery_name = mastery_detail.get("mastery", "")

            # Extract the raw stats, excluding the mastery text which we present separately
            stats_text = re.sub(r";?\s*Mastery:\s*[^;]+", "", desc, flags=re.IGNORECASE).strip("; ")

            row = idx // columns
            col = idx % columns

            border_color = COLORS["accent"] if is_selected else COLORS["border_medium"]
            if is_selected:
                bg_hex = COLORS.get("tile_hover", COLORS["bg_highest"])
            else:
                bg_hex = COLORS.get("tile_bg", COLORS["bg_surface"])

            tile_border = tk.Frame(grid_frame, bg=border_color, cursor="hand2")
            tile_border.grid(row=row, column=col, sticky="nsew", padx=SPACING["xs"], pady=SPACING["xs"])
            
            tile = tk.Frame(tile_border, bg=bg_hex, cursor="hand2")
            tile.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

            title_lbl = tk.Label(
                tile,
                text=weapon_name,
                font=FONTS["body_bold"],
                fg=COLORS["fg"] if not is_selected else COLORS["accent_text"],
                bg=bg_hex,
                cursor="hand2"
            )
            title_lbl.pack(anchor="w", padx=SPACING["sm"], pady=(SPACING["sm"], 0))

            stats_lbl = None
            if stats_text:
                stats_lbl = WrappingLabel(
                    tile,
                    text=stats_text,
                    background=bg_hex,
                    foreground=COLORS["fg_dim"],
                    cursor="hand2"
                )
                stats_lbl.pack(fill=tk.X, anchor="w", padx=SPACING["sm"], pady=(0, SPACING["xs"]))

            sep = None
            mastery_title = None
            mastery_lbl = None
            if mastery_desc:
                sep = tk.Frame(tile, bg=COLORS["border_subtle"], height=1)
                sep.pack(fill=tk.X, padx=SPACING["sm"], pady=4)
                
                mastery_title = tk.Label(
                    tile,
                    text=f"Mastery: {mastery_name}" if mastery_name else "Mastery",
                    font=FONTS["body_bold"],
                    fg=COLORS["gold"],
                    bg=bg_hex,
                    cursor="hand2"
                )
                mastery_title.pack(anchor="w", padx=SPACING["sm"])

                mastery_lbl = WrappingLabel(
                    tile,
                    text=mastery_desc,
                    background=bg_hex,
                    foreground=COLORS["fg_dim"],
                    cursor="hand2"
                )
                mastery_lbl.pack(fill=tk.X, anchor="w", padx=SPACING["sm"], pady=(0, SPACING["sm"]))
            tile_refs[weapon_name] = {
                "border": tile_border,
                "tile": tile,
                "title": title_lbl,
                "stats": stats_lbl,
                "sep": sep,
                "mastery_title": mastery_title,
                "mastery_lbl": mastery_lbl
            }
                
            # Bind events for everything
            click_func = lambda e, w=weapon_name: on_toggle(w)
            enter_func = lambda e, w=weapon_name: on_enter_tile(w)
            leave_func = lambda e, w=weapon_name: on_leave_tile(w)

            widgets_to_bind = [tile_border, tile, title_lbl, stats_lbl, sep, mastery_title, mastery_lbl]
            for widget in widgets_to_bind:
                if widget:
                    widget.bind("<Button-1>", click_func, add="+")
                    widget.bind("<Enter>", enter_func, add="+")
                    widget.bind("<Leave>", leave_func, add="+")



    def _populate_invocation_origin_feats(self):
        if self._invocation_feat_list is None:
            return

        filters = self.data.source_filters.get("feats", {})
        enabled = {cat for cat, on in filters.items() if on}

        owned = get_owned_feat_names(self.character)
        current_name = str(
            (self._choice_value("warlock_lessons_feat", "") or "")
        ).strip()
        current_key = current_name.casefold() if current_name else ""

        origin_feats = []
        for feat in self.data.feats:
            if feat.get("category") != "origin":
                continue
            name = str(feat.get("name", "") or "").strip()
            key = name.casefold()
            if key in owned and key != current_key:
                continue
            origin_feats.append(feat)

        grouped = group_by_category(origin_feats, "feats")
        sections = [
            (cat, [feat["name"] for feat in items])
            for cat, items in grouped
            if cat in enabled
        ]
        self._invocation_feat_list.set_sectioned_items(sections)

    def _clear_invocation_feat_details(self):
        if self._invocation_feat_label is not None:
            self._invocation_feat_label.configure(text="Select a feat")
        if self._invocation_feat_source is not None:
            self._invocation_feat_source.configure(text="")
        if self._invocation_feat_benefits_frame is not None:
            for widget in self._invocation_feat_benefits_frame.winfo_children():
                widget.destroy()

    def _render_feat_benefits(self, feat: dict, parent):
        background = parent.cget("bg") if hasattr(parent, "cget") else COLORS["bg_surface"]
        for benefit in feat.get("benefits", []):
            block = tk.Frame(parent, bg=background)
            block.pack(fill=tk.X, pady=2)
            tk.Label(
                block,
                text=benefit.get("name", ""),
                font=FONTS["body_bold"],
                fg=COLORS["accent_text"],
                bg=background,
            ).pack(anchor="w")
            description = benefit.get("description", "")
            if description:
                FormattedDescription(
                    block,
                    text=description,
                    font=FONTS["body_small"],
                    foreground=COLORS["fg_dim"],
                    background=background,
                ).pack(fill=tk.X, anchor="w", padx=(SPACING["lg"], 0))

    def _on_invocation_feat_hover(self, name: str):
        feat = self.data.feats_by_name.get(name)
        if feat:
            self._show_invocation_feat_details(feat)

    def _on_invocation_feat_select(self, name: str):
        feat = self.data.feats_by_name.get(name)
        if not feat:
            return

        if not isinstance(self.character.level1_class_choices, dict):
            self.character.level1_class_choices = {}
        self.character.level1_class_choices["warlock_lessons_feat"] = feat["name"]
        self._update_warlock_feat_tile_styles()
        self.notify_change()

    def _show_invocation_feat_details(self, feat: dict):
        if self._invocation_feat_label is None or self._invocation_feat_source is None:
            return

        self._invocation_feat_label.configure(text=feat["name"])
        self._invocation_feat_source.configure(
            text=f"Source: {feat.get('source', 'Unknown')}"
        )

        if self._invocation_feat_benefits_frame is not None:
            for widget in self._invocation_feat_benefits_frame.winfo_children():
                widget.destroy()
            self._render_feat_benefits(feat, self._invocation_feat_benefits_frame)

    def _build_warlock_origin_feat_picker(self):
        SectionHeader(self._content, text="Invocation Feat (Lessons Of The First Ones)").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )

        filter_frame = tk.Frame(self._content, bg=COLORS["bg"])
        filter_frame.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        tk.Label(
            filter_frame,
            text="Choose an Origin Feat:",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
        ).pack(anchor="w")

        self._warlock_feat_tiles = {}
        
        # Get feats
        filters = self.data.source_filters.get("feats", {})
        enabled = {cat for cat, on in filters.items() if on}
        owned = get_owned_feat_names(self.character)
        current_name = str((self._choice_value("warlock_lessons_feat", "") or "")).strip()
        current_key = current_name.casefold() if current_name else ""

        origin_feats = []
        for feat in self.data.feats:
            if feat.get("category") != "origin":
                continue
            name = str(feat.get("name", "") or "").strip()
            key = name.casefold()
            if key in owned and key != current_key:
                continue
            origin_feats.append(feat)

        # Render cards
        for feat in sorted(origin_feats, key=lambda f: f["name"]):
            self._create_warlock_feat_tile(self._content, feat)

        self._update_warlock_feat_tile_styles()

    def _create_warlock_feat_tile(self, parent, feat):
        name = feat["name"]
        bg_hex = COLORS["bg_surface"]
        
        tile_border = tk.Frame(parent, bg=COLORS["border_medium"], cursor="hand2")
        tile_border.pack(fill=tk.X, padx=SPACING["lg"], pady=SPACING["xs"])
        
        tile = tk.Frame(tile_border, bg=bg_hex, cursor="hand2")
        tile.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        title_lbl = tk.Label(
            tile,
            text=name,
            font=FONTS["body_bold"],
            fg=COLORS["fg"],
            bg=bg_hex,
            cursor="hand2",
            anchor="w"
        )
        title_lbl.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["md"], 0))

        source_lbl = tk.Label(
            tile,
            text=f"Source: {feat.get('source', 'Unknown')}",
            font=FONTS["label_tiny"],
            fg=COLORS["fg_dim"],
            bg=bg_hex,
            cursor="hand2",
            anchor="w"
        )
        source_lbl.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["xs"]))

        benefits_frame = tk.Frame(tile, bg=bg_hex)
        benefits_frame.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["md"]))
        self._render_feat_benefits(feat, benefits_frame)

        self._warlock_feat_tiles[name] = {
            "border": tile_border,
            "tile": tile,
            "title": title_lbl,
            "source": source_lbl,
            "benefits": benefits_frame
        }

        # Bindings
        def on_click(_e):
            self._on_invocation_feat_select(name)

        def on_enter(_e):
            if str(self._choice_value("warlock_lessons_feat", "")) != name:
                tile_border.configure(bg=COLORS["accent"])
                tile.configure(bg=COLORS["bg_high"])
                title_lbl.configure(bg=COLORS["bg_high"])
                source_lbl.configure(bg=COLORS["bg_high"])
                for child in benefits_frame.winfo_children():
                    child.configure(bg=COLORS["bg_high"])
                    for subchild in child.winfo_children():
                        if isinstance(subchild, (tk.Label, tk.Frame)):
                            if not isinstance(subchild, FormattedDescription):
                                subchild.configure(bg=COLORS["bg_high"])

        def on_leave(_e):
            if str(self._choice_value("warlock_lessons_feat", "")) != name:
                self._update_warlock_feat_tile_styles()

        for w in [tile_border, tile, title_lbl, source_lbl]:
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

    def _update_warlock_feat_tile_styles(self):
        current = str(self._choice_value("warlock_lessons_feat", "") or "").strip()
        for name, widgets in self._warlock_feat_tiles.items():
            is_sel = (current == name)
            border_c = COLORS["accent"] if is_sel else COLORS["border_medium"]
            bg_c = COLORS["bg_high"] if is_sel else COLORS["bg_surface"]
            fg_title = COLORS["accent_text"] if is_sel else COLORS["fg"]
            
            widgets["border"].configure(bg=border_c)
            widgets["tile"].configure(bg=bg_c)
            widgets["title"].configure(bg=bg_c, fg=fg_title)
            widgets["source"].configure(bg=bg_c)
            widgets["benefits"].configure(bg=bg_c)
            for child in widgets["benefits"].winfo_children():
                child.configure(bg=bg_c)
                for subchild in child.winfo_children():
                    if isinstance(subchild, (tk.Label, tk.Frame)):
                        if not isinstance(subchild, FormattedDescription):
                            subchild.configure(bg=bg_c)
                        else:
                            subchild.configure(background=bg_c)

        selected_name = str(self._choice_value("warlock_lessons_feat", "") or "").strip()
        if selected_name:
            # If the stored Lessons feat duplicates another source (such as
            # the background feat or species origin feat), clear it.
            bg_name = str(
                (getattr(self.character, "feat", None) or {}).get("name", "") or ""
            ).strip()
            sp_name = str(
                (getattr(self.character, "species_origin_feat", None) or {}).get(
                    "name", ""
                )
                or ""
            ).strip()
            if selected_name in {bg_name, sp_name}:
                if not isinstance(self.character.level1_class_choices, dict):
                    self.character.level1_class_choices = {}
                self.character.level1_class_choices.pop("warlock_lessons_feat", None)
                selected_name = ""

        if selected_name:
            feat = self.data.feats_by_name.get(selected_name)
            if feat:
                self._show_invocation_feat_details(feat)
                self._invocation_feat_list.select_item(selected_name)

    def _build_warlock_invocation_selector(self):
        self._invocation_vars.clear()
        self._invocation_checkbuttons.clear()

        invocation_options = get_available_warlock_invocations()
        current_invocation = str(self._choice_value("warlock_invocation", "") or "")

        SectionHeader(self._content, text="Eldritch Invocation").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )

        container = tk.Frame(self._content, bg=COLORS["bg"])
        container.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        top_row = tk.Frame(container, bg=COLORS["bg"])
        top_row.pack(fill=tk.X)
        top_row.columnconfigure(0, weight=1)
        top_row.columnconfigure(1, weight=1)

        left = tk.Frame(top_row, bg=COLORS["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["xs"]))

        selected_count = 1 if current_invocation else 0
        tk.Label(
            left,
            text=f"{selected_count} / 1 invocation selected",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
        ).pack(anchor="w", padx=4, pady=(0, 1))

        list_outer = tk.Frame(left, bg=COLORS["bg"])
        list_outer.pack(fill=tk.BOTH, expand=True, pady=(2, 0))

        self._invocation_selector = ModernSectionedListbox(
            list_outer,
            multiselect=True,
            on_hover=lambda name: self._show_invocation_detail(self._invocation_vars[name]["invocation"]),
            on_select=lambda name: self._on_invocation_toggle(self._invocation_vars[name]["invocation"])
        )
        self._invocation_selector.pack(fill=tk.BOTH, expand=True)

        for option in sorted(invocation_options, key=lambda item: item["name"]):
            name = option["name"]
            if name == current_invocation:
                selected_option = option
            var = tk.BooleanVar(value=(name == current_invocation))
            self._invocation_vars[name] = {"var": var, "invocation": option}

        sections = [("Eldritch Invocations", [o["name"] for o in sorted(invocation_options, key=lambda i: i["name"])])]
        self._invocation_selector.set_sectioned_items(sections, [current_invocation] if current_invocation else [])

        right = tk.Frame(top_row, bg=COLORS["bg"])
        right.grid(row=0, column=1, sticky="nsew", padx=(SPACING["xs"], 0))

        SectionHeader(right, text="Invocation Details").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        detail_card = CardFrame(right, pad=SPACING["lg"])
        detail_card.pack(fill=tk.BOTH, expand=True)

        self._invocation_detail_text = tk.Text(
            detail_card.inner,
            wrap=tk.WORD,
            bg=COLORS["bg_surface"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            state=tk.DISABLED,
        )
        self._invocation_detail_text.pack(fill=tk.BOTH, expand=True)

        if selected_option is not None:
            self._show_invocation_detail(selected_option)

    def _build_warlock_binding_section(self, invocation: str):
        card = self._card(
            "Invocation Binding",
            f"Bind {invocation} to one of your damage-dealing Warlock cantrips.",
        )
        options = get_warlock_invocation_binding_options(self.character, self.data)
        if not options:
            WrappingLabel(
                card.inner,
                text=(
                    "Go back to the Spells step and choose a damage-dealing Warlock "
                    "cantrip first. This invocation cannot be completed without one."
                ),
                background=COLORS["bg_surface"],
                foreground=COLORS["fg_dim"],
            ).pack(fill=tk.X, anchor="w")
            return

        row = tk.Frame(card.inner, bg=COLORS["bg_surface"])
        row.pack(fill=tk.X)
        self._binding_var.set(str(self._choice_value("warlock_invocation_cantrip", "") or ""))
        combo = ttk.Combobox(
            row,
            textvariable=self._binding_var,
            values=options,
            state="readonly",
            width=42,
        )
        combo.pack(fill=tk.X, expand=True)
        combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._set_choice(
                "warlock_invocation_cantrip",
                self._binding_var.get().strip(),
            ),
        )

    def _build_warlock_followup_section(self):
        invocation = str(self._choice_value("warlock_invocation", "") or "").strip()
        followup_kind = self._warlock_followup_kind()
        if followup_kind == "binding":
            self._build_warlock_binding_section(invocation)
        elif followup_kind == "tome":
            self._build_combo_slots(
                "warlock_tome_cantrips",
                "Pact Of The Tome Cantrips",
                get_tome_cantrip_options(self.data),
                3,
                "Cantrip",
                "Choose three cantrips from any class list for your Book of Shadows.",
            )
            self._build_combo_slots(
                "warlock_tome_rituals",
                "Pact Of The Tome Rituals",
                get_tome_ritual_options(self.data),
                2,
                "Ritual",
                "Choose two level-1 ritual spells from any class list.",
            )
        elif followup_kind == "feat":
            self._build_warlock_origin_feat_picker()

    def _build_fighter_step_one(self):
        self._build_radio_group(
            "fighting_style",
            "Fighting Style",
            [
                {
                    "name": feat["name"],
                    "description": " ".join(
                        str(benefit.get("description", "") or "").strip()
                        for benefit in feat.get("benefits", [])
                        if str(benefit.get("description", "") or "").strip()
                    ),
                }
                for feat in get_available_fighting_styles(self.data)
            ],
        )

    def _on_invocation_toggle(self, invocation: dict):
        if self._updating_invocations:
            return
        self._updating_invocations = True
        try:
            name = invocation["name"]
            selected = [n for n, data in self._invocation_vars.items() if data["var"].get()]

            if len(selected) > 1:
                self._invocation_vars[name]["var"].set(False)
                selected = [
                    n for n, data in self._invocation_vars.items() if data["var"].get()
                ]

            chosen = selected[0] if selected else ""
            self._set_choice("warlock_invocation", chosen)
        finally:
            self._updating_invocations = False

    def _show_invocation_detail(self, invocation: dict):
        if self._invocation_detail_text is None:
            return
        self._invocation_detail_text.configure(state=tk.NORMAL)
        self._invocation_detail_text.delete("1.0", tk.END)

        name = invocation.get("name", "")
        desc = str(invocation.get("description", "") or "").strip()
        lines = [name, ""]
        if desc:
            lines.append(desc)

        self._invocation_detail_text.insert("1.0", "\n".join(lines))
        self._invocation_detail_text.configure(state=tk.DISABLED)

    def _update_invocation_states(self):
        selected = [n for n, data in self._invocation_vars.items() if data["var"].get()]
        at_max = len(selected) >= 1

        for name, cb in self._invocation_checkbuttons.items():
            if at_max and name not in selected:
                cb.configure(state=tk.DISABLED)
            else:
                cb.configure(state=tk.NORMAL)

    def _build_current_content(self):
        slug = self._class_slug()
        if slug in {"cleric", "druid"}:
            key = "divine_order" if slug == "cleric" else "primal_order"
            title = "Divine Order" if slug == "cleric" else "Primal Order"
            self._build_radio_group(key, title, get_available_order_options(self.character))
            return

        if slug == "fighter":
            if self._current_substep == 0:
                self._build_fighter_step_one()
            else:
                self._build_weapon_mastery_section()
            return

        if slug == "warlock":
            if self._current_substep == 0 or not self.has_substeps():
                self._build_warlock_invocation_selector()
            else:
                self._build_warlock_followup_section()
            return

        mastery_count = get_weapon_mastery_count(self.character)
        if mastery_count:
            self._build_weapon_mastery_section()

    def _rebuild(self):
        substep_changed = self._sync_substep_state()
        self._clear_content()

        if not self.character.character_class:
            self._build_empty_state("Choose a class first.")
            if substep_changed:
                self.notify_substep_change()
            return

        if not requires_level1_class_features_step(self.character, self.data):
            self._build_empty_state(
                "This class has no extra level-1 class feature choices beyond the other wizard steps."
            )
            if substep_changed:
                self.notify_substep_change()
            return

        self._build_current_content()
        if substep_changed:
            self.notify_substep_change()

    def is_valid(self) -> bool:
        return not get_unmet_level1_class_requirements(
            self.character,
            self.data,
            step_key="class_features",
        )
