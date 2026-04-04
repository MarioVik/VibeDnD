"""Step 8: Spell selection for caster classes."""

import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import register_mousewheel_target, GradientHeader, SectionHeader, CardFrame
from models.level1_class_rules import (
    get_effective_cantrips_known,
    get_effective_prepared_spells,
    get_unmet_level1_class_requirements,
    scrub_level1_class_choices,
)


class SpellsStep(WizardStep):
    tab_title = "Spells"

    def __init__(self, parent_notebook, character, game_data):
        self._updating_cantrips = False
        self._updating_spells = False
        self.cantrip_checkbuttons = {}
        self.spell_checkbuttons = {}
        self.cantrip_vars = {}
        self.spell_vars = {}
        super().__init__(parent_notebook, character, game_data)

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # ── Hero header ─────────────────────────────────────────
        hero = GradientHeader(self.frame, min_height=60)
        hero.grid(row=0, column=0, sticky="ew")

        hero_row = tk.Frame(hero.inner, bg=COLORS["bg_hero"])
        hero_row.pack(fill=tk.X, padx=SPACING["card_pad"], pady=(SPACING["xl"], SPACING["xl"]))

        tk.Label(
            hero_row,
            text="Select Spells",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        self.info_label = tk.Label(
            hero_row,
            text="",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        )
        self.info_label.pack(side=tk.RIGHT)

        # Non-caster message
        self.no_spells_card = CardFrame(self.frame, pad=SPACING["xl"])
        self.no_spells_label = tk.Label(
            self.no_spells_card.inner,
            text="Your class does not have spellcasting at level 1.",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        )
        self.no_spells_label.pack()

        # Main content: two-column split (list left, detail right)
        self.content_frame = tk.Frame(self.frame, bg=COLORS["bg"])
        # Not gridded yet — done in _show_spell_ui

    def on_enter(self):
        """Refresh spell lists based on current class."""
        scrub_level1_class_choices(self.character, self.data)
        cls = self.character.character_class
        if not cls or not cls.get("caster_type"):
            self._show_no_spells()
            return

        self._show_spell_ui()

    def _show_no_spells(self):
        self.content_frame.grid_forget()
        self.no_spells_card.grid(row=1, column=0, padx=SPACING["lg"], pady=SPACING["xl"], sticky="ew")

    def _show_spell_ui(self):
        """Build the full spell selection UI: left list + right detail."""
        self.no_spells_card.grid_forget()

        for w in self.content_frame.winfo_children():
            w.destroy()
        self.cantrip_vars.clear()
        self.spell_vars.clear()
        self.cantrip_checkbuttons.clear()
        self.spell_checkbuttons.clear()

        cls = self.character.character_class
        class_name = cls["name"]
        cantrip_max = get_effective_cantrips_known(self.character)
        spell_max = get_effective_prepared_spells(self.character)

        self.info_label.configure(
            text=f"{class_name}: {cantrip_max} cantrips, {spell_max} prepared spells"
        )

        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=SPACING["lg"], pady=(0, SPACING["sm"]))
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.columnconfigure(1, weight=1)
        self.content_frame.rowconfigure(0, weight=1)

        # --- LEFT: spell list column ---
        left = tk.Frame(self.content_frame, bg=COLORS["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["xs"]))

        cantrips = self.data.cantrips_for_class(class_name)
        level1_spells = [
            s
            for s in self.data.spells_for_class(class_name, max_level=1)
            if s["level"] == 1
        ]
        has_cantrips = cantrip_max > 0 and len(cantrips) > 0
        has_spells = spell_max > 0 and len(level1_spells) > 0

        current_cantrip_count = len(self.character.selected_cantrips)
        current_spell_count = len(self.character.selected_spells)

        _bg = COLORS["bg"]
        if has_cantrips:
            self.cantrip_count_label = tk.Label(
                left,
                text=f"{current_cantrip_count} / {cantrip_max} cantrips selected",
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg_dim"],
                bg=_bg,
            )
            self.cantrip_count_label.pack(anchor="w", padx=4, pady=(0, 1))

        if has_spells:
            self.spell_count_label = tk.Label(
                left,
                text=f"{current_spell_count} / {spell_max} spells selected",
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg_dim"],
                bg=_bg,
            )
            self.spell_count_label.pack(anchor="w", padx=4, pady=(0, 1))

        # Scrollable list
        list_outer = tk.Frame(left, bg=COLORS["bg"])
        list_outer.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        canvas, inner = self._make_scrollable_list(list_outer)

        def _section_header(parent, title):
            tk.Label(
                parent,
                text=f"\u2500\u2500 {title} \u2500\u2500",
                font=FONTS["body_bold"],
                fg=COLORS["accent_text"],
                bg=COLORS["bg"],
            ).pack(anchor="w", pady=(6, 2))

        if has_cantrips:
            _section_header(inner, "Cantrips")

            for spell in sorted(cantrips, key=lambda s: s["name"]):
                var = tk.BooleanVar(
                    value=spell["name"] in self.character.selected_cantrips
                )
                var.trace_add("write", lambda *a, s=spell: self._on_cantrip_toggle(s))
                self.cantrip_vars[spell["name"]] = {"var": var, "spell": spell}
                cb = ttk.Checkbutton(
                    inner,
                    text=spell["name"],
                    variable=var,
                )
                cb.pack(anchor="w", pady=1, padx=(8, 0))
                cb.bind("<Enter>", lambda e, s=spell: self._show_detail(s))
                self.cantrip_checkbuttons[spell["name"]] = cb

        if has_spells:
            _section_header(inner, "1st-Level")

            for spell in sorted(level1_spells, key=lambda s: s["name"]):
                var = tk.BooleanVar(
                    value=spell["name"] in self.character.selected_spells
                )
                var.trace_add("write", lambda *a, s=spell: self._on_spell_toggle(s))
                self.spell_vars[spell["name"]] = {"var": var, "spell": spell}

                cb = ttk.Checkbutton(inner, text=spell["name"], variable=var)
                cb.pack(anchor="w", pady=1, padx=(8, 0))
                cb.bind("<Enter>", lambda e, s=spell: self._show_detail(s))
                self.spell_checkbuttons[spell["name"]] = cb

        self._update_cantrip_states()
        self._update_spell_states()

        # --- RIGHT: spell detail panel ---
        right = tk.Frame(self.content_frame, bg=COLORS["bg"])
        right.grid(row=0, column=1, sticky="nsew", padx=(SPACING["xs"], 0))

        SectionHeader(right, text="Spell Details").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        detail_card = CardFrame(right, pad=SPACING["lg"])
        detail_card.pack(fill=tk.BOTH, expand=True)

        self.spell_detail_text = tk.Text(
            detail_card.inner,
            wrap=tk.WORD,
            bg=COLORS["bg_surface"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            state=tk.DISABLED,
        )
        self.spell_detail_text.pack(fill=tk.BOTH, expand=True)

    def _make_scrollable_list(self, parent_frame):
        canvas = tk.Canvas(
            parent_frame, bg=COLORS["bg"], highlightthickness=0, borderwidth=0
        )
        scrollbar = ttk.Scrollbar(
            parent_frame, orient=tk.VERTICAL, command=canvas.yview
        )
        inner = tk.Frame(canvas, bg=COLORS["bg"])

        inner.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.bind(
            "<Configure>",
            lambda e, cw=canvas_window: canvas.itemconfig(cw, width=e.width),
        )

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        register_mousewheel_target(parent_frame, canvas)
        register_mousewheel_target(canvas, canvas)
        register_mousewheel_target(inner, canvas)

        return canvas, inner

    # ── toggle handlers ──────────────────────────────────────────

    def _on_cantrip_toggle(self, spell):
        if self._updating_cantrips:
            return
        self._updating_cantrips = True
        try:
            cantrip_max = get_effective_cantrips_known(self.character)

            selected = [name for name, d in self.cantrip_vars.items() if d["var"].get()]
            if len(selected) > cantrip_max:
                self.cantrip_vars[spell["name"]]["var"].set(False)
                selected = [
                    name for name, d in self.cantrip_vars.items() if d["var"].get()
                ]

            self.character.selected_cantrips = selected
            scrub_level1_class_choices(self.character, self.data)
            self.cantrip_count_label.configure(
                text=f"{len(selected)} / {cantrip_max} cantrips selected"
            )
            self._update_cantrip_states()
            self.notify_change()
        finally:
            self._updating_cantrips = False

    def _on_spell_toggle(self, spell):
        if self._updating_spells:
            return
        self._updating_spells = True
        try:
            spell_max = get_effective_prepared_spells(self.character)

            selected = [name for name, d in self.spell_vars.items() if d["var"].get()]
            if len(selected) > spell_max:
                self.spell_vars[spell["name"]]["var"].set(False)
                selected = [
                    name for name, d in self.spell_vars.items() if d["var"].get()
                ]

            self.character.selected_spells = selected
            self.spell_count_label.configure(
                text=f"{len(selected)} / {spell_max} spells selected"
            )
            self._update_spell_states()
            self.notify_change()
        finally:
            self._updating_spells = False

    def _update_cantrip_states(self):
        cantrip_max = get_effective_cantrips_known(self.character)
        selected = [name for name, d in self.cantrip_vars.items() if d["var"].get()]
        at_max = len(selected) >= cantrip_max

        for name, cb in self.cantrip_checkbuttons.items():
            if at_max and name not in selected:
                cb.configure(state=tk.DISABLED)
            else:
                cb.configure(state=tk.NORMAL)

    def _update_spell_states(self):
        spell_max = get_effective_prepared_spells(self.character)
        selected = [name for name, d in self.spell_vars.items() if d["var"].get()]
        at_max = len(selected) >= spell_max

        for name, cb in self.spell_checkbuttons.items():
            if at_max and name not in selected:
                cb.configure(state=tk.DISABLED)
            else:
                cb.configure(state=tk.NORMAL)

    def is_valid(self) -> bool:
        cls = self.character.character_class
        if not cls or not cls.get("caster_type"):
            return True
        return not get_unmet_level1_class_requirements(
            self.character,
            self.data,
            step_key="spells",
        )

    # ── spell detail hover ───────────────────────────────────────

    def _show_detail(self, spell):
        self.spell_detail_text.configure(state=tk.NORMAL)
        self.spell_detail_text.delete("1.0", tk.END)

        lines = [
            f"{spell['name']}",
            f"{'Cantrip' if spell['level'] == 0 else 'Level ' + str(spell['level'])} {spell['school']}",
            f"Casting Time: {spell.get('casting_time', '?')}{'  (Ritual)' if spell.get('ritual') else ''}",
            f"Range: {spell.get('range', '?')}",
            f"Duration: {'Concentration, ' if spell.get('concentration') else ''}{spell.get('duration', '?')}",
            "",
            spell.get("description", ""),
        ]

        if spell.get("higher_levels"):
            lines.extend(["", f"At Higher Levels: {spell['higher_levels']}"])
        if spell.get("cantrip_upgrade"):
            lines.extend(["", f"Cantrip Upgrade: {spell['cantrip_upgrade']}"])

        self.spell_detail_text.insert("1.0", "\n".join(lines))
        self.spell_detail_text.configure(state=tk.DISABLED)
