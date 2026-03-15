"""Read-only character sheet viewer with export and edit buttons."""

import tkinter as tk
from tkinter import ttk, filedialog

from gui.theme import COLORS, FONTS
from gui.widgets import ScrollableFrame, AlertDialog, SectionedListbox
from gui.sheet_builder import build_character_sheet
from models.character_store import save_character
from paths import characters_dir
from gui.add_inventory_dialog import AddInventoryDialog


class CharacterViewer(ttk.Frame):
    """Full-screen read-only character sheet with navigation and export."""

    def __init__(self, parent, character, save_path, game_data, app):
        super().__init__(parent)
        self.character = character
        self.save_path = save_path
        self.data = game_data
        self.app = app
        self._spell_index = {
            s.get("name", ""): s for s in (self.data.spells if self.data else [])
        }
        self._refresh_scheduled = False
        self._building_tabs = False
        self._build_ui()

    def _build_ui(self):
        # ── Top bar ─────────────────────────────────────────────
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=12, pady=(12, 4))

        ttk.Button(
            top,
            text="\u25c0  Back to Menu",
            command=self._on_back,
        ).pack(side=tk.LEFT)

        if self.character.level < 20:
            ttk.Button(
                top,
                text="Level Up",
                command=self._on_level_up,
            ).pack(side=tk.LEFT, padx=8)

        ttk.Button(
            top,
            text="Add to inventory",
            command=self._on_add_inventory,
        ).pack(side=tk.LEFT, padx=4)

        # Character name
        ttk.Label(
            top,
            text=self.character.name or "Unnamed",
            font=("Segoe UI", 18, "bold"),
            foreground=COLORS["accent"],
        ).pack(side=tk.LEFT, padx=8)

        # Export buttons (right side)
        ttk.Button(top, text="Export Character", command=self._export_json).pack(
            side=tk.RIGHT, padx=4
        )
        ttk.Button(top, text="Export PDF", command=self._export_pdf).pack(
            side=tk.RIGHT, padx=4
        )

        ttk.Button(
            top,
            text="Respec character",
            command=self._on_edit,
        ).pack(side=tk.RIGHT, padx=8)

        # ── Character tabs ──────────────────────────────────────
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 10))

        self.general_tab = ttk.Frame(self.tabs)
        self.inventory_tab = ttk.Frame(self.tabs)
        self.spells_tab = ttk.Frame(self.tabs)

        self.tabs.add(self.general_tab, text="General")
        self.tabs.add(self.inventory_tab, text="Inventory")
        self.tabs.add(self.spells_tab, text="Spells")

        general_scroll = ScrollableFrame(self.general_tab)
        general_scroll.pack(fill=tk.BOTH, expand=True)
        self._general_parent = general_scroll.inner

        inventory_scroll = ScrollableFrame(self.inventory_tab)
        inventory_scroll.pack(fill=tk.BOTH, expand=True)
        self._inventory_parent = inventory_scroll.inner

        self._build_spells_tab()
        self._refresh_tabs()

    def _build_spells_tab(self):
        self.spells_tab.columnconfigure(0, weight=0)
        self.spells_tab.columnconfigure(1, weight=1)
        self.spells_tab.rowconfigure(0, weight=1)

        left = ttk.Frame(self.spells_tab, width=300)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(2, 2))
        left.grid_propagate(False)

        ttk.Label(left, text="Known Spells", style="Heading.TLabel").pack(
            anchor="w", pady=(0, 2)
        )
        self.spells_list = SectionedListbox(left, on_select=self._on_spell_select)
        self.spells_list.pack(fill=tk.BOTH, expand=True)
        self.spells_list.search_entry.configure(style="ViewerCompactSpells.TEntry")

        style = ttk.Style(self)
        style.configure("ViewerCompactSpells.TEntry", padding=(6, 2))

        right = ttk.LabelFrame(self.spells_tab, text="Spell Details")
        right.grid(row=0, column=1, sticky="nsew", pady=(2, 2))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.spell_title = ttk.Label(
            right,
            text="Select a spell",
            style="Subheading.TLabel",
        )
        self.spell_title.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))

        self.spell_detail_text = tk.Text(
            right,
            wrap=tk.WORD,
            bg=COLORS["bg_light"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            state=tk.DISABLED,
        )
        self.spell_detail_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        self.spell_detail_text.tag_configure(
            "label", font=(FONTS["body"][0], FONTS["body"][1], "bold")
        )

    def _refresh_tabs(self, refresh_spells: bool = True):
        self._building_tabs = True
        try:
            build_character_sheet(
                self._general_parent,
                self.character,
                self.data,
                on_change=self._on_sheet_changed,
                compact=True,
                include_sections={
                    "header",
                    "combat",
                    "abilities",
                    "saving_throws",
                    "skills",
                    "standard_actions",
                    "species_traits",
                    "class_features",
                    "subclass",
                    "feats",
                },
            )

            build_character_sheet(
                self._inventory_parent,
                self.character,
                self.data,
                on_change=self._on_sheet_changed,
                compact=True,
                include_sections={"wealth", "equipment", "inventory"},
            )
            if refresh_spells:
                self._refresh_spells_tab()
        finally:
            self._building_tabs = False

    def _refresh_spells_tab(self):
        cantrips = list(dict.fromkeys(self.character.selected_cantrips or []))
        spells = list(dict.fromkeys(self.character.selected_spells or []))

        sections: list[tuple[str, list[str]]] = []
        if cantrips:
            sections.append(("Cantrips", sorted(cantrips)))

        by_level: dict[int, list[str]] = {}
        unknown_level: list[str] = []
        for name in spells:
            spell = self._spell_index.get(name)
            if spell is None:
                unknown_level.append(name)
                continue
            lvl = int(spell.get("level", 1))
            by_level.setdefault(lvl, []).append(name)

        for lvl in sorted(by_level.keys()):
            sections.append((f"Level {lvl}", sorted(by_level[lvl])))
        if unknown_level:
            sections.append(("Other", sorted(unknown_level)))

        self.spells_list.set_sectioned_items(sections)

        if sections and sections[0][1]:
            self.spells_list.select_item(sections[0][1][0])
            self._show_spell_details(sections[0][1][0])
        else:
            self._show_spell_details(None)

    def _on_spell_select(self, spell_name: str):
        self._show_spell_details(spell_name)

    def _show_spell_details(self, spell_name: str | None):
        if not spell_name:
            self.spell_title.configure(text="No spells known")
            self._set_spell_detail_text(
                "This character has no selected cantrips or spells."
            )
            return

        spell = self._spell_index.get(spell_name, {})
        if not spell:
            self.spell_title.configure(text=spell_name)
            self._set_spell_detail_text("No spell data found for this entry.")
            return

        level = spell.get("level", 0)
        level_text = "Cantrip" if level == 0 else f"Level {level}"
        school = spell.get("school", "Unknown")

        comps = spell.get("components", {}) or {}
        comp_text = []
        for k in ["V", "S", "M"]:
            val = comps.get(k)
            if not val:
                continue
            if k == "M" and isinstance(val, str):
                comp_text.append(f"M ({val})")
            else:
                comp_text.append(k)
        components = ", ".join(comp_text) if comp_text else "None"

        self.spell_title.configure(text=spell.get("name", spell_name))
        body = [
            f"Level: {level_text}",
            f"School: {school}",
            f"Casting Time: {spell.get('casting_time', 'Unknown')}",
            f"Range: {spell.get('range', 'Unknown')}",
            f"Duration: {spell.get('duration', 'Unknown')}",
            f"Components: {components}",
        ]
        source = spell.get("source")
        if source:
            body.append(f"Source: {source}")
        body.append("")
        body.append(spell.get("description", "No description available."))

        higher = (spell.get("higher_levels") or "").strip()
        if higher:
            body.extend(["", f"At Higher Levels: {higher}"])

        self._set_spell_detail_text("\n".join(body))

    def _set_spell_detail_text(self, text: str):
        label_prefixes = {
            "Level",
            "School",
            "Casting Time",
            "Range",
            "Duration",
            "Components",
            "Source",
            "At Higher Levels",
        }

        self.spell_detail_text.configure(state=tk.NORMAL)
        self.spell_detail_text.delete("1.0", tk.END)

        for raw_line in text.splitlines():
            if ":" in raw_line:
                key, rest = raw_line.split(":", 1)
                if key in label_prefixes:
                    self.spell_detail_text.insert(tk.END, f"{key}:", "label")
                    self.spell_detail_text.insert(tk.END, f"{rest}\n")
                    continue
            self.spell_detail_text.insert(tk.END, f"{raw_line}\n")

        self.spell_detail_text.configure(state=tk.DISABLED)

    def _on_sheet_changed(self):
        if not self.save_path:
            self._schedule_tab_refresh()
            return
        save_character(
            self.character, characters_dir(), existing_filename=self.save_path
        )
        self._schedule_tab_refresh()

    def _schedule_tab_refresh(self):
        if self._refresh_scheduled:
            return
        self._refresh_scheduled = True
        self.after_idle(self._refresh_after_sheet_change)

    def _refresh_after_sheet_change(self):
        self._refresh_scheduled = False
        if self._building_tabs:
            self._schedule_tab_refresh()
            return
        selected = self.tabs.index("current")
        self._refresh_tabs(refresh_spells=False)
        self.tabs.select(selected)

    # ── Navigation ──────────────────────────────────────────────

    def _on_back(self):
        self.app.show_home()

    def _on_edit(self):
        self.app.show_wizard(self.character, self.save_path)

    def _on_add_inventory(self):
        AddInventoryDialog(
            self,
            self.character,
            self.data,
            on_changed=lambda: (self._on_sheet_changed(), self._refresh_tabs()),
        )

    def _on_level_up(self):
        from gui.level_up_wizard import LevelUpWizard

        def on_complete():
            # Save and refresh
            save_character(
                self.character, characters_dir(), existing_filename=self.save_path
            )
            self.app.show_viewer(self.character, self.save_path)

        LevelUpWizard(self, self.character, self.data, on_complete=on_complete)

    # ── Exports (same pattern as SummaryStep) ───────────────────

    def _export_json(self):
        from models.character_store import character_to_save_dict
        import json

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"{self.character.name}.json",
        )
        if path:
            data = character_to_save_dict(self.character)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            AlertDialog(self.winfo_toplevel(), "Export", f"Character saved to {path}")

    def _export_pdf(self):
        from export.pdf_export import export_pdf

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"{self.character.name}.pdf",
        )
        if path:
            try:
                export_pdf(self.character, path)
                AlertDialog(
                    self.winfo_toplevel(),
                    "Export",
                    f"PDF character sheet saved to {path}",
                )
            except Exception as e:
                AlertDialog(
                    self.winfo_toplevel(),
                    "Export Error",
                    f"Failed to generate PDF:\n{e}",
                )
