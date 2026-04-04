"""Main application: screen manager for home, wizard and viewer screens."""

import tkinter as tk
from tkinter import ttk, filedialog

from gui.theme import apply_theme, COLORS, FONTS, SPACING
from gui.data_loader import GameData
from gui.sidebar import WizardSidebar
from gui.widgets import AlertDialog, ConfirmDialog, HPBar

from gui.step_species import SpeciesStep
from gui.step_class import ClassStep
from gui.step_background import BackgroundStep
from gui.step_languages import LanguagesStep
from gui.step_skills import SkillsStep
from gui.step_class_features import ClassFeaturesStep
from gui.step_ability_scores import AbilityScoresStep
from gui.step_feat import FeatStep
from gui.step_spells import SpellsStep
from gui.step_equipment import EquipmentStep
from gui.step_biography import BiographyStep
from gui.step_summary import SummaryStep
from models.level1_class_rules import (
    get_effective_cantrips_known,
    get_effective_prepared_spells,
    get_unmet_level1_class_requirements,
    requires_level1_class_features_step,
)
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
    ("class_features", "Class Features", "", ClassFeaturesStep),
    ("equipment", "Equipment", "", EquipmentStep),
    ("spells", "Spells", "", SpellsStep),
    ("languages", "Languages", "", LanguagesStep),
    ("biography", "Biography", "", BiographyStep),
    ("summary", "Summary", "", SummaryStep),
]
_WIZARD_STEP_LABELS = {key: label for key, label, _, _ in _WIZARD_STEPS}

