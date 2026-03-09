"""Step 2: Class selection."""

import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import SearchableListbox, ScrollableFrame, WrappingLabel
from gui.theme import COLORS, FONTS


class ClassStep(WizardStep):
    tab_title = "Class"

    def build_ui(self):
        self._edit_initialized = False
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(0, weight=1)

        # Left: class list
        left = ttk.Frame(self.frame, width=220)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.grid_propagate(False)

        ttk.Label(left, text="Choose Class", style="Heading.TLabel").pack(anchor="w", pady=(0, 6))
        self.class_list = SearchableListbox(left, on_select=self._on_select)
        self.class_list.pack(fill=tk.BOTH, expand=True)

        # Right: detail
        right = ScrollableFrame(self.frame)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        self.detail = right.inner

        self.detail_name = ttk.Label(self.detail, text="Select a class", style="Heading.TLabel")
        self.detail_name.pack(anchor="w", pady=(0, 4))

        self.detail_source = ttk.Label(self.detail, text="", style="Dim.TLabel")
        self.detail_source.pack(anchor="w")

        self.detail_desc = WrappingLabel(self.detail, text="")
        self.detail_desc.pack(fill=tk.X, anchor="w", pady=(8, 0))

        ttk.Separator(self.detail, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

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

    def _populate_list(self):
        names = sorted([c["name"] for c in self.data.classes])
        self.class_list.set_items(names)

    def _on_select(self, name: str):
        cls = self.data.classes_by_name.get(name)
        if not cls:
            return

        self.character.character_class = cls
        self.character.selected_skills = []

        # Initialize class_levels with level 1 entry
        from models.class_level import ClassLevel
        slug = cls.get("slug", "")
        if not self.character.class_levels or self.character.class_levels[0].class_slug != slug:
            hit_die = cls.get("hit_die", 8)
            self.character.class_levels = [ClassLevel(class_slug=slug, class_level=1, hit_die=hit_die)]
        self.detail_name.configure(text=cls["name"])
        self.detail_source.configure(text=f"Source: {cls.get('source', 'Unknown')}")
        self.detail_desc.configure(text=cls.get("description", ""))

        # Core traits
        for w in self.traits_frame.winfo_children():
            w.destroy()

        info = [
            ("Hit Die", f"d{cls['hit_die']}"),
            ("Primary Ability", ", ".join(cls.get("primary_ability", []))),
            ("Saving Throws", ", ".join(cls.get("saving_throws", []))),
            ("Armor", ", ".join(cls.get("armor_proficiencies", [])) or "None"),
            ("Weapons", ", ".join(cls.get("weapon_proficiencies", []))),
        ]

        if cls.get("caster_type"):
            info.append(("Spellcasting", f"{cls['spellcasting_ability']} ({cls['caster_type']} caster)"))
            if cls.get("cantrips_known"):
                info.append(("Cantrips at Lvl 1", str(cls["cantrips_known"])))
            if cls.get("spells_prepared"):
                info.append(("Prepared Spells", str(cls["spells_prepared"])))
            if cls.get("spell_slots"):
                slots_str = ", ".join(f"{k}: {v}" for k, v in cls["spell_slots"].items())
                info.append(("Spell Slots", slots_str))

        for label, value in info:
            row = ttk.Frame(self.traits_frame)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=f"{label}:", foreground=COLORS["accent"],
                      font=FONTS["body"], width=20, anchor="e").pack(side=tk.LEFT)
            ttk.Label(row, text=f"  {value}").pack(side=tk.LEFT, padx=(4, 0))

        # Skills
        for w in self.skills_frame.winfo_children():
            w.destroy()
        self.skill_vars.clear()

        skill_choices = cls.get("skill_choices", {})
        self.skill_limit = skill_choices.get("count", 2)
        options = skill_choices.get("options", [])

        ttk.Label(self.skills_frame, text=f"Choose {self.skill_limit}:",
                  style="Dim.TLabel").pack(anchor="w", padx=4)

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

        # Features
        for w in self.features_frame.winfo_children():
            w.destroy()

        features = cls.get("level_1_features", [])
        if features:
            ttk.Label(self.features_frame, text="Level 1 Features",
                      style="Subheading.TLabel").pack(anchor="w", pady=(0, 4))
            for feat in features:
                ttk.Label(self.features_frame, text=f"  {feat['name']}",
                          foreground=COLORS["accent"], font=FONTS["subheading"]).pack(anchor="w")
                if feat.get("description"):
                    WrappingLabel(self.features_frame, text=f"    {feat['description']}",
                              foreground=COLORS["fg_dim"]).pack(fill=tk.X, anchor="w", pady=(0, 4))

        # Equipment
        equip = cls.get("starting_equipment", [])
        if equip:
            ttk.Label(self.features_frame, text="Starting Equipment",
                      style="Subheading.TLabel").pack(anchor="w", pady=(8, 4))
            for opt in equip:
                WrappingLabel(self.features_frame,
                          text=f"  ({opt['option']}) {opt['items']}",
                          foreground=COLORS["fg_dim"]).pack(fill=tk.X, anchor="w")

        self.notify_change()

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
