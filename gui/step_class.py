"""Step 2: Class selection with grid tile view and detail substep."""

import os
import re
import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import (
    ScrollableFrame,
    WrappingLabel,
    FormattedDescription,
    ThemedTable,
    GradientHeader,
    SectionHeader,
    CardFrame,
    PillBadge,
    Chip,
    TileGrid,
)
from gui.theme import COLORS, FONTS, SPACING
from gui.source_config import (
    SECTION_ORDER,
    UA_CATEGORY,
    group_by_category,
    get_category,
    handle_ua_toggle,
    save_settings,
)
from paths import images_dir


def _first_sentence(text: str) -> str:
    if not text:
        return ""
    for end in (".", "!", "?"):
        idx = text.find(end)
        if idx != -1:
            return text[: idx + 1]
    return text[:120] + ("..." if len(text) > 120 else "")


def _slug(name: str) -> str:
    return name.lower().replace(" ", "_").replace("'", "")


class ClassStep(WizardStep):
    tab_title = "Class"
    CLASS_OVERVIEW_LABEL = "Class Overview"

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
            return "Next: Choose Background  \u25b6"
        return None

    # ── Grid View (substep 0) ─────────────────────────────────────

    def _build_grid_view(self):
        header = tk.Frame(self._grid_frame, bg=COLORS["bg"])
        header.pack(fill=tk.X, padx=SPACING["xl"], pady=(SPACING["xl"], 0))

        tk.Label(
            header,
            text="Choose Your Class",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Your class defines your hero\u2019s training, abilities, and role in the party. "
            "Select the path that best matches your desired playstyle.",
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

        # Tile grid
        self._tile_grid = TileGrid(self._grid_frame, on_select=self._on_tile_click)
        self._tile_grid.pack(fill=tk.BOTH, expand=True, padx=SPACING["sm"], pady=SPACING["sm"])

        self._populate_tiles()

    def _build_toggles(self):
        """Build source filter checkboxes for classes and subclasses."""
        for w in self._grid_toggle_frame.winfo_children():
            w.destroy()
        self.toggle_vars.clear()

        filters = self.data.source_filters.get("classes", {})
        sections = SECTION_ORDER["classes"]
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

        # Keep subclass filters fully in sync
        self.data.source_filters["subclasses"] = {
            cat: filters.get(cat, cat != UA_CATEGORY) for cat in sections
        }

    def _on_toggle_change(self):
        """Update filters and rebuild tiles/list when a toggle changes."""
        ua_var = self.toggle_vars.get(UA_CATEGORY)
        proceed, _ = handle_ua_toggle(self.frame, ua_var, self._ua_prev_enabled)
        if not proceed:
            return

        filters = {cat: var.get() for cat, var in self.toggle_vars.items()}
        self.data.source_filters["classes"] = filters
        self.data.source_filters["subclasses"] = dict(filters)
        self._ua_prev_enabled = filters.get(UA_CATEGORY, False)
        save_settings(self.data.source_filters)
        self._populate_tiles()
        if self.character.character_class and hasattr(self, "_subclass_combo"):
            class_name = self.character.character_class.get("name", "")
            self._refresh_subclass_preview_options(class_name)

    def _get_class_level1_features(self, cls: dict) -> list[str]:
        """Get up to 3 level 1 feature names from progression data."""
        prog = self.data.get_progression(cls.get("slug", ""))
        if prog and prog.get("levels"):
            lvl1 = prog["levels"][0]
            details = lvl1.get("feature_details", [])
            if details:
                return [f["name"] for f in details[:3]]
            return lvl1.get("features", [])[:3]
        # Fallback to level_1_features
        return [f["name"] for f in cls.get("level_1_features", [])[:3]]

    def _populate_tiles(self):
        filters = self.data.source_filters.get("classes", {})
        enabled = {cat for cat, on in filters.items() if on}

        grouped = group_by_category(self.data.classes, "classes")
        img_base = os.path.join(images_dir(), "classes")

        sections = []
        for cat, items in grouped:
            if cat not in enabled:
                continue
            cat_tiles = []
            for cls in items:
                traits = self._get_class_level1_features(cls)
                slug = _slug(cls["name"])
                img_path = os.path.join(img_base, f"{slug}.png")
                cat_tiles.append({
                    "name": cls["name"],
                    "description": _first_sentence(cls.get("description", "")),
                    "traits": traits,
                    "image_path": img_path if os.path.isfile(img_path) else None,
                })
            if cat_tiles:
                sections.append((cat, cat_tiles))
        self._tile_grid.set_sectioned_tiles(sections)

    def _on_tile_click(self, name: str):
        """Handle tile click: select class and switch to detail view."""
        cls = self.data.classes_by_name.get(name)
        if not cls:
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
        self._subclass_lookup_by_class: dict[str, dict[str, dict]] = {}

        # Hero header for selected class
        self._hero = GradientHeader(self.detail, min_height=60)
        self._hero.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))

        self.detail_name = tk.Label(
            self._hero.inner,
            text="Select a class",
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

        self.subclass_preview_frame = tk.Frame(self.detail, bg=COLORS["bg"])
        self.subclass_preview_frame.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        SectionHeader(self.subclass_preview_frame, text="Subclass Preview").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        subclass_card = CardFrame(self.subclass_preview_frame, pad=SPACING["md"])
        subclass_card.pack(fill=tk.X)

        tk.Label(
            subclass_card.inner,
            text="Preview level 3 subclasses without changing your chosen class.",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", pady=(0, SPACING["xs"]))

        self._subclass_var = tk.StringVar(value=self.CLASS_OVERVIEW_LABEL)
        self._subclass_combo = ttk.Combobox(
            subclass_card.inner,
            textvariable=self._subclass_var,
            state="readonly",
            values=[self.CLASS_OVERVIEW_LABEL],
        )
        self._subclass_combo.pack(fill=tk.X)
        self._subclass_combo.bind("<<ComboboxSelected>>", self._on_subclass_preview_change)

        # Equipment - Top
        self.equip_frame = tk.Frame(self.detail, bg=COLORS["bg"])
        self.equip_frame.pack(fill=tk.X)

        self.traits_frame = tk.Frame(self.detail, bg=COLORS["bg"])
        self.traits_frame.pack(fill=tk.X)

        # Features
        self.features_frame = tk.Frame(self.detail, bg=COLORS["bg"])
        self.features_frame.pack(fill=tk.X, pady=(SPACING["sm"], 0))

    def _show_class_panels(self):
        """Show normal class detail sections."""
        self.equip_frame.pack_forget()
        self.traits_frame.pack_forget()
        self.features_frame.pack_forget()

        self.equip_frame.pack(fill=tk.X)
        self.traits_frame.pack(fill=tk.X)
        self.features_frame.pack(fill=tk.X, pady=(SPACING["sm"], 0))

    def _show_subclass_panels(self):
        """Hide class-only sections while previewing subclass details."""
        self.equip_frame.pack_forget()
        self.traits_frame.pack_forget()
        if not self.features_frame.winfo_manager():
            self.features_frame.pack(fill=tk.X, pady=(SPACING["sm"], 0))

    def _subclass_summary(self, subclass: dict) -> str:
        desc = (subclass.get("description") or "").strip()
        if not desc:
            return ""
        parts = re.split(r"\bLevel\s+\d+\s*:", desc, maxsplit=1)
        return parts[0].strip()

    def on_enter(self):
        """Pre-select class when editing an existing character."""
        if not self._edit_initialized and self.character.character_class:
            self._edit_initialized = True
            name = self.character.character_class.get("name", "")
            saved_skills = list(self.character.selected_skills)
            self._on_select(name)
            self.character.selected_skills = saved_skills
            self.go_to_substep(1)

    def _refresh_subclass_preview_options(self, class_name: str):
        cls = self.data.classes_by_name.get(class_name)
        values = [self.CLASS_OVERVIEW_LABEL]
        lookup: dict[str, dict] = {}

        if cls:
            sub_filters = self.data.source_filters.get("subclasses", {})
            enabled_sub_cats = {cat for cat, on in sub_filters.items() if on}
            subclasses = self.data.get_subclasses_for_class(cls.get("slug", ""))
            for subclass in sorted(subclasses, key=lambda s: s["name"]):
                category = get_category("subclasses", subclass.get("source", ""))
                if category not in enabled_sub_cats:
                    continue
                label = subclass["name"]
                if category == UA_CATEGORY:
                    label = f"[UA] {label}"
                values.append(label)
                lookup[label] = subclass

        self._subclass_lookup_by_class[class_name] = lookup
        current_value = self._subclass_var.get()
        self._subclass_combo.configure(values=values)

        if current_value in values:
            self._subclass_var.set(current_value)
            return

        self._subclass_var.set(self.CLASS_OVERVIEW_LABEL)
        if self.character.character_class and self.character.character_class.get("name") == class_name:
            self._on_select(class_name)

    def _on_subclass_preview_change(self, _event=None):
        current_cls = self.character.character_class or {}
        class_name = current_cls.get("name", "")
        if not class_name:
            return

        selected = self._subclass_var.get()
        if selected == self.CLASS_OVERVIEW_LABEL:
            self._on_select(class_name)
            return

        self._on_sub_select(class_name, selected)

    def _clear_detail_frames(self):
        for f in [self.equip_frame, self.traits_frame, self.features_frame]:
            for w in f.winfo_children():
                w.destroy()

    def _on_sub_select(self, class_name: str, sub_label: str):
        subclass = self._subclass_lookup_by_class.get(class_name, {}).get(sub_label)
        if not subclass:
            return

        current_cls = self.character.character_class
        if not current_cls or current_cls.get("name") != class_name:
            self._on_select(class_name)

        self._subclass_var.set(sub_label)
        self._show_subclass_panels()

        self.detail_name.configure(text=subclass.get("name", "Subclass"))
        self.detail_source.configure(
            text=f"Source: {subclass.get('source', 'Unknown')}"
        )

        preview_note = (
            "Previewing subclass details \u2014 class selection remains unchanged."
        )
        desc = self._subclass_summary(subclass)
        self.detail_desc.configure(
            text=f"{preview_note}\n\n{desc}" if desc else preview_note
        )

        self._clear_detail_frames()

        SectionHeader(self.features_frame, text="Subclass Features").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )

        features_by_level = subclass.get("features", {})
        if not features_by_level:
            tk.Label(
                self.features_frame,
                text="No detailed subclass features available.",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg"],
            ).pack(anchor="w", padx=SPACING["lg"])
            return

        def _lvl_key(level_str: str):
            try:
                return int(level_str)
            except (TypeError, ValueError):
                return 99

        feat_grid = tk.Frame(self.features_frame, bg=COLORS["bg"])
        feat_grid.pack(fill=tk.X, padx=SPACING["lg"])
        feat_grid.columnconfigure(0, weight=1)
        feat_grid.columnconfigure(1, weight=1)
        card_idx = 0

        for lvl in sorted(features_by_level.keys(), key=_lvl_key):
            for feat in features_by_level.get(lvl, []):
                card = CardFrame(feat_grid, bg=COLORS["bg_container"],
                                 border_color=COLORS["border_subtle"], pad=SPACING["lg"])
                card.grid(row=card_idx // 2, column=card_idx % 2, padx=4, pady=4, sticky="nsew")

                header = tk.Frame(card.inner, bg=COLORS["bg_container"])
                header.pack(fill=tk.X)
                tk.Label(
                    header,
                    text=feat.get("name", "Feature"),
                    font=FONTS["heading_serif_sm"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_container"],
                ).pack(side=tk.LEFT)
                PillBadge(
                    header,
                    text=f"LEVEL {lvl}",
                    bg_color=COLORS["badge_glass_dim"],
                    fg_color=COLORS["gold"],
                ).pack(side=tk.RIGHT)

                feat_desc = feat.get("description", "")
                if feat_desc:
                    FormattedDescription(
                        card.inner,
                        text=feat_desc,
                        font=FONTS["body_small"],
                        foreground=COLORS["fg_dim"],
                        background=COLORS["bg_container"],
                    ).pack(fill=tk.X, pady=(6, 0))
                card_idx += 1

    def _on_select(self, name: str):
        cls = self.data.classes_by_name.get(name)
        if not cls:
            return

        self._show_class_panels()

        current_cls = self.character.character_class or {}
        same_class = current_cls.get("slug") == cls.get("slug")
        self.character.character_class = cls
        if not same_class:
            self.character.selected_skills = []

        # Initialize class_levels with level 1 entry
        from models.class_level import ClassLevel

        slug = cls.get("slug", "")
        if (
            not self.character.class_levels
            or self.character.class_levels[0].class_slug != slug
        ):
            hit_die = cls.get("hit_die", 8)
            self.character.class_levels = [
                ClassLevel(class_slug=slug, class_level=1, hit_die=hit_die)
            ]
        self._subclass_var.set(self.CLASS_OVERVIEW_LABEL)
        self._refresh_subclass_preview_options(cls["name"])
        self.detail_name.configure(text=cls["name"])
        self.detail_source.configure(text=f"Source: {cls.get('source', 'Unknown')}")
        self.detail_desc.configure(text=cls.get("description", ""))

        self._clear_detail_frames()

        # Equipment
        equip = cls.get("starting_equipment", [])
        if equip:
            SectionHeader(self.equip_frame, text="Starting Equipment").pack(
                fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"])
            )
            equip_card = CardFrame(self.equip_frame, pad=SPACING["md"])
            equip_card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

            for i, opt in enumerate(equip):
                if i > 0:
                    tk.Label(
                        equip_card.inner,
                        text="or",
                        font=FONTS["body_small"],
                        fg=COLORS["fg_dim"],
                        bg=COLORS["bg_surface"],
                    ).pack(anchor="w", pady=2)

                tk.Label(
                    equip_card.inner,
                    text=f"({opt['option']}) {opt['items']}",
                    font=FONTS["body"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_surface"],
                ).pack(anchor="w")

        # Core traits
        SectionHeader(self.traits_frame, text="Core Traits").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"])
        )

        traits_card = CardFrame(self.traits_frame, pad=SPACING["lg"])
        traits_card.pack(fill=tk.X, padx=SPACING["lg"])

        skill_choices = cls.get("skill_choices", {})
        skill_count = skill_choices.get("count", 0)
        skill_options = skill_choices.get("options", [])
        if skill_options:
            skill_text = f"Choose {skill_count} from: {', '.join(skill_options)}"
        else:
            skill_text = "None"

        info = [
            ("Hit Die", f"d{cls['hit_die']}"),
            ("Primary Ability", ", ".join(cls.get("primary_ability", []))),
            ("Saving Throws", ", ".join(cls.get("saving_throws", []))),
            ("Armor", ", ".join(cls.get("armor_proficiencies", [])) or "None"),
            ("Weapons", ", ".join(cls.get("weapon_proficiencies", []))),
            ("Skills", skill_text),
        ]

        if cls.get("caster_type"):
            info.append(
                (
                    "Spellcasting",
                    f"{cls['spellcasting_ability']} ({cls['caster_type']} caster)",
                )
            )

        _bg = COLORS["bg_surface"]
        for label, value in info:
            row = tk.Frame(traits_card.inner, bg=_bg)
            row.pack(fill=tk.X, pady=1)
            tk.Label(
                row,
                text=f"{label}:",
                font=FONTS["body_bold"],
                fg=COLORS["accent_text"],
                bg=_bg,
                width=20,
                anchor="e",
            ).pack(side=tk.LEFT)
            tk.Label(
                row,
                text=f"  {value}",
                font=FONTS["body"],
                fg=COLORS["fg"],
                bg=_bg,
            ).pack(side=tk.LEFT, padx=(4, 0))

        # Features - All Levels Roadmap
        for w in self.features_frame.winfo_children():
            w.destroy()

        prog = self.data.get_progression(cls["slug"])
        if prog and "levels" in prog:
            SectionHeader(self.features_frame, text=f"{cls['name']} Progression").pack(
                fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
            )

            extra_keys = set()
            all_slots = set()
            has_cantrips = False
            has_prepared = False

            for lvl_data in prog["levels"]:
                extra_keys.update(lvl_data.get("extra", {}).keys())
                slots = lvl_data.get("spell_slots", {})
                if slots:
                    all_slots.update(slots.keys())
                if lvl_data.get("cantrips"):
                    has_cantrips = True
                if lvl_data.get("prepared_spells"):
                    has_prepared = True

            _slot_order = {
                "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5,
                "6th": 6, "7th": 7, "8th": 8, "9th": 9,
            }
            sorted_slots = sorted(
                [s for s in all_slots if s in _slot_order], key=lambda x: _slot_order[x]
            )
            sorted_extra = sorted(list(extra_keys))

            col_configs = [
                {"id": "lvl", "text": "Lvl", "width": 40},
                {"id": "prof", "text": "Proficiency Bonus", "width": 130},
                {"id": "features", "text": "Features", "width": 350, "anchor": "w", "stretch": True},
            ]
            if has_cantrips:
                col_configs.append({"id": "cantrips", "text": "Cntp", "width": 50})
            if has_prepared:
                col_configs.append({"id": "prepared", "text": "Prep", "width": 50})

            for s in sorted_slots:
                col_configs.append({"id": s, "text": s, "width": 50})
            for e in sorted_extra:
                col_configs.append({"id": e, "text": e, "width": 100})

            col_ids = [c["id"] for c in col_configs]

            container = tk.Frame(self.features_frame, bg=COLORS["bg"])
            container.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["xl"]))

            table = ThemedTable(container, columns=col_ids, height=20)
            table.pack(fill=tk.X, expand=True)
            table.set_columns(col_configs)

            for lvl_data in prog["levels"]:
                row_vals = []
                for cid in col_ids:
                    if cid == "lvl":
                        row_vals.append(lvl_data.get("level"))
                    elif cid == "prof":
                        row_vals.append(f"+{lvl_data.get('proficiency_bonus')}")
                    elif cid == "features":
                        f_list = [
                            f for f in lvl_data.get("features", [])
                            if f not in ["-", "Ability Score Improvement"]
                        ]
                        if "Ability Score Improvement" in lvl_data.get("features", []):
                            f_list.append("ASI")
                        row_vals.append(", ".join(f_list) or "-")
                    elif cid == "cantrips":
                        row_vals.append(lvl_data.get("cantrips") or "-")
                    elif cid == "prepared":
                        row_vals.append(lvl_data.get("prepared_spells") or "-")
                    elif cid in sorted_slots:
                        slots = lvl_data.get("spell_slots", {})
                        row_vals.append(slots.get(cid) or "-")
                    elif cid in sorted_extra:
                        extra = lvl_data.get("extra", {})
                        val = extra.get(cid)
                        row_vals.append(val if val is not None else "-")
                table.insert_row(row_vals)

            SectionHeader(self.features_frame, text="Feature Descriptions").pack(
                fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"])
            )

            for lvl_data in prog["levels"]:
                lvl = lvl_data.get("level")
                feats = lvl_data.get("feature_details", [])
                all_feature_names = lvl_data.get("features", [])

                if not feats and not [f for f in all_feature_names if f != "-"]:
                    continue

                prof = lvl_data.get("proficiency_bonus", 2)
                header_text = f"Level {lvl}  [+{prof} Proficiency Bonus]"

                extra = lvl_data.get("extra", {})
                if extra:
                    extra_parts = [
                        f"{k}: {v}" for k, v in extra.items() if v is not None
                    ]
                    if extra_parts:
                        header_text += f" | {', '.join(extra_parts)}"

                tk.Label(
                    self.features_frame,
                    text=header_text,
                    font=FONTS["subheading"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg"],
                ).pack(anchor="w", padx=SPACING["lg"], pady=(SPACING["md"], SPACING["xs"]))

                shown_feats = set()
                if feats:
                    for feat in feats:
                        feat_name = feat.get("name", "Feature")
                        shown_feats.add(feat_name.lower())

                        card = CardFrame(
                            self.features_frame,
                            bg=COLORS["bg_container"],
                            border_color=COLORS["border_subtle"],
                            pad=SPACING["md"],
                        )
                        card.pack(fill=tk.X, padx=SPACING["lg"], pady=2)

                        tk.Label(
                            card.inner,
                            text=feat_name,
                            font=FONTS["heading_serif_sm"],
                            fg=COLORS["fg"],
                            bg=COLORS["bg_container"],
                        ).pack(anchor="w")

                        if feat.get("description"):
                            FormattedDescription(
                                card.inner,
                                text=feat["description"],
                                font=FONTS["body_small"],
                                foreground=COLORS["fg_dim"],
                                background=COLORS["bg_container"],
                            ).pack(fill=tk.X, pady=(4, 0))

                for f_name in all_feature_names:
                    if f_name.lower() not in shown_feats and f_name not in [
                        "-", "Ability Score Improvement",
                    ]:
                        tk.Label(
                            self.features_frame,
                            text=f"  \u2022 {f_name}",
                            font=FONTS["body_bold"],
                            fg=COLORS["accent_text"],
                            bg=COLORS["bg"],
                        ).pack(anchor="w", padx=SPACING["lg"])
                    elif (
                        f_name == "Ability Score Improvement"
                        and f_name.lower() not in shown_feats
                    ):
                        tk.Label(
                            self.features_frame,
                            text=f"  \u2022 {f_name}",
                            font=FONTS["body"],
                            fg=COLORS["fg_dim"],
                            bg=COLORS["bg"],
                        ).pack(anchor="w", padx=SPACING["lg"])
        else:
            features = cls.get("level_1_features", [])
            if features:
                SectionHeader(self.features_frame, text="Level 1 Features").pack(
                    fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
                )
                for feat in features:
                    card = CardFrame(
                        self.features_frame,
                        bg=COLORS["bg_container"],
                        border_color=COLORS["border_subtle"],
                        pad=SPACING["md"],
                    )
                    card.pack(fill=tk.X, padx=SPACING["lg"], pady=2)

                    tk.Label(
                        card.inner,
                        text=feat["name"],
                        font=FONTS["heading_serif_sm"],
                        fg=COLORS["fg"],
                        bg=COLORS["bg_container"],
                    ).pack(anchor="w")

                    if feat.get("description"):
                        FormattedDescription(
                            card.inner,
                            text=feat["description"],
                            font=FONTS["body_small"],
                            foreground=COLORS["fg_dim"],
                            background=COLORS["bg_container"],
                        ).pack(fill=tk.X, pady=(4, 0))

        self.notify_change()

    def is_valid(self) -> bool:
        return self.character.character_class is not None
