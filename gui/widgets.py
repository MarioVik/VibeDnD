"""Reusable custom widgets for the character creator."""

import tkinter as tk
from tkinter import ttk
from gui.theme import COLORS, FONTS


def configure_modal_dialog(dialog: tk.Toplevel, parent):
    """Make dialog modal and bring it above the active app window."""
    top = parent.winfo_toplevel() if parent is not None else None
    if top is not None:
        dialog.transient(top)
    dialog.grab_set()
    dialog.update_idletasks()

    try:
        dialog.lift(top) if top is not None else dialog.lift()
    except tk.TclError:
        pass

    try:
        dialog.attributes("-topmost", True)
        dialog.after_idle(lambda: dialog.attributes("-topmost", False))
    except tk.TclError:
        pass

    try:
        dialog.focus_force()
    except tk.TclError:
        dialog.focus_set()


def center_dialog_over_parent(dialog: tk.Toplevel, parent):
    """Center a dialog over the parent toplevel window."""
    top = parent.winfo_toplevel() if parent is not None else None
    if top is None:
        return

    top.update_idletasks()
    dialog.update_idletasks()

    width = dialog.winfo_width() or dialog.winfo_reqwidth()
    height = dialog.winfo_height() or dialog.winfo_reqheight()

    parent_x = top.winfo_rootx()
    parent_y = top.winfo_rooty()
    parent_w = top.winfo_width()
    parent_h = top.winfo_height()

    x = parent_x + max(0, (parent_w - width) // 2)
    y = parent_y + max(0, (parent_h - height) // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")


class WrappingLabel(ttk.Label):
    """A label that automatically updates its wraplength based on its allocated width.
    Must be packed with fill=tk.X or fill=tk.BOTH to receive width updates."""

    def __init__(self, master=None, **kwargs):
        # Remove any fixed wraplength passed by default so it can be managed dynamically
        kwargs.pop("wraplength", None)
        super().__init__(master, **kwargs)
        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, event):
        # Leave a tiny margin to prevent layout thrashing
        new_wrap = event.width - 4
        if new_wrap > 0:
            current_wrap = self.cget("wraplength")
            if current_wrap != new_wrap:
                self.configure(wraplength=new_wrap)


class SearchableListbox(ttk.Frame):
    """A listbox with a search/filter entry above it."""

    def __init__(self, parent, items=None, on_select=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.all_items = items or []
        self.on_select = on_select

        # Search entry
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._filter)
        self.search_entry = ttk.Entry(self, textvariable=self.search_var)
        self.search_entry.pack(fill=tk.X, padx=2, pady=(2, 4))

        # Listbox with scrollbar
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(
            list_frame,
            bg=COLORS["bg_light"],
            fg=COLORS["fg"],
            selectbackground=COLORS["select_bg"],
            selectforeground=COLORS["select_fg"],
            font=FONTS["body"],
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
        )
        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.listbox.yview
        )
        self.listbox.configure(yscrollcommand=scrollbar.set)

        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        self._populate()

    def set_items(self, items: list[str]):
        self.all_items = items
        self._populate()

    def _populate(self):
        self.listbox.delete(0, tk.END)
        query = self.search_var.get().lower()
        for item in self.all_items:
            if not query or query in item.lower():
                self.listbox.insert(tk.END, item)

    def _filter(self, *args):
        self._populate()

    def _on_select(self, event):
        sel = self.listbox.curselection()
        if sel and self.on_select:
            self.on_select(self.listbox.get(sel[0]))

    def get_selection(self) -> str | None:
        sel = self.listbox.curselection()
        if sel:
            return self.listbox.get(sel[0])
        return None

    def select_item(self, name: str):
        """Programmatically select an item by name."""
        for i in range(self.listbox.size()):
            if self.listbox.get(i) == name:
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(i)
                self.listbox.see(i)
                break


