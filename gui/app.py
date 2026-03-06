"""Main application: character creation wizard with live summary panel."""

import tkinter as tk
from tkinter import ttk

from gui.theme import apply_theme, COLORS, FONTS
from gui.data_loader import GameData
from gui.widgets import ScrollableFrame
from models.character import Character
from models.enums import ALL_SKILLS

from gui.step_species import SpeciesStep
from gui.step_class import ClassStep
from gui.step_background import BackgroundStep
from gui.step_ability_scores import AbilityScoresStep
from gui.step_feat import FeatStep
from gui.step_spells import SpellsStep
from gui.step_equipment import EquipmentStep
from gui.step_summary import SummaryStep


class SummaryPanel(ttk.Frame):
    """Live-updating summary panel on the right side of the window."""

    def __init__(self, parent, character: Character):
        super().__init__(parent, style="Card.TFrame")
        self.character = character

        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill=tk.BOTH, expand=True)
        self.inner = self.scroll.inner
        self.inner.configure(style="Card.TFrame")
        self.scroll.canvas.configure(bg=COLORS["bg_card"])

        self._build()

    def _build(self):
        for w in self.inner.winfo_children():
            w.destroy()

        c = self.character

        # Title
        ttk.Label(self.inner, text="Character", style="CardHeading.TLabel").pack(
            anchor="w", padx=8, pady=(8, 2))

        self.summary_label = ttk.Label(self.inner, text=c.summary_text(),
                                        style="Card.TLabel", wraplength=220)
        self.summary_label.pack(anchor="w", padx=8)

        ttk.Separator(self.inner, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4, pady=6)

        # Stats
        stats_frame = ttk.Frame(self.inner, style="Card.TFrame")
        stats_frame.pack(fill=tk.X, padx=8)

        self.stat_labels = {}
        for label in ["HP", "AC", "Speed", "Init"]:
            row = ttk.Frame(stats_frame, style="Card.TFrame")
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=f"{label}:", width=8,
                      background=COLORS["bg_card"], foreground=COLORS["fg_dim"]).pack(side=tk.LEFT)
            val_label = ttk.Label(row, text="—", background=COLORS["bg_card"],
                                  foreground=COLORS["fg_bright"], font=FONTS["subheading"])
            val_label.pack(side=tk.LEFT)
            self.stat_labels[label] = val_label

        ttk.Separator(self.inner, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4, pady=6)

        # Ability scores
        ttk.Label(self.inner, text="Abilities", style="CardHeading.TLabel").pack(
            anchor="w", padx=8, pady=(0, 2))

        self.ability_labels = {}
        ab_frame = ttk.Frame(self.inner, style="Card.TFrame")
        ab_frame.pack(fill=tk.X, padx=8)

        for ability_name in ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]:
            row = ttk.Frame(ab_frame, style="Card.TFrame")
            row.pack(fill=tk.X, pady=1)
            short = ability_name[:3].upper()
            ttk.Label(row, text=f"{short}:", width=6,
                      background=COLORS["bg_card"], foreground=COLORS["fg_dim"]).pack(side=tk.LEFT)
            val_label = ttk.Label(row, text="10 (+0)", background=COLORS["bg_card"],
                                  foreground=COLORS["fg"])
            val_label.pack(side=tk.LEFT)
            self.ability_labels[ability_name] = val_label

        ttk.Separator(self.inner, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4, pady=6)

        # Selections summary
        ttk.Label(self.inner, text="Choices", style="CardHeading.TLabel").pack(
            anchor="w", padx=8, pady=(0, 2))

        self.choices_frame = ttk.Frame(self.inner, style="Card.TFrame")
        self.choices_frame.pack(fill=tk.X, padx=8)

        self.choice_labels = {}
        for label in ["Species", "Class", "Background", "Feat", "Skills"]:
            row = ttk.Frame(self.choices_frame, style="Card.TFrame")
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=f"{label}:", width=10,
                      background=COLORS["bg_card"], foreground=COLORS["fg_dim"]).pack(side=tk.LEFT)
            val_label = ttk.Label(row, text="—", background=COLORS["bg_card"],
                                  foreground=COLORS["fg"], wraplength=160)
            val_label.pack(side=tk.LEFT)
            self.choice_labels[label] = val_label

    def refresh(self):
        """Update all labels from current character state."""
        c = self.character

        self.summary_label.configure(text=c.summary_text())

        # Combat stats
        if c.character_class:
            self.stat_labels["HP"].configure(text=str(c.hit_points))
            self.stat_labels["AC"].configure(text=str(c.armor_class))
        else:
            self.stat_labels["HP"].configure(text="—")
            self.stat_labels["AC"].configure(text="—")

        self.stat_labels["Speed"].configure(text=f"{c.speed} ft")
        init = c.initiative
        self.stat_labels["Init"].configure(text=f"+{init}" if init >= 0 else str(init))

        # Abilities
        for ability_name in ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]:
            total = c.ability_scores.total(ability_name)
            mod_str = c.ability_scores.modifier_str(ability_name)
            self.ability_labels[ability_name].configure(text=f"{total} ({mod_str})")

        # Choices
        self.choice_labels["Species"].configure(
            text=c.species_name + (f" ({c.species_sub_choice})" if c.species_sub_choice else ""))
        self.choice_labels["Class"].configure(text=c.class_name)
        self.choice_labels["Background"].configure(text=c.background_name)

        feat_parts = []
        if c.feat:
            if c.background and c.background.get("feat"):
                feat_parts.append(c.background["feat"])
            else:
                feat_parts.append(c.feat.get("name", "?"))
        if c.species_origin_feat:
            feat_parts.append(c.species_origin_feat.get("name", "?"))
        self.choice_labels["Feat"].configure(text=", ".join(feat_parts) if feat_parts else "—")

        all_skills = sorted(c.all_skill_proficiencies)
        self.choice_labels["Skills"].configure(text=", ".join(all_skills) if all_skills else "—")


class CharacterCreatorApp:
    """Main application window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("D&D 2024 Character Creator")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)

        apply_theme(self.root)

        self.character = Character()
        self.data = GameData()

        self._build_ui()

    def _build_ui(self):
        # Main horizontal split: notebook (left) + summary (right)
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Notebook
        self.notebook = ttk.Notebook(paned)

        # Summary panel
        self.summary = SummaryPanel(paned, self.character)

        paned.add(self.notebook, weight=3)
        paned.add(self.summary, weight=1)

        # Create wizard steps
        self.steps = [
            SpeciesStep(self.notebook, self.character, self.data),
            ClassStep(self.notebook, self.character, self.data),
            BackgroundStep(self.notebook, self.character, self.data),
            AbilityScoresStep(self.notebook, self.character, self.data),
            FeatStep(self.notebook, self.character, self.data),
            SpellsStep(self.notebook, self.character, self.data),
            EquipmentStep(self.notebook, self.character, self.data),
            SummaryStep(self.notebook, self.character, self.data),
        ]

        # Register change callbacks
        for step in self.steps:
            step.on_change_callbacks.append(self.summary.refresh)

        # Tab change event
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, event):
        idx = self.notebook.index(self.notebook.select())
        if 0 <= idx < len(self.steps):
            self.steps[idx].on_enter()

    def run(self):
        self.root.mainloop()
