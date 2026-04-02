"""Reusable custom widgets for the character creator."""

import math
import os
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from gui.theme import COLORS, FONTS


def _wheel_units(event, source_name: str = "MouseWheel") -> float:
    """Normalise wheel/touchpad delta to scroll units.

    - MouseWheel events are normalized from 120-based deltas (Windows/Linux)
      and small deltas (macOS).
    - TouchpadScroll events on some Tk/macOS builds report wrapped 16-bit
      deltas (e.g. 65520 for -16), so we unwrap and scale them.
    """
    delta = float(getattr(event, "delta", 0) or 0)
    if delta == 0:
        return 0

    if source_name.endswith("TouchpadScroll"):
        # Unwrap 16-bit signed values (Tk 9 on macOS may expose wrapped deltas).
        signed_delta = ((int(round(delta)) + 32768) % 65536) - 32768
        units = -signed_delta / 240.0
    elif sys.platform == "darwin":
        # Tk on macOS can report either small smooth deltas (trackpad)
        # or 120-based wheel deltas (some mice/drivers).
        if abs(delta) >= 100:
            units = -delta / 120.0
        else:
            units = -delta
    else:
        units = -delta / 120.0

    return units


_WHEEL_CANVAS_ATTR = "_vibednd_wheel_canvas"
_GLOBAL_WHEEL_BINDING_INSTALLED = False
_WHEEL_BOUND_TOPLEVELS: set[str] = set()
_CLASS_WHEEL_BINDING_INSTALLED = False
_TOUCHPAD_PIXELS_PER_UNIT = 13.0


def _quantize_wheel_units(raw_units: float) -> int:
    if raw_units == 0:
        return 0

    if raw_units > 0:
        units_int = max(1, int(round(raw_units)))
    else:
        units_int = min(-1, int(round(raw_units)))

    max_units = 6
    if units_int > max_units:
        return max_units
    if units_int < -max_units:
        return -max_units
    return units_int


def _canvas_scrollable_pixels(canvas: tk.Canvas) -> float:
    try:
        region = canvas.cget("scrollregion") or ""
        if region:
            parts = [float(p) for p in str(region).split()]
            if len(parts) == 4:
                total_height = max(parts[3] - parts[1], 0.0)
            else:
                total_height = 0.0
        else:
            total_height = 0.0
    except (tk.TclError, ValueError):
        total_height = 0.0

    if total_height <= 0:
        try:
            bbox = canvas.bbox("all")
            total_height = float(max((bbox[3] - bbox[1]) if bbox else 0, 0))
        except tk.TclError:
            total_height = 0.0

    try:
        viewport_height = float(max(canvas.winfo_height(), 1))
    except tk.TclError:
        return 0.0

    return max(total_height - viewport_height, 0.0)


def _scroll_touchpad(canvas: tk.Canvas, raw_units: float) -> bool:
    if raw_units == 0:
        return False

    scrollable_px = _canvas_scrollable_pixels(canvas)
    if scrollable_px <= 0:
        return False

    try:
        first, last = canvas.yview()
    except tk.TclError:
        return False

    visible = max(last - first, 0.0)
    max_first = max(1.0 - visible, 0.0)
    if max_first <= 0:
        return False

    delta_fraction = (raw_units * _TOUCHPAD_PIXELS_PER_UNIT) / scrollable_px
    target = first + delta_fraction
    if target < 0.0:
        target = 0.0
    elif target > max_first:
        target = max_first

    if abs(target - first) < 1e-9:
        return False

    try:
        canvas.yview_moveto(target)
    except tk.TclError:
        return False
    return True


def _wheel_debug(msg: str):
    if os.environ.get("VIBEDND_DEBUG_WHEEL"):
        print(f"[wheel] {msg}")


def _nearest_wheel_canvas(widget) -> tk.Canvas | None:
    current = widget
    while current is not None:
        canvas = getattr(current, _WHEEL_CANVAS_ATTR, None)
        if isinstance(canvas, tk.Canvas):
            try:
                if int(canvas.winfo_exists()) and canvas.winfo_ismapped():
                    return canvas
            except tk.TclError:
                return None
        current = getattr(current, "master", None)
    return None


def _canvas_for_wheel_event(event) -> tk.Canvas | None:
    widget = getattr(event, "widget", None)
    if widget is None:
        return None

    try:
        top = widget.winfo_toplevel()
    except tk.TclError:
        top = widget

    try:
        pointer_x, pointer_y = widget.winfo_pointerxy()
        hovered = top.winfo_containing(pointer_x, pointer_y)
    except tk.TclError:
        hovered = None
    if hovered is not None:
        canvas = _nearest_wheel_canvas(hovered)
        if canvas is not None:
            return canvas

    x_root = getattr(event, "x_root", None)
    y_root = getattr(event, "y_root", None)
    if x_root is not None and y_root is not None:
        try:
            hovered = top.winfo_containing(x_root, y_root)
        except tk.TclError:
            hovered = None
        if hovered is not None:
            canvas = _nearest_wheel_canvas(hovered)
            if canvas is not None:
                return canvas

    return _nearest_wheel_canvas(widget)


def _dispatch_delta_scroll(event, source_name: str):
    canvas = _canvas_for_wheel_event(event)
    if canvas is None:
        _wheel_debug(f"{source_name} ignored: no target canvas")
        return None

    raw_units = _wheel_units(event, source_name=source_name)
    if source_name.endswith("TouchpadScroll"):
        moved = _scroll_touchpad(canvas, raw_units)
        if not moved:
            _wheel_debug(f"{source_name} ignored: no movement (raw={raw_units:.4f})")
            return None
        _wheel_debug(f"{source_name} -> {canvas} mode=moveto raw={raw_units:.4f}")
        return "break"

    units = _quantize_wheel_units(raw_units)
    if units == 0:
        _wheel_debug(f"{source_name} ignored: computed 0 units (raw={raw_units:.4f})")
        return None

    try:
        canvas.yview_scroll(units, "units")
    except tk.TclError:
        _wheel_debug(f"{source_name} ignored: target canvas no longer valid")
        return None
    _wheel_debug(f"{source_name} -> {canvas} units={units} raw={raw_units:.4f}")
    return "break"


def _dispatch_mousewheel(event):
    return _dispatch_delta_scroll(event, "MouseWheel")


def _dispatch_touchpad_scroll(event):
    return _dispatch_delta_scroll(event, "TouchpadScroll")


def _dispatch_shift_mousewheel(event):
    return _dispatch_delta_scroll(event, "Shift-MouseWheel")


def _dispatch_shift_touchpad_scroll(event):
    return _dispatch_delta_scroll(event, "Shift-TouchpadScroll")


def _dispatch_option_mousewheel(event):
    return _dispatch_delta_scroll(event, "Option-MouseWheel")


def _dispatch_command_mousewheel(event):
    return _dispatch_delta_scroll(event, "Command-MouseWheel")


def _dispatch_option_touchpad_scroll(event):
    return _dispatch_delta_scroll(event, "Option-TouchpadScroll")


def _dispatch_command_touchpad_scroll(event):
    return _dispatch_delta_scroll(event, "Command-TouchpadScroll")


def _bind_wheel_sequences(bind_fn):
    sequences = [
        ("<MouseWheel>", _dispatch_mousewheel),
        ("<TouchpadScroll>", _dispatch_touchpad_scroll),
        ("<Shift-MouseWheel>", _dispatch_shift_mousewheel),
        ("<Shift-TouchpadScroll>", _dispatch_shift_touchpad_scroll),
        ("<Option-MouseWheel>", _dispatch_option_mousewheel),
        ("<Option-TouchpadScroll>", _dispatch_option_touchpad_scroll),
        ("<Command-MouseWheel>", _dispatch_command_mousewheel),
        ("<Command-TouchpadScroll>", _dispatch_command_touchpad_scroll),
    ]
    for seq, handler in sequences:
        try:
            bind_fn(seq, handler)
        except tk.TclError:
            pass


def _dispatch_button4(event):
    canvas = _canvas_for_wheel_event(event)
    if canvas is None:
        _wheel_debug("Button-4 ignored: no target canvas")
        return None
    try:
        canvas.yview_scroll(-1, "units")
    except tk.TclError:
        _wheel_debug("Button-4 ignored: target canvas no longer valid")
        return None
    _wheel_debug(f"Button-4 -> {canvas} units=-1")
    return "break"


def _dispatch_button5(event):
    canvas = _canvas_for_wheel_event(event)
    if canvas is None:
        _wheel_debug("Button-5 ignored: no target canvas")
        return None
    try:
        canvas.yview_scroll(1, "units")
    except tk.TclError:
        _wheel_debug("Button-5 ignored: target canvas no longer valid")
        return None
    _wheel_debug(f"Button-5 -> {canvas} units=1")
    return "break"


def _ensure_global_wheel_binding(widget):
    global _GLOBAL_WHEEL_BINDING_INSTALLED
    if _GLOBAL_WHEEL_BINDING_INSTALLED:
        _ensure_toplevel_wheel_binding(widget)
        _ensure_class_wheel_bindings(widget)
        return

    _bind_wheel_sequences(lambda seq, cb: widget.bind_all(seq, cb, add="+"))
    widget.bind_all("<Button-4>", _dispatch_button4, add="+")
    widget.bind_all("<Button-5>", _dispatch_button5, add="+")
    _GLOBAL_WHEEL_BINDING_INSTALLED = True
    _wheel_debug("Installed global wheel dispatcher")
    _ensure_toplevel_wheel_binding(widget)
    _ensure_class_wheel_bindings(widget)


