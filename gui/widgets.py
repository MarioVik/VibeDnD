"""Reusable custom widgets for the character creator."""

import tkinter as tk
from tkinter import ttk
from gui.theme import COLORS, FONTS


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
            bg=COLORS["bg_light"], fg=COLORS["fg"],
            selectbackground=COLORS["select_bg"], selectforeground=COLORS["select_fg"],
            font=FONTS["body"], borderwidth=0, highlightthickness=0,
            activestyle="none",
        )
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
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


class ScrollableFrame(ttk.Frame):
    """A frame with a vertical scrollbar."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.canvas = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
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
        self.score_label = ttk.Label(self, textvariable=self.score_var, style="Stat.TLabel")
        self.score_label.configure(background=COLORS["bg_card"])
        self.score_label.pack()

        self.mod_var = tk.StringVar(value="+0")
        self.mod_label = ttk.Label(self, textvariable=self.mod_var, style="StatMod.TLabel")
        self.mod_label.configure(background=COLORS["bg_card"])
        self.mod_label.pack()

    def update_values(self, score: int, modifier: str):
        self.score_var.set(str(score))
        self.mod_var.set(modifier)
        mod_val = int(modifier.replace("+", "")) if modifier.startswith("+") else int(modifier)
        if mod_val > 0:
            self.mod_label.configure(foreground=COLORS["positive"])
        elif mod_val < 0:
            self.mod_label.configure(foreground=COLORS["negative"])
        else:
            self.mod_label.configure(foreground=COLORS["fg_dim"])
