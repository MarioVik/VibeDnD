"""Home screen: main menu with character library and sidebar navigation."""

import tkinter as tk
from tkinter import ttk, filedialog

from gui.theme import COLORS, FONTS
from gui.sidebar import Sidebar
from gui.widgets import ScrollableFrame, ConfirmDialog, AlertDialog
from models.character_store import list_saved_characters, delete_character
from paths import characters_dir


class HomeScreen:
    """The landing page shown when the app starts."""

    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent, bg=COLORS["bg"])
        self._build_ui()

    def _build_ui(self):
        # ── Sidebar ───────────────────────────────────────────────
        self.sidebar = Sidebar(
            self.frame,
            nav_items=[
                {"key": "library", "text": "Character Library", "icon": "\U0001F4DC"},
            ],
            on_navigate=self._on_nav,
            bottom_buttons=[
                {
                    "text": "\u2795  Create New Character",
                    "command": self._on_create_new,
                    "style": "Accent.TButton",
                },
                {
                    "text": "\U0001F4E5  Import Character",
                    "command": self._on_import,
                },
            ],
        )
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.set_active("library")

        # ── Content area ──────────────────────────────────────────
        content = tk.Frame(self.frame, bg=COLORS["bg"])
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Header
        header = tk.Frame(content, bg=COLORS["bg"])
        header.pack(fill=tk.X, padx=32, pady=(32, 0))

        tk.Label(
            header,
            text="VibeDnD",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["accent_text"],
            bg=COLORS["bg"],
            anchor="w",
        ).pack(fill=tk.X)

        tk.Label(
            header,
            text="D&D 2024 Character Creator",
            font=FONTS["label_upper"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
            anchor="w",
        ).pack(fill=tk.X, pady=(2, 0))

        # Separator
        tk.Frame(content, bg=COLORS["outline_dim"], height=1).pack(
            fill=tk.X, padx=32, pady=(16, 0)
        )

        # Section heading
        section_head = tk.Frame(content, bg=COLORS["bg"])
        section_head.pack(fill=tk.X, padx=32, pady=(16, 8))

        tk.Label(
            section_head,
            text="Your Characters",
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
            anchor="w",
        ).pack(side=tk.LEFT)

        self._count_label = tk.Label(
            section_head,
            text="",
            font=FONTS["label_upper"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
            anchor="e",
        )
        self._count_label.pack(side=tk.RIGHT)

        # Scrollable character card grid
        self.list_scroll = ScrollableFrame(content)
        self.list_scroll.pack(fill=tk.BOTH, expand=True, padx=32, pady=(0, 20))
        self.list_inner = self.list_scroll.inner

    # ── Public ──────────────────────────────────────────────────

    def refresh(self):
        """Reload the character list from disk."""
        for w in self.list_inner.winfo_children():
            w.destroy()

        chars = list_saved_characters(characters_dir())
        self._count_label.configure(text=f"{len(chars)} saved")

        if not chars:
            empty = tk.Frame(self.list_inner, bg=COLORS["bg"])
            empty.pack(fill=tk.BOTH, expand=True, pady=60)

            tk.Label(
                empty,
                text="\U0001F4DC",
                font=("", 36),
                fg=COLORS["fg_dim"],
                bg=COLORS["bg"],
            ).pack()

            tk.Label(
                empty,
                text="No characters yet",
                font=FONTS["heading_serif_sm"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg"],
            ).pack(pady=(8, 4))

            tk.Label(
                empty,
                text="Create a new character or import an existing one to get started.",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg"],
            ).pack()
            return

        for info in chars:
            self._add_character_card(info)

    # ── Internals ───────────────────────────────────────────────

    def _on_nav(self, key: str):
        pass  # single-item nav, nothing to switch

    def _add_character_card(self, info: dict):
        """Add a character card to the list."""
        card = tk.Frame(
            self.list_inner,
            bg=COLORS["bg_surface"],
            highlightbackground=COLORS["outline_dim"],
            highlightthickness=1,
            padx=16,
            pady=12,
        )
        card.pack(fill=tk.X, pady=4)

        # Left side: name + summary
        text_frame = tk.Frame(card, bg=COLORS["bg_surface"])
        text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            text_frame,
            text=info["name"],
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
            anchor="w",
        ).pack(fill=tk.X)

        lvl = info.get("level", 1)
        summary = f'Level {lvl} {info.get("species", "?")} {info.get("class_name", "?")}'
        tk.Label(
            text_frame,
            text=summary.upper(),
            font=FONTS["label_upper"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
            anchor="w",
        ).pack(fill=tk.X)

        # Right side: buttons
        btn_frame = tk.Frame(card, bg=COLORS["bg_surface"])
        btn_frame.pack(side=tk.RIGHT, padx=(12, 0))

        view_btn = ttk.Button(
            btn_frame,
            text="View",
            style="Accent.TButton",
            command=lambda p=info["path"]: self._on_view(p),
        )
        view_btn.pack(side=tk.LEFT, padx=(0, 6))

        del_btn = ttk.Button(
            btn_frame,
            text="Delete",
            command=lambda p=info["path"]: self._on_delete(p),
        )
        del_btn.pack(side=tk.LEFT)

        # Hover effects
        def on_enter(e):
            card.configure(highlightbackground=COLORS["accent"])

        def on_leave(e):
            card.configure(highlightbackground=COLORS["outline_dim"])

        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)

    def _on_create_new(self):
        self.app.show_wizard()

    def _on_import(self):
        path = filedialog.askopenfilename(
            title="Import Character",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        from models.character_store import import_character_from_export, save_character
        try:
            character = import_character_from_export(path, self.app.data)
            save_path = save_character(character, characters_dir())
            self.app.show_viewer(character, save_path)
        except Exception as e:
            AlertDialog(self.frame, "Import Error", f"Could not import character:\n{e}")

    def _on_view(self, path):
        from models.character_store import load_character
        try:
            character = load_character(path, self.app.data)
            self.app.show_viewer(character, path)
        except Exception as e:
            AlertDialog(self.frame, "Load Error", f"Could not load character:\n{e}")

    def _on_delete(self, path):
        dlg = ConfirmDialog(
            self.frame, "Delete Character",
            "Are you sure you want to delete this character?"
        )
        if dlg.result:
            delete_character(path)
            self.refresh()
