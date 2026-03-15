"""Read-only character sheet viewer with export and edit buttons."""

import tkinter as tk
from tkinter import ttk, filedialog

from gui.theme import COLORS, FONTS
from gui.widgets import ScrollableFrame, AlertDialog, SectionedListbox, WrappingLabel
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

        right_scroll = ScrollableFrame(self.spells_tab)
        right_scroll.grid(row=0, column=1, sticky="nsew", pady=(2, 2))
        self._spell_detail = right_scroll.inner

        self.spell_title = ttk.Label(
            self._spell_detail,
            text="Select a spell",
            style="Heading.TLabel",
        )
        self.spell_title.pack(anchor="w", pady=(0, 2))

        self.spell_meta = ttk.Label(self._spell_detail, text="", style="Dim.TLabel")
        self.spell_meta.pack(anchor="w", pady=(0, 4))

        self.spell_desc = WrappingLabel(self._spell_detail, text="")
        self.spell_desc.pack(fill=tk.X, anchor="w", pady=(0, 2))

        self.spell_higher = WrappingLabel(
            self._spell_detail,
            text="",
            foreground=COLORS["fg_dim"],
        )
        self.spell_higher.pack(fill=tk.X, anchor="w", pady=(4, 0))

    def _refresh_tabs(self):
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
        self._refresh_spells_tab()

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
            self.spell_meta.configure(text="")
            self.spell_desc.configure(
                text="This character has no selected cantrips or spells."
            )
            self.spell_higher.configure(text="")
            return

        spell = self._spell_index.get(spell_name, {})
        if not spell:
            self.spell_title.configure(text=spell_name)
            self.spell_meta.configure(text="Details unavailable")
            self.spell_desc.configure(text="No spell data found for this entry.")
            self.spell_higher.configure(text="")
            return

        level = spell.get("level", 0)
        level_text = "Cantrip" if level == 0 else f"Level {level}"
        school = spell.get("school", "Unknown school")
        meta = (
            f"{level_text}  |  {school}  |  Casting: {spell.get('casting_time', 'Unknown')}"
            f"  |  Range: {spell.get('range', 'Unknown')}  |  Duration: {spell.get('duration', 'Unknown')}"
        )

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
        if comp_text:
            meta += f"  |  Components: {', '.join(comp_text)}"

        self.spell_title.configure(text=spell.get("name", spell_name))
        self.spell_meta.configure(text=meta)
        self.spell_desc.configure(text=spell.get("description", ""))

        higher = (spell.get("higher_levels") or "").strip()
        if higher:
            self.spell_higher.configure(text=f"At Higher Levels: {higher}")
        else:
            self.spell_higher.configure(text="")

    def _on_sheet_changed(self):
        if not self.save_path:
            return
        save_character(
            self.character, characters_dir(), existing_filename=self.save_path
        )

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
