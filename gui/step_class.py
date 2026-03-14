"""Step 2: Class selection."""

import re
import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import SectionedListbox, ScrollableFrame, WrappingLabel, ThemedTable
from gui.theme import COLORS, FONTS
from gui.source_config import (
    SECTION_ORDER,
    UA_CATEGORY,
    group_by_category,
    get_category,
    handle_ua_toggle,
    save_settings,
)


class ClassStep(WizardStep):
    tab_title = "Class"

    def build_ui(self):
        self._edit_initialized = False
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(0, weight=1)

        # Left: class list
        left = ttk.Frame(self.frame, width=280)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.grid_propagate(False)

        ttk.Label(left, text="Choose Class", style="Heading.TLabel").pack(
            anchor="w", pady=(0, 6)
        )

        # Source filter toggles
        self.toggle_frame = ttk.Frame(left)
        self.toggle_frame.pack(fill=tk.X, pady=(0, 4))
        self.toggle_vars: dict[str, tk.BooleanVar] = {}
        self._ua_prev_enabled = False
        self._build_toggles()

        self.class_list = SectionedListbox(
            left,
            on_select=self._on_select,
            on_sub_select=self._on_sub_select,
        )
        self.class_list.pack(fill=tk.BOTH, expand=True)
        self._subclass_lookup_by_class: dict[str, dict[str, dict]] = {}

        # Right: detail
        right = ScrollableFrame(self.frame)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        self.detail = right.inner

        self.detail_name = ttk.Label(
            self.detail, text="Select a class", style="Heading.TLabel"
        )
        self.detail_name.pack(anchor="w", pady=(0, 4))

        self.detail_source = ttk.Label(self.detail, text="", style="Dim.TLabel")
        self.detail_source.pack(anchor="w")

        self.detail_desc = WrappingLabel(self.detail, text="")
        self.detail_desc.pack(fill=tk.X, anchor="w", pady=(8, 0))

        ttk.Separator(self.detail, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

        # Equipment - Top
        self.equip_frame = ttk.Frame(self.detail)
        self.equip_frame.pack(fill=tk.X)

        self.traits_frame = ttk.Frame(self.detail)
        self.traits_frame.pack(fill=tk.X)

        # Skill selection
        self.skills_frame = ttk.LabelFrame(self.detail, text="Skill Proficiencies")
        self.skills_frame.pack(fill=tk.X, pady=(8, 0))
        self.skill_vars = {}
        self.skill_limit = 0

        # Features
        self.features_frame = ttk.Frame(self.detail)
        self.features_frame.pack(fill=tk.X, pady=(8, 0))

        self._populate_list()

    def _show_class_panels(self):
        """Show normal class detail sections."""
        self.equip_frame.pack_forget()
        self.traits_frame.pack_forget()
        self.skills_frame.pack_forget()
        self.features_frame.pack_forget()

        self.equip_frame.pack(fill=tk.X)
        self.traits_frame.pack(fill=tk.X)
        self.skills_frame.pack(fill=tk.X, pady=(8, 0))
        self.features_frame.pack(fill=tk.X, pady=(8, 0))

    def _show_subclass_panels(self):
        """Hide class-only sections while previewing subclass details."""
        self.equip_frame.pack_forget()
        self.traits_frame.pack_forget()
        self.skills_frame.pack_forget()
        if not self.features_frame.winfo_manager():
            self.features_frame.pack(fill=tk.X, pady=(8, 0))

    def _subclass_summary(self, subclass: dict) -> str:
        """Keep intro summary only, avoid repeating all level feature text."""
        desc = (subclass.get("description") or "").strip()
        if not desc:
            return ""
        parts = re.split(r"\bLevel\s+\d+\s*:", desc, maxsplit=1)
        return parts[0].strip()

    def on_enter(self):
        """Pre-select class and skills when editing an existing character."""
        if not self._edit_initialized and self.character.character_class:
            self._edit_initialized = True
            name = self.character.character_class.get("name", "")
            # Snapshot skills (_on_select resets selected_skills to [])
            saved_skills = list(self.character.selected_skills)
            # Select in list and populate detail panel
            self.class_list.select_item(name)
            self._on_select(name)
            # Restore skill checkbox selections
            for skill_name in saved_skills:
                if skill_name in self.skill_vars:
                    self.skill_vars[skill_name].set(True)
            self.character.selected_skills = saved_skills

    def _build_toggles(self):
        """Build source filter checkboxes for classes and subclasses."""
        for w in self.toggle_frame.winfo_children():
            w.destroy()
        self.toggle_vars.clear()

        filters = self.data.source_filters.get("classes", {})
        sections = SECTION_ORDER["classes"]
        self._ua_prev_enabled = filters.get(UA_CATEGORY, False)

        for cat in sections:
            label = "UA" if cat == UA_CATEGORY else cat
            var = tk.BooleanVar(value=filters.get(cat, cat != UA_CATEGORY))
            cb = ttk.Checkbutton(
                self.toggle_frame,
                text=label,
                variable=var,
                command=self._on_toggle_change,
            )
            cb.pack(side=tk.LEFT, padx=(0, 6))
            self.toggle_vars[cat] = var

        # Keep subclass filters fully in sync with the class filter toggles.
        self.data.source_filters["subclasses"] = {
            cat: filters.get(cat, cat != UA_CATEGORY) for cat in sections
        }

    def _on_toggle_change(self):
        """Update filters and rebuild list when a toggle changes."""
        # Intercept UA enable with confirmation dialog
        ua_var = self.toggle_vars.get(UA_CATEGORY)
        proceed, _ = handle_ua_toggle(self.frame, ua_var, self._ua_prev_enabled)
        if not proceed:
            return

        filters = {cat: var.get() for cat, var in self.toggle_vars.items()}
        self.data.source_filters["classes"] = filters
        # Sync subclass filters with same toggle state
        self.data.source_filters["subclasses"] = dict(filters)
        self._ua_prev_enabled = filters.get(UA_CATEGORY, False)
        save_settings(self.data.source_filters)
        self._populate_list()

    def _populate_list(self):
        filters = self.data.source_filters.get("classes", {})
        enabled = {cat for cat, on in filters.items() if on}

        grouped = group_by_category(self.data.classes, "classes")
        sections = [
            (cat, [c["name"] for c in items])
            for cat, items in grouped
            if cat in enabled
        ]

        # Build sub-items: subclass names listed under each class, filtered by source
        sub_filters = self.data.source_filters.get("subclasses", {})
        enabled_sub_cats = {cat for cat, on in sub_filters.items() if on}
        sub_items: dict[str, list[str]] = {}
        sub_lookup: dict[str, dict[str, dict]] = {}
        for cls in self.data.classes:
            slug = cls.get("slug", "")
            subs = self.data.get_subclasses_for_class(slug)
            if subs:
                visible = [
                    sc
                    for sc in subs
                    if get_category("subclasses", sc.get("source", ""))
                    in enabled_sub_cats
                ]
                if visible:
                    names = []
                    class_lookup: dict[str, dict] = {}
                    for sc in sorted(visible, key=lambda s: s["name"]):
                        name = sc["name"]
                        if (
                            get_category("subclasses", sc.get("source", ""))
                            == UA_CATEGORY
                        ):
                            name = f"[UA] {name}"
                        names.append(name)
                        class_lookup[name] = sc
                    sub_items[cls["name"]] = names
                    sub_lookup[cls["name"]] = class_lookup

        self._subclass_lookup_by_class = sub_lookup
        self.class_list.set_sectioned_items(sections, sub_items=sub_items)

    def _clear_detail_frames(self):
        for f in [
            self.equip_frame,
            self.traits_frame,
            self.skills_frame,
            self.features_frame,
        ]:
            for w in f.winfo_children():
                w.destroy()

    def _on_sub_select(self, class_name: str, sub_label: str):
        subclass = self._subclass_lookup_by_class.get(class_name, {}).get(sub_label)
        if not subclass:
            return

        self._show_subclass_panels()

        self.detail_name.configure(text=subclass.get("name", "Subclass"))
        self.detail_source.configure(
            text=f"Source: {subclass.get('source', 'Unknown')}"
        )

        preview_note = (
            "Previewing subclass details — class selection remains unchanged."
        )
        desc = self._subclass_summary(subclass)
        self.detail_desc.configure(
            text=f"{preview_note}\n\n{desc}" if desc else preview_note
        )

        self._clear_detail_frames()

        ttk.Label(
            self.features_frame,
            text="Subclass Features",
            style="Subheading.TLabel",
        ).pack(anchor="w", pady=(8, 4))

        features_by_level = subclass.get("features", {})
        if not features_by_level:
            ttk.Label(
                self.features_frame,
                text="No detailed subclass features available.",
                style="Dim.TLabel",
            ).pack(anchor="w")
            return

        def _lvl_key(level_str: str):
            try:
                return int(level_str)
            except (TypeError, ValueError):
                return 99

        for lvl in sorted(features_by_level.keys(), key=_lvl_key):
            ttk.Label(
                self.features_frame,
                text=f"Level {lvl}",
                style="Subheading.TLabel",
            ).pack(anchor="w", pady=(8, 2))

            for feat in features_by_level.get(lvl, []):
                feat_name = feat.get("name", "Feature")
                ttk.Label(
                    self.features_frame,
                    text=f"  • {feat_name}",
                    foreground=COLORS["accent"],
                    font=FONTS["body"],
                ).pack(anchor="w")

                feat_desc = feat.get("description", "")
                if feat_desc:
                    WrappingLabel(
                        self.features_frame,
                        text=f"    {feat_desc}",
                        foreground=COLORS["fg_dim"],
                    ).pack(fill=tk.X, anchor="w", pady=(0, 4))

    def _on_select(self, name: str):
        cls = self.data.classes_by_name.get(name)
        if not cls:
            return

        self._show_class_panels()

        self.character.character_class = cls
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
        self.detail_name.configure(text=cls["name"])
        self.detail_source.configure(text=f"Source: {cls.get('source', 'Unknown')}")
        self.detail_desc.configure(text=cls.get("description", ""))

        self._clear_detail_frames()

        # Equipment - Top
        equip = cls.get("starting_equipment", [])
        if equip:
            ttk.Label(
                self.equip_frame, text="Starting Equipment", style="Subheading.TLabel"
            ).pack(anchor="w", pady=(8, 4))
            for i, opt in enumerate(equip):
                if i > 0:
                    ttk.Label(
                        self.equip_frame,
                        text="   or",
                        foreground=COLORS["fg_dim"],
                        font=("Segoe UI", 9, "italic"),
                    ).pack(anchor="w")

                WrappingLabel(
                    self.equip_frame,
                    text=f"  ({opt['option']}) {opt['items']}",
                    foreground=COLORS["fg_dim"],
                ).pack(fill=tk.X, anchor="w")
            ttk.Separator(self.equip_frame, orient=tk.HORIZONTAL).pack(
                fill=tk.X, pady=16
            )

        # Core traits

        info = [
            ("Hit Die", f"d{cls['hit_die']}"),
            ("Primary Ability", ", ".join(cls.get("primary_ability", []))),
            ("Saving Throws", ", ".join(cls.get("saving_throws", []))),
            ("Armor", ", ".join(cls.get("armor_proficiencies", [])) or "None"),
            ("Weapons", ", ".join(cls.get("weapon_proficiencies", []))),
        ]

        if cls.get("caster_type"):
            info.append(
                (
                    "Spellcasting",
                    f"{cls['spellcasting_ability']} ({cls['caster_type']} caster)",
                )
            )
            if cls.get("cantrips_known"):
                info.append(("Cantrips at Lvl 1", str(cls["cantrips_known"])))
            if cls.get("spells_prepared"):
                info.append(("Prepared Spells", str(cls["spells_prepared"])))
            if cls.get("spell_slots"):
                slots_str = ", ".join(
                    f"{k}: {v}" for k, v in cls["spell_slots"].items()
                )
                info.append(("Spell Slots", slots_str))

        for label, value in info:
            row = ttk.Frame(self.traits_frame)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(
                row,
                text=f"{label}:",
                foreground=COLORS["accent"],
                font=FONTS["body"],
                width=20,
                anchor="e",
            ).pack(side=tk.LEFT)
            ttk.Label(row, text=f"  {value}").pack(side=tk.LEFT, padx=(4, 0))

        # Skills
        for w in self.skills_frame.winfo_children():
            w.destroy()
        self.skill_vars.clear()

        skill_choices = cls.get("skill_choices", {})
        self.skill_limit = skill_choices.get("count", 2)
        options = skill_choices.get("options", [])

        ttk.Label(
            self.skills_frame, text=f"Choose {self.skill_limit}:", style="Dim.TLabel"
        ).pack(anchor="w", padx=4)

        cols_frame = ttk.Frame(self.skills_frame)
        cols_frame.pack(fill=tk.X, padx=4, pady=4)

        for i, skill_name in enumerate(options):
            var = tk.BooleanVar(value=False)
            var.trace_add("write", self._on_skill_change)
            self.skill_vars[skill_name] = var
            col = i % 3
            row = i // 3
            cb = ttk.Checkbutton(cols_frame, text=skill_name, variable=var)
            cb.grid(row=row, column=col, sticky="w", padx=8, pady=1)

        # Features - All Levels Roadmap
        for w in self.features_frame.winfo_children():
            w.destroy()

        prog = self.data.get_progression(cls["slug"])
        if prog and "levels" in prog:
            ttk.Label(
                self.features_frame,
                text=f"{cls['name']} Progression Matrix",
                style="Heading.TLabel",
            ).pack(anchor="w", pady=(8, 8))

            # 1. Gather all unique columns across all 20 levels
            extra_keys = set()
            all_slots = set()
            has_cantrips = False
            has_prepared = False

            for lvl_data in prog["levels"]:
                # Class specific columns like Martial Arts, Focus Points, etc.
                extra_keys.update(lvl_data.get("extra", {}).keys())
                # Spell slots cols
                slots = lvl_data.get("spell_slots", {})
                if slots:
                    all_slots.update(slots.keys())
                if lvl_data.get("cantrips"):
                    has_cantrips = True
                if lvl_data.get("prepared_spells"):
                    has_prepared = True

            # Sort spell slots and other extras
            _slot_order = {
                "1st": 1,
                "2nd": 2,
                "3rd": 3,
                "4th": 4,
                "5th": 5,
                "6th": 6,
                "7th": 7,
                "8th": 8,
                "9th": 9,
            }
            sorted_slots = sorted(
                [s for s in all_slots if s in _slot_order], key=lambda x: _slot_order[x]
            )
            sorted_extra = sorted(list(extra_keys))

            # Initial setup of columns
            col_configs = [
                {"id": "lvl", "text": "Lvl", "width": 40},
                {"id": "prof", "text": "Proficiency Bonus", "width": 130},
                {
                    "id": "features",
                    "text": "Features",
                    "width": 350,
                    "anchor": "w",
                    "stretch": True,
                },
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

            # 2. Build and Populate Table
            container = ttk.Frame(self.features_frame)
            container.pack(fill=tk.X, pady=(0, 24))

            # Use a height of 20 to show all levels at once
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
                        # Only show specific names, exclude generic ones common to many levels
                        f_list = [
                            f
                            for f in lvl_data.get("features", [])
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

            # 3. Add Roadmap Heading
            ttk.Label(
                self.features_frame,
                text="Feature Descriptions Roadmap",
                style="Heading.TLabel",
            ).pack(anchor="w", pady=(16, 8))

            # Existing roadmap display logic follows...
            for lvl_data in prog["levels"]:
                lvl = lvl_data.get("level")
                feats = lvl_data.get("feature_details", [])
                all_feature_names = lvl_data.get("features", [])

                # Filter for useful level display: only show levels that have features or interesting changes
                if not feats and not [f for f in all_feature_names if f != "-"]:
                    continue

                # Compose Level Header
                prof = lvl_data.get("proficiency_bonus", 2)
                header_text = f"Level {lvl}  [+{prof} Proficiency Bonus]"

                extra = lvl_data.get("extra", {})
                if extra:
                    extra_parts = [
                        f"{k}: {v}" for k, v in extra.items() if v is not None
                    ]
                    if extra_parts:
                        header_text += f" | {', '.join(extra_parts)}"

                ttk.Label(
                    self.features_frame, text=header_text, style="Subheading.TLabel"
                ).pack(anchor="w", pady=(12, 4))

                shown_feats = set()
                if feats:
                    for feat in feats:
                        name = feat.get("name", "Feature")
                        shown_feats.add(name.lower())
                        ttk.Label(
                            self.features_frame,
                            text=f"  \u2022 {name}",
                            foreground=COLORS["accent"],
                            font=FONTS["subheading"],
                        ).pack(anchor="w")
                        if feat.get("description"):
                            WrappingLabel(
                                self.features_frame,
                                text=f"    {feat['description']}",
                                foreground=COLORS["fg_dim"],
                            ).pack(fill=tk.X, anchor="w", pady=(0, 4))

                for f_name in all_feature_names:
                    if f_name.lower() not in shown_feats and f_name not in [
                        "-",
                        "Ability Score Improvement",
                    ]:
                        ttk.Label(
                            self.features_frame,
                            text=f"  \u2022 {f_name}",
                            foreground=COLORS["accent"],
                            font=FONTS["subheading"],
                        ).pack(anchor="w")
                    elif (
                        f_name == "Ability Score Improvement"
                        and f_name.lower() not in shown_feats
                    ):
                        ttk.Label(
                            self.features_frame,
                            text=f"  \u2022 {f_name}",
                            foreground=COLORS["fg_dim"],
                            font=FONTS["body"],
                        ).pack(anchor="w")
        else:
            # Fallback to current simple feature display if no progression
            features = cls.get("level_1_features", [])
            if features:
                ttk.Label(
                    self.features_frame,
                    text="Level 1 Features",
                    style="Subheading.TLabel",
                ).pack(anchor="w", pady=(8, 4))
                for feat in features:
                    ttk.Label(
                        self.features_frame,
                        text=f"  {feat['name']}",
                        foreground=COLORS["accent"],
                        font=FONTS["subheading"],
                    ).pack(anchor="w")
                    if feat.get("description"):
                        WrappingLabel(
                            self.features_frame,
                            text=f"    {feat['description']}",
                            foreground=COLORS["fg_dim"],
                        ).pack(fill=tk.X, anchor="w", pady=(0, 4))

        self.notify_change()

    def is_valid(self) -> bool:
        if not self.character.character_class:
            return False
        return len(self.character.selected_skills) == self.skill_limit

    def _on_skill_change(self, *args):
        selected = [name for name, var in self.skill_vars.items() if var.get()]

        if len(selected) > self.skill_limit:
            # Uncheck the last one
            for name, var in self.skill_vars.items():
                if var.get() and name not in self.character.selected_skills:
                    var.set(False)
                    return

        self.character.selected_skills = selected
        self.notify_change()
