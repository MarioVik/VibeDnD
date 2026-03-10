"""Main application: screen manager for home, wizard and viewer screens."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from gui.theme import apply_theme, COLORS, FONTS
from gui.data_loader import GameData
from gui.widgets import ScrollableFrame, WrappingLabel, AlertDialog
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
        """Create the wizard frame containing the step notebook."""
        frame = ttk.Frame(self.container)

        # Top bar with back button + save/export buttons
        top = ttk.Frame(frame)
        top.pack(fill=tk.X, padx=8, pady=(6, 2))
        if save_path:
            # Edit mode: go back to the character viewer
            back_text = "\u25c0  Back to Character"
            back_cmd = lambda: self.show_viewer(character, save_path)
        else:
            # New character: go back to home
            back_text = "\u25c0  Back to Menu"
            back_cmd = self.show_home

        ttk.Button(
            top, text=back_text,
            command=back_cmd,
        ).pack(side=tk.LEFT)

        ttk.Button(
            top, text="Save & Finish",
            style="Accent.TButton",
            command=self._save_and_finish,
        ).pack(side=tk.LEFT, padx=12)

        # Navigation buttons at bottom
        self.nav_frame = ttk.Frame(frame, padding=(12, 12))
        self.nav_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.back_btn = ttk.Button(self.nav_frame, text="\u25c0  Back", command=self._wizard_back)
        self.back_btn.pack(side=tk.LEFT)
        
        self.next_btn = ttk.Button(self.nav_frame, text="Next  \u25b6", style="Accent.TButton", command=self._wizard_next)
        self.next_btn.pack(side=tk.RIGHT)

        # Notebook for wizard steps
        self.wizard_notebook = ttk.Notebook(frame)
        self.wizard_notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Create wizard steps
        self.wizard_steps = [
            SpeciesStep(self.wizard_notebook, character, self.data),
            ClassStep(self.wizard_notebook, character, self.data),
            BackgroundStep(self.wizard_notebook, character, self.data),
            AbilityScoresStep(self.wizard_notebook, character, self.data),
            FeatStep(self.wizard_notebook, character, self.data),
            SpellsStep(self.wizard_notebook, character, self.data),
            EquipmentStep(self.wizard_notebook, character, self.data),
            SummaryStep(self.wizard_notebook, character, self.data,
                        app=self, save_path=save_path),
        ]
        
        # Add on_change callback to ClassStep index (1) to toggle spells tab
        self.wizard_steps[1].on_change_callbacks.append(self._update_spells_visibility)

        # Hide all except first initially if new character
        if not save_path:
            for i in range(1, len(self.wizard_steps)):
                self.wizard_notebook.tab(i, state="hidden")
        
        # Initial spells visibility check
        self._update_spells_visibility()

        # Tab change event
        def on_tab_change(event):
            idx = self.wizard_notebook.index(self.wizard_notebook.select())
            if 0 <= idx < len(self.wizard_steps):
                self.wizard_steps[idx].on_enter()
                # discovery
                self.wizard_notebook.tab(idx, state="normal")
                self._update_nav_buttons()

        self.wizard_notebook.bind("<<NotebookTabChanged>>", on_tab_change)
        self._update_nav_buttons()

        return frame

    def _update_spells_visibility(self):
        """Hide or show the spells tab based on caster status."""
        if not hasattr(self, 'wizard_notebook'):
            return
        
        SPELLS_INDEX = 5
        curr = self.wizard_notebook.index(self.wizard_notebook.select())
        
        if self.character.is_caster:
            # Only show if they have reached this step or are in edit mode
            if self.current_save_path:
                self.wizard_notebook.tab(SPELLS_INDEX, state="normal")
        else:
            self.wizard_notebook.tab(SPELLS_INDEX, state="hidden")
            # If we were on the spells tab somehow, move back
            if curr == SPELLS_INDEX:
                self.wizard_notebook.select(4)

    def _wizard_next(self):
        curr = self.wizard_notebook.index(self.wizard_notebook.select())
        if curr < len(self.wizard_steps) - 1:
            next_idx = curr + 1
            
            # Skip Spells tab if not a caster
            if next_idx == 5 and not self.character.is_caster:
                next_idx += 1
            
            if next_idx < len(self.wizard_steps):
                self.wizard_notebook.tab(next_idx, state="normal")
                self.wizard_notebook.select(next_idx)

    def _wizard_back(self):
        curr = self.wizard_notebook.index(self.wizard_notebook.select())
        if curr > 0:
            prev_idx = curr - 1
            
            # Skip Spells tab if not a caster
            if prev_idx == 5 and not self.character.is_caster:
                prev_idx -= 1
            
            if prev_idx >= 0:
                self.wizard_notebook.select(prev_idx)

    def _update_nav_buttons(self):
        curr = self.wizard_notebook.index(self.wizard_notebook.select())
        self.back_btn.configure(state=tk.NORMAL if curr > 0 else tk.DISABLED)
        
        if curr == len(self.wizard_steps) - 1:
            self.next_btn.configure(text="Finish \u2713", command=self._save_and_finish)
        else:
            self.next_btn.configure(text="Next  \u25b6", command=self._wizard_next)


    # ── Save & Export ──────────────────────────────────────────

    def _save_and_finish(self):
        if not self.character or not self.character.name or self.character.name == "New Character":
            AlertDialog(self.root, "Name Required",
                        "Please enter a character name on the Summary tab before saving.")
            return

        from models.character_store import save_character
        from paths import characters_dir

        path = save_character(self.character, characters_dir(), self.current_save_path)
        self.current_save_path = path

        if self.current_save_path:
            # Edit mode: return to the character viewer
            self.show_viewer(self.character, self.current_save_path)
        else:
            self.show_home()

    def _export_json(self):
        if not self.character:
            return
        from models.character_store import character_to_save_dict
        import json
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"{self.character.name}.json",
        )
        if path:
            data = character_to_save_dict(self.character)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            AlertDialog(self.root, "Export", f"Character saved to {path}")

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
                AlertDialog(self.root, "Export", f"PDF character sheet saved to {path}")
            except Exception as e:
                AlertDialog(self.root, "Export Error", f"Failed to generate PDF:\n{e}")

    def run(self):
        self.root.mainloop()
