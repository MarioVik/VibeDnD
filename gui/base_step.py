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
