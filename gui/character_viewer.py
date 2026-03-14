"""Read-only character sheet viewer with export and edit buttons."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from gui.theme import COLORS, FONTS
from gui.widgets import ScrollableFrame, AlertDialog
from gui.sheet_builder import build_character_sheet
from models.character_store import save_character
from paths import characters_dir
from gui.add_inventory_dialog import AddInventoryDialog


class CharacterViewer(ttk.Frame):
    """Full-screen read-only character sheet with navigation and export."""

    def __init__(self, parent, character, save_path, game_data, app):
        super().__init__(parent)
        self.character = character
        self.save_path = save_path
        self.data = game_data
        self.app = app
        self._build_ui()

    def _build_ui(self):
        # ── Top bar ─────────────────────────────────────────────
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=12, pady=(12, 4))

        ttk.Button(
            top,
            text="\u25c0  Back to Menu",
            command=self._on_back,
        ).pack(side=tk.LEFT)

        if self.character.level < 20:
            ttk.Button(
                top,
                text="Level Up",
                command=self._on_level_up,
            ).pack(side=tk.LEFT, padx=8)

        ttk.Button(
            top,
            text="Add to inventory",
            command=self._on_add_inventory,
        ).pack(side=tk.LEFT, padx=4)

        # Character name
        ttk.Label(
            top,
            text=self.character.name or "Unnamed",
            font=("Segoe UI", 18, "bold"),
            foreground=COLORS["accent"],
        ).pack(side=tk.LEFT, padx=8)

        # Export buttons (right side)
        ttk.Button(top, text="Export Character", command=self._export_json).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(top, text="Export PDF", command=self._export_pdf).pack(
            side=tk.RIGHT, padx=4
        )

        ttk.Button(
            top,
            text="Respec character",
            command=self._on_edit,
        ).pack(side=tk.RIGHT, padx=8)

        # ── Character sheet ─────────────────────────────────────
        scroll = ScrollableFrame(self)
        scroll.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 12))
        self._sheet_parent = scroll.inner

        self._refresh_sheet()

    def _refresh_sheet(self):
        for w in self._sheet_parent.winfo_children():
            w.destroy()

        build_character_sheet(
            self._sheet_parent,
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

    # ── Navigation ──────────────────────────────────────────────

    def _on_back(self):
        self.app.show_home()

    def _on_edit(self):
        self.app.show_wizard(self.character, self.save_path)

    def _on_add_inventory(self):
        AddInventoryDialog(
            self,
            self.character,
            self.data,
            on_changed=lambda: (self._on_sheet_changed(), self._refresh_sheet()),
        )

    def _on_level_up(self):
        from gui.level_up_wizard import LevelUpWizard

        def on_complete():
            # Save and refresh
            save_character(
                self.character, characters_dir(), existing_filename=self.save_path
            )
            self.app.show_viewer(self.character, self.save_path)

        LevelUpWizard(self, self.character, self.data, on_complete=on_complete)

    # ── Exports (same pattern as SummaryStep) ───────────────────

    def _export_json(self):
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
            AlertDialog(self.winfo_toplevel(), "Export", f"Character saved to {path}")

    def _export_pdf(self):
        from export.pdf_export import export_pdf

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"{self.character.name}.pdf",
        )
        if path:
            try:
                export_pdf(self.character, path)
                AlertDialog(
                    self.winfo_toplevel(),
                    "Export",
                    f"PDF character sheet saved to {path}",
                )
            except Exception as e:
                AlertDialog(
                    self.winfo_toplevel(),
                    "Export Error",
                    f"Failed to generate PDF:\n{e}",
                )
