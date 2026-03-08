"""Level-up wizard dialog for advancing a character by one level."""

import tkinter as tk
from tkinter import ttk, messagebox

from gui.theme import COLORS, FONTS
from gui.widgets import ScrollableFrame, WrappingLabel
from models.character import Character
from models.class_level import ClassLevel


class LevelUpWizard(tk.Toplevel):
    """Modal dialog that walks the player through gaining one level."""

    def __init__(self, parent, character: Character, game_data, on_complete=None):
        super().__init__(parent)
        self.character = character
        self.data = game_data
        self.on_complete = on_complete

        self.title(f"Level Up - {character.name}")
        self.geometry("750x600")
        self.minsize(650, 500)
        self.configure(bg=COLORS["bg"])
        self.transient(parent)
        self.grab_set()

        # Determine what the next level will be
        self.new_total_level = character.level + 1
        self.primary_class_slug = character.character_class.get("slug", "") if character.character_class else ""
        self.class_slug = self.primary_class_slug
        self.class_var = tk.StringVar(value=self.class_slug)

        self._update_level_data()

        # Choices to collect
        self.hp_choice = tk.IntVar(value=0)
        self.subclass_var = tk.StringVar()
        self.feat_var = tk.StringVar()
        self.selected_new_cantrips = []
        self.selected_new_spells = []

        self._build_ui()

    def _update_level_data(self):
        """Update progression data for the currently selected class."""
        self.class_slug = self.class_var.get()
        self.new_class_level = self.character.class_level_in(self.class_slug) + 1
        self.progression = self.data.get_progression(self.class_slug)
        self.level_data = self.data.get_level_data(self.class_slug, self.new_class_level)

        # Get class data dict for the selected class
        self.selected_class_data = None
        for cls in self.data.classes:
            if cls.get("slug") == self.class_slug:
                self.selected_class_data = cls
                break

    def _build_ui(self):
        # Header
        header = ttk.Frame(self)
        header.pack(fill=tk.X, padx=16, pady=(16, 8))

        self.header_label = ttk.Label(
            header,
            text=self._header_text(),
            font=("Segoe UI", 16, "bold"),
            foreground=COLORS["accent"],
        )
        self.header_label.pack(side=tk.LEFT)

        ttk.Label(
            header,
            text=f"(Total Level {self.new_total_level})",
            font=FONTS["body"],
            foreground=COLORS["fg_dim"],
        ).pack(side=tk.LEFT, padx=8)

        # Multiclass selector
        mc_frame = ttk.Frame(self)
        mc_frame.pack(fill=tk.X, padx=16, pady=(0, 4))

        ttk.Label(mc_frame, text="Class:", foreground=COLORS["fg"]).pack(side=tk.LEFT)
        class_options = [cls["slug"] for cls in self.data.classes]
        self.class_combo = ttk.Combobox(
            mc_frame,
            textvariable=self.class_var,
            values=class_options,
            state="readonly",
            width=20,
        )
        self.class_combo.pack(side=tk.LEFT, padx=8)

        self.prereq_label = ttk.Label(mc_frame, text="", foreground="#e74c3c")
        self.prereq_label.pack(side=tk.LEFT, padx=8)

        self.class_var.trace_add("write", self._on_class_change)

        # Scrollable content area
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)
        self.content = self.scroll.inner

        # Bottom buttons (fixed at bottom)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=16, pady=(8, 16))

        ttk.Button(
            btn_frame, text="Cancel",
            command=self.destroy,
        ).pack(side=tk.LEFT)

        ttk.Button(
            btn_frame, text="Confirm Level Up",
            style="Accent.TButton",
            command=self._confirm,
        ).pack(side=tk.RIGHT)

        # Build dynamic content
        self._rebuild_content()

    def _header_text(self) -> str:
        cls_name = self.class_slug.title()
        if self.selected_class_data:
            cls_name = self.selected_class_data.get("name", cls_name)
        return f"Level Up to {cls_name} {self.new_class_level}"

    def _on_class_change(self, *_):
        """Handle multiclass selection change."""
        self._update_level_data()
        self.header_label.configure(text=self._header_text())
        self.subclass_var.set("")
        self.feat_var.set("")

        # Check multiclass prerequisites if switching to a new class
        if self.class_slug != self.primary_class_slug and self.character.class_level_in(self.class_slug) == 0:
            met, reason = self.character.multiclass_prereqs_met(self.class_slug)
            # Also check leaving the primary class
            pri_met, pri_reason = self.character.multiclass_prereqs_met(self.primary_class_slug)
            if not met:
                self.prereq_label.configure(text=f"\u26a0 {reason}")
            elif not pri_met:
                self.prereq_label.configure(text=f"\u26a0 Primary class: {pri_reason}")
            else:
                self.prereq_label.configure(text="")
        else:
            self.prereq_label.configure(text="")

        self._rebuild_content()

    def _rebuild_content(self):
        """Rebuild the scrollable content area."""
        for w in self.content.winfo_children():
            w.destroy()

        self._build_features_section()
        self._build_hp_section()

        if self.level_data:
            features = self.level_data.get("features", [])
            if any("Ability Score Improvement" in f for f in features):
                self._build_asi_section()
            if any("Subclass" in f and "Feature" not in f for f in features):
                self._build_subclass_section()
            if self._has_new_spell_options():
                self._build_spell_section()


    def _build_features_section(self):
        """Show what features are gained at this level."""
        if not self.level_data:
            ttk.Label(
                self.content,
                text="No progression data available for this class/level.",
                foreground=COLORS["fg_dim"],
            ).pack(anchor="w", pady=4)
            return

        features = self.level_data.get("features", [])
        details = self.level_data.get("feature_details", [])

        if not features:
            return

        ttk.Label(
            self.content,
            text="New Features",
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(8, 4))

        for feat_name in features:
            if feat_name == "-" or feat_name == "Ability Score Improvement":
                continue

            # If this is a "Subclass Feature" level, show subclass features
            sub_slug = self.character.subclass_for_class(self.class_slug)
            if feat_name == "Subclass Feature" and sub_slug:
                self._show_subclass_features()
                continue

            frame = ttk.Frame(self.content, style="Card.TFrame")
            frame.pack(fill=tk.X, pady=2, padx=4)

            ttk.Label(
                frame,
                text=feat_name,
                font=FONTS["subheading"],
                foreground=COLORS["fg_bright"],
                background=COLORS["bg_card"],
            ).pack(anchor="w", padx=8, pady=(4, 0))

            # Find description
            desc = ""
            for d in details:
                if d["name"].lower() == feat_name.lower():
                    desc = d["description"]
                    break

            if desc:
                # Truncate long descriptions
                if len(desc) > 300:
                    desc = desc[:297] + "..."
                WrappingLabel(
                    frame,
                    text=desc,
                    foreground=COLORS["fg_dim"],
                    background=COLORS["bg_card"],
                ).pack(fill=tk.X, anchor="w", padx=8, pady=(0, 4))

        # Show extra column changes
        extra = self.level_data.get("extra", {})
        if extra:
            for col_name, val in extra.items():
                if val is not None:
                    ttk.Label(
                        self.content,
                        text=f"{col_name}: {val}",
                        foreground=COLORS["fg"],
                    ).pack(anchor="w", padx=12, pady=1)

    def _show_subclass_features(self):
        """Show subclass features gained at this level."""
        sub_slug = self.character.subclass_for_class(self.class_slug)
        subclass = self.data.get_subclass(self.class_slug, sub_slug)
        if not subclass:
            ttk.Label(
                self.content,
                text=f"Subclass Feature (data not available for {sub_slug})",
                foreground=COLORS["fg_dim"],
            ).pack(anchor="w", padx=12, pady=2)
            return

        sub_features = subclass.get("features", {}).get(str(self.new_class_level), [])
        if not sub_features:
            sub_name = subclass.get("name", sub_slug)
            ttk.Label(
                self.content,
                text=f"{sub_name} Feature (Level {self.new_class_level})",
                foreground=COLORS["fg"],
            ).pack(anchor="w", padx=12, pady=2)
            return

        for feat in sub_features:
            frame = ttk.Frame(self.content, style="Card.TFrame")
            frame.pack(fill=tk.X, pady=2, padx=4)

            ttk.Label(
                frame,
                text=f"{feat['name']} (Subclass)",
                font=FONTS["subheading"],
                foreground=COLORS["fg_bright"],
                background=COLORS["bg_card"],
            ).pack(anchor="w", padx=8, pady=(4, 0))

            desc = feat.get("description", "")
            if desc:
                if len(desc) > 300:
                    desc = desc[:297] + "..."
                WrappingLabel(
                    frame,
                    text=desc,
                    foreground=COLORS["fg_dim"],
                    background=COLORS["bg_card"],
                ).pack(fill=tk.X, anchor="w", padx=8, pady=(0, 4))

    def _build_hp_section(self):
        """HP gain section."""
        ttk.Separator(self.content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

        ttk.Label(
            self.content,
            text="Hit Points",
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(4, 4))

        hit_die = self.selected_class_data.get("hit_die", 8) if self.selected_class_data else 8
        con_mod = self.character.ability_scores.modifier("Constitution")
        average = hit_die // 2 + 1

        hp_frame = ttk.Frame(self.content)
        hp_frame.pack(fill=tk.X, padx=12)

        ttk.Radiobutton(
            hp_frame,
            text=f"Take average ({average} + {con_mod} CON = {average + con_mod} HP)",
            variable=self.hp_choice,
            value=average,
        ).pack(anchor="w", pady=2)

        ttk.Radiobutton(
            hp_frame,
            text=f"Take max ({hit_die} + {con_mod} CON = {hit_die + con_mod} HP)",
            variable=self.hp_choice,
            value=hit_die,
        ).pack(anchor="w", pady=2)

        self.hp_choice.set(average)

    def _build_asi_section(self):
        """Ability Score Improvement / Feat selection."""
        ttk.Separator(self.content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

        ttk.Label(
            self.content,
            text="Ability Score Improvement",
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(4, 4))

        ttk.Label(
            self.content,
            text="Choose a feat (the Ability Score Improvement feat lets you increase two scores):",
            foreground=COLORS["fg"],
        ).pack(anchor="w", padx=12)

        # Build feat list - general feats and epic boons at level 19
        feat_options = []
        for feat in self.data.feats:
            cat = feat.get("category", "general")
            if cat == "general":
                feat_options.append(feat["name"])
            elif cat == "epic_boon" and self.new_total_level >= 19:
                feat_options.append(feat["name"])

        feat_options.sort()

        feat_frame = ttk.Frame(self.content)
        feat_frame.pack(fill=tk.X, padx=12, pady=4)

        self.feat_var.set("")
        combo = ttk.Combobox(
            feat_frame,
            textvariable=self.feat_var,
            values=feat_options,
            state="readonly",
            width=40,
        )
        combo.pack(anchor="w")

    def _build_subclass_section(self):
        """Subclass selection at level 3."""
        ttk.Separator(self.content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

        ttk.Label(
            self.content,
            text="Choose Subclass",
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(4, 4))

        # Get available subclasses
        subclasses = self.data.get_subclasses_for_class(self.class_slug)

        # Also include PHB subclasses from progression data
        phb_names = set()
        if self.progression:
            for name in self.progression.get("subclass_names", []):
                phb_names.add(name)

        sub_frame = ttk.Frame(self.content)
        sub_frame.pack(fill=tk.X, padx=12, pady=4)

        options = []
        for sc in subclasses:
            options.append(sc["name"])
        # Add PHB names that don't have UA data
        ua_names_lower = {sc["name"].lower() for sc in subclasses}
        for name in sorted(phb_names):
            if name.lower() not in ua_names_lower:
                options.append(f"{name} (PHB)")

        self.subclass_var.set("")
        combo = ttk.Combobox(
            sub_frame,
            textvariable=self.subclass_var,
            values=sorted(options),
            state="readonly",
            width=40,
        )
        combo.pack(anchor="w")

        # Show subclass description when selected
        self.sub_desc_label = WrappingLabel(
            self.content, text="",
            foreground=COLORS["fg_dim"],
        )
        self.sub_desc_label.pack(fill=tk.X, anchor="w", padx=12, pady=4)

        def on_sub_select(*_):
            name = self.subclass_var.get().replace(" (PHB)", "")
            for sc in subclasses:
                if sc["name"] == name:
                    self.sub_desc_label.configure(text=sc.get("description", "")[:300])
                    return
            self.sub_desc_label.configure(text="(Core subclass - feature data not available)")

        self.subclass_var.trace_add("write", on_sub_select)

    def _has_new_spell_options(self) -> bool:
        """Check if this level grants new cantrips or spell options."""
        if not self.level_data:
            return False
        # Check if cantrips or prepared spells increased from previous level
        prev = self.data.get_level_data(self.class_slug, self.new_class_level - 1)
        if not prev:
            return False

        curr_cantrips = self.level_data.get("cantrips", 0) or 0
        prev_cantrips = prev.get("cantrips", 0) or 0
        curr_prepared = self.level_data.get("prepared_spells", 0) or 0
        prev_prepared = prev.get("prepared_spells", 0) or 0

        return curr_cantrips > prev_cantrips or curr_prepared > prev_prepared

    def _build_spell_section(self):
        """Show new spell/cantrip slots gained."""
        prev = self.data.get_level_data(self.class_slug, self.new_class_level - 1)
        if not prev:
            return

        curr_cantrips = self.level_data.get("cantrips", 0) or 0
        prev_cantrips = prev.get("cantrips", 0) or 0
        new_cantrips = curr_cantrips - prev_cantrips

        curr_prepared = self.level_data.get("prepared_spells", 0) or 0
        prev_prepared = prev.get("prepared_spells", 0) or 0
        new_prepared = curr_prepared - prev_prepared

        # Get new spell slot levels unlocked
        curr_slots = self.level_data.get("spell_slots", {})
        prev_slots = prev.get("spell_slots", {})
        new_slot_levels = set(curr_slots.keys()) - set(prev_slots.keys())

        ttk.Separator(self.content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

        ttk.Label(
            self.content,
            text="Spellcasting Changes",
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(4, 4))

        info_parts = []
        if new_cantrips > 0:
            info_parts.append(f"Learn {new_cantrips} new cantrip(s)")
        if new_prepared > 0:
            info_parts.append(f"Prepare {new_prepared} additional spell(s)")
        if new_slot_levels:
            slot_names = sorted(new_slot_levels, key=lambda x: {"1st":1,"2nd":2,"3rd":3,"4th":4,"5th":5,"6th":6,"7th":7,"8th":8,"9th":9}.get(x, 99))
            info_parts.append(f"New spell slot level(s): {', '.join(slot_names)}")

        # Show current slot progression
        if curr_slots:
            slots_str = ", ".join(f"{k}: {v}" for k, v in sorted(curr_slots.items(),
                key=lambda x: {"1st":1,"2nd":2,"3rd":3,"4th":4,"5th":5,"6th":6,"7th":7,"8th":8,"9th":9}.get(x[0], 99)))
            info_parts.append(f"Total spell slots: {slots_str}")

        for part in info_parts:
            ttk.Label(
                self.content,
                text=f"  {part}",
                foreground=COLORS["fg"],
            ).pack(anchor="w", padx=12, pady=1)

        ttk.Label(
            self.content,
            text="(Spell selection can be updated via the Edit Character screen)",
            foreground=COLORS["fg_dim"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=12, pady=(4, 0))

    def _confirm(self):
        """Apply the level-up choices to the character."""
        # Validate multiclass prerequisites
        if self.class_slug != self.primary_class_slug and self.character.class_level_in(self.class_slug) == 0:
            met, reason = self.character.multiclass_prereqs_met(self.class_slug)
            if not met:
                messagebox.showwarning(
                    "Prerequisites Not Met",
                    f"Cannot multiclass into {self.class_slug.title()}:\n{reason}",
                    parent=self)
                return
            pri_met, pri_reason = self.character.multiclass_prereqs_met(self.primary_class_slug)
            if not pri_met:
                messagebox.showwarning(
                    "Prerequisites Not Met",
                    f"Cannot multiclass out of {self.primary_class_slug.title()}:\n{pri_reason}",
                    parent=self)
                return

        # Validate required choices
        if self.level_data:
            features = self.level_data.get("features", [])

            if any("Ability Score Improvement" in f for f in features):
                if not self.feat_var.get():
                    messagebox.showwarning(
                        "Missing Choice",
                        "Please select a feat for your Ability Score Improvement.",
                        parent=self)
                    return

            if any("Subclass" in f and "Feature" not in f for f in features):
                if not self.subclass_var.get():
                    messagebox.showwarning(
                        "Missing Choice",
                        "Please select a subclass.",
                        parent=self)
                    return

        # Determine hit die for this class
        hit_die = self.selected_class_data.get("hit_die", 8) if self.selected_class_data else 8

        # Build the new ClassLevel
        cl = ClassLevel(
            class_slug=self.class_slug,
            class_level=self.new_class_level,
            hp_roll=self.hp_choice.get(),
            hit_die=hit_die,
        )

        # Subclass
        if self.subclass_var.get():
            sub_name = self.subclass_var.get().replace(" (PHB)", "")
            # Find the slug
            for sc in self.data.get_subclasses_for_class(self.class_slug):
                if sc["name"] == sub_name:
                    cl.subclass_slug = sc["slug"]
                    break
            if not cl.subclass_slug:
                cl.subclass_slug = sub_name.lower().replace(" ", "-")

        # Feat choice
        if self.feat_var.get():
            cl.feat_choice = self.feat_var.get()

        # Apply to character
        self.character.class_levels.append(cl)

        # Save and close
        if self.on_complete:
            self.on_complete()

        self.destroy()