class SectionedListbox(ttk.Frame):
    """A listbox with search, grouped by sections with non-selectable headers.

    Items can optionally have sub-items (displayed as indented, non-selectable
    dim rows beneath each item).  Pass them via ``set_sectioned_items`` using
    the ``sub_items`` dict mapping item names to lists of sub-item strings.
    """

    HEADER_PREFIX = "\u2500\u2500 "  # ── prefix for section headers
    HEADER_SUFFIX = " \u2500\u2500"
    SUB_ITEM_PREFIX = "         - "

    def __init__(self, parent, on_select=None, on_sub_select=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_select = on_select
        self.on_sub_select = on_sub_select
        self.sections: list[tuple[str, list[str]]] = []  # [(section_name, [items])]
        self.sub_items: dict[str, list[str]] = {}  # item_name -> [sub-item texts]
        self._header_indices: set[int] = set()  # listbox indices that are headers
        self._sub_item_indices: set[int] = set()  # listbox indices that are sub-items
        self._sub_leaf_indices: dict[int, tuple[str, str]] = {}
        self._item_row_indices: dict[
            int, str
        ] = {}  # idx -> item name for selectable rows

        # Search entry
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._filter)
        self.search_entry = ttk.Entry(self, textvariable=self.search_var)
        self.search_entry.pack(fill=tk.X, padx=2, pady=(2, 4))

        # Listbox with scrollbar
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(
            list_frame,
            bg=COLORS["bg_light"],
            fg=COLORS["fg"],
            selectbackground=COLORS["select_bg"],
            selectforeground=COLORS["select_fg"],
            font=FONTS["body"],
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
        )
        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.listbox.yview
        )
        self.listbox.configure(yscrollcommand=scrollbar.set)

        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox.bind("<<ListboxSelect>>", self._on_select)

    def set_sectioned_items(
        self,
        sections: list[tuple[str, list[str]]],
        sub_items: dict[str, list[str]] | None = None,
    ):
        """Set items grouped by section.

        Args:
            sections: [(section_name, [item_names])]
            sub_items: optional dict mapping item names to lists of sub-item
                       display strings shown beneath that item when visible.
        """
        self.sections = sections
        self.sub_items = sub_items or {}
        self._populate()

    def _populate(self):
        self.listbox.delete(0, tk.END)
        self._header_indices.clear()
        self._sub_item_indices.clear()
        self._sub_leaf_indices.clear()
        self._item_row_indices.clear()
        query = self.search_var.get().lower()
        idx = 0

        for section_name, items in self.sections:
            # Filter items by search query (also match on sub-item names)
            visible = []
            for it in items:
                subs = self.sub_items.get(it, [])
                if (
                    not query
                    or query in it.lower()
                    or any(query in s.lower() for s in subs)
                ):
                    visible.append(it)
            if not visible:
                continue

            # Insert section header
            header_text = f"{self.HEADER_PREFIX}{section_name}{self.HEADER_SUFFIX}"
            self.listbox.insert(tk.END, header_text)
            self.listbox.itemconfig(
                idx,
                fg=COLORS["accent"],
                selectbackground=COLORS["bg_light"],
                selectforeground=COLORS["accent"],
            )
            self._header_indices.add(idx)
            idx += 1

            # Insert items and optional sub-items
            for item in visible:
                self.listbox.insert(tk.END, f"  {item}")
                self._item_row_indices[idx] = item
                idx += 1

                subs = self.sub_items.get(item, [])
                if subs:
                    for sub in subs:
                        self.listbox.insert(tk.END, f"{self.SUB_ITEM_PREFIX}{sub}")
                        self.listbox.itemconfig(
                            idx,
                            fg=COLORS["fg_dim"],
                            selectbackground=COLORS["select_bg"],
                            selectforeground=COLORS["select_fg"],
                        )
                        self._sub_item_indices.add(idx)
                        self._sub_leaf_indices[idx] = (item, sub)
                        idx += 1

    def _filter(self, *args):
        self._populate()

    def _is_non_selectable(self, index: int) -> bool:
        return index in self._header_indices or index in self._sub_item_indices

    def _on_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        i = sel[0]

        if i in self._sub_leaf_indices:
            parent_item, sub_item = self._sub_leaf_indices[i]
            if self.on_sub_select:
                self.on_sub_select(parent_item, sub_item)
            return

        if self._is_non_selectable(i):
            self.listbox.selection_clear(i)
            return

        if self.on_select:
            name = self.listbox.get(i).strip()
            self.on_select(name)

    def get_selection(self) -> str | None:
        sel = self.listbox.curselection()
        if sel and not self._is_non_selectable(sel[0]):
            return self.listbox.get(sel[0]).strip()
        return None

    def select_item(self, name: str):
        """Programmatically select an item by name."""
        for i in range(self.listbox.size()):
            if not self._is_non_selectable(i) and self.listbox.get(i).strip() == name:
                self.listbox.selection_clear(0, tk.END)
                self.listbox.selection_set(i)
                self.listbox.see(i)
                break


