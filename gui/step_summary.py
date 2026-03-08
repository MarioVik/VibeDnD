"""Step 8: Character sheet summary, save and export."""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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

        # Top bar: name + save/export buttons
        top = ttk.Frame(self.frame)
        top.pack(fill=tk.X, padx=12, pady=(12, 4))

        ttk.Label(top, text="Character Name:", style="Subheading.TLabel").pack(side=tk.LEFT)
        self.name_var = tk.StringVar(value=self.character.name or "New Character")
        self.name_var.trace_add("write", self._on_name_change)
        name_entry = ttk.Entry(top, textvariable=self.name_var, width=25, font=FONTS["heading"])
        name_entry.pack(side=tk.LEFT, padx=8)

        # Save & Finish button (only when app reference is available)
        if self.app is not None:
            ttk.Button(top, text="Save & Finish", style="Accent.TButton",
                       command=self._save_and_finish).pack(side=tk.LEFT, padx=12)

        ttk.Button(top, text="Export JSON", command=self._export_json).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="Export Text", command=self._export_text).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="Export PDF", command=self._export_pdf).pack(side=tk.RIGHT, padx=4)

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

    def _save_and_finish(self):
        if not self.character.name or self.character.name == "New Character":
            messagebox.showwarning("Name Required",
                                   "Please enter a character name before saving.")
            return

        from models.character_store import save_character
        from paths import characters_dir

        path = save_character(self.character, characters_dir(), self.save_path)
        self.save_path = path
        self.app.show_home()

    def _export_json(self):
        from export.json_export import export_json
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"{self.character.name}.json",
        )
        if path:
            export_json(self.character, path)
            messagebox.showinfo("Export", f"Character saved to {path}")

    def _export_text(self):
        from export.text_export import export_text
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile=f"{self.character.name}.txt",
        )
        if path:
            export_text(self.character, path)
            messagebox.showinfo("Export", f"Character sheet saved to {path}")

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
                messagebox.showinfo("Export", f"PDF character sheet saved to {path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to generate PDF:\n{e}")
