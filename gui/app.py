"""Main application: screen manager for home, wizard and viewer screens."""

import tkinter as tk
from tkinter import ttk, filedialog

from gui.theme import apply_theme, COLORS, FONTS, SPACING
from gui.data_loader import GameData
from gui.sidebar import WizardSidebar
from gui.widgets import AlertDialog, HPBar

from gui.step_species import SpeciesStep
from gui.step_class import ClassStep
from gui.step_background import BackgroundStep
from gui.step_languages import LanguagesStep
from gui.step_skills import SkillsStep
from gui.step_ability_scores import AbilityScoresStep
from gui.step_feat import FeatStep
from gui.step_spells import SpellsStep
from gui.step_equipment import EquipmentStep
from gui.step_biography import BiographyStep
from gui.step_summary import SummaryStep
from models.language_utils import compute_language_sources
from models.skill_utils import compute_skill_sources

from gui.home_screen import HomeScreen
from gui.character_viewer import CharacterViewer

# Wizard step definitions: (key, label, icon, StepClass)
_WIZARD_STEPS = [
    ("species", "Species", "", SpeciesStep),
    ("class", "Class", "", ClassStep),
    ("background", "Background", "", BackgroundStep),
    ("feat", "Feat", "", FeatStep),
    ("abilities", "Ability Scores", "", AbilityScoresStep),
    ("skills", "Skills", "", SkillsStep),
    ("equipment", "Equipment", "", EquipmentStep),
    ("spells", "Spells", "", SpellsStep),
    ("languages", "Languages", "", LanguagesStep),
    ("biography", "Biography", "", BiographyStep),
    ("summary", "Summary", "", SummaryStep),
]

FEAT_INDEX = 3  # index of feat step in _WIZARD_STEPS
SPELLS_INDEX = 7  # index of spells step in _WIZARD_STEPS

# Labels for the wizard's primary confirm action
_CONFIRM_STEP_LABELS = {
    "species": "Confirm Species Choice",
    "class": "Confirm Class Choice",
    "background": "Confirm Background Choice",
    "feat": "Confirm Feat Choice",
    "abilities": "Confirm Ability Scores",
    "skills": "Confirm Skills",
    "equipment": "Confirm Equipment",
    "spells": "Confirm Spells",
    "languages": "Confirm Languages",
    "biography": "Confirm Biography",
    "summary": "Summary",
}