def _ensure_toplevel_wheel_binding(widget):
    try:
        top = widget.winfo_toplevel()
    except tk.TclError:
        return

    top_key = str(top)
    if top_key in _WHEEL_BOUND_TOPLEVELS:
        return

    _bind_wheel_sequences(lambda seq, cb: top.bind(seq, cb, add="+"))
    top.bind("<Button-4>", _dispatch_button4, add="+")
    top.bind("<Button-5>", _dispatch_button5, add="+")
    _WHEEL_BOUND_TOPLEVELS.add(top_key)
    _wheel_debug(f"Installed toplevel wheel dispatcher for {top_key}")


def _ensure_class_wheel_bindings(widget):
    global _CLASS_WHEEL_BINDING_INSTALLED
    if _CLASS_WHEEL_BINDING_INSTALLED:
        return

    classes = (
        "Frame",
        "Label",
        "Button",
        "Checkbutton",
        "Radiobutton",
        "Canvas",
        "TFrame",
        "TLabel",
        "TButton",
        "TCheckbutton",
        "TRadiobutton",
        "TLabelframe",
    )
    for class_name in classes:
        _bind_wheel_sequences(
            lambda seq, cb, name=class_name: widget.bind_class(name, seq, cb, add="+")
        )
        widget.bind_class(class_name, "<Button-4>", _dispatch_button4, add="+")
        widget.bind_class(class_name, "<Button-5>", _dispatch_button5, add="+")

    _CLASS_WHEEL_BINDING_INSTALLED = True
    _wheel_debug("Installed class-level wheel dispatcher fallbacks")


def register_mousewheel_target(widget, canvas: tk.Canvas):
    setattr(widget, _WHEEL_CANVAS_ATTR, canvas)
    _ensure_global_wheel_binding(widget)


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


class FormattedDescription(tk.Text):
    """A read-only Text widget that renders multi-paragraph descriptions.

    Sub-headings (short lines ending with '.') are rendered in bold.
    Paragraph breaks (\\n\\n) produce visible spacing.
    Accepts the same font/foreground/background kwargs as WrappingLabel.
    """

    def __init__(
        self,
        master=None,
        text="",
        font=None,
        foreground=None,
        background=None,
        **kwargs,
    ):
        bg = background or kwargs.pop("bg", COLORS["bg"])
        fg = foreground or kwargs.pop("fg", COLORS["fg_dim"])
        base_font = font or FONTS["body_small"]

        super().__init__(
            master,
            wrap="word",
            borderwidth=0,
            highlightthickness=0,
            padx=0,
            pady=0,
            bg=bg,
            fg=fg,
            font=base_font,
            cursor="",
            spacing3=4,  # space after each line/paragraph
            **kwargs,
        )

        # Bold tag for sub-headings
        bold_font = (
            (base_font[0], base_font[1], "bold")
            if isinstance(base_font, tuple)
            else base_font
        )
        self.tag_configure("subheading", font=bold_font, foreground=fg)
        self.tag_configure("two_col_bullets", tabs=(260,))

        if text:
            self._set_text(text)

        self.configure(state="disabled")
        self._last_width = 0
        self.bind("<Configure>", self._on_configure)

    @staticmethod
    def _is_subheading(line: str) -> bool:
        return (
            len(line) < 50
            and line.endswith(".")
            and line[0].isupper()
            and line.count(".") == 1
            and len(line.split()) <= 4
            and not line.startswith("See ")
        )

    @staticmethod
    def _maybe_two_column_bullets(paragraph: str) -> str:
        """Render dense short bullet lists into two columns.

        Keeps long or complex bullet content as a single column.
        """
        lines = [line.strip() for line in paragraph.split("\n") if line.strip()]
        if len(lines) < 12:
            return paragraph
        if not all(line.startswith("• ") for line in lines):
            return paragraph

        items = [line[2:].strip() for line in lines]
        if not items:
            return paragraph

        # Only compact very short simple entries (e.g., Tinker's Magic item list).
        if any(len(item) > 22 for item in items):
            return paragraph
        if any("—" in item or ":" in item for item in items):
            return paragraph

        split = (len(items) + 1) // 2
        left = items[:split]
        right = items[split:]

        compact_lines = []
        for i in range(split):
            left_cell = f"• {left[i]}"
            if i < len(right):
                compact_lines.append(f"{left_cell}\t• {right[i]}")
            else:
                compact_lines.append(left_cell)
        return "\n".join(compact_lines)

    def _set_text(self, text: str):
        self.configure(state="normal")
        self.delete("1.0", "end")
        paragraphs = text.split("\n\n")
        first = True
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if not first:
                self.insert("end", "\n\n")  # blank line between paragraphs
            first = False
            if self._is_subheading(para):
                self.insert("end", para, "subheading")
            else:
                formatted = self._maybe_two_column_bullets(para)
                if "\t" in formatted:
                    self.insert("end", formatted, "two_col_bullets")
                else:
                    self.insert("end", formatted)
        self.configure(state="disabled")

    def _on_configure(self, event):
        if abs(event.width - self._last_width) < 3:
            return
        self._last_width = event.width
        self.after_idle(self._resize_height)

    def _resize_height(self):
        self.update_idletasks()
        # Count how many display lines the text occupies
        num_lines = int(self.index("end-1c").split(".")[0])
        total_display_lines = 0
        for i in range(1, num_lines + 1):
            info = self.dlineinfo(f"{i}.0")
            if info is None:
                # Widget not yet mapped; estimate
                total_display_lines += 1
                continue
            # Count wrapped display lines for this text line
            bbox_start = self.count(f"{i}.0", f"{i}.end", "displaylines")
            if bbox_start:
                total_display_lines += bbox_start[0] + 1
            else:
                total_display_lines += 1

        if total_display_lines > 0:
            self.configure(height=total_display_lines)


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

    def __init__(
        self,
        parent,
        on_select=None,
        on_sub_select=None,
        horizontal_scroll: bool = False,
        **kwargs,
    ):
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
        self._horizontal_scroll = horizontal_scroll

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

        if self._horizontal_scroll:
            xscroll = ttk.Scrollbar(
                self, orient=tk.HORIZONTAL, command=self.listbox.xview
            )
            self.listbox.configure(xscrollcommand=xscroll.set)
            xscroll.pack(fill=tk.X, padx=2, pady=(2, 0))

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

    def __init__(
        self,
        parent,
        inner_padding: int = 16,
        auto_hide_scrollbar: bool = False,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self._inner_pad = inner_padding
        self._auto_hide_scrollbar = auto_hide_scrollbar
        self._scrollbar_visible = True

        self.canvas = tk.Canvas(
            self, bg=COLORS["bg"], highlightthickness=0, borderwidth=0
        )
        self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, padding=inner_padding)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Make inner frame fill canvas width
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mousewheel scrolling
        register_mousewheel_target(self, self.canvas)
        register_mousewheel_target(self.canvas, self.canvas)
        register_mousewheel_target(self.inner, self.canvas)

    def _on_inner_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_scrollbar_visibility()

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        self._update_scrollbar_visibility()

    def _update_scrollbar_visibility(self):
        if not self._auto_hide_scrollbar:
            return

        bbox = self.canvas.bbox("all")
        content_height = max((bbox[3] - bbox[1]) if bbox else 0, 0)
        viewport_height = max(self.canvas.winfo_height(), 1)
        should_show = content_height > viewport_height + 1

        if should_show and not self._scrollbar_visible:
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self._scrollbar_visible = True
        elif not should_show and self._scrollbar_visible:
            self.scrollbar.pack_forget()
            self._scrollbar_visible = False


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

        self.focus_set()
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

        self.focus_set()

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


# ---------------------------------------------------------------------------
# Mythic Modern widgets
# ---------------------------------------------------------------------------


