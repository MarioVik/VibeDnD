"""Reusable sidebar navigation component for the Mythic Modern layout."""

import base64
import io
import tkinter as tk
from typing import Callable

from gui.theme import COLORS, FONTS
from gui.widgets import NavButton

try:
    from PIL import Image, ImageTk
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


class Sidebar(tk.Frame):
    """Fixed-width sidebar with optional character info, nav items, and bottom actions.

    Args:
        parent: Parent widget.
        nav_items: List of dicts with keys ``key``, ``text``, and optional ``icon``.
        on_navigate: Callback ``(key: str) -> None`` fired when a nav item is clicked.
        bottom_buttons: Optional list of dicts with ``text``, ``command``, and optional ``style``.
        show_character_info: Whether to display the character portrait/name section.
        width: Sidebar width in pixels (default 256).
    """

    SIDEBAR_WIDTH = 256

    def __init__(
        self,
        parent,
        nav_items: list[dict],
        on_navigate: Callable[[str], None],
        bottom_buttons: list[dict] | None = None,
        show_character_info: bool = False,
        width: int = SIDEBAR_WIDTH,
    ):
        super().__init__(parent, bg=COLORS["bg_surface"], width=width,
                         highlightbackground=COLORS["border_medium"],
                         highlightthickness=1)
        self.pack_propagate(False)
        self._on_navigate = on_navigate
        self._nav_buttons: dict[str, NavButton] = {}
        self._active_key: str | None = None
        self._portrait_label: tk.Label | None = None
        self._portrait_image = None  # prevent GC
        self._name_label: tk.Label | None = None
        self._summary_label: tk.Label | None = None
        self._level_label: tk.Label | None = None

        # ---- Character info section (optional) ----
        if show_character_info:
            self._build_character_info()

        # ---- Separator ----
        if show_character_info:
            tk.Frame(self, bg=COLORS["border_subtle"], height=1).pack(
                fill=tk.X, padx=16, pady=(0, 8)
            )

        # ---- Navigation items ----
        nav_frame = tk.Frame(self, bg=COLORS["bg_surface"])
        nav_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        for item in nav_items:
            btn = NavButton(
                nav_frame,
                text=item["text"],
                key=item["key"],
                icon_char=item.get("icon", ""),
                on_click=self._handle_nav,
            )
            btn.pack(fill=tk.X, pady=1)
            self._nav_buttons[item["key"]] = btn

        # ---- Bottom actions ----
        self._action_buttons: dict[str, "ttk.Button"] = {}
        if bottom_buttons:
            tk.Frame(self, bg=COLORS["border_subtle"], height=1).pack(
                fill=tk.X, padx=16, pady=(8, 4)
            )
            btn_frame = tk.Frame(self, bg=COLORS["bg_surface"])
            btn_frame.pack(fill=tk.X, padx=8, pady=(0, 12))

            from tkinter import ttk

            for btn_cfg in bottom_buttons:
                style = btn_cfg.get("style", "TButton")
                state = btn_cfg.get("state", tk.NORMAL)
                submenu = btn_cfg.get("submenu")

                if submenu:
                    menu = tk.Menu(
                        btn_frame, tearoff=0,
                        bg=COLORS["bg_highest"], fg=COLORS["fg"],
                        activebackground=COLORS["bg_high"], activeforeground=COLORS["fg"],
                        font=FONTS["body"],
                    )
                    for item in submenu:
                        menu.add_command(label=item["text"], command=item["command"])

                    def _show_menu(event=None, _btn=None, _menu=menu):
                        x = _btn.winfo_rootx()
                        y = _btn.winfo_rooty() + _btn.winfo_height()
                        _menu.tk_popup(x, y)

                    b = ttk.Button(btn_frame, text=btn_cfg["text"], style=style, state=state)
                    b.configure(command=lambda _b=b, _m=menu: _show_menu(_btn=_b, _menu=_m))
                else:
                    b = ttk.Button(
                        btn_frame,
                        text=btn_cfg["text"],
                        command=btn_cfg.get("command"),
                        style=style,
                        state=state,
                    )
                b.pack(fill=tk.X, pady=2)
                key = btn_cfg.get("key")
                if key:
                    self._action_buttons[key] = b

    def get_action_button(self, key: str):
        """Return a bottom action button by key, or None."""
        return self._action_buttons.get(key)

    def _build_character_info(self):
        """Build the character portrait + name area at the top."""
        info_frame = tk.Frame(self, bg=COLORS["bg_surface"])
        info_frame.pack(fill=tk.X, padx=16, pady=(16, 12))

        row = tk.Frame(info_frame, bg=COLORS["bg_surface"])
        row.pack(fill=tk.X)

        # Portrait (48x48 circular-ish)
        self._portrait_label = tk.Label(
            row,
            bg=COLORS["bg_highest"],
            width=6,
            height=3,
        )
        self._portrait_label.pack(side=tk.LEFT, padx=(0, 10))

        # Text column
        text_col = tk.Frame(row, bg=COLORS["bg_surface"])
        text_col.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._name_label = tk.Label(
            text_col,
            text="",
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
            anchor="w",
        )
        self._name_label.pack(fill=tk.X)

        self._summary_label = tk.Label(
            text_col,
            text="",
            font=FONTS["label_upper"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
            anchor="w",
        )
        self._summary_label.pack(fill=tk.X)

        self._level_label = tk.Label(
            text_col,
            text="",
            font=FONTS["label_upper"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
            anchor="w",
        )
        self._level_label.pack(fill=tk.X)

    def set_character_info(
        self,
        name: str,
        summary: str,
        image_data: str | None = None,
        image_format: str = "png",
        level: str = "",
    ):
        """Update the character portrait and name in the sidebar."""
        if self._name_label:
            self._name_label.configure(text=name)
        if self._summary_label:
            self._summary_label.configure(text=summary.upper())
        if self._level_label:
            self._level_label.configure(text=level.upper())
        if self._portrait_label and image_data:
            self._set_portrait(image_data, image_format)

    def _set_portrait(self, image_data: str, image_format: str):
        """Decode base64 portrait and display as thumbnail."""
        if not _HAS_PIL or not self._portrait_label:
            return
        try:
            raw = base64.b64decode(image_data)
            img = Image.open(io.BytesIO(raw))
            img.thumbnail((48, 48), Image.LANCZOS)
            self._portrait_image = ImageTk.PhotoImage(img)
            self._portrait_label.configure(
                image=self._portrait_image,
                width=48,
                height=48,
            )
        except Exception:
            pass

    def _handle_nav(self, key: str):
        self.set_active(key)
        self._on_navigate(key)

    def set_active(self, key: str):
        """Highlight the given nav item as active, deactivate others."""
        if self._active_key and self._active_key in self._nav_buttons:
            self._nav_buttons[self._active_key].set_active(False)
        self._active_key = key
        if key in self._nav_buttons:
            self._nav_buttons[key].set_active(True)
