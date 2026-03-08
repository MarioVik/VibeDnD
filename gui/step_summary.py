"""Step 8: Character sheet summary."""

import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import ScrollableFrame
from gui.sheet_builder import build_character_sheet
from gui.theme import FONTS


class SummaryStep(WizardStep):
    tab_title = "Summary"

    def __init__(self, parent_notebook, character, game_data, app=None,
                 save_path=None):
        self.app = app
        self.save_path = save_path
        super().__init__(parent_notebook, character, game_data)

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # Top bar: name entry
        top = ttk.Frame(self.frame)
        top.pack(fill=tk.X, padx=12, pady=(12, 4))

        ttk.Label(top, text="Character Name:", style="Subheading.TLabel").pack(side=tk.LEFT)
        self.name_var = tk.StringVar(value=self.character.name or "New Character")
        self.name_var.trace_add("write", self._on_name_change)
        name_entry = ttk.Entry(top, textvariable=self.name_var, width=25, font=FONTS["heading"])
        name_entry.pack(side=tk.LEFT, padx=8)

        # Scrollable character sheet
        self.scroll = ScrollableFrame(self.frame)
        self.scroll.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 12))
        self.sheet = self.scroll.inner

    def on_enter(self):
        # Sync name field
        if self.character.name and self.character.name != self.name_var.get():
            self.name_var.set(self.character.name)
        elif not self.character.name:
            self.character.name = self.name_var.get()
        build_character_sheet(self.sheet, self.character, self.data)

    def _on_name_change(self, *args):
        self.character.name = self.name_var.get()
