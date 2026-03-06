"""Step 6: Spell selection for caster classes."""

import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import SearchableListbox, ScrollableFrame
from gui.theme import COLORS, FONTS


class SpellsStep(WizardStep):
    tab_title = "Spells"

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

    def _populate_cantrips(self):
        for w in self.cantrip_list_frame.winfo_children():
            w.destroy()
        self.cantrip_vars.clear()

        cls = self.character.character_class
        if not cls:
            return

        class_name = cls["name"]
        cantrips = self.data.cantrips_for_class(class_name)
        cantrip_max = cls.get("cantrips_known", 0) or 0

        self.cantrip_count_label.configure(text=f"0 / {cantrip_max} selected")

        # Scrollable checkbox list
        canvas = tk.Canvas(self.cantrip_list_frame, bg=COLORS["bg"],
                           highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(self.cantrip_list_frame, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas)

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for spell in sorted(cantrips, key=lambda s: s["name"]):
            var = tk.BooleanVar(value=spell["name"] in self.character.selected_cantrips)
            var.trace_add("write", lambda *a, s=spell: self._on_cantrip_toggle(s))
            self.cantrip_vars[spell["name"]] = {"var": var, "spell": spell}
            cb = ttk.Checkbutton(inner, text=f"{spell['name']} ({spell['school']})",
                                 variable=var)
            cb.pack(anchor="w", pady=1)
            cb.bind("<Enter>", lambda e, s=spell: self._show_detail(s))

    def _populate_spells(self):
        for w in self.spell_list_frame.winfo_children():
            w.destroy()
        self.spell_vars.clear()

        cls = self.character.character_class
        if not cls:
            return

        class_name = cls["name"]
        spells = self.data.spells_for_class(class_name, max_level=1)
        level1_spells = [s for s in spells if s["level"] == 1]
        spell_max = cls.get("spells_prepared", 0) or 0

        self.spell_count_label.configure(text=f"0 / {spell_max} selected")

        canvas = tk.Canvas(self.spell_list_frame, bg=COLORS["bg"],
                           highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(self.spell_list_frame, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas)

        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

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

    def _on_cantrip_toggle(self, spell):
        cls = self.character.character_class
        cantrip_max = cls.get("cantrips_known", 0) or 0 if cls else 0

        selected = [name for name, d in self.cantrip_vars.items() if d["var"].get()]
        if len(selected) > cantrip_max:
            self.cantrip_vars[spell["name"]]["var"].set(False)
            return

        self.character.selected_cantrips = selected
        self.cantrip_count_label.configure(text=f"{len(selected)} / {cantrip_max} selected")
        self.notify_change()

    def _on_spell_toggle(self, spell):
        cls = self.character.character_class
        spell_max = cls.get("spells_prepared", 0) or 0 if cls else 0

        selected = [name for name, d in self.spell_vars.items() if d["var"].get()]
        if len(selected) > spell_max:
            self.spell_vars[spell["name"]]["var"].set(False)
            return

        self.character.selected_spells = selected
        self.spell_count_label.configure(text=f"{len(selected)} / {spell_max} selected")
        self.notify_change()

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
