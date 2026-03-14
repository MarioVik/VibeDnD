"""Step 8: Character sheet summary."""

import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import ScrollableFrame
from gui.sheet_builder import build_character_sheet
from gui.theme import FONTS
from models.character_store import save_character
from paths import characters_dir
from gui.add_inventory_dialog import AddInventoryDialog


class SummaryStep(WizardStep):
    tab_title = "Summary"

    def __init__(self, parent_notebook, character, game_data, app=None, save_path=None):
        self.app = app
        self.save_path = save_path
        super().__init__(parent_notebook, character, game_data)

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # Top bar: name entry
        top = ttk.Frame(self.frame)
        top.pack(fill=tk.X, padx=12, pady=(12, 4))

        ttk.Label(top, text="Character Name:", style="Subheading.TLabel").pack(
            side=tk.LEFT
        )
        self.name_var = tk.StringVar(value=self.character.name or "New Character")
        self.name_var.trace_add("write", self._on_name_change)
        name_entry = ttk.Entry(
            top, textvariable=self.name_var, width=25, font=FONTS["heading"]
        )
        name_entry.pack(side=tk.LEFT, padx=8)

        ttk.Button(
            top,
            text="Add to inventory",
            command=self._on_add_inventory,
        ).pack(side=tk.RIGHT)

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
        self._refresh_sheet()

    def _refresh_sheet(self):
        for w in self.sheet.winfo_children():
            w.destroy()
        build_character_sheet(
            self.sheet,
            self.character,
            self.data,
            on_change=self._on_sheet_changed,
        )

    def _on_sheet_changed(self):
        if not self.save_path:
            return
        save_character(
            self.character, characters_dir(), existing_filename=self.save_path
        )

    def _on_name_change(self, *args):
        self.character.name = self.name_var.get()

    def _on_add_inventory(self):
        AddInventoryDialog(
            self.frame,
            self.character,
            self.data,
            on_changed=lambda: (self._on_sheet_changed(), self._refresh_sheet()),
        )
