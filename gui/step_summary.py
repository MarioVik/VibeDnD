"""Step 8: Character sheet summary."""

import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import ScrollableFrame
from gui.sheet_builder import build_character_sheet
from gui.theme import FONTS, COLORS
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
        self.frame.rowconfigure(2, weight=1)

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

        # HP override container (populated in on_enter once class is known)
        self._hp_frame = ttk.Frame(self.frame)
        self._hp_frame.pack(fill=tk.X, padx=12, pady=(0, 4))

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
        self._build_hp_override()
        self._refresh_sheet()

    def _build_hp_override(self):
        """Build/rebuild the level-1 HP override section based on current class."""
        for w in self._hp_frame.winfo_children():
            w.destroy()

        if not self.character.class_levels:
            return

        cl0 = self.character.class_levels[0]
        char_class = self.character.character_class
        if not char_class:
            return

        hit_die = char_class.get("hit_die", 8)
        con_mod = self.character.ability_scores.modifier("Constitution")
        average = hit_die // 2 + 1

        # Fresh StringVars each rebuild to avoid stale trace accumulation
        self._hp_mode = tk.StringVar()
        self._hp_manual_var = tk.StringVar()

        # Restore mode from existing hp_roll if any
        if cl0.hp_roll is None:
            self._hp_mode.set("max")
        elif cl0.hp_roll == hit_die:
            self._hp_mode.set("max")
        elif cl0.hp_roll == average:
            self._hp_mode.set("average")
        else:
            self._hp_mode.set("manual")
            self._hp_manual_var.set(str(cl0.hp_roll))

        ttk.Label(
            self._hp_frame,
            text="HP at Level 1",
            style="Subheading.TLabel",
        ).pack(anchor="w", pady=(2, 2))

        radio_row = ttk.Frame(self._hp_frame)
        radio_row.pack(fill=tk.X)

        ttk.Radiobutton(
            radio_row,
            text=f"Max ({hit_die} + {con_mod} CON = {hit_die + con_mod} HP)",
            variable=self._hp_mode,
            value="max",
        ).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Radiobutton(
            radio_row,
            text=f"Average ({average} + {con_mod} CON = {average + con_mod} HP)",
            variable=self._hp_mode,
            value="average",
        ).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Radiobutton(
            radio_row,
            text="Manual:",
            variable=self._hp_mode,
            value="manual",
        ).pack(side=tk.LEFT)

        manual_entry = ttk.Entry(radio_row, textvariable=self._hp_manual_var, width=5)
        manual_entry.pack(side=tk.LEFT, padx=(4, 4))

        self._hp_hint_label = ttk.Label(
            radio_row,
            text=f"+ {con_mod} CON = ? HP",
            foreground=COLORS["fg_dim"],
        )
        self._hp_hint_label.pack(side=tk.LEFT)

        def _update_state(*_):
            if self._hp_mode.get() == "manual":
                manual_entry.config(state="normal")
            else:
                manual_entry.config(state="disabled")
            _update_hint()
            self._apply_hp_override(hit_die, con_mod, average)

        def _update_hint(*_):
            if self._hp_mode.get() != "manual":
                return
            val = self._hp_manual_var.get().strip()
            try:
                roll = int(val)
                if roll >= 1:
                    self._hp_hint_label.config(text=f"+ {con_mod} CON = {roll + con_mod} HP")
                else:
                    self._hp_hint_label.config(text="(must be ≥ 1)")
            except ValueError:
                self._hp_hint_label.config(text=f"+ {con_mod} CON = ? HP")

        self._hp_mode.trace_add("write", _update_state)
        self._hp_manual_var.trace_add("write", lambda *_: (_update_hint(), self._apply_hp_override(hit_die, con_mod, average)))

        # Set initial disabled state
        if self._hp_mode.get() != "manual":
            manual_entry.config(state="disabled")

    def _apply_hp_override(self, hit_die, con_mod, average):
        """Write the chosen HP value into character.class_levels[0].hp_roll."""
        if not self.character.class_levels:
            return
        cl0 = self.character.class_levels[0]
        mode = self._hp_mode.get()
        if mode == "max":
            cl0.hp_roll = None  # None = use max (default)
        elif mode == "average":
            cl0.hp_roll = average
        elif mode == "manual":
            val = self._hp_manual_var.get().strip()
            try:
                roll = int(val)
                if roll >= 1:
                    cl0.hp_roll = roll
            except ValueError:
                pass  # leave existing value until valid input
        # Refresh the sheet so HP stat updates live
        if hasattr(self, "sheet") and self.sheet.winfo_exists():
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
