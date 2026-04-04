"""Abstract base class for wizard steps."""

import tkinter as tk
from tkinter import ttk
from abc import ABC, abstractmethod

from gui.theme import COLORS


class WizardStep(ABC):
    """Abstract base for each page in the character creation wizard.

    Supports both legacy notebook parents and plain frame parents.
    When the parent is a ttk.Notebook, the step auto-adds itself as a tab.
    When the parent is a plain frame, the step creates its frame but does
    not pack/grid it — the caller manages visibility.
    """

    tab_title: str = "Step"

    def __init__(self, parent, character, game_data):
        self.character = character
        self.data = game_data
        self.on_change_callbacks = []
        self.on_substep_change_callbacks = []

        if isinstance(parent, ttk.Notebook):
            # Legacy notebook mode
            self.notebook = parent
            self.frame = tk.Frame(parent, bg=COLORS["bg"])
            self.build_ui()
            parent.add(self.frame, text=f" {self.tab_title} ")
        else:
            # Frame-based mode (new sidebar wizard)
            self.notebook = None
            self.frame = tk.Frame(parent, bg=COLORS["bg"])
            self.build_ui()

    @abstractmethod
    def build_ui(self):
        """Create the widgets for this step."""

    def on_enter(self):
        """Called when user navigates to this step. Override to refresh."""
        pass

    def is_valid(self) -> bool:
        """Return True if the step is complete and valid."""
        return True

    def notify_change(self):
        """Notify that character data changed (update summary panel etc)."""
        for cb in self.on_change_callbacks:
            cb()

    # ── Substep protocol (override in steps with grid+detail views) ──

    def has_substeps(self) -> bool:
        """Return True if this step has internal substeps (grid + detail)."""
        return False

    def get_current_substep(self) -> int:
        """Return the current substep index (0-based)."""
        return 0

    def get_substep_count(self) -> int:
        """Return the total number of substeps."""
        return 1

    def go_to_substep(self, index: int):
        """Navigate to the given substep index."""
        pass

    def get_next_label(self) -> str | None:
        """Return contextual label for the Next button, or None for default."""
        return None

    def is_primary_action_visible(self) -> bool:
        """Return whether the primary action should be shown on this substep."""
        return not (self.has_substeps() and self.get_current_substep() == 0)

    def is_primary_action_enabled(self) -> bool:
        """Return whether the primary action button should be enabled."""
        return self.is_valid()

    def is_current_substep_valid(self) -> bool:
        """Return whether the current substep is complete enough to advance."""
        return self.is_valid()

    def get_primary_action_label(self) -> str | None:
        """Return a contextual label for the primary action, or None for default."""
        return None

    def notify_substep_change(self):
        """Notify that the substep changed (update nav bar etc)."""
        for cb in self.on_substep_change_callbacks:
            cb()