class NavButton(tk.Frame):
    """Sidebar navigation item with step name, subtitle, active indicator, and hover."""

    def __init__(
        self,
        parent,
        text: str,
        key: str,
        icon_char: str = "",
        on_click=None,
        subtitle: str = "",
        **kwargs,
    ):
        super().__init__(parent, bg=COLORS["bg_surface"], cursor="hand2", **kwargs)
        self.key = key
        self._on_click = on_click
        self._active = False
        self._locked = False
        self._completed = False

        # Accent left-border indicator (hidden by default)
        self._indicator = tk.Frame(self, bg=COLORS["bg_surface"], width=3)
        self._indicator.pack(side=tk.LEFT, fill=tk.Y)

        # Content area
        self._inner = tk.Frame(self, bg=COLORS["bg_surface"])
        self._inner.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 12), pady=6)

        # Text column
        self._text_col = tk.Frame(self._inner, bg=COLORS["bg_surface"])
        self._text_col.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._label = tk.Label(
            self._text_col,
            text=text,
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
            anchor="w",
        )
        self._label.pack(fill=tk.X)

        self._subtitle = tk.Label(
            self._text_col,
            text=subtitle or "",
            font=FONTS["nav_subtitle"],
            fg=COLORS["sidebar_locked_fg"],
            bg=COLORS["bg_surface"],
            anchor="w",
            justify=tk.LEFT,
            wraplength=190,
        )
        if subtitle:
            self._subtitle.pack(fill=tk.X)

        # Keep icon ref for backward compat but don't display
        self._icon = None

        # Bind click and hover to all child widgets
        self._bind_all_children()

    def _bind_all_children(self):
        widgets = [self, self._inner, self._text_col, self._label, self._subtitle]
        for widget in widgets:
            widget.bind("<Button-1>", self._handle_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _handle_click(self, _event=None):
        if self._locked:
            return
        if self._on_click:
            self._on_click(self.key)

    def _on_enter(self, _event=None):
        if not self._active and not self._locked:
            bg = COLORS["bg_container"]
            self.configure(bg=bg)
            for child in self.winfo_children():
                self._set_bg_recursive(child, bg)

    def _on_leave(self, _event=None):
        if not self._active and not self._locked:
            bg = COLORS["bg_surface"]
            self.configure(bg=bg)
            for child in self.winfo_children():
                self._set_bg_recursive(child, bg)

    def set_subtitle(self, text: str):
        self._subtitle.configure(text=text)
        if text:
            self._subtitle.pack(fill=tk.X)
        else:
            self._subtitle.pack_forget()

    def set_status(self, active: bool = False, completed: bool = False, locked: bool = False):
        """Update visual state: active, completed, or locked."""
        self._active = active
        self._locked = locked
        self._completed = completed

        if locked:
            bg = COLORS["bg_surface"]
            fg = COLORS["sidebar_locked_fg"]
            sub_fg = COLORS["sidebar_locked_fg"]
            indicator_bg = COLORS["outline_dim"]
            self.configure(cursor="")
        elif active:
            bg = COLORS["bg_container"]
            fg = COLORS["accent_text"]
            sub_fg = COLORS["accent_text"]
            indicator_bg = COLORS["accent"]
            self.configure(cursor="hand2")
        elif completed:
            bg = COLORS["bg_surface"]
            fg = COLORS["fg_dim"]
            sub_fg = COLORS["sidebar_completed_fg"]
            indicator_bg = COLORS["outline_dim"]
            self.configure(cursor="hand2")
        else:
            bg = COLORS["bg_surface"]
            fg = COLORS["fg_dim"]
            sub_fg = COLORS["sidebar_locked_fg"]
            indicator_bg = COLORS["bg_surface"]
            self.configure(cursor="hand2")

        self._indicator.configure(bg=indicator_bg)
        self.configure(bg=bg)
        for child in self.winfo_children():
            self._set_bg_recursive(child, bg)
        self._label.configure(fg=fg)
        self._subtitle.configure(fg=sub_fg)

    def set_active(self, active: bool):
        """Backward-compatible: set active state only."""
        if active:
            self.set_status(active=True)
        else:
            self.set_status(active=False, completed=self._completed, locked=self._locked)

    @staticmethod
    def _set_bg_recursive(widget, bg):
        try:
            widget.configure(bg=bg)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            NavButton._set_bg_recursive(child, bg)


class WizardNavButton(tk.Frame):
    """Creator-only navigation item with a compact vertical pill indicator."""

    _INDICATOR_WIDTH = 10
    _INDICATOR_HEIGHT = 36
    _INDICATOR_OUTER_WIDTH = 5
    _INDICATOR_INNER_WIDTH = 3
    _INDICATOR_RADIUS = 2

    def __init__(
        self,
        parent,
        text: str,
        key: str,
        icon_char: str = "",
        on_click=None,
        subtitle: str = "",
        **kwargs,
    ):
        super().__init__(parent, bg=COLORS["bg_surface"], cursor="hand2", **kwargs)
        self.key = key
        self._on_click = on_click
        self._active = False
        self._locked = False
        self._completed = False

        self._indicator = tk.Canvas(
            self,
            width=self._INDICATOR_WIDTH,
            height=self._INDICATOR_HEIGHT,
            highlightthickness=0,
            bd=0,
            relief="flat",
            bg=COLORS["bg_surface"],
            cursor="hand2",
        )
        self._indicator.pack(side=tk.LEFT, padx=(4, 14), pady=2)
        self._indicator.bind("<Configure>", lambda _event: self._redraw_indicator())

        self._inner = tk.Frame(self, bg=COLORS["bg_surface"])
        self._inner.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), pady=4)

        self._text_col = tk.Frame(self._inner, bg=COLORS["bg_surface"])
        self._text_col.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._label = tk.Label(
            self._text_col,
            text=text,
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
            anchor="w",
        )
        self._label.pack(fill=tk.X)

        self._subtitle = tk.Label(
            self._text_col,
            text=subtitle or "",
            font=FONTS["nav_subtitle"],
            fg=COLORS["sidebar_locked_fg"],
            bg=COLORS["bg_surface"],
            anchor="w",
            justify=tk.LEFT,
            wraplength=180,
        )
        if subtitle:
            self._subtitle.pack(fill=tk.X, pady=(2, 0))

        self._icon = None
        self._bind_all_children()
        self._redraw_indicator()

    def _bind_all_children(self):
        widgets = [self, self._indicator, self._inner, self._text_col, self._label, self._subtitle]
        for widget in widgets:
            widget.bind("<Button-1>", self._handle_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _handle_click(self, _event=None):
        if self._locked:
            return
        if self._on_click:
            self._on_click(self.key)

    def _on_enter(self, _event=None):
        if not self._active and not self._locked:
            bg = COLORS["bg_container"]
            self.configure(bg=bg)
            for child in self.winfo_children():
                self._set_bg_recursive(child, bg)
            self._redraw_indicator()

    def _on_leave(self, _event=None):
        if not self._active and not self._locked:
            bg = COLORS["bg_surface"]
            self.configure(bg=bg)
            for child in self.winfo_children():
                self._set_bg_recursive(child, bg)
            self._redraw_indicator()

    def set_subtitle(self, text: str):
        self._subtitle.configure(text=text)
        if text:
            self._subtitle.pack(fill=tk.X, pady=(2, 0))
        else:
            self._subtitle.pack_forget()

    def set_status(self, active: bool = False, completed: bool = False, locked: bool = False):
        self._active = active
        self._locked = locked
        self._completed = completed

        if locked:
            bg = COLORS["bg_surface"]
            fg = COLORS["sidebar_locked_fg"]
            sub_fg = COLORS["sidebar_locked_fg"]
            self.configure(cursor="")
        elif active:
            bg = COLORS["bg_surface"]
            fg = COLORS["accent_text"]
            sub_fg = COLORS["accent_text"]
            self.configure(cursor="hand2")
        elif completed:
            bg = COLORS["bg_surface"]
            fg = COLORS["fg_dim"]
            sub_fg = COLORS["sidebar_completed_fg"]
            self.configure(cursor="hand2")
        else:
            bg = COLORS["bg_surface"]
            fg = COLORS["fg_dim"]
            sub_fg = COLORS["sidebar_locked_fg"]
            self.configure(cursor="hand2")

        self.configure(bg=bg)
        for child in self.winfo_children():
            self._set_bg_recursive(child, bg)
        self._label.configure(fg=fg)
        self._subtitle.configure(fg=sub_fg)
        self._redraw_indicator()

    def set_active(self, active: bool):
        if active:
            self.set_status(active=True)
        else:
            self.set_status(active=False, completed=self._completed, locked=self._locked)

    def _indicator_colors(self) -> tuple[str, str]:
        if self._active:
            return (
                COLORS["sidebar_indicator_active_outer"],
                COLORS["sidebar_indicator_active_inner"],
            )
        if self._completed:
            return (
                COLORS["sidebar_indicator_completed_outer"],
                COLORS["sidebar_indicator_completed_inner"],
            )
        return (
            COLORS["sidebar_indicator_locked_outer"],
            COLORS["sidebar_indicator_locked_inner"],
        )

    def _redraw_indicator(self):
        if not self._indicator.winfo_exists():
            return

        width = max(self._indicator.winfo_width(), self._INDICATOR_WIDTH)
        height = max(self._indicator.winfo_height(), self._INDICATOR_HEIGHT)
        self._indicator.delete("all")

        top = 1
        bottom = height - 1
        center_x = width / 2.0
        outer_color, inner_color = self._indicator_colors()

        self._draw_pill(
            center_x - (self._INDICATOR_OUTER_WIDTH / 2.0),
            top,
            center_x + (self._INDICATOR_OUTER_WIDTH / 2.0),
            bottom,
            outer_color,
        )
        self._draw_pill(
            center_x - (self._INDICATOR_INNER_WIDTH / 2.0),
            top + 1,
            center_x + (self._INDICATOR_INNER_WIDTH / 2.0),
            bottom - 1,
            inner_color,
        )

    def _draw_pill(self, x0: float, y0: float, x1: float, y1: float, fill: str):
        radius = min(self._INDICATOR_RADIUS, max((x1 - x0) / 2.0, 1.0), max((y1 - y0) / 2.0, 1.0))
        if (y1 - y0) <= (radius * 2.0):
            self._indicator.create_oval(x0, y0, x1, y1, fill=fill, outline=fill)
            return

        self._indicator.create_arc(
            x0, y0, x0 + (radius * 2.0), y0 + (radius * 2.0),
            start=90,
            extent=90,
            style=tk.PIESLICE,
            fill=fill,
            outline=fill,
        )
        self._indicator.create_arc(
            x1 - (radius * 2.0), y0, x1, y0 + (radius * 2.0),
            start=0,
            extent=90,
            style=tk.PIESLICE,
            fill=fill,
            outline=fill,
        )
        self._indicator.create_arc(
            x0, y1 - (radius * 2.0), x0 + (radius * 2.0), y1,
            start=180,
            extent=90,
            style=tk.PIESLICE,
            fill=fill,
            outline=fill,
        )
        self._indicator.create_arc(
            x1 - (radius * 2.0), y1 - (radius * 2.0), x1, y1,
            start=270,
            extent=90,
            style=tk.PIESLICE,
            fill=fill,
            outline=fill,
        )
        self._indicator.create_rectangle(
            x0 + radius, y0, x1 - radius, y1,
            fill=fill,
            outline=fill,
        )
        self._indicator.create_rectangle(
            x0, y0 + radius, x1, y1 - radius,
            fill=fill,
            outline=fill,
        )

    @staticmethod
    def _set_bg_recursive(widget, bg):
        try:
            widget.configure(bg=bg)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            WizardNavButton._set_bg_recursive(child, bg)


class StatCard(tk.Frame):
    """Bento-style stat card: uppercase label, large number, optional modifier badge."""

    def __init__(
        self,
        parent,
        label: str,
        value: str = "",
        modifier: str = "",
        suffix: str = "",
        highlight: bool = False,
        **kwargs,
    ):
        _bg = COLORS["bg_surface"]
        super().__init__(
            parent,
            bg=_bg,
            padx=20,
            pady=16,
            highlightthickness=0,
            **kwargs,
        )
        self._card_bg = _bg

        # Uppercase stat name
        self._lbl = tk.Label(
            self,
            text=label.upper(),
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=_bg,
        )
        self._lbl.pack()

        # Large number (+ inline suffix if present)
        if suffix:
            val_row = tk.Frame(self, bg=_bg)
            val_row.pack()
            self._val = tk.Label(
                val_row,
                text=value,
                font=FONTS["stat_large"],
                fg=COLORS["fg"],
                bg=_bg,
            )
            self._val.pack(side=tk.LEFT)
            self._suffix = tk.Label(
                val_row,
                text=suffix,
                font=FONTS["body_small"],
                fg=COLORS["fg_dim"],
                bg=_bg,
            )
            self._suffix.pack(side=tk.LEFT, padx=(4, 0), anchor="s", pady=(0, 4))
        else:
            self._val = tk.Label(
                self,
                text=value,
                font=FONTS["stat_large"],
                fg=COLORS["fg"],
                bg=_bg,
            )
            self._val.pack()
            self._suffix = None

        # Modifier badge
        self._mod_frame = None
        self._mod_lbl = None
        if modifier:
            self._build_modifier(modifier)

        if highlight:
            self._apply_highlight()

    def _build_modifier(self, modifier: str):
        mod_bg = COLORS["bg_container"]
        self._mod_frame = tk.Frame(self, bg=mod_bg, padx=8, pady=2)
        self._mod_frame.pack(pady=(4, 0))
        self._mod_lbl = tk.Label(
            self._mod_frame,
            text=modifier,
            font=FONTS["body_bold"],
            fg=COLORS["fg"],
            bg=mod_bg,
        )
        self._mod_lbl.pack()

    def _apply_highlight(self):
        """Highlight card with accent ring (for proficient saves etc.)."""
        self.configure(highlightbackground="#4a2028", highlightthickness=1)
        self._lbl.configure(fg=COLORS["accent_text"])

    def update_values(self, value: str, modifier: str = "", highlight: bool = False):
        self._val.configure(text=value)
        if modifier and self._mod_lbl:
            self._mod_lbl.configure(text=modifier)
        elif modifier and not self._mod_lbl:
            self._build_modifier(modifier)
        if highlight:
            self._apply_highlight()
        else:
            self.configure(highlightthickness=0)
            self._lbl.configure(fg=COLORS["fg_dim"])


class SectionHeader(tk.Frame):
    """Serif italic heading with horizontal separator line and optional right label."""

    def __init__(
        self,
        parent,
        text: str,
        right_text: str = "",
        **kwargs,
    ):
        super().__init__(parent, bg=COLORS["bg"], **kwargs)

        self._heading = tk.Label(
            self,
            text=text,
            font=FONTS["heading_serif"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
        )
        self._heading.pack(side=tk.LEFT, padx=(0, 12))

        # Horizontal line (subtle)
        self._line = tk.Frame(self, bg=COLORS["border_subtle"], height=1)
        self._line.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=1)

        if right_text:
            self._right = tk.Label(
                self,
                text=right_text.upper(),
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg"],
            )
            self._right.pack(side=tk.RIGHT, padx=(12, 0))
        else:
            self._right = None

    def set_bg(self, bg: str):
        """Update background for all parts of the header."""
        self.configure(bg=bg)
        self._heading.configure(bg=bg)
        if self._right:
            self._right.configure(bg=bg)


class Chip(tk.Label):
    """Small tag/badge label — used for proficiencies, spell components, etc."""

    def __init__(
        self,
        parent,
        text: str,
        style: str = "gold",
        **kwargs,
    ):
        if style == "gold":
            bg = COLORS["gold_dark"]
            fg = COLORS["gold_on_dark"]
        elif style == "accent":
            bg = COLORS["accent"]
            fg = COLORS["accent_text"]
        else:
            bg = COLORS["bg_highest"]
            fg = COLORS["fg_dim"]

        super().__init__(
            parent,
            text=text.upper(),
            font=FONTS["label_tiny"],
            fg=fg,
            bg=bg,
            padx=10,
            pady=3,
            **kwargs,
        )


class HPBar(tk.Canvas):
    """Horizontal HP bar showing current/max with accent fill."""

    def __init__(self, parent, width: int = 200, height: int = 8, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=COLORS["bg_highest"],
            highlightthickness=0,
            **kwargs,
        )
        self._bar_height = height
        self._current = 0
        self._maximum = 1
        self.bind("<Configure>", lambda e: self._redraw())

    def set_hp(self, current: int, maximum: int):
        """Update the bar fill based on current/max HP."""
        self._current = current
        self._maximum = maximum
        self._redraw()

    def _redraw(self):
        """Redraw the bar using the actual widget width."""
        self.delete("all")
        if self._maximum <= 0:
            return

        bar_w = self.winfo_width()
        if bar_w <= 1:
            # Widget not yet rendered; fall back to requested width
            bar_w = self.winfo_reqwidth()

        ratio = max(0, min(1, self._current / self._maximum))
        fill_w = int(bar_w * ratio)

        color = COLORS["accent_text"]
        h = self._bar_height
        r = h // 2  # radius for rounded ends

        # Draw rounded trough (grey background)
        self.create_oval(0, 0, h, h, fill=COLORS["bg_highest"], outline="")
        self.create_oval(bar_w - h, 0, bar_w, h, fill=COLORS["bg_highest"], outline="")
        self.create_rectangle(r, 0, bar_w - r, h, fill=COLORS["bg_highest"], outline="")

        # Draw filled portion (red)
        if fill_w > h:
            self.create_oval(0, 0, h, h, fill=color, outline="")
            self.create_oval(fill_w - h, 0, fill_w, h, fill=color, outline="")
            self.create_rectangle(r, 0, fill_w - r, h, fill=color, outline="")
        elif fill_w > 0:
            self.create_oval(0, 0, h, h, fill=color, outline="")


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert #RRGGBB to (r, g, b) tuple."""
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert (r, g, b) to #RRGGBB."""
    return f"#{r:02x}{g:02x}{b:02x}"


def _lerp_color(c1: str, c2: str, t: float) -> str:
    """Linearly interpolate between two hex colors. t=0 → c1, t=1 → c2."""
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return _rgb_to_hex(
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    )


class CardFrame(tk.Frame):
    """Card container with subtle border and optional accent left stripe.

    Use ``.inner`` to pack children inside the card.
    """

    def __init__(
        self,
        parent,
        bg: str = COLORS["bg_surface"],
        border_color: str = COLORS["border_subtle"],
        accent_left: bool = False,
        pad: int = 20,
        **kwargs,
    ):
        super().__init__(
            parent,
            bg=bg,
            highlightbackground=border_color,
            highlightthickness=0,
            **kwargs,
        )

        if accent_left:
            tk.Frame(self, bg="#4a2028", width=3).pack(side=tk.LEFT, fill=tk.Y)

        self.inner = tk.Frame(self, bg=bg)
        self.inner.pack(fill=tk.BOTH, expand=True, padx=pad, pady=pad)

    def set_hover(self, hover_border: str = COLORS["border_medium"]):
        """Enable hover effect — border becomes more visible on mouse enter."""
        normal_border = self.cget("highlightbackground")
        self.bind("<Enter>", lambda _: self.configure(highlightbackground=hover_border))
        self.bind(
            "<Leave>", lambda _: self.configure(highlightbackground=normal_border)
        )


class GradientHeader(tk.Frame):
    """Hero header section with elevated background and accent bottom border.

    Children go in ``.inner``.  The section has a lighter surface background
    than the page body, plus a thin crimson accent line at the bottom to
    create clear visual separation.
    """

    def __init__(
        self,
        parent,
        color_top: str = COLORS["bg_hero"],
        color_bottom: str = COLORS["bg"],
        min_height: int = 120,
        **kwargs,
    ):
        kwargs.pop("highlightthickness", None)
        super().__init__(parent, bg=color_bottom, **kwargs)

        # Main content area with elevated bg
        self.inner = tk.Frame(self, bg=color_top)
        self.inner.pack(fill=tk.X, side=tk.TOP)

        # Subtle accent bottom border (muted crimson, 2px)
        accent_line = tk.Frame(self, bg="#4a2028", height=2)
        accent_line.pack(fill=tk.X, side=tk.TOP)
        accent_line.pack_propagate(False)


class PillBadge(tk.Canvas):
    """Pill-shaped badge with simulated glass background.

    Draws a rounded pill and places text centered inside it.
    """

    def __init__(
        self,
        parent,
        text: str = "",
        bg_color: str = COLORS["badge_glass"],
        fg_color: str = COLORS["gold"],
        font=None,
        **kwargs,
    ):
        self._text = text
        self._bg_color = bg_color
        self._fg_color = fg_color
        self._font = font or FONTS["label_tiny"]

        # Inherit parent background so canvas blends in
        try:
            parent_bg = parent.cget("bg") or parent.cget("background")
        except Exception:
            parent_bg = COLORS["bg"]
        super().__init__(
            parent,
            highlightthickness=0,
            bg=parent_bg,
            **kwargs,
        )
        self._draw_id = None
        self.bind("<Configure>", self._redraw)
        # Initial draw after idle so geometry is known
        self.after_idle(self._measure_and_draw)

    def _measure_and_draw(self):
        # Temporary text to measure
        tmp = self.create_text(0, 0, text=self._text, font=self._font, anchor="nw")
        bbox = self.bbox(tmp)
        self.delete(tmp)
        if not bbox:
            return
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad_x, pad_y = 14, 6
        w = tw + pad_x * 2
        h = th + pad_y * 2
        self.configure(width=w, height=h)
        self._draw(w, h)

    def _redraw(self, event=None):
        w = self.winfo_width()
        h = self.winfo_height()
        if w > 1 and h > 1:
            self._draw(w, h)

    def _draw(self, w: int, h: int):
        self.delete("all")
        r = h // 2  # full pill radius

        # Draw pill shape
        self.create_oval(0, 0, h, h, fill=self._bg_color, outline="")
        self.create_oval(w - h, 0, w, h, fill=self._bg_color, outline="")
        if w > h:
            self.create_rectangle(r, 0, w - r, h, fill=self._bg_color, outline="")

        # Draw subtle border
        self.create_arc(
            0,
            0,
            h,
            h,
            start=90,
            extent=180,
            outline=COLORS["border_medium"],
            style="arc",
        )
        self.create_arc(
            w - h,
            0,
            w,
            h,
            start=270,
            extent=180,
            outline=COLORS["border_medium"],
            style="arc",
        )
        self.create_line(r, 0, w - r, 0, fill=COLORS["border_medium"])
        self.create_line(r, h, w - r, h, fill=COLORS["border_medium"])

        # Centered text
        self.create_text(
            w // 2,
            h // 2,
            text=self._text,
            font=self._font,
            fill=self._fg_color,
            anchor="center",
        )

    def set_text(self, text: str):
        self._text = text
        self._measure_and_draw()


class StepperButton(tk.Canvas):
    """Ghost-style +/− button that blends into card surfaces.

    At rest only a dim symbol is visible. On hover a soft rounded rectangle
    appears; on press the fill darkens for click feedback.
    """

    def __init__(
        self,
        parent,
        text: str = "+",
        command=None,
        size: int = 22,
        **kwargs,
    ):
        self._sym = text
        self._command = command
        self._size = size

        # Match parent background so canvas is invisible
        try:
            parent_bg = parent.cget("bg") or parent.cget("background")
        except Exception:
            parent_bg = COLORS["bg_surface"]
        self._parent_bg = parent_bg

        super().__init__(
            parent,
            width=size,
            height=size,
            highlightthickness=0,
            bg=parent_bg,
            cursor="hand2",
            **kwargs,
        )

        self._hovered = False
        self._pressed = False

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.after_idle(self._draw)

    # ── drawing ──────────────────────────────────────────────

    def _rounded_rect(self, x1, y1, x2, y2, r, **kw):
        """Draw a rounded rectangle on the canvas."""
        points = [
            x1 + r,
            y1,
            x2 - r,
            y1,
            x2,
            y1,
            x2,
            y1 + r,
            x2,
            y2 - r,
            x2,
            y2,
            x2 - r,
            y2,
            x1 + r,
            y2,
            x1,
            y2,
            x1,
            y2 - r,
            x1,
            y1 + r,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, **kw)

    def _draw(self):
        self.delete("all")
        s = self._size

        if self._pressed:
            self._rounded_rect(
                0,
                0,
                s,
                s,
                4,
                fill=COLORS["bg_high"],
                outline=COLORS["border_subtle"],
            )
            text_color = COLORS["fg"]
        elif self._hovered:
            self._rounded_rect(
                0,
                0,
                s,
                s,
                4,
                fill=COLORS["bg_container"],
                outline=COLORS["border_subtle"],
            )
            text_color = COLORS["fg"]
        else:
            text_color = COLORS["fg_dim"]

        self.create_text(
            s // 2,
            s // 2,
            text=self._sym,
            font=FONTS["body_bold"],
            fill=text_color,
            anchor="center",
        )

    # ── event handlers ───────────────────────────────────────

    def _on_enter(self, _event=None):
        self._hovered = True
        self._draw()

    def _on_leave(self, _event=None):
        self._hovered = False
        self._pressed = False
        self._draw()

    def _on_press(self, _event=None):
        self._pressed = True
        self._draw()

    def _on_release(self, _event=None):
        self._pressed = False
        self._draw()
        if self._hovered and self._command:
            self._command()


class StepperPair(tk.Frame):
    """Vertically stacked + / − ghost buttons."""

    def __init__(self, parent, on_increment, on_decrement, size: int = 22, **kwargs):
        try:
            parent_bg = parent.cget("bg") or parent.cget("background")
        except Exception:
            parent_bg = COLORS["bg_surface"]
        super().__init__(parent, bg=parent_bg, **kwargs)
        StepperButton(self, text="+", command=on_increment, size=size).pack(
            side=tk.TOP,
            pady=(0, 1),
        )
        StepperButton(self, text="\u2212", command=on_decrement, size=size).pack(
            side=tk.TOP,
        )


# ── Tile Grid widgets for substep selection views ────────────────────

from gui.theme import SPACING

try:
    from PIL import Image as _PILImage, ImageDraw as _PILImageDraw, ImageTk as _PILImageTk
except ImportError:
    _PILImage = _PILImageDraw = _PILImageTk = None

_TILE_BASE_IMAGE_CACHE: dict[tuple[str, int, int], object | None] = {}
_TILE_RENDER_CACHE: dict[tuple[str | None, int, int, str], tuple[object | None, object | None]] = {}


class OptionTile(tk.Frame):
    """A clickable tile card for species/class/background selection.

    Displays the image filling the entire tile with a gradient overlay
    at the bottom where name and trait text are rendered — matching the
    Archive card style from the home screen. Background tiles can opt into
    a text-led lore-card variant that does not require artwork.
    """

    TILE_WIDTH = 310
    TILE_HEIGHT = 380
    OVERLAY_HEIGHT = 120

    def __init__(
        self,
        parent,
        name: str,
        description: str = "",
        traits: list[str] | None = None,
        image_path: str | None = None,
        variant: str | None = None,
        tile_width: int | None = None,
        tile_height: int | None = None,
        on_click=None,
        **kwargs,
    ):
        tw = tile_width or self.TILE_WIDTH
        th = tile_height or self.TILE_HEIGHT
        self._variant = variant or "default"
        base_bg = COLORS["bg_surface"] if self._variant == "lore" else COLORS["tile_bg"]
        base_border = COLORS["border_medium"] if self._variant == "lore" else COLORS["tile_border"]
        super().__init__(
            parent,
            bg=base_bg,
            highlightbackground=base_border,
            highlightthickness=1,
            cursor="hand2",
            width=tw,
            height=th,
            **kwargs,
        )
        self.pack_propagate(False)
        self.grid_propagate(False)

        self._name = name
        self._description = " ".join((description or "").split())
        self._on_click = on_click
        self._traits = traits or []
        self._image_path = image_path
        self._tile_width = tw
        self._tile_height = th
        self._hovered = False
        self._photo_normal = None  # cached normal-state PhotoImage
        self._photo_hover = None   # cached hover-state PhotoImage
        self._last_render_size: tuple[int, int] = (0, 0)
        self._render_job = None
        self._canvas = None
        self._lore_content_pad_x = 18
        self._lore_feat_text = ""
        self._lore_feat = None
        self._lore_feat_label = None
        self._lore_feat_value = None
        self._lore_meta_rows: list[dict] = []

        if self._variant == "lore":
            self._build_lore_tile()
            self.bind("<Configure>", self._on_configure)
            self.after_idle(self._update_lore_layout)
        else:
            self._canvas = tk.Canvas(
                self,
                bg=COLORS["tile_bg"],
                highlightthickness=0,
                cursor="hand2",
            )
            self._canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)

            self._canvas.bind("<Button-1>", self._handle_click)
            self._canvas.bind("<Enter>", self._on_enter)
            self._canvas.bind("<Leave>", self._on_leave)
            self._canvas.bind("<Configure>", self._on_configure)

    def set_tile_size(self, width: int, height: int):
        width = max(1, int(width))
        height = max(1, int(height))
        if width == self._tile_width and height == self._tile_height:
            return

        self._tile_width = width
        self._tile_height = height
        self.configure(width=width, height=height)
        if self._variant == "lore":
            self._update_lore_layout()
        else:
            self._photo_normal = None
            self._photo_hover = None
            self._last_render_size = (0, 0)
            self._queue_render()

    def _build_lore_tile(self):
        surface = COLORS["bg_surface"]
        self._lore_shell = tk.Frame(self, bg=surface)
        self._lore_shell.pack(fill=tk.BOTH, expand=True)

        self._lore_top_band = tk.Frame(self._lore_shell, bg=COLORS["accent"], height=4)
        self._lore_top_band.pack(fill=tk.X)
        self._lore_top_band.pack_propagate(False)

        self._lore_content = tk.Frame(
            self._lore_shell,
            bg=surface,
            padx=self._lore_content_pad_x,
            pady=16,
        )
        self._lore_content.pack(fill=tk.BOTH, expand=True)

        self._lore_rule_row = tk.Frame(self._lore_content, bg=surface)
        self._lore_rule_row.pack(fill=tk.X, pady=(0, 10))

        self._lore_rule_short = tk.Frame(
            self._lore_rule_row,
            bg=COLORS["gold_dark"],
            width=34,
            height=2,
        )
        self._lore_rule_short.pack(side=tk.LEFT)
        self._lore_rule_short.pack_propagate(False)

        self._lore_rule_long = tk.Frame(
            self._lore_rule_row,
            bg=COLORS["border_subtle"],
            height=1,
        )
        self._lore_rule_long.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0), pady=(1, 0))
        self._lore_rule_long.pack_propagate(False)

        self._lore_eyebrow = tk.Label(
            self._lore_content,
            text="BACKGROUND",
            font=FONTS["label_upper_bold"],
            fg=COLORS["accent_text"],
            bg=surface,
            anchor="w",
        )
        self._lore_eyebrow.pack(fill=tk.X)

        self._lore_title = tk.Label(
            self._lore_content,
            text=self._name,
            font=FONTS["card_title_lg"],
            fg=COLORS["fg"],
            bg=surface,
            justify=tk.LEFT,
            anchor="w",
        )
        self._lore_title.pack(fill=tk.X, pady=(4, 0))

        self._lore_desc = tk.Label(
            self._lore_content,
            text=self._description,
            font=FONTS["tile_desc"],
            fg=COLORS["fg_dim"],
            bg=surface,
            justify=tk.LEFT,
            anchor="w",
        )
        if self._description:
            self._lore_desc.pack(fill=tk.X, pady=(8, 0))

        feat_text, meta_rows = self._split_lore_traits()
        self._lore_feat_text = feat_text
        if feat_text:
            self._lore_feat = tk.Frame(
                self._lore_content,
                bg=COLORS["bg_highest"],
                highlightbackground=COLORS["gold_dark"],
                highlightthickness=1,
                padx=10,
                pady=8,
            )
            self._lore_feat.pack(fill=tk.X, pady=(12, 0))

            self._lore_feat_label = tk.Label(
                self._lore_feat,
                text="FEAT",
                font=FONTS["label_tiny"],
                fg=COLORS["gold"],
                bg=COLORS["bg_highest"],
                anchor="w",
            )
            self._lore_feat_label.pack(anchor="w")

            self._lore_feat_value = tk.Label(
                self._lore_feat,
                text=feat_text,
                font=FONTS["body_bold"],
                fg=COLORS["fg"],
                bg=COLORS["bg_highest"],
                justify=tk.LEFT,
                anchor="w",
            )
            self._lore_feat_value.pack(fill=tk.X, pady=(4, 0))

        self._lore_meta = tk.Frame(self._lore_content, bg=surface)
        if meta_rows:
            self._lore_meta.pack(fill=tk.X, pady=(12, 0))

        for index, (label_text, value_text) in enumerate(meta_rows[:2]):
            row = tk.Frame(self._lore_meta, bg=surface)
            row.pack(fill=tk.X, pady=(0, 6 if index < len(meta_rows[:2]) - 1 else 0))

            tag = tk.Label(
                row,
                text=label_text.upper(),
                font=FONTS["label_tiny"],
                fg=COLORS["accent_text"],
                bg=COLORS["badge_glass"],
                padx=8,
                pady=3,
                anchor="center",
            )
            tag.pack(side=tk.LEFT, anchor="n", padx=(0, 8))

            value = tk.Label(
                row,
                text=value_text,
                font=FONTS["body_small"],
                fg=COLORS["fg_dim"],
                bg=surface,
                justify=tk.LEFT,
                anchor="w",
            )
            value.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._lore_meta_rows.append({
                "frame": row,
                "tag": tag,
                "value": value,
                "text": value_text,
            })

        self._lore_bottom_bar = tk.Frame(self._lore_shell, bg=COLORS["gold_dark"], height=3)
        self._lore_bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self._lore_bottom_bar.pack_propagate(False)

        self._apply_lore_state(False)
        self._bind_lore_interaction(self)

    def _bind_lore_interaction(self, widget):
        try:
            widget.configure(cursor="hand2")
        except tk.TclError:
            pass

        widget.bind("<Button-1>", self._handle_click, add="+")
        widget.bind("<Enter>", self._sync_lore_hover, add="+")
        widget.bind("<Leave>", self._sync_lore_hover, add="+")
        widget.bind("<Motion>", self._sync_lore_hover, add="+")

        for child in widget.winfo_children():
            self._bind_lore_interaction(child)

    def _split_lore_traits(self) -> tuple[str, list[tuple[str, str]]]:
        feat_text = ""
        meta_rows: list[tuple[str, str]] = []

        for raw_trait in self._traits:
            trait = " ".join(str(raw_trait).split())
            if not trait:
                continue

            label, separator, value = trait.partition(":")
            if separator:
                label = label.strip()
                value = value.strip()
            else:
                label = ""
                value = trait

            if label.lower() == "feat" and value and not feat_text:
                feat_text = value
                continue

            meta_rows.append(((label or "Detail").upper(), value or trait))

        return feat_text, meta_rows

    def _apply_lore_state(self, hovered: bool):
        surface = COLORS["bg_container"] if hovered else COLORS["bg_surface"]
        border = COLORS["outline"] if hovered else COLORS["border_medium"]
        feat_bg = COLORS["bg_high"] if hovered else COLORS["bg_highest"]
        tag_bg = COLORS["bg_highest"] if hovered else COLORS["badge_glass"]

        self.configure(bg=surface, highlightbackground=border)
        self._lore_shell.configure(bg=surface)
        self._lore_content.configure(bg=surface)
        self._lore_rule_row.configure(bg=surface)
        self._lore_top_band.configure(bg=COLORS["accent_text"] if hovered else COLORS["accent"])
        self._lore_rule_short.configure(bg=COLORS["gold"] if hovered else COLORS["gold_dark"])
        self._lore_rule_long.configure(bg=COLORS["outline_dim"] if hovered else COLORS["border_subtle"])
        self._lore_eyebrow.configure(bg=surface)
        self._lore_title.configure(bg=surface)
        self._lore_desc.configure(bg=surface, fg=COLORS["fg"] if hovered else COLORS["fg_dim"])

        if self._lore_feat is not None:
            self._lore_feat.configure(
                bg=feat_bg,
                highlightbackground=COLORS["gold"] if hovered else COLORS["gold_dark"],
            )
            self._lore_feat_label.configure(bg=feat_bg)
            self._lore_feat_value.configure(bg=feat_bg)

        self._lore_meta.configure(bg=surface)
        for row in self._lore_meta_rows:
            row["frame"].configure(bg=surface)
            row["tag"].configure(bg=tag_bg)
            row["value"].configure(bg=surface, fg=COLORS["fg"] if hovered else COLORS["fg_dim"])

        self._lore_bottom_bar.configure(bg=COLORS["gold"] if hovered else COLORS["gold_dark"])

    def _sync_lore_hover(self, _event=None):
        if self._variant != "lore":
            return

        try:
            pointer_x = self.winfo_pointerx() - self.winfo_rootx()
            pointer_y = self.winfo_pointery() - self.winfo_rooty()
            inside = (
                0 <= pointer_x < max(self.winfo_width(), 1)
                and 0 <= pointer_y < max(self.winfo_height(), 1)
            )
        except tk.TclError:
            inside = False

        if inside != self._hovered:
            self._hovered = inside
            self._apply_lore_state(inside)

    def _wrap_text_lines(self, text: str, font_spec, width: int) -> list[str]:
        normalized = " ".join((text or "").split())
        if not normalized:
            return []

        width = max(int(width), 1)
        font = tkfont.Font(font=font_spec)
        lines: list[str] = []
        current = ""

        for word in normalized.split():
            candidate = word if not current else f"{current} {word}"
            if current and font.measure(candidate) > width:
                lines.append(current)
                current = word
            else:
                current = candidate

        if current:
            lines.append(current)

        return lines

    def _truncate_wrapped_text(
        self,
        text: str,
        font_spec,
        width: int,
        max_lines: int,
    ) -> str:
        lines = self._wrap_text_lines(text, font_spec, width)
        if len(lines) <= max_lines:
            return "\n".join(lines)

        font = tkfont.Font(font=font_spec)
        visible = lines[:max_lines]
        last = visible[-1].rstrip()
        ellipsis = "..."
        while last and font.measure(f"{last}{ellipsis}") > width:
            if " " in last:
                last = last.rsplit(" ", 1)[0].rstrip()
            else:
                last = last[:-1].rstrip()

        visible[-1] = f"{last}{ellipsis}" if last else ellipsis
        return "\n".join(visible)

    def _update_lore_layout(self):
        if self._variant != "lore":
            return

        width = self.winfo_width()
        if width < 2:
            width = self._tile_width

        content_width = max(width - (self._lore_content_pad_x * 2), 80)
        title_text = self._truncate_wrapped_text(
            self._name,
            FONTS["card_title_lg"],
            content_width,
            max_lines=2,
        )
        self._lore_title.configure(text=title_text, wraplength=content_width)

        if self._description:
            desc_text = self._truncate_wrapped_text(
                self._description,
                FONTS["tile_desc"],
                content_width,
                max_lines=2,
            )
            self._lore_desc.configure(text=desc_text, wraplength=content_width)

        if self._lore_feat_value is not None:
            feat_width = max(content_width - 20, 80)
            feat_text = self._truncate_wrapped_text(
                self._lore_feat_text,
                FONTS["body_bold"],
                feat_width,
                max_lines=2,
            )
            self._lore_feat_value.configure(text=feat_text, wraplength=feat_width)

        meta_value_width = max(content_width - 84, 56)
        for row in self._lore_meta_rows:
            value_text = self._truncate_wrapped_text(
                row["text"],
                FONTS["body_small"],
                meta_value_width,
                max_lines=2,
            )
            row["value"].configure(text=value_text, wraplength=meta_value_width)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _queue_render(self):
        if self._variant == "lore":
            return
        if self._render_job is not None:
            return
        self._render_job = self.after_idle(self._perform_queued_render)

    def _perform_queued_render(self):
        self._render_job = None
        if self._variant == "lore" or self._canvas is None:
            return
        self._render(hovered=self._hovered)

    def _render(self, hovered: bool = False):
        """Composite the tile image with gradient overlay and draw text."""
        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if w < 2 or h < 2:
            w, h = self._tile_width, self._tile_height

        # Use cached image if size hasn't changed
        if (w, h) == self._last_render_size:
            photo = self._photo_hover if hovered else self._photo_normal
            if photo is not None:
                self._canvas.delete("all")
                self._canvas.create_image(w // 2, h // 2, image=photo)
                self._draw_text(w, h)
                return

        # Size changed — invalidate caches
        if (w, h) != self._last_render_size:
            self._photo_normal = None
            self._photo_hover = None
            self._last_render_size = (w, h)

        if _PILImage is not None:
            self._render_pil(w, h, hovered)
        else:
            self._render_fallback(w, h, hovered)

    def _render_pil(self, w: int, h: int, hovered: bool):
        """PIL-based rendering: composited image + gradient overlay."""
        cache_key = (self._image_path, w, h, "pil")
        cached = _TILE_RENDER_CACHE.get(cache_key)
        if cached is None:
            base = self._build_tile_image(w, h)
            if base is not None:
                img_normal = self._apply_overlay(base, w, h, hovered=False)
                img_hover = self._apply_overlay(base, w, h, hovered=True)
                cached = (
                    _PILImageTk.PhotoImage(img_normal),
                    _PILImageTk.PhotoImage(img_hover),
                )
            else:
                # Some source PNGs load in Tk but fail PIL decoding.
                fallback_photo = self._build_tk_tile_image(w, h)
                if fallback_photo is not None:
                    cached = (fallback_photo, fallback_photo)
                else:
                    base = _PILImage.new(
                        "RGBA",
                        (w, h),
                        _hex_to_rgb(COLORS["bg_high"]) + (255,),
                    )
                    img_normal = self._apply_overlay(base, w, h, hovered=False)
                    img_hover = self._apply_overlay(base, w, h, hovered=True)
                    cached = (
                        _PILImageTk.PhotoImage(img_normal),
                        _PILImageTk.PhotoImage(img_hover),
                    )
            _TILE_RENDER_CACHE[cache_key] = cached

        self._photo_normal, self._photo_hover = cached

        photo = self._photo_hover if hovered else self._photo_normal
        self._canvas.delete("all")
        self._canvas.create_image(w // 2, h // 2, image=photo)
        self._draw_text(w, h)

    def _render_fallback(self, w: int, h: int, hovered: bool):
        """Tk-only fallback when PIL is unavailable."""
        cache_key = (self._image_path, w, h, "tk")
        cached = _TILE_RENDER_CACHE.get(cache_key)
        if cached is None:
            photo = self._build_tk_tile_image(w, h)
            cached = (photo, photo)
            _TILE_RENDER_CACHE[cache_key] = cached
        self._photo_normal, self._photo_hover = cached

        self._canvas.delete("all")
        bg = COLORS["tile_hover"] if hovered else COLORS["tile_bg"]
        self._canvas.create_rectangle(0, 0, w, h, fill=bg, outline="")

        photo = self._photo_hover if hovered else self._photo_normal
        if photo is not None:
            self._canvas.create_image(w // 2, h // 2, image=photo)
            if hovered:
                self._canvas.create_rectangle(
                    0,
                    0,
                    w,
                    h,
                    fill=COLORS["bg_deepest"],
                    outline="",
                    stipple="gray50",
                )

        panel_top = h - self.OVERLAY_HEIGHT
        self._canvas.create_rectangle(
            0, panel_top, w, h,
            fill=COLORS["bg_surface"], outline=COLORS["outline_dim"], width=1,
        )
        self._draw_text(w, h)

    def _build_tk_tile_image(self, width: int, height: int) -> tk.PhotoImage | None:
        """Load a PNG with Tk directly when Pillow/ImageTk is unavailable."""
        if not self._image_path or not os.path.isfile(self._image_path):
            return None

        try:
            source = tk.PhotoImage(file=self._image_path)
        except tk.TclError:
            return None

        src_w = max(source.width(), 1)
        src_h = max(source.height(), 1)
        scale = max(1, math.ceil(max(src_w / max(width, 1), src_h / max(height, 1))))
        if scale > 1:
            try:
                source = source.subsample(scale, scale)
            except tk.TclError:
                pass

        return source

    def _build_tile_image(self, width: int, height: int):
        """Load, crop, and resize the source image to fill the tile."""
        if not self._image_path or not os.path.isfile(self._image_path):
            return None
        cache_key = (self._image_path, width, height)
        cached = _TILE_BASE_IMAGE_CACHE.get(cache_key, ...)
        if cached is not ...:
            return cached
        try:
            source = _PILImage.open(self._image_path).convert("RGBA")
        except Exception:
            _TILE_BASE_IMAGE_CACHE[cache_key] = None
            return None

        src_w, src_h = source.size
        if src_w <= 0 or src_h <= 0:
            _TILE_BASE_IMAGE_CACHE[cache_key] = None
            return None

        target_ratio = width / float(height)
        source_ratio = src_w / float(src_h)
        if source_ratio > target_ratio:
            # Source wider — center crop horizontally
            crop_w = int(src_h * target_ratio)
            left = max((src_w - crop_w) // 2, 0)
            box = (left, 0, left + crop_w, src_h)
        else:
            # Source taller — top crop (preserve top, trim bottom)
            crop_h = int(src_w / target_ratio)
            box = (0, 0, src_w, crop_h)

        try:
            cropped = source.crop(box).resize((width, height), _PILImage.LANCZOS)
        except Exception:
            _TILE_BASE_IMAGE_CACHE[cache_key] = None
            return None

        # Matte transparent artwork onto the tile background so soft alpha
        # edges do not pick up black halos from the source image.
        background = _PILImage.new(
            "RGBA",
            (width, height),
            _hex_to_rgb(COLORS["tile_bg"]) + (255,),
        )
        composited = _PILImage.alpha_composite(background, cropped)
        _TILE_BASE_IMAGE_CACHE[cache_key] = composited
        return composited

    def _apply_overlay(self, base, width: int, height: int, hovered: bool = False):
        """Apply scrim gradient + bottom panel overlay (Archive card style)."""
        overlay = _PILImage.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = _PILImageDraw.Draw(overlay)

        # Scrim gradient from 34% down
        scrim_rgb = _hex_to_rgb(COLORS["bg_deepest"])
        scrim_top = int(height * 0.34)
        scrim_bottom_alpha = 188 if hovered else 164
        scrim_span = max(height - scrim_top - 1, 1)
        for y in range(scrim_top, height):
            ratio = (y - scrim_top) / float(scrim_span)
            alpha = int(scrim_bottom_alpha * ratio)
            draw.line((0, y, width, y), fill=scrim_rgb + (alpha,))

        # Bottom panel gradient
        panel_height = min(self.OVERLAY_HEIGHT, height)
        panel = _PILImage.new("RGBA", (width, panel_height), (0, 0, 0, 0))
        pdraw = _PILImageDraw.Draw(panel)
        panel_rgb = _hex_to_rgb(COLORS["bg_surface"])
        top_alpha = 224 if hovered else 202
        bottom_alpha = 252 if hovered else 244
        gradient_span = max(panel_height - 1, 1)
        for y in range(panel_height):
            ratio = y / float(gradient_span)
            a = int(top_alpha + (bottom_alpha - top_alpha) * ratio)
            pdraw.line((0, y, width, y), fill=panel_rgb + (a,))
        # Thin top line
        top_line_alpha = 115 if hovered else 90
        pdraw.line(
            (0, 0, width, 0),
            fill=_hex_to_rgb(COLORS["outline_dim"]) + (top_line_alpha,),
            width=1,
        )
        overlay.paste(panel, (0, height - panel_height), panel)

        return _PILImage.alpha_composite(base.convert("RGBA"), overlay)

    def _draw_text(self, width: int, height: int):
        """Render name and traits on the canvas over the gradient overlay."""
        panel_height = min(self.OVERLAY_HEIGHT, height)
        pad_x = 16
        pad_top = 24
        panel_top = height - panel_height + pad_top
        text_width = max(width - pad_x * 2, 80)

        # Name with shadow
        self._canvas.create_text(
            pad_x + 1, panel_top + 1,
            text=self._name, font=FONTS["tile_name"],
            fill=COLORS["bg_deepest"], anchor="nw", width=text_width,
        )
        title_id = self._canvas.create_text(
            pad_x, panel_top,
            text=self._name, font=FONTS["tile_name"],
            fill=COLORS["fg"], anchor="nw", width=text_width,
        )

        # Traits below name
        if self._traits:
            title_bbox = self._canvas.bbox(title_id)
            traits_y = (title_bbox[3] if title_bbox else panel_top + 20) + 6
            traits_text = "  ·  ".join(self._traits[:3])
            self._canvas.create_text(
                pad_x + 1, traits_y + 1,
                text=traits_text, font=FONTS["tile_trait"],
                fill=COLORS["bg_deepest"], anchor="nw", width=text_width,
            )
            self._canvas.create_text(
                pad_x, traits_y,
                text=traits_text, font=FONTS["tile_trait"],
                fill=COLORS["gold"], anchor="nw", width=text_width,
            )

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def _handle_click(self, _event=None):
        if self._on_click:
            self._on_click(self._name)

    def _on_enter(self, _event=None):
        if self._variant == "lore":
            self._hovered = True
            self._apply_lore_state(True)
            return
        self._hovered = True
        self.configure(highlightbackground=COLORS["accent_text"])
        self._render(hovered=True)

    def _on_leave(self, _event=None):
        if self._variant == "lore":
            self._hovered = False
            self._apply_lore_state(False)
            return
        self._hovered = False
        self.configure(highlightbackground=COLORS["tile_border"])
        self._render(hovered=False)

    def _on_configure(self, _event=None):
        if self._variant == "lore":
            self._update_lore_layout()
            return

        w = self._canvas.winfo_width()
        h = self._canvas.winfo_height()
        if (w, h) != self._last_render_size and w > 1 and h > 1:
            self._photo_normal = None
            self._photo_hover = None
            self._queue_render()


class TileGrid(tk.Frame):
    """Responsive grid of OptionTile widgets inside a ScrollableFrame.

    Automatically recalculates column count on resize.
    """

    def __init__(
        self,
        parent,
        on_select=None,
        tile_width: int = OptionTile.TILE_WIDTH,
        tile_height: int = OptionTile.TILE_HEIGHT,
        preferred_cols: int | None = None,
        min_tile_width: int | None = None,
        responsive_tile_height: bool = False,
        content_side_padding: int = 0,
        **kwargs,
    ):
        super().__init__(parent, bg=COLORS["bg"], **kwargs)
        self._on_select = on_select
        self._base_tile_width = tile_width
        self._base_tile_height = tile_height
        self._tile_width = tile_width
        self._tile_height = tile_height
        self._preferred_cols = preferred_cols
        self._min_tile_width = min_tile_width
        self._responsive_tile_height = responsive_tile_height
        self._content_side_padding = max(0, int(content_side_padding))
        self._tile_ratio = tile_height / float(max(tile_width, 1))
        self._tiles: list[OptionTile] = []
        self._sections: list[tuple[SectionHeader, list[OptionTile]]] = []
        self._tile_data: list[dict] = []
        self._visible_names: set[str] | None = None
        self._cols = 3
        self._max_cols_seen = self._cols
        self._relayout_job = None

        self._scroll = ScrollableFrame(self, inner_padding=SPACING["lg"])
        self._scroll.pack(fill=tk.BOTH, expand=True)
        self._grid_frame = self._scroll.inner
        self._grid_frame.grid_anchor("n")

        self._scroll.canvas.bind("<Configure>", self._on_canvas_resize)

    def _clear_content(self):
        for t in self._tiles:
            t.destroy()
        for header, _ in self._sections:
            header.destroy()
        self._tiles.clear()
        self._sections.clear()
        self._tile_data.clear()

    def _create_tile(self, tile_data: dict) -> OptionTile:
        return OptionTile(
            self._grid_frame,
            name=tile_data["name"],
            description=tile_data.get("description", ""),
            traits=tile_data.get("traits"),
            image_path=tile_data.get("image_path"),
            variant=tile_data.get("variant"),
            tile_width=self._tile_width,
            tile_height=self._tile_height,
            on_click=self._handle_select,
        )

    def set_tiles(self, tiles: list[dict]):
        """Rebuild the tile grid.

        Each dict: {"name": str, "description": str, "traits": list[str], "image_path": str | None}
        """
        self._clear_content()
        self._tile_data = list(tiles)
        self._tiles = [self._create_tile(td) for td in tiles]

        self._layout_tiles()

    def set_sectioned_tiles(self, sections: list[tuple[str, list[dict]]]):
        """Rebuild the tile grid with visible section headers."""
        self._clear_content()
        self._tile_data = [tile for _section, tiles in sections for tile in tiles]

        for section_name, tiles in sections:
            if not tiles:
                continue
            header = SectionHeader(self._grid_frame, text=section_name)
            section_tiles = [self._create_tile(td) for td in tiles]
            self._sections.append((header, section_tiles))
            self._tiles.extend(section_tiles)

        self._layout_tiles()

    def set_filter(self, enabled_names: set[str] | None):
        """Show only tiles whose names are in enabled_names (None = show all)."""
        self._visible_names = enabled_names
        self._layout_tiles()

    def _handle_select(self, name: str):
        if self._on_select:
            self._on_select(name)

    def _on_canvas_resize(self, event):
        if self._relayout_job:
            try:
                self.after_cancel(self._relayout_job)
            except Exception:
                pass
        self._relayout_job = self.after(50, lambda: self._recalc_layout(event.width))

    def _recalc_layout(self, width: int):
        self._relayout_job = None
        gap = SPACING["tile_gap"]
        available_width = max(1, width - (self._content_side_padding * 2))
        new_cols = max(1, (available_width + gap) // (self._base_tile_width + gap))
        new_tile_width = self._base_tile_width

        if self._preferred_cols is not None:
            preferred_width = max(
                1,
                (
                    available_width - gap * max(self._preferred_cols - 1, 0)
                ) // self._preferred_cols,
            )
            min_width = self._min_tile_width or 1

            if preferred_width >= min_width:
                new_cols = self._preferred_cols
                new_tile_width = min(self._base_tile_width, preferred_width)
            else:
                fit_width = min_width
                new_cols = max(1, (available_width + gap) // (fit_width + gap))
                if new_cols > 0:
                    new_tile_width = min(
                        self._base_tile_width,
                        max(
                            1,
                            (
                                available_width - gap * max(new_cols - 1, 0)
                            ) // new_cols,
                        ),
                    )

        new_tile_height = self._tile_height
        if self._responsive_tile_height:
            new_tile_height = max(180, int(round(new_tile_width * self._tile_ratio)))

        size_changed = (
            new_tile_width != self._tile_width or new_tile_height != self._tile_height
        )
        if size_changed:
            self._tile_width = new_tile_width
            self._tile_height = new_tile_height
            for tile in self._tiles:
                tile.set_tile_size(self._tile_width, self._tile_height)

        if new_cols != self._cols or size_changed:
            self._cols = new_cols
            self._layout_tiles()

    def _layout_tiles(self):
        gap = SPACING["tile_gap"]

        # Configure columns
        self._max_cols_seen = max(self._max_cols_seen, self._cols)
        for c in range(self._max_cols_seen):
            self._grid_frame.columnconfigure(c, weight=0)

        for tile in self._tiles:
            tile.grid_forget()
        for header, _ in self._sections:
            header.grid_forget()

        if self._sections:
            row = 0
            for header, tiles in self._sections:
                visible_tiles = [
                    tile
                    for tile in tiles
                    if self._visible_names is None or tile._name in self._visible_names
                ]
                if not visible_tiles:
                    continue

                top_pad = gap // 2 if row == 0 else gap
                header.grid(
                    row=row,
                    column=0,
                    columnspan=self._cols,
                    padx=gap // 2,
                    pady=(top_pad, gap // 2),
                    sticky="ew",
                )
                row += 1

                col = 0
                for tile in visible_tiles:
                    tile.grid(
                        row=row,
                        column=col,
                        padx=gap // 2,
                        pady=gap // 2,
                        sticky="nsew",
                    )
                    col += 1
                    if col >= self._cols:
                        col = 0
                        row += 1

                if col != 0:
                    row += 1
            return

        col = 0
        row = 0

        for tile in self._tiles:
            if self._visible_names is not None and tile._name not in self._visible_names:
                continue

            tile.grid(
                row=row,
                column=col,
                padx=gap // 2,
                pady=gap // 2,
                sticky="nsew",
            )
            col += 1
            if col >= self._cols:
                col = 0
                row += 1
