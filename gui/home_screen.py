"""Home screen: main menu with 'Create New' and saved character list."""

import tkinter as tk
from tkinter import ttk, messagebox

from gui.theme import COLORS, FONTS
from gui.widgets import ScrollableFrame
from models.character_store import list_saved_characters, delete_character
from paths import characters_dir


class HomeScreen:
    """The landing page shown when the app starts."""

    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        self._build_ui()

    def _build_ui(self):
        # ── Title ───────────────────────────────────────────────
        title_frame = ttk.Frame(self.frame)
        title_frame.pack(fill=tk.X, padx=20, pady=(40, 0))

        ttk.Label(
            title_frame,
            text="D&D 2024 Character Creator",
            font=("Segoe UI", 24, "bold"),
            foreground=COLORS["accent"],
        ).pack()

        ttk.Label(
            title_frame,
            text="Create and manage your characters",
            foreground=COLORS["fg_dim"],
        ).pack(pady=(2, 0))

        # ── Create New button ───────────────────────────────────
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(pady=24)

        ttk.Button(
            btn_frame,
            text="  Create New Character  ",
            style="Accent.TButton",
            command=self._on_create_new,
        ).pack()

        # ── Separator ──────────────────────────────────────────
        ttk.Separator(self.frame, orient=tk.HORIZONTAL).pack(
            fill=tk.X, padx=60, pady=(4, 12))

        # ── Saved Characters heading ───────────────────────────
        ttk.Label(
            self.frame,
            text="Saved Characters",
            style="Subheading.TLabel",
        ).pack(anchor="w", padx=60)

        # ── Scrollable character list ──────────────────────────
        self.list_scroll = ScrollableFrame(self.frame)
        self.list_scroll.pack(fill=tk.BOTH, expand=True, padx=60, pady=(8, 20))
        self.list_inner = self.list_scroll.inner

    # ── Public ──────────────────────────────────────────────────

    def refresh(self):
        """Reload the character list from disk."""
        for w in self.list_inner.winfo_children():
            w.destroy()

        chars = list_saved_characters(characters_dir())

        if not chars:
            ttk.Label(
                self.list_inner,
                text="No saved characters yet.  Click 'Create New Character' to get started!",
                foreground=COLORS["fg_dim"],
            ).pack(pady=30)
            return

        for info in chars:
            self._add_character_row(info)

    # ── Internals ───────────────────────────────────────────────

    def _add_character_row(self, info: dict):
        row = ttk.Frame(self.list_inner, style="Card.TFrame")
        row.pack(fill=tk.X, pady=4, ipady=8)

        # Left side: name + summary
        text_frame = ttk.Frame(row, style="Card.TFrame")
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12)

        ttk.Label(
            text_frame,
            text=info["name"],
            font=FONTS["subheading"],
            foreground=COLORS["fg_bright"],
            background=COLORS["bg_card"],
        ).pack(anchor="w")

        lvl = info.get("level", 1)
        summary = f'Level {lvl} {info.get("species", "?")} {info.get("class_name", "?")}'
        ttk.Label(
            text_frame,
            text=summary,
            foreground=COLORS["fg_dim"],
            background=COLORS["bg_card"],
        ).pack(anchor="w")

        # Right side: buttons
        btn_frame = ttk.Frame(row, style="Card.TFrame")
        btn_frame.pack(side=tk.RIGHT, padx=12)

        ttk.Button(
            btn_frame,
            text="Delete",
            command=lambda p=info["path"]: self._on_delete(p),
        ).pack(side=tk.RIGHT, padx=(4, 0))

        ttk.Button(
            btn_frame,
            text="View",
            style="Accent.TButton",
            command=lambda p=info["path"]: self._on_view(p),
        ).pack(side=tk.RIGHT, padx=(4, 0))

    def _on_create_new(self):
        self.app.show_wizard()

    def _on_view(self, path):
        from models.character_store import load_character
        try:
            character = load_character(path, self.app.data)
            self.app.show_viewer(character, path)
        except Exception as e:
            messagebox.showerror("Load Error", f"Could not load character:\n{e}")

    def _on_delete(self, path):
        if messagebox.askyesno("Delete Character",
                               "Are you sure you want to delete this character?"):
            delete_character(path)
            self.refresh()
