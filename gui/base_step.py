"""Abstract base class for wizard steps."""

import tkinter as tk
from tkinter import ttk
from abc import ABC, abstractmethod


class WizardStep(ABC):
    """Abstract base for each page in the character creation wizard."""

    tab_title: str = "Step"

    def __init__(self, parent_notebook: ttk.Notebook, character, game_data):
        self.notebook = parent_notebook
        self.character = character
        self.data = game_data
        self.frame = ttk.Frame(parent_notebook)
        self.on_change_callbacks = []
        self.build_ui()
        parent_notebook.add(self.frame, text=f" {self.tab_title} ")

    @abstractmethod
    def build_ui(self):
        """Create the widgets for this step."""

    def on_enter(self):
        """Called when user navigates to this step. Override to refresh."""
        pass

    def notify_change(self):
        """Notify that character data changed (update summary panel etc)."""
        for cb in self.on_change_callbacks:
            cb()
