"""Step 6: Spell selection for caster classes."""

import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import SearchableListbox, ScrollableFrame
from gui.theme import COLORS, FONTS


class SpellsStep(WizardStep):
    tab_title = "Spells"

    def __init__(self, parent_notebook, character, game_data):
        self._updating_cantrips = False
        self._updating_spells = False
        self.cantrip_checkbuttons = {}
        self.spell_checkbuttons = {}
        super().__init__(parent_notebook, character, game_data)

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # Title
        ttk.Label(self.frame, text="Select Spells", style="Heading.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 4))

        self.info_label = ttk.Label(self.frame, text="", style="Dim.TLabel")
        self.info_label.grid(row=0, column=1, sticky="e", padx=12)

        # Non-caster message
        self.no_spells_label = ttk.Label(self.frame,
                                          text="Your class does not have spellcasting at level 1.",
                                          style="Dim.TLabel")

        # Left: Cantrips
        self.cantrip_frame = ttk.LabelFrame(self.frame, text="Cantrips")
        self.cantrip_count_label = ttk.Label(self.cantrip_frame, text="0 / 0 selected",
                                              style="Dim.TLabel")
        self.cantrip_count_label.pack(anchor="w", padx=4, pady=(4, 2))
        self.cantrip_list_frame = ttk.Frame(self.cantrip_frame)
        self.cantrip_list_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.cantrip_vars = {}

        # Right: Level 1 spells
        self.spell_frame = ttk.LabelFrame(self.frame, text="Level 1 Spells")
        self.spell_count_label = ttk.Label(self.spell_frame, text="0 / 0 selected",
                                            style="Dim.TLabel")
        self.spell_count_label.pack(anchor="w", padx=4, pady=(4, 2))
        self.spell_list_frame = ttk.Frame(self.spell_frame)
        self.spell_list_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.spell_vars = {}

        # Spell detail
        self.spell_detail = ttk.LabelFrame(self.frame, text="Spell Details")
        self.spell_detail_text = tk.Text(self.spell_detail, wrap=tk.WORD, height=8,
                                          bg=COLORS["bg_light"], fg=COLORS["fg"],
                                          font=FONTS["body"], borderwidth=0,
                                          state=tk.DISABLED)
        self.spell_detail_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def on_enter(self):
        """Refresh spell lists based on current class."""
        cls = self.character.character_class
        if not cls or not cls.get("caster_type"):
            self._show_no_spells()
            return

        self._show_spell_ui()
        self._populate_cantrips()
        self._populate_spells()

    def _show_no_spells(self):
        self.cantrip_frame.grid_forget()
        self.spell_frame.grid_forget()
        self.spell_detail.grid_forget()
        self.no_spells_label.grid(row=1, column=0, columnspan=2, padx=12, pady=20)

    def _show_spell_ui(self):
        self.no_spells_label.grid_forget()
        self.cantrip_frame.grid(row=1, column=0, sticky="nsew", padx=(12, 4), pady=4)
        self.spell_frame.grid(row=1, column=1, sticky="nsew", padx=(4, 12), pady=4)
        self.spell_detail.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=12, pady=(4, 8))

        cls = self.character.character_class
        cantrip_max = cls.get("cantrips_known", 0) or 0
        spell_max = cls.get("spells_prepared", 0) or 0
        self.info_label.configure(
            text=f"{cls['name']}: {cantrip_max} cantrips, {spell_max} prepared spells")

    def _make_scrollable_list(self, parent_frame):
        """Create a scrollable canvas+inner frame inside parent_frame.

        Returns (canvas, inner_frame).  Includes mousewheel scrolling and
        automatic width-sync so the inner frame fills the canvas.
        """
        canvas = tk.Canvas(parent_frame, bg=COLORS["bg"],
                           highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(parent_frame, orient=tk.VERTICAL,
                                  command=canvas.yview)
        inner = ttk.Frame(canvas)

        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Keep inner frame as wide as the canvas
        canvas.bind("<Configure>",
                    lambda e, cw=canvas_window: canvas.itemconfig(cw, width=e.width))

        # Pack scrollbar FIRST so it gets space priority over the canvas
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Mousewheel scrolling — scoped to whichever list the cursor is over
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_wheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_wheel(event):
            canvas.unbind_all("<MouseWheel>")

        inner.bind("<Enter>", _bind_wheel)
        inner.bind("<Leave>", _unbind_wheel)

        return canvas, inner

    def _populate_cantrips(self):
        for w in self.cantrip_list_frame.winfo_children():
            w.destroy()
        self.cantrip_vars.clear()
        self.cantrip_checkbuttons.clear()

        cls = self.character.character_class
        if not cls:
            return

        class_name = cls["name"]
        cantrips = self.data.cantrips_for_class(class_name)
        cantrip_max = cls.get("cantrips_known", 0) or 0
        current_count = len(self.character.selected_cantrips)

        self.cantrip_count_label.configure(text=f"{current_count} / {cantrip_max} selected")

        # Scrollable checkbox list
        canvas, inner = self._make_scrollable_list(self.cantrip_list_frame)

        for spell in sorted(cantrips, key=lambda s: s["name"]):
            var = tk.BooleanVar(value=spell["name"] in self.character.selected_cantrips)
            var.trace_add("write", lambda *a, s=spell: self._on_cantrip_toggle(s))
            self.cantrip_vars[spell["name"]] = {"var": var, "spell": spell}
            cb = ttk.Checkbutton(inner, text=f"{spell['name']} ({spell['school']})",
                                 variable=var)
            cb.pack(anchor="w", pady=1)
            cb.bind("<Enter>", lambda e, s=spell: self._show_detail(s))
            self.cantrip_checkbuttons[spell["name"]] = cb

        # Disable unchecked if already at max
        self._update_cantrip_states()

    def _populate_spells(self):
        for w in self.spell_list_frame.winfo_children():
            w.destroy()
        self.spell_vars.clear()
        self.spell_checkbuttons.clear()

        cls = self.character.character_class
        if not cls:
            return

        class_name = cls["name"]
        spells = self.data.spells_for_class(class_name, max_level=1)
        level1_spells = [s for s in spells if s["level"] == 1]
        spell_max = cls.get("spells_prepared", 0) or 0
        current_count = len(self.character.selected_spells)

        self.spell_count_label.configure(text=f"{current_count} / {spell_max} selected")

        canvas, inner = self._make_scrollable_list(self.spell_list_frame)

        for spell in sorted(level1_spells, key=lambda s: s["name"]):
            var = tk.BooleanVar(value=spell["name"] in self.character.selected_spells)
            var.trace_add("write", lambda *a, s=spell: self._on_spell_toggle(s))
            self.spell_vars[spell["name"]] = {"var": var, "spell": spell}

            text = f"{spell['name']} ({spell['school']}"
            if spell.get("concentration"):
                text += ", C"
            if spell.get("ritual"):
                text += ", R"
            text += ")"

            cb = ttk.Checkbutton(inner, text=text, variable=var)
            cb.pack(anchor="w", pady=1)
            cb.bind("<Enter>", lambda e, s=spell: self._show_detail(s))
            self.spell_checkbuttons[spell["name"]] = cb

        # Disable unchecked if already at max
        self._update_spell_states()

    def _on_cantrip_toggle(self, spell):
        if self._updating_cantrips:
            return
        self._updating_cantrips = True
        try:
            cls = self.character.character_class
            cantrip_max = (cls.get("cantrips_known", 0) or 0) if cls else 0

            selected = [name for name, d in self.cantrip_vars.items() if d["var"].get()]
            if len(selected) > cantrip_max:
                # Undo the toggle
                self.cantrip_vars[spell["name"]]["var"].set(False)
                selected = [name for name, d in self.cantrip_vars.items() if d["var"].get()]

            self.character.selected_cantrips = selected
            self.cantrip_count_label.configure(text=f"{len(selected)} / {cantrip_max} selected")
            self._update_cantrip_states()
            self.notify_change()
        finally:
            self._updating_cantrips = False

    def _on_spell_toggle(self, spell):
        if self._updating_spells:
            return
        self._updating_spells = True
        try:
            cls = self.character.character_class
            spell_max = (cls.get("spells_prepared", 0) or 0) if cls else 0

            selected = [name for name, d in self.spell_vars.items() if d["var"].get()]
            if len(selected) > spell_max:
                # Undo the toggle
                self.spell_vars[spell["name"]]["var"].set(False)
                selected = [name for name, d in self.spell_vars.items() if d["var"].get()]

            self.character.selected_spells = selected
            self.spell_count_label.configure(text=f"{len(selected)} / {spell_max} selected")
            self._update_spell_states()
            self.notify_change()
        finally:
            self._updating_spells = False

    def _update_cantrip_states(self):
        """Disable unchecked cantrip checkboxes when at max."""
        cls = self.character.character_class
        cantrip_max = (cls.get("cantrips_known", 0) or 0) if cls else 0
        selected = [name for name, d in self.cantrip_vars.items() if d["var"].get()]
        at_max = len(selected) >= cantrip_max

        for name, cb in self.cantrip_checkbuttons.items():
            if at_max and name not in selected:
                cb.configure(state=tk.DISABLED)
            else:
                cb.configure(state=tk.NORMAL)

    def _update_spell_states(self):
        """Disable unchecked spell checkboxes when at max."""
        cls = self.character.character_class
        spell_max = (cls.get("spells_prepared", 0) or 0) if cls else 0
        selected = [name for name, d in self.spell_vars.items() if d["var"].get()]
        at_max = len(selected) >= spell_max

        for name, cb in self.spell_checkbuttons.items():
            if at_max and name not in selected:
                cb.configure(state=tk.DISABLED)
            else:
                cb.configure(state=tk.NORMAL)

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
            spell.get("description", "")[:500],
        ]

        if spell.get("higher_levels"):
            lines.extend(["", f"At Higher Levels: {spell['higher_levels'][:200]}"])
        if spell.get("cantrip_upgrade"):
            lines.extend(["", f"Cantrip Upgrade: {spell['cantrip_upgrade'][:200]}"])

        self.spell_detail_text.insert("1.0", "\n".join(lines))
        self.spell_detail_text.configure(state=tk.DISABLED)
