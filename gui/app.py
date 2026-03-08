"""Main application: screen manager for home, wizard and viewer screens."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

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

from gui.home_screen import HomeScreen
from gui.character_viewer import CharacterViewer


class SummaryPanel(ttk.Frame):
    """Live-updating summary panel on the right side of the wizard."""

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
            val_label = ttk.Label(row, text="\u2014", background=COLORS["bg_card"],
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
            val_label = ttk.Label(row, text="\u2014", background=COLORS["bg_card"],
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
            self.stat_labels["HP"].configure(text="\u2014")
            self.stat_labels["AC"].configure(text="\u2014")

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
        self.choice_labels["Feat"].configure(text=", ".join(feat_parts) if feat_parts else "\u2014")

        all_skills = sorted(c.all_skill_proficiencies)
        self.choice_labels["Skills"].configure(text=", ".join(all_skills) if all_skills else "\u2014")


class CharacterCreatorApp:
    """Main application window with screen management."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("D&D 2024 Character Creator")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)

        apply_theme(self.root)
        self.data = GameData()

        # Container for all screens
        self.container = ttk.Frame(self.root)
        self.container.pack(fill=tk.BOTH, expand=True)

        # Screen references
        self.home_screen = HomeScreen(self.container, self)
        self.wizard_frame = None   # built lazily
        self.viewer_frame = None   # built lazily

        # State
        self.character = None
        self.current_save_path = None

        # Start on home screen
        self.show_home()

    # ── Screen transitions ──────────────────────────────────────

    def show_home(self):
        """Switch to the home screen."""
        self._hide_all()
        self.home_screen.refresh()
        self.home_screen.frame.pack(fill=tk.BOTH, expand=True)

    def show_wizard(self, character=None, save_path=None):
        """Switch to the character creation wizard.

        If *character* is provided (edit mode), the wizard is populated
        with that character's data.
        """
        self._hide_all()

        if character is None:
            character = Character()
        self.character = character
        self.current_save_path = save_path

        # Rebuild wizard each time (steps bind to a specific Character)
        if self.wizard_frame:
            self.wizard_frame.destroy()
        self.wizard_frame = self._build_wizard(character, save_path)
        self.wizard_frame.pack(fill=tk.BOTH, expand=True)

    def show_viewer(self, character, save_path):
        """Switch to the read-only character viewer."""
        self._hide_all()
        self.character = character
        self.current_save_path = save_path

        if self.viewer_frame:
            self.viewer_frame.destroy()
        self.viewer_frame = CharacterViewer(
            self.container, character, save_path, self.data, self)
        self.viewer_frame.pack(fill=tk.BOTH, expand=True)

    def _hide_all(self):
        self.home_screen.frame.pack_forget()
        if self.wizard_frame:
            self.wizard_frame.pack_forget()
        if self.viewer_frame:
            self.viewer_frame.pack_forget()

    # ── Wizard builder ──────────────────────────────────────────

    def _build_wizard(self, character, save_path=None):
        """Create the wizard frame containing notebook + summary panel."""
        frame = ttk.Frame(self.container)

        # Top bar with back button + save/export buttons
        top = ttk.Frame(frame)
        top.pack(fill=tk.X, padx=8, pady=(6, 2))
        ttk.Button(
            top, text="\u25c0  Back to Menu",
            command=self.show_home,
        ).pack(side=tk.LEFT)

        ttk.Button(
            top, text="Save & Finish",
            style="Accent.TButton",
            command=self._save_and_finish,
        ).pack(side=tk.LEFT, padx=12)

        ttk.Button(top, text="Export JSON",
                   command=self._export_json).pack(side=tk.LEFT, padx=4)

        ttk.Button(top, text="Export PDF",
                   command=self._export_pdf).pack(side=tk.LEFT, padx=4)

        if character.character_class and character.level < 20:
            ttk.Button(
                top, text="Level Up",
                style="Accent.TButton",
                command=self._on_level_up,
            ).pack(side=tk.LEFT, padx=4)

        # Main horizontal split: notebook (left) + summary (right)
        paned = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        notebook = ttk.Notebook(paned)
        summary = SummaryPanel(paned, character)

        paned.add(notebook, weight=3)
        paned.add(summary, weight=1)

        # Create wizard steps
        steps = [
            SpeciesStep(notebook, character, self.data),
            ClassStep(notebook, character, self.data),
            BackgroundStep(notebook, character, self.data),
            AbilityScoresStep(notebook, character, self.data),
            FeatStep(notebook, character, self.data),
            SpellsStep(notebook, character, self.data),
            EquipmentStep(notebook, character, self.data),
            SummaryStep(notebook, character, self.data,
                        app=self, save_path=save_path),
        ]

        # Store references for level-up refresh
        self._wizard_notebook = notebook
        self._wizard_steps = steps
        self._wizard_summary = summary

        # Register change callbacks
        for step in steps:
            step.on_change_callbacks.append(summary.refresh)

        # Tab change event
        def on_tab_change(event):
            idx = notebook.index(notebook.select())
            if 0 <= idx < len(steps):
                steps[idx].on_enter()

        notebook.bind("<<NotebookTabChanged>>", on_tab_change)

        return frame

    # ── Level Up ──────────────────────────────────────────────

    def _on_level_up(self):
        if not self.character or not self.character.character_class:
            return
        from gui.level_up_wizard import LevelUpWizard

        def on_complete():
            # Refresh the wizard UI (no save — user must click Save & Finish)
            self._wizard_summary.refresh()
            try:
                idx = self._wizard_notebook.index(self._wizard_notebook.select())
                if 0 <= idx < len(self._wizard_steps):
                    self._wizard_steps[idx].on_enter()
            except Exception:
                pass

        LevelUpWizard(self.wizard_frame, self.character, self.data,
                      on_complete=on_complete)

    # ── Save & Export ──────────────────────────────────────────

    def _save_and_finish(self):
        if not self.character or not self.character.name or self.character.name == "New Character":
            messagebox.showwarning("Name Required",
                                   "Please enter a character name on the Summary tab before saving.")
            return

        from models.character_store import save_character
        from paths import characters_dir

        path = save_character(self.character, characters_dir(), self.current_save_path)
        self.current_save_path = path
        self.show_home()

    def _export_json(self):
        if not self.character:
            return
        from export.json_export import export_json
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"{self.character.name}.json",
        )
        if path:
            export_json(self.character, path)
            messagebox.showinfo("Export", f"Character saved to {path}")

    def _export_pdf(self):
        if not self.character:
            return
        from export.pdf_export import export_pdf
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"{self.character.name}.pdf",
        )
        if path:
            try:
                export_pdf(self.character, path)
                messagebox.showinfo("Export", f"PDF character sheet saved to {path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to generate PDF:\n{e}")

    def run(self):
        self.root.mainloop()