# Labels for the wizard's primary confirm action
_CONFIRM_STEP_LABELS = {
    "species": "Confirm Species Choice",
    "class": "Confirm Class Choice",
    "background": "Confirm Background Choice",
    "feat": "Confirm Feat Choice",
    "abilities": "Confirm Ability Scores",
    "skills": "Confirm Skills",
    "class_features": "Confirm Class Features",
    "equipment": "Confirm Equipment",
    "spells": "Confirm Spells",
    "languages": "Confirm Languages",
    "biography": "Confirm Biography",
    "summary": "Summary",
}
_DYNAMIC_PRIMARY_ACTION_LABELS = ["Confirm Expertise"]


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
            style="WizardAccent.TButton",
            command=self._wizard_next,
        )
        self._next_btn.pack(side=tk.RIGHT)
        candidate_next_labels = (
            ["Finish \u2713"]
            + list(_CONFIRM_STEP_LABELS.values())
            + _DYNAMIC_PRIMARY_ACTION_LABELS
        )
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
        self._reached_step_keys = set()

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

        if save_path:
            self._reached_step_keys = set(self._step_keys)
        else:
            self._reached_step_keys = {self._step_keys[0]}

        # Register callbacks
        self.wizard_steps[0].on_change_callbacks.append(self._update_optional_step_visibility)
        self.wizard_steps[1].on_change_callbacks.append(self._update_optional_step_visibility)
        for step in self.wizard_steps:
            step.on_change_callbacks.append(self._update_nav_buttons)

        # Register substep change callbacks for every step so dynamic substep
        # steps can start emitting them later as character choices evolve.
        for step in self.wizard_steps:
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
            on_back=self._cancel_wizard,
            width=224,
        )
        self._wizard_sidebar.pack(side=tk.LEFT, fill=tk.Y)

        # Pack content after sidebar
        content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Initial state
        self._update_optional_step_visibility()
        self._show_step(self._step_index(self._visible_step_keys()[0]))

        return frame

    def _on_sidebar_nav(self, key: str):
        """Handle sidebar click — only allow navigating to reached steps."""
        if key not in self._step_keys:
            return

        if key not in self._reached_step_keys:
            return

        if not self._is_step_visible_key(key):
            return

        idx = self._step_index(key)

        # If navigating to a step with substeps that has a selection, show detail
        step = self.wizard_steps[idx]
        if step.has_substeps():
            if step.is_valid():
                step.go_to_substep(self._last_available_substep_index(step))
            else:
                step.go_to_substep(0)

        self._show_step(idx)

    def _last_available_substep_index(self, step) -> int:
        """Return the deepest currently-available substep index for a step."""
        return max(0, step.get_substep_count() - 1)

    def _step_index(self, key: str) -> int:
        return self._step_keys.index(key)

    def _ordered_step_keys(self) -> list[str]:
        """Return the current wizard order before visibility filtering."""
        keys = list(self._step_keys)
        slug = str((self.character.character_class or {}).get("slug", "") or "")
        if slug == "warlock" and "class_features" in keys and "spells" in keys:
            keys.remove("class_features")
            keys.insert(keys.index("spells") + 1, "class_features")
        return keys

    def _get_sidebar_step_title(self, key: str) -> str:
        """Return the current sidebar title text for a wizard step."""
        base_label = _WIZARD_STEP_LABELS.get(key, key.title())
        current_key = self._step_keys[self._current_step_idx]
        if current_key != key:
            return base_label

        step = self.wizard_steps[self._step_index(key)]
        return step.get_sidebar_title() or base_label

    def _update_sidebar_titles(self):
        """Refresh dynamic sidebar titles such as Skills substep counters."""
        if not hasattr(self, "_wizard_sidebar"):
            return

        for step_key in self._step_keys:
            self._wizard_sidebar.set_nav_text(
                step_key,
                self._get_sidebar_step_title(step_key),
            )

    def _show_step(self, idx: int):
        """Show the step at the given index, hiding the current one."""
        if 0 <= self._current_step_idx < len(self.wizard_steps):
            self.wizard_steps[self._current_step_idx].frame.pack_forget()

        self._current_step_idx = idx
        self._reached_step_keys.add(self._step_keys[idx])
        step = self.wizard_steps[idx]
        step.frame.pack(fill=tk.BOTH, expand=True)
        step.on_enter()

        self._update_sidebar_state()
        self._update_nav_buttons()

    def _update_sidebar_state(self):
        """Update sidebar step states and per-step selections."""
        if not hasattr(self, "_wizard_sidebar"):
            return

        self._update_sidebar_titles()
        idx = self._current_step_idx
        visible_keys = self._visible_step_keys()
        current_key = self._step_keys[idx]
        self._wizard_sidebar.update_step_states(
            visible_keys,
            current_key,
            self._reached_step_keys,
        )
        deferred_choice_steps = {"species", "class", "background"}
        if self._feat_selection_required():
            deferred_choice_steps.add("feat")

        visible_key_set = set(visible_keys)
        for step_key in self._step_keys:
            if step_key not in visible_key_set or step_key not in self._reached_step_keys:
                self._wizard_sidebar.set_selection(step_key, "")
                continue
            value = self._get_sidebar_selection_text(step_key)
            if step_key == current_key and step_key in deferred_choice_steps:
                value = "Currently Editing"
            elif step_key == current_key and not value:
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

        if key == "class_features":
            return (
                not requires_level1_class_features_step(self.character, self.data)
                or self.wizard_steps[self._step_keys.index(key)].is_valid()
            )

        if key == "equipment":
            return self.wizard_steps[self._step_keys.index(key)].is_valid()

        if key == "spells":
            return self.wizard_steps[self._step_keys.index(key)].is_valid()

        if key == "languages":
            return self.wizard_steps[self._step_keys.index(key)].is_valid()

        if key == "biography":
            return self.wizard_steps[self._step_keys.index(key)].is_valid()

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

    def _is_step_visible_key(self, key: str) -> bool:
        """Return whether a wizard step should currently be visible."""
        if key == "feat":
            return self._feat_selection_required()
        if key == "class_features":
            return requires_level1_class_features_step(self.character, self.data)
        if key == "spells":
            return self.character.is_caster
        return True

    def _is_step_visible(self, idx: int) -> bool:
        """Return whether a wizard step should currently be visible."""
        return self._is_step_visible_key(self._step_keys[idx])

    def _next_visible_step_index(self, idx: int) -> int | None:
        """Return the next visible step index after idx."""
        current_key = self._step_keys[idx]
        visible_keys = self._visible_step_keys()
        if current_key not in visible_keys:
            return None
        next_pos = visible_keys.index(current_key) + 1
        if next_pos >= len(visible_keys):
            return None
        return self._step_index(visible_keys[next_pos])

    def _previous_visible_step_index(self, idx: int) -> int | None:
        """Return the previous visible step index before idx."""
        current_key = self._step_keys[idx]
        visible_keys = self._visible_step_keys()
        if current_key not in visible_keys:
            return None
        prev_pos = visible_keys.index(current_key) - 1
        if prev_pos < 0:
            return None
        return self._step_index(visible_keys[prev_pos])

    def _visible_step_indices(self) -> list[int]:
        """Return the list of currently visible wizard step indices."""
        return [self._step_index(key) for key in self._visible_step_keys()]

    def _visible_step_keys(self) -> list[str]:
        """Return the list of currently visible wizard step keys in active order."""
        return [
            key
            for key in self._ordered_step_keys()
            if self._is_step_visible_key(key)
        ]

    def _update_optional_step_visibility(self):
        """Hide or show optional wizard steps such as feat and spells."""
        if not hasattr(self, "_wizard_sidebar"):
            return

        self._update_sidebar_titles()
        for key in self._step_keys:
            btn = self._wizard_sidebar._nav_buttons.get(key)
            if not btn:
                continue
            btn.pack_forget()
        for key in self._visible_step_keys():
            btn = self._wizard_sidebar._nav_buttons.get(key)
            if btn:
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

    def _confirm_cancel_wizard(self) -> bool:
        """Confirm leaving the wizard and discarding unsaved progress."""
        title = "Cancel Character Creation"
        message = (
            "Cancel character creation and leave The Forge?\n\n"
            "All unsaved progress will be lost."
        )
        if self.current_save_path:
            title = "Cancel Character Editing"
            message = (
                "Cancel your changes and leave The Forge?\n\n"
                "All unsaved progress will be lost."
            )

        dlg = ConfirmDialog(self.root, title, message)
        return dlg.result

    def _cancel_wizard(self):
        """Leave the wizard after confirming any unsaved progress loss."""
        if not self._confirm_cancel_wizard():
            return

        if self.current_save_path:
            from models.character_store import load_character

            try:
                character = load_character(self.current_save_path, self.data)
            except Exception as exc:
                AlertDialog(
                    self.root,
                    "Cancel Failed",
                    "The saved character could not be reloaded, so your current "
                    f"changes were kept open.\n\n{exc}",
                )
                return

            self.show_viewer(character, self.current_save_path)
            return

        self.show_home()

    def _wizard_next(self):
        curr = self._current_step_idx
        step = self.wizard_steps[curr]

        # Handle substep advancement (grid -> detail)
        if step.has_substeps() and step.get_current_substep() < step.get_substep_count() - 1:
            if not step.is_current_substep_valid():
                self._show_validation_error(step)
                return
            step.go_to_substep(step.get_current_substep() + 1)
            self._update_nav_buttons()
            return

        if not step.is_valid():
            self._show_validation_error(step)
            return

        next_idx = self._next_visible_step_index(curr)

        if next_idx is not None:
            self._reached_step_keys.add(self._step_keys[next_idx])
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
                    prev_step.go_to_substep(self._last_available_substep_index(prev_step))
                self._show_step(prev_idx)

    def _show_validation_error(self, step):
        """Show context-specific validation error for the current step."""
        if isinstance(step, SkillsStep):
            sources = compute_skill_sources(self.character)
            chosen = len(self.character.selected_skills)
            needed = sources["choose_count"]
            skill_word = "skill" if needed == 1 else "skills"
            expertise_needed = sources["expertise_choose_count"]
            expertise_chosen = sources["expertise_chosen_count"]
            expertise_word = "selection" if expertise_needed == 1 else "selections"
            parts = []
            current_substep = step.get_current_substep()
            is_split = step.get_substep_count() > 1
            show_skills = not is_split or current_substep == 0
            show_expertise = not is_split or current_substep > 0
            if needed and show_skills:
                parts.append(
                    f"Choose {needed} class {skill_word} before moving on. "
                    f"({chosen}/{needed} selected)"
                )
            if expertise_needed and show_expertise:
                parts.append(
                    f"Choose {expertise_needed} Expertise {expertise_word} as well. "
                    f"({expertise_chosen}/{expertise_needed} selected)"
                )
            message = "\n\n".join(parts) if parts else "Complete your skill selections before moving on."
            AlertDialog(
                self.root,
                "Skill Selection Required",
                message,
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
            blockers = get_unmet_level1_class_requirements(
                self.character,
                self.data,
                step_key="spells",
            )
            cantrip_max = get_effective_cantrips_known(self.character)
            spell_max = get_effective_prepared_spells(self.character)
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
        elif isinstance(step, ClassFeaturesStep):
            blockers = step.get_current_substep_requirements()
            body = "\n\n".join(blocker["message"] for blocker in blockers) or (
                "Resolve the required level-1 class feature choices before moving on."
            )
            AlertDialog(self.root, "Class Feature Selection Required", body)
        elif isinstance(step, EquipmentStep):
            blockers = get_unmet_level1_class_requirements(
                self.character,
                self.data,
                step_key="equipment",
            )
            body = blockers[0]["message"] if blockers else "Choose your starting equipment before moving on."
            AlertDialog(self.root, "Equipment Selection Required", body)
        elif isinstance(step, BiographyStep):
            AlertDialog(
                self.root,
                "Character Name Required",
                "Enter a character name before moving on.",
            )

    def _first_invalid_visible_step_index(self) -> int | None:
        summary_idx = self._step_keys.index("summary")
        for idx in self._visible_step_indices():
            if idx == summary_idx:
                continue
            if not self.wizard_steps[idx].is_valid():
                return idx
        return None

    def _all_visible_steps_valid(self) -> bool:
        return self._first_invalid_visible_step_index() is None

    def _update_nav_buttons(self):
        curr = self._current_step_idx
        step = self.wizard_steps[curr]
        key = self._step_keys[curr]
        self._update_sidebar_titles()
        visible_indices = self._visible_step_indices()
        is_last_visible_step = bool(visible_indices) and curr == visible_indices[-1]

        # Back button: hide it when there's nowhere to go back to
        can_go_back = (
            self._previous_visible_step_index(curr) is not None
            or (step.has_substeps() and step.get_current_substep() > 0)
        )
        if can_go_back:
            self._back_btn.configure(state=tk.NORMAL)
            if not self._back_btn.winfo_manager():
                self._back_btn.pack(side=tk.LEFT)
        elif self._back_btn.winfo_manager():
            self._back_btn.pack_forget()

        show_primary_action = is_last_visible_step or step.is_primary_action_visible()
        if show_primary_action:
            if not self._next_btn.winfo_manager():
                self._next_btn.pack(side=tk.RIGHT)
        elif self._next_btn.winfo_manager():
            self._next_btn.pack_forget()

        if is_last_visible_step:
            is_valid = self._all_visible_steps_valid()
            self._next_btn.configure(
                text="Finish \u2713",
                command=self._save_and_finish,
                state=tk.NORMAL if is_valid else tk.DISABLED,
            )
        elif show_primary_action:
            confirm_label = step.get_primary_action_label() or _CONFIRM_STEP_LABELS.get(
                key, "Confirm"
            )
            self._next_btn.configure(
                text=confirm_label,
                command=self._wizard_next,
                state=(
                    tk.NORMAL if step.is_primary_action_enabled() else tk.DISABLED
                ),
            )

        # Update step counter and progress bar
        visible_count = len(visible_indices)
        visible_idx = visible_indices.index(curr) if curr in visible_indices else 0
        self._step_label.configure(text=f"Step {visible_idx + 1} of {visible_count}")
        self._progress_bar.set_hp(visible_idx + 1, visible_count)

    # ── Save & Export ──────────────────────────────────────────

    def _save_and_finish(self):
        invalid_idx = self._first_invalid_visible_step_index()
        if invalid_idx is not None:
            self._show_step(invalid_idx)
            self._show_validation_error(self.wizard_steps[invalid_idx])
            return

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
            self.show_archive()
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