class ScrollableFrame(ttk.Frame):
    """A frame with a vertical scrollbar."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.canvas = tk.Canvas(
            self, bg=COLORS["bg"], highlightthickness=0, borderwidth=0
        )
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Make inner frame fill canvas width
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mousewheel scrolling
        self.inner.bind("<Enter>", self._bind_mousewheel)
        self.inner.bind("<Leave>", self._unbind_mousewheel)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class StatDisplay(ttk.Frame):
    """Compact display of an ability score with modifier."""

    def __init__(self, parent, label: str, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(style="Card.TFrame")

        self.label = ttk.Label(self, text=label[:3].upper(), style="Dim.TLabel")
        self.label.configure(background=COLORS["bg_card"])
        self.label.pack()

        self.score_var = tk.StringVar(value="10")
        self.score_label = ttk.Label(
            self, textvariable=self.score_var, style="Stat.TLabel"
        )
        self.score_label.configure(background=COLORS["bg_card"])
        self.score_label.pack()

        self.mod_var = tk.StringVar(value="+0")
        self.mod_label = ttk.Label(
            self, textvariable=self.mod_var, style="StatMod.TLabel"
        )
        self.mod_label.configure(background=COLORS["bg_card"])
        self.mod_label.pack()

    def update_values(self, score: int, modifier: str):
        self.score_var.set(str(score))
        self.mod_var.set(modifier)
        mod_val = (
            int(modifier.replace("+", ""))
            if modifier.startswith("+")
            else int(modifier)
        )
        if mod_val > 0:
            self.mod_label.configure(foreground=COLORS["positive"])
        elif mod_val < 0:
            self.mod_label.configure(foreground=COLORS["negative"])
        else:
            self.mod_label.configure(foreground=COLORS["fg_dim"])


class AlertDialog(tk.Toplevel):
    """A custom centered alert/info dialog that matches the app theme."""

    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)

        configure_modal_dialog(self, parent)

        # UI
        main_frame = ttk.Frame(self, padding=24)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=message, wraplength=350, justify=tk.CENTER).pack(
            pady=(0, 24)
        )

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        # OK button centered
        self.ok_btn = ttk.Button(
            btn_frame, text="OK", style="Accent.TButton", command=self.destroy
        )
        self.ok_btn.pack(side=tk.TOP, anchor="center")

        # Centering logic
        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()

        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)

        self.geometry(f"+{x}+{y}")

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self.destroy())

        self.ok_btn.focus_set()
        self.wait_window(self)


class ConfirmDialog(tk.Toplevel):
    """A custom centered confirmation dialog that matches the app theme."""

    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.result = False
        self.title(title)
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)

        configure_modal_dialog(self, parent)

        # UI
        main_frame = ttk.Frame(self, padding=24)
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text=message, wraplength=350, justify=tk.CENTER).pack(
            pady=(0, 24)
        )

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        # Cancel (No) is on the left, Confirm (Yes) is on the right
        self.no_btn = ttk.Button(btn_frame, text="No", command=self._on_no)
        self.no_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.yes_btn = ttk.Button(
            btn_frame, text="Yes", style="Accent.TButton", command=self._on_yes
        )
        self.yes_btn.pack(side=tk.RIGHT)

        # Centering logic
        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()

        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)

        self.geometry(f"+{x}+{y}")

        self.bind("<Escape>", lambda e: self._on_no())
        self.bind("<Return>", lambda e: self._on_yes())

        # Focus the Yes button by default
        self.yes_btn.focus_set()

        self.wait_window(self)

    def _on_yes(self):
        self.result = True
        self.destroy()

    def _on_no(self):
        self.result = False
        self.destroy()


class ThemedTable(ttk.Frame):
    """A themed table using ttk.Treeview with scrollbars."""

    def __init__(self, parent, columns, height=20, **kwargs):
        super().__init__(parent, **kwargs)

        # We use a custom style to ensure the treeview fits the theme
        self.tree = ttk.Treeview(
            self, columns=columns, show="headings", selectmode="none", height=height
        )

        ysb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        xsb = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def set_columns(self, column_configs: list[dict]):
        """column_configs = [{'id': 'lvl', 'text': 'Level', 'width': 50}, ...]"""
        # Re-initialize tree with new columns if needed?
        # Actually ttk.Treeview doesn't easily support changing the number of columns after creation.
        # But we create it with all columns initially.
        for cfg in column_configs:
            col_id = cfg["id"]
            self.tree.heading(col_id, text=cfg.get("text", col_id))
            self.tree.column(
                col_id,
                width=cfg.get("width", 100),
                anchor=cfg.get("anchor", "center"),
                stretch=cfg.get("stretch", False),
            )

    def insert_row(self, values):
        self.tree.insert("", tk.END, values=values)

    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
