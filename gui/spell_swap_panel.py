"""Reusable two-column spell swap panel used by level-up wizard and rest dialog."""

from __future__ import annotations

import tkinter as tk
from itertools import groupby
from tkinter import ttk

from gui.theme import COLORS, FONTS

LEVEL_NAMES = {
    0: "Cantrips",
    1: "1st-Level",
    2: "2nd-Level",
    3: "3rd-Level",
    4: "4th-Level",
    5: "5th-Level",
    6: "6th-Level",
    7: "7th-Level",
    8: "8th-Level",
    9: "9th-Level",
}


class SpellSwapPanel:
    """Builds a two-column spell swap UI with level headers, scrollable lists,
    and a shared spell-detail panel.

    After the user interacts, read ``forget_var`` and ``learn_var`` to get the
    current selections.  Values are plain spell names for spells; cantrips are
    prefixed with ``C:`` and spells with ``S:`` when *allow_cantrips* is True.
    """

    def __init__(
        self,
        parent: tk.Widget,
        *,
        forget_spells: list[dict],
        learn_spells: list[dict],
        forget_cantrips: list[dict] | None = None,
        learn_cantrips: list[dict] | None = None,
        allow_cantrips: bool = False,
        left_label: str = "Forget",
        right_label: str = "Learn",
        no_swap_label: str = "Don\u2019t swap",
    ):
        self.forget_var = tk.StringVar(value="")
        self.learn_var = tk.StringVar(value="")
        self._cantrip_rbs: list[tuple[ttk.Radiobutton, dict]] = []
        self._spell_rbs: list[tuple[ttk.Radiobutton, dict]] = []
        self._allow_cantrips = allow_cantrips

        # ── Two-column split ──
        cols = ttk.Frame(parent)
        cols.pack(fill=tk.BOTH, expand=True, pady=4)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)
        cols.rowconfigure(0, weight=1)

        # --- LEFT: Forget ---
        left_lf = ttk.LabelFrame(cols, text=left_label)
        left_lf.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        left_outer = ttk.Frame(left_lf)
        left_outer.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        _, left_inner = _make_scrollable_list(left_outer)

        ttk.Radiobutton(
            left_inner,
            text=no_swap_label,
            variable=self.forget_var,
            value="",
        ).pack(anchor="w", pady=1)

        # Cantrips to forget
        if allow_cantrips and forget_cantrips:
            _section_header(left_inner, "Cantrips")
            for spell in sorted(forget_cantrips, key=lambda s: s["name"]):
                rb = ttk.Radiobutton(
                    left_inner,
                    text=spell["name"],
                    variable=self.forget_var,
                    value=f"C:{spell['name']}",
                )
                rb.pack(anchor="w", pady=1, padx=8)
                rb.bind("<Enter>", lambda e, s=spell: self._show_detail(s))

        # Spells to forget (grouped by level)
        if forget_spells:
            forget_sorted = sorted(forget_spells, key=lambda s: (s["level"], s["name"]))
            for lvl, group in groupby(forget_sorted, key=lambda s: s["level"]):
                _section_header(left_inner, LEVEL_NAMES.get(lvl, f"Level {lvl}"))
                for spell in group:
                    val = f"S:{spell['name']}" if allow_cantrips else spell["name"]
                    rb = ttk.Radiobutton(
                        left_inner,
                        text=spell["name"],
                        variable=self.forget_var,
                        value=val,
                    )
                    rb.pack(anchor="w", pady=1, padx=8)
                    rb.bind("<Enter>", lambda e, s=spell: self._show_detail(s))

        # --- RIGHT: Learn ---
        right_lf = ttk.LabelFrame(cols, text=right_label)
        right_lf.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right_outer = ttk.Frame(right_lf)
        right_outer.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        _, right_inner = _make_scrollable_list(right_outer)

        ttk.Radiobutton(
            right_inner,
            text="\u2014",
            variable=self.learn_var,
            value="",
        ).pack(anchor="w", pady=1)

        # Available cantrips
        if allow_cantrips and learn_cantrips:
            _section_header(right_inner, "Cantrips")
            for spell in sorted(learn_cantrips, key=lambda s: s["name"]):
                rb = ttk.Radiobutton(
                    right_inner,
                    text=spell["name"],
                    variable=self.learn_var,
                    value=spell["name"],
                )
                rb.pack(anchor="w", pady=1, padx=8)
                rb.bind("<Enter>", lambda e, s=spell: self._show_detail(s))
                self._cantrip_rbs.append((rb, spell))

        # Available spells (grouped by level)
        if learn_spells:
            learn_sorted = sorted(learn_spells, key=lambda s: (s["level"], s["name"]))
            for lvl, group in groupby(learn_sorted, key=lambda s: s["level"]):
                _section_header(right_inner, LEVEL_NAMES.get(lvl, f"Level {lvl}"))
                for spell in group:
                    rb = ttk.Radiobutton(
                        right_inner,
                        text=spell["name"],
                        variable=self.learn_var,
                        value=spell["name"],
                    )
                    rb.pack(anchor="w", pady=1, padx=8)
                    rb.bind("<Enter>", lambda e, s=spell: self._show_detail(s))
                    self._spell_rbs.append((rb, spell))

        if not learn_spells and not (allow_cantrips and learn_cantrips):
            ttk.Label(
                right_inner,
                text="No additional spells available.",
                foreground=COLORS["fg_dim"],
            ).pack(anchor="w", padx=8, pady=4)

        # --- Shared Detail Panel ---
        detail_lf = ttk.LabelFrame(parent, text="Spell Details")
        detail_lf.pack(fill=tk.X, pady=(4, 0))
        self._detail_text = tk.Text(
            detail_lf,
            wrap=tk.WORD,
            height=6,
            bg=COLORS["bg_light"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            state=tk.DISABLED,
        )
        self._detail_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ── Wire up enable/disable logic ──
        if allow_cantrips:
            self.forget_var.trace_add("write", self._on_forget_change)
            self.learn_var.trace_add("write", lambda *_: None)  # no extra logic needed
            self._on_forget_change()
        else:
            # For prepared casters: no cantrip distinction, just disable learn when "don't swap"
            self.forget_var.trace_add("write", self._on_forget_change_simple)
            self._on_forget_change_simple()

    # ── Detail panel ──

    def _show_detail(self, spell: dict):
        self._detail_text.configure(state=tk.NORMAL)
        self._detail_text.delete("1.0", tk.END)
        lines = [
            spell["name"],
            f"{'Cantrip' if spell['level'] == 0 else 'Level ' + str(spell['level'])} "
            f"{spell['school']}",
            f"Casting Time: {spell.get('casting_time', '?')}"
            f"{'  (Ritual)' if spell.get('ritual') else ''}",
            f"Range: {spell.get('range', '?')}",
            f"Duration: {'Concentration, ' if spell.get('concentration') else ''}"
            f"{spell.get('duration', '?')}",
            "",
            spell.get("description", ""),
        ]
        if spell.get("higher_levels"):
            lines.extend(["", f"At Higher Levels: {spell['higher_levels']}"])
        if spell.get("cantrip_upgrade"):
            lines.extend(["", f"Cantrip Upgrade: {spell['cantrip_upgrade']}"])
        self._detail_text.insert("1.0", "\n".join(lines))
        self._detail_text.configure(state=tk.DISABLED)

    # ── Enable/disable logic (with cantrip distinction) ──

    def _on_forget_change(self, *_):
        val = self.forget_var.get()
        if not val:
            # "Don't swap" — disable all learn buttons
            self.learn_var.set("")
            for rb, _ in self._cantrip_rbs + self._spell_rbs:
                rb.configure(state=tk.DISABLED)
        elif val.startswith("C:"):
            # Cantrip selected — only cantrip learns enabled
            for rb, _ in self._cantrip_rbs:
                rb.configure(state=tk.NORMAL)
            for rb, _ in self._spell_rbs:
                rb.configure(state=tk.DISABLED)
            # Clear learn if it was a spell
            if self.learn_var.get() and not any(
                s["name"] == self.learn_var.get() for _, s in self._cantrip_rbs
            ):
                self.learn_var.set("")
        else:  # S: prefix — spell selected
            for rb, _ in self._cantrip_rbs:
                rb.configure(state=tk.DISABLED)
            for rb, _ in self._spell_rbs:
                rb.configure(state=tk.NORMAL)
            if self.learn_var.get() and not any(
                s["name"] == self.learn_var.get() for _, s in self._spell_rbs
            ):
                self.learn_var.set("")

    # ── Enable/disable logic (simple — no cantrips) ──

    def _on_forget_change_simple(self, *_):
        val = self.forget_var.get()
        if not val:
            self.learn_var.set("")
            for rb, _ in self._spell_rbs:
                rb.configure(state=tk.DISABLED)
        else:
            for rb, _ in self._spell_rbs:
                rb.configure(state=tk.NORMAL)


# ── Module-level helpers ──


def _make_scrollable_list(parent_frame):
    """Create a scrollable canvas with an inner frame. Returns (canvas, inner)."""
    canvas = tk.Canvas(
        parent_frame, bg=COLORS["bg"], highlightthickness=0, borderwidth=0
    )
    scrollbar = ttk.Scrollbar(
        parent_frame, orient=tk.VERTICAL, command=canvas.yview
    )
    inner = ttk.Frame(canvas)

    inner.bind(
        "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    cw = canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.bind(
        "<Configure>", lambda e, _cw=cw: canvas.itemconfig(_cw, width=e.width)
    )

    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def _on_wheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    inner.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_wheel))
    inner.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    return canvas, inner


def _section_header(parent, title):
    """Add a styled level-group header."""
    ttk.Label(
        parent,
        text=f"\u2500\u2500 {title} \u2500\u2500",
        foreground=COLORS["accent"],
        font=FONTS["body"],
    ).pack(anchor="w", pady=(6, 2))
