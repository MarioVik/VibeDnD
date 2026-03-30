"""Reusable sidebar navigation component for the Mythic Modern layout."""

import tkinter as tk
from typing import Callable

from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import NavButton


class Sidebar(tk.Frame):
    """Fixed-width sidebar with step counter, nav items, and selection panel.

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
        on_back: Callable[[], None] | None = None,
        width: int = SIDEBAR_WIDTH,
        ):
        super().__init__(
            parent,
            bg=COLORS["bg_surface"],
            width=width,
            highlightbackground=COLORS["border_medium"],
            highlightcolor=COLORS["border_medium"],
            highlightthickness=1,
        )
        self.pack_propagate(False)
        self._on_navigate = on_navigate
        self._on_back: Callable[[], None] | None = on_back
        self._nav_buttons: dict[str, NavButton] = {}
        self._active_key: str | None = None
        self._name_label: tk.Label | None = None
        self._summary_label: tk.Label | None = None
        self._level_label: tk.Label | None = None
        self._nav_keys: list[str] = [item["key"] for item in nav_items]

        # ---- Step counter header (wizard only) ----
        self._step_counter: tk.Label | None = None
        if not show_character_info:
            self._step_counter = tk.Label(
                self,
                text="",
                font=FONTS["step_counter"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
                anchor="w",
            )
            self._step_counter.pack(
                fill=tk.X,
                padx=SPACING["lg"],
                pady=(SPACING["xl"], SPACING["lg"]),
            )

        # ---- Back button + character info (optional) ----
        if show_character_info:
            self._build_character_info()
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
                subtitle="" if show_character_info else "Locked",
            )
            btn.pack(fill=tk.X, pady=1)
            self._nav_buttons[item["key"]] = btn

        # ---- Bottom selection panel ----
        self._selection_frame = tk.Frame(self, bg=COLORS["bg_surface"])
        self._selection_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=SPACING["sm"], pady=(0, SPACING["md"]))
        self._selection_labels: dict[str, tuple[tk.Label, tk.Label]] = {}

        # Glass-style card for selections
        self._sel_card = tk.Frame(
            self._selection_frame,
            bg=COLORS["bg_container"],
            highlightbackground=COLORS["border_subtle"],
            highlightcolor=COLORS["border_subtle"],
            highlightthickness=1,
        )
        self._sel_card.pack(fill=tk.X, padx=4, pady=4)
        # Initially hidden
        self._sel_card.pack_forget()

        # ---- Bottom actions (legacy support) ----
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

                    b = ttk.Button(
                        btn_frame,
                        text=btn_cfg["text"],
                        style=style,
                        state=state,
                    )
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

    # ---- Step counter ----

    def set_step_counter(self, current: int, total: int):
        """Update the 'STEP X OF N' header text."""
        if self._step_counter is not None:
            self._step_counter.configure(text=f"STEP  {current}  OF  {total}")

    # ---- Step states ----

    def update_step_states(self, current_idx: int, reached_idx: int):
        """Update all nav buttons to reflect current, completed, and locked states."""
        for i, key in enumerate(self._nav_keys):
            btn = self._nav_buttons.get(key)
            if not btn:
                continue

            if i == current_idx:
                btn.set_status(active=True)
                btn.set_subtitle("Currently Editing")
            elif i <= reached_idx:
                btn.set_status(completed=True)
                btn.set_subtitle("Completed")
            else:
                btn.set_status(locked=True)
                btn.set_subtitle("Locked")

    # ---- Selection panel ----

    def set_selection(self, key: str, value: str):
        """Update or add a selection entry in the bottom panel.

        key: step key (e.g., "species"), value: selection name (e.g., "Elf")
        Empty value removes the entry.
        """
        if key in self._selection_labels:
            header_lbl, val_lbl = self._selection_labels[key]
            if value:
                val_lbl.configure(text=value)
                header_lbl.pack(fill=tk.X)
                val_lbl.pack(fill=tk.X)
            else:
                header_lbl.pack_forget()
                val_lbl.pack_forget()
                del self._selection_labels[key]
        elif value:
            header_lbl = tk.Label(
                self._sel_card,
                text=f"SELECTED {key.upper()}",
                font=FONTS["nav_subtitle"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_container"],
                anchor="w",
            )
            header_lbl.pack(fill=tk.X, padx=SPACING["md"], pady=(SPACING["sm"], 0))

            val_lbl = tk.Label(
                self._sel_card,
                text=value,
                font=FONTS["heading_serif_sm"],
                fg=COLORS["gold"],
                bg=COLORS["bg_container"],
                anchor="w",
            )
            val_lbl.pack(fill=tk.X, padx=SPACING["md"], pady=(0, SPACING["sm"]))
            self._selection_labels[key] = (header_lbl, val_lbl)

        # Show/hide the card based on whether there are any selections
        if self._selection_labels:
            self._sel_card.pack(fill=tk.X, padx=4, pady=4)
        else:
            self._sel_card.pack_forget()

    # ---- Character info (for viewer sidebar) ----

    def _build_character_info(self):
        """Build the back button + character name area at the top."""
        info_frame = tk.Frame(self, bg=COLORS["bg_surface"])
        info_frame.pack(fill=tk.X, padx=16, pady=(16, 12))

        row = tk.Frame(info_frame, bg=COLORS["bg_surface"])
        row.pack(fill=tk.X)

        if self._on_back:
            back_btn = tk.Label(
                row,
                text="\u25c0",
                font=FONTS["heading_serif_sm"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
                cursor="hand2",
            )
            back_btn.pack(side=tk.LEFT, padx=(0, 10))
            back_btn.bind("<Button-1>", lambda e: self._on_back())
            back_btn.bind(
                "<Enter>",
                lambda _event, widget=back_btn: self._animate_label_color(
                    widget, COLORS["accent_text"],
                ),
            )
            back_btn.bind(
                "<Leave>",
                lambda _event, widget=back_btn: self._animate_label_color(
                    widget, COLORS["fg_dim"],
                ),
            )

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
        """Update the character name and summary in the sidebar."""
        if self._name_label:
            self._name_label.configure(text=name)
        if self._summary_label:
            self._summary_label.configure(text=summary.upper())
        if self._level_label:
            self._level_label.configure(text=level.upper())

    def _handle_nav(self, key: str):
        self._on_navigate(key)

    def set_active(self, key: str):
        """Highlight the given nav item as active, deactivate others."""
        if self._active_key and self._active_key in self._nav_buttons:
            self._nav_buttons[self._active_key].set_active(False)
        self._active_key = key
        if key in self._nav_buttons:
            self._nav_buttons[key].set_active(True)
        if self._step_counter is None:
            for nav_key, btn in self._nav_buttons.items():
                btn.set_subtitle("")

    def _animate_label_color(self, widget: tk.Label, target_color: str, steps: int = 6, delay: int = 18):
        current_job = getattr(widget, "_color_anim_job", None)
        if current_job:
            try:
                widget.after_cancel(current_job)
            except tk.TclError:
                pass

        start_color = widget.cget("fg")
        start_rgb = self._hex_to_rgb(start_color)
        target_rgb = self._hex_to_rgb(target_color)

        def step(index: int):
            ratio = index / float(steps)
            blended = tuple(
                int(start + ((target - start) * ratio))
                for start, target in zip(start_rgb, target_rgb)
            )
            try:
                widget.configure(fg=self._rgb_to_hex(blended))
            except tk.TclError:
                return

            if index < steps:
                widget._color_anim_job = widget.after(delay, lambda: step(index + 1))
            else:
                widget._color_anim_job = None

        step(1)

    def _hex_to_rgb(self, value: str) -> tuple[int, int, int]:
        color = value.strip().lstrip("#")
        if len(color) == 3:
            color = "".join(ch * 2 for ch in color)
        return tuple(int(color[idx:idx + 2], 16) for idx in (0, 2, 4))

    def _rgb_to_hex(self, value: tuple[int, int, int]) -> str:
        return "#{:02x}{:02x}{:02x}".format(*value)