class CharacterCreatorApp:
    """Main application window with screen management."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("VibeDnD \u2014 D&D 2024 Character Creator")
        self.root.geometry("1600x1050")
        self.root.minsize(1100, 750)

        apply_theme(self.root)
        self.data = GameData()

        # Container for all screens
        self.container = ttk.Frame(self.root)
        self.container.pack(fill=tk.BOTH, expand=True)

        # Screen references
        self.home_screen = HomeScreen(self.container, self)
        self.wizard_frame = None
        self.viewer_frame = None

        # State
        self.character = None
        self.current_save_path = None

        # Start on home screen
        self.show_home()

    # ── Screen transitions ──────────────────────────────────────

    def show_home(self):
        """Switch to the landing screen."""
        self._hide_all()
        self.home_screen.show_landing()
        self.home_screen.frame.pack(fill=tk.BOTH, expand=True)

    def show_archive(self):
        """Switch to the saved-character archive."""
        self._hide_all()
        self.home_screen.show_archive()
        self.home_screen.frame.pack(fill=tk.BOTH, expand=True)

    def show_wizard(self, character=None, save_path=None):
        """Switch to the character creation wizard."""
        self._hide_all()

        if character is None:
            from models.character import Character
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
            self.container, character, save_path, self.data, self
        )
        self.viewer_frame.pack(fill=tk.BOTH, expand=True)

    def _hide_all(self):
        self.home_screen.frame.pack_forget()
        if self.wizard_frame:
            self.wizard_frame.pack_forget()
        if self.viewer_frame:
            self.viewer_frame.pack_forget()

    # ── Wizard builder ──────────────────────────────────────────

    def _build_wizard(self, character, save_path=None):
        """Create the wizard with sidebar step navigation."""
        frame = tk.Frame(self.container, bg=COLORS["bg"])

        # -- Content area (right side) --
        content_area = tk.Frame(frame, bg=COLORS["bg"])

        # Bottom nav bar (pack FIRST so it claims space)
        nav_bar = tk.Frame(
            content_area,
            bg=COLORS["bg_surface"],
            highlightbackground=COLORS["border_subtle"],
            highlightcolor=COLORS["border_subtle"],
            highlightthickness=1,
        )
        nav_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # Step content container
        self._step_container = tk.Frame(content_area, bg=COLORS["bg"])
        self._step_container.pack(fill=tk.BOTH, expand=True)

        # ---- Build bottom nav bar ----
        nav_inner = tk.Frame(nav_bar, bg=COLORS["bg_surface"])
        nav_inner.pack(fill=tk.X, padx=SPACING["lg"], pady=10)

        # Left section: Previous
        left_frame = tk.Frame(nav_inner, bg=COLORS["bg_surface"])
        left_frame.pack(side=tk.LEFT)

        if save_path:
            cancel_cmd = lambda: self.show_viewer(character, save_path)
        else:
            cancel_cmd = self.show_home

        self._back_btn = ttk.Button(
            left_frame,
            text="\u25c0  Back",
            command=self._wizard_back,
        )
        self._back_btn.pack(side=tk.LEFT)
        left_frame.update_idletasks()
        left_frame.configure(
            width=self._back_btn.winfo_reqwidth(),
            height=self._back_btn.winfo_reqheight(),
        )
        left_frame.pack_propagate(False)

        # Center section: Step counter + progress bar
        center_frame = tk.Frame(nav_inner, bg=COLORS["bg_surface"])
        center_frame.pack(side=tk.LEFT, expand=True)

        center_inner = tk.Frame(center_frame, bg=COLORS["bg_surface"])
        center_inner.pack()

        self._step_label = tk.Label(
            center_inner,
            text="Step 1 of 11",
            font=FONTS["step_counter"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        )
        self._step_label.pack(side=tk.LEFT, padx=(0, SPACING["md"]))

        # Progress bar
        self._progress_bar = HPBar(center_inner, width=160, height=6)
        self._progress_bar.pack(side=tk.LEFT)

        # Right section: Next button
        right_frame = tk.Frame(nav_inner, bg=COLORS["bg_surface"])
        right_frame.pack(side=tk.RIGHT)

        self._next_btn = ttk.Button(
            right_frame,
            text="Next  \u25b6",
            style="Accent.TButton",
            command=self._wizard_next,
        )
        self._next_btn.pack(side=tk.RIGHT)
        candidate_next_labels = ["Finish \u2713"] + list(_CONFIRM_STEP_LABELS.values())
        original_next_text = self._next_btn.cget("text")
        max_next_width = 0
        for label in candidate_next_labels:
            self._next_btn.configure(text=label)
            right_frame.update_idletasks()
            max_next_width = max(max_next_width, self._next_btn.winfo_reqwidth())
        self._next_btn.configure(text=original_next_text)
        right_frame.configure(
            width=max_next_width,
            height=self._next_btn.winfo_reqheight(),
        )
        right_frame.pack_propagate(False)

        # -- Create wizard steps --
        self.wizard_steps = []
        self._step_keys = []
        self._current_step_idx = 0
        self._reached_step = 0 if not save_path else len(_WIZARD_STEPS) - 1

        for key, label, icon, StepClass in _WIZARD_STEPS:
            if StepClass is SummaryStep:
                step = StepClass(
                    self._step_container, character, self.data,
                    app=self, save_path=save_path,
                )
            else:
                step = StepClass(self._step_container, character, self.data)
            self.wizard_steps.append(step)
            self._step_keys.append(key)

        # Register callbacks
        self.wizard_steps[0].on_change_callbacks.append(self._update_optional_step_visibility)
        self.wizard_steps[1].on_change_callbacks.append(self._update_optional_step_visibility)
        for step in self.wizard_steps:
            step.on_change_callbacks.append(self._update_nav_buttons)

        # Register substep change callbacks for steps with substeps
        for step in self.wizard_steps:
            if step.has_substeps():
                step.on_substep_change_callbacks.append(self._update_nav_buttons)
                step.on_substep_change_callbacks.append(self._update_sidebar_state)

        # -- Sidebar (left side) --
        nav_items = []
        for key, label, icon, _ in _WIZARD_STEPS:
            nav_items.append({"key": key, "text": label, "icon": icon})

        self._wizard_sidebar = WizardSidebar(
            frame,
            nav_items=nav_items,
            on_navigate=self._on_sidebar_nav,
            header_title="The Forge",
            on_back=cancel_cmd,
            width=232,
        )
        self._wizard_sidebar.pack(side=tk.LEFT, fill=tk.Y)

        # Pack content after sidebar
        content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Initial state
        self._update_optional_step_visibility()
        self._show_step(0)

        return frame

    def _on_sidebar_nav(self, key: str):
        """Handle sidebar click — only allow navigating to reached steps."""
        try:
            idx = self._step_keys.index(key)
        except ValueError:
            return

        # Don't allow jumping ahead of reached steps
        if idx > self._reached_step:
            return

        if not self._is_step_visible(idx):
            return

        # If navigating to a step with substeps that has a selection, show detail
        step = self.wizard_steps[idx]
        if step.has_substeps():
            if step.is_valid():
                step.go_to_substep(1)
            else:
                step.go_to_substep(0)

        self._show_step(idx)

    def _show_step(self, idx: int):
        """Show the step at the given index, hiding the current one."""
        if 0 <= self._current_step_idx < len(self.wizard_steps):
            self.wizard_steps[self._current_step_idx].frame.pack_forget()

        self._current_step_idx = idx
        step = self.wizard_steps[idx]
        step.frame.pack(fill=tk.BOTH, expand=True)
        step.on_enter()

        self._update_sidebar_state()
        self._update_nav_buttons()

    def _update_sidebar_state(self):
        """Update sidebar step states and per-step selections."""
        if not hasattr(self, "_wizard_sidebar"):
            return

        idx = self._current_step_idx
        self._wizard_sidebar.update_step_states(idx, self._reached_step)
        deferred_choice_steps = {"species", "class", "background"}
        if self._feat_selection_required():
            deferred_choice_steps.add("feat")

        for step_idx, step_key in enumerate(self._step_keys):
            if step_idx > self._reached_step:
                continue
            value = self._get_sidebar_selection_text(step_key)
            if step_idx == idx and step_key in deferred_choice_steps:
                value = "Currently Editing"
            elif step_idx == idx and not value:
                value = "Currently Editing"
            elif not value:
                value = "Selection Required"
            self._wizard_sidebar.set_selection(step_key, value)

    def _get_sidebar_selection_text(self, key: str) -> str:
        """Return the sidebar subtitle for a wizard step."""
        if key == "species":
            species = self.character.species or {}
            return species.get("name", "")

        if key == "class":
            char_class = self.character.character_class or {}
            return char_class.get("name", "")

        if key == "background":
            background = self.character.background or {}
            return background.get("name", "")

        if key == "feat":
            feat = self.character.species_origin_feat or {}
            name = feat.get("name", "")
            if name and self._feat_selection_required():
                return name
            if self._is_sidebar_step_complete(key):
                return "Completed"
            return ""

        if self._is_sidebar_step_complete(key):
            return "Completed"

        return ""

    def _is_sidebar_step_complete(self, key: str) -> bool:
        """Return whether a non-selection sidebar step should show as completed."""
        if key == "feat":
            return not self._feat_selection_required()

        if key == "abilities":
            return self.wizard_steps[self._step_keys.index(key)].is_valid()

        if key == "skills":
            return self.wizard_steps[self._step_keys.index(key)].is_valid()

        if key == "equipment":
            return bool(self.character.character_class or self.character.background)

        if key == "spells":
            return self.wizard_steps[self._step_keys.index(key)].is_valid()

        if key == "languages":
            return self.wizard_steps[self._step_keys.index(key)].is_valid()

        if key == "biography":
            return any(
                [
                    self.character.name and self.character.name != "New Character",
                    self.character.biography_backstory,
                    self.character.biography_personality,
                    self.character.biography_description,
                    self.character.biography_image_data,
                ]
            )

        if key == "summary":
            return self._current_step_idx == self._step_keys.index("summary")

        return False

    def _feat_selection_required(self) -> bool:
        """Return True when the selected species grants an origin feat."""
        species = self.character.species or {}
        for trait in species.get("traits", []):
            if "origin feat" in trait.get("description", "").lower():
                return True
        return False

    def _is_step_visible(self, idx: int) -> bool:
        """Return whether a wizard step should currently be visible."""
        if idx == FEAT_INDEX:
            return self._feat_selection_required()
        if idx == SPELLS_INDEX:
            return self.character.is_caster
        return True

    def _next_visible_step_index(self, idx: int) -> int | None:
        """Return the next visible step index after idx."""
        for next_idx in range(idx + 1, len(self.wizard_steps)):
            if self._is_step_visible(next_idx):
                return next_idx
        return None

    def _previous_visible_step_index(self, idx: int) -> int | None:
        """Return the previous visible step index before idx."""
        for prev_idx in range(idx - 1, -1, -1):
            if self._is_step_visible(prev_idx):
                return prev_idx
        return None

    def _visible_step_indices(self) -> list[int]:
        """Return the list of currently visible wizard step indices."""
        return [idx for idx in range(len(self.wizard_steps)) if self._is_step_visible(idx)]

    def _update_optional_step_visibility(self):
        """Hide or show optional wizard steps such as feat and spells."""
        if not hasattr(self, "_wizard_sidebar"):
            return

        for idx, (key, _, _, _) in enumerate(_WIZARD_STEPS):
            btn = self._wizard_sidebar._nav_buttons.get(key)
            if not btn:
                continue
            btn.pack_forget()
            if self._is_step_visible(idx):
                btn.pack(fill=tk.X, pady=1)

        if not self._is_step_visible(self._current_step_idx):
            fallback_idx = self._previous_visible_step_index(self._current_step_idx)
            if fallback_idx is None:
                fallback_idx = self._next_visible_step_index(self._current_step_idx)
            if fallback_idx is not None:
                self._show_step(fallback_idx)
            return

        self._update_sidebar_state()
        self._update_nav_buttons()

    def _wizard_next(self):
        curr = self._current_step_idx
        step = self.wizard_steps[curr]

        # Handle substep advancement (grid -> detail)
        if step.has_substeps() and step.get_current_substep() < step.get_substep_count() - 1:
            step.go_to_substep(step.get_current_substep() + 1)
            self._update_nav_buttons()
            return

        if not step.is_valid():
            self._show_validation_error(step)
            return

        next_idx = self._next_visible_step_index(curr)

        if next_idx is not None:
            if next_idx > self._reached_step:
                self._reached_step = next_idx
            self._show_step(next_idx)

    def _wizard_back(self):
        curr = self._current_step_idx
        step = self.wizard_steps[curr]

        # Handle substep back (detail -> grid)
        if step.has_substeps() and step.get_current_substep() > 0:
            step.go_to_substep(step.get_current_substep() - 1)
            self._update_nav_buttons()
            return

        if curr > 0:
            prev_idx = self._previous_visible_step_index(curr)

            if prev_idx is not None:
                # When going back to a step with substeps, show detail if it has a selection
                prev_step = self.wizard_steps[prev_idx]
                if prev_step.has_substeps() and prev_step.is_valid():
                    prev_step.go_to_substep(1)
                self._show_step(prev_idx)

    def _show_validation_error(self, step):
        """Show context-specific validation error for the current step."""
        if isinstance(step, SkillsStep):
            sources = compute_skill_sources(self.character)
            chosen = len(self.character.selected_skills)
            needed = sources["choose_count"]
            skill_word = "skill" if needed == 1 else "skills"
            AlertDialog(
                self.root,
                "Skill Selection Required",
                f"Choose {needed} class {skill_word} before moving on. "
                f"({chosen}/{needed} selected)",
            )
        elif isinstance(step, SpeciesStep):
            species_name = (
                self.character.species.get("name", "This species")
                if self.character and self.character.species
                else "This species"
            )
            AlertDialog(
                self.root,
                "Species Choice Required",
                f"{species_name} requires an additional choice before moving on. "
                "Please pick one option in the species details panel.",
            )
        elif isinstance(step, LanguagesStep):
            sources = compute_language_sources(self.character)
            chosen = len(self.character.chosen_languages)
            needed = sources["free_count"]
            lang_word = "language" if needed == 1 else "languages"
            AlertDialog(
                self.root,
                "Language Selection Required",
                f"Choose {needed} {lang_word} before moving on. "
                f"({chosen}/{needed} selected)",
            )
        elif isinstance(step, SpellsStep):
            cls = self.character.character_class or {}
            cantrip_max = cls.get("cantrips_known", 0) or 0
            spell_max = cls.get("spells_prepared", 0) or 0
            cantrip_count = len(self.character.selected_cantrips)
            spell_count = len(self.character.selected_spells)
            parts = []
            if cantrip_max > 0 and cantrip_count < cantrip_max:
                parts.append(f"{cantrip_count}/{cantrip_max} cantrips")
            if spell_max > 0 and spell_count < spell_max:
                parts.append(f"{spell_count}/{spell_max} spells")
            AlertDialog(
                self.root,
                "Spell Selection Required",
                f"Select all your spells before moving on. ({', '.join(parts)} selected)",
            )

    def _update_nav_buttons(self):
        curr = self._current_step_idx
        step = self.wizard_steps[curr]
        key = self._step_keys[curr]

        # Back button: hide it when there's nowhere to go back to
        can_go_back = curr > 0 or (step.has_substeps() and step.get_current_substep() > 0)
        if can_go_back:
            self._back_btn.configure(state=tk.NORMAL)
            if not self._back_btn.winfo_manager():
                self._back_btn.pack(side=tk.LEFT)
        elif self._back_btn.winfo_manager():
            self._back_btn.pack_forget()

        # Species keeps Next clickable; validation handled on click
        if isinstance(step, SpeciesStep):
            is_valid = True
        else:
            is_valid = step.is_valid()

        is_tile_selection_substep = step.has_substeps() and step.get_current_substep() == 0
        if is_tile_selection_substep:
            if self._next_btn.winfo_manager():
                self._next_btn.pack_forget()
        elif not self._next_btn.winfo_manager():
            self._next_btn.pack(side=tk.RIGHT)

        if curr == len(self.wizard_steps) - 1:
            self._next_btn.configure(
                text="Finish \u2713",
                command=self._save_and_finish,
                state=tk.NORMAL if is_valid else tk.DISABLED,
            )
        elif not is_tile_selection_substep:
            confirm_label = _CONFIRM_STEP_LABELS.get(key, "Confirm")
            self._next_btn.configure(
                text=confirm_label,
                command=self._wizard_next,
                state=tk.NORMAL if is_valid else tk.DISABLED,
            )

        # Update step counter and progress bar
        visible_indices = self._visible_step_indices()
        visible_count = len(visible_indices)
        visible_idx = visible_indices.index(curr) if curr in visible_indices else 0
        self._step_label.configure(text=f"Step {visible_idx + 1} of {visible_count}")
        self._progress_bar.set_hp(visible_idx + 1, visible_count)

    # ── Save & Export ──────────────────────────────────────────

    def _save_and_finish(self):
        if (
            not self.character
            or not self.character.name
            or self.character.name == "New Character"
        ):
            AlertDialog(
                self.root,
                "Name Required",
                "Please enter a character name on the Biography tab before saving.",
            )
            return

        from models.character_store import save_character
        from paths import characters_dir

        path = save_character(self.character, characters_dir(), self.current_save_path)
        self.current_save_path = path

        if self.current_save_path:
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
