"""Step 1: Species selection."""

import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import SectionedListbox, ScrollableFrame, WrappingLabel
from gui.theme import COLORS, FONTS
from gui.source_config import SECTION_ORDER, group_by_category, save_settings


class SpeciesStep(WizardStep):
    tab_title = "Species"

    def build_ui(self):
        self._edit_initialized = False
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(0, weight=1)

        # Left: species list with source toggles
        left = ttk.Frame(self.frame, width=220)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left.grid_propagate(False)

        ttk.Label(left, text="Choose Species", style="Heading.TLabel").pack(anchor="w", pady=(0, 4))

        # Source filter toggles
        self.toggle_frame = ttk.Frame(left)
        self.toggle_frame.pack(fill=tk.X, pady=(0, 4))
        self.toggle_vars: dict[str, tk.BooleanVar] = {}
        self._build_toggles()

        self.species_list = SectionedListbox(left, on_select=self._on_select)
        self.species_list.pack(fill=tk.BOTH, expand=True)

        # Right: detail panel
        right = ScrollableFrame(self.frame)
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        self.detail = right.inner

        self.detail_name = ttk.Label(self.detail, text="Select a species", style="Heading.TLabel")
        self.detail_name.pack(anchor="w", pady=(0, 4))

        self.detail_source = ttk.Label(self.detail, text="", style="Dim.TLabel")
        self.detail_source.pack(anchor="w")

        self.detail_desc = WrappingLabel(self.detail, text="")
        self.detail_desc.pack(fill=tk.X, anchor="w", pady=(8, 0))

        ttk.Separator(self.detail, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

        # Stats frame
        self.stats_frame = ttk.Frame(self.detail)
        self.stats_frame.pack(fill=tk.X)

        # Size choice (for species with options)
        self.size_frame = ttk.Frame(self.detail)
        self.size_var = tk.StringVar(value="Medium")
        self.size_var.trace_add("write", self._on_size_change)

        # Sub-choice (lineages etc)
        self.sub_frame = ttk.Frame(self.detail)
        self.sub_var = tk.StringVar()
        self.sub_var.trace_add("write", self._on_sub_change)

        # Traits
        self.traits_frame = ttk.Frame(self.detail)
        self.traits_frame.pack(fill=tk.X, pady=(8, 0))

        self._populate_list()

    def on_enter(self):
        """Pre-select species when editing an existing character."""
        if not self._edit_initialized and self.character.species:
            self._edit_initialized = True
            name = self.character.species.get("name", "")
            # Snapshot values that _on_select will reset
            saved_sub = self.character.species_sub_choice
            saved_size = self.character.size_choice
            # Select in list and populate detail panel
            self.species_list.select_item(name)
            self._on_select(name)
            # Restore saved choices
            if saved_sub:
                self.sub_var.set(saved_sub)
            if saved_size:
                self.size_var.set(saved_size)

    def _build_toggles(self):
        """Build source filter checkboxes."""
        for w in self.toggle_frame.winfo_children():
            w.destroy()
        self.toggle_vars.clear()

        filters = self.data.source_filters.get("species", {})
        sections = SECTION_ORDER["species"]

        for cat in sections:
            var = tk.BooleanVar(value=filters.get(cat, True))
            cb = ttk.Checkbutton(self.toggle_frame, text=cat, variable=var,
                                 command=self._on_toggle_change)
            cb.pack(side=tk.LEFT, padx=(0, 6))
            self.toggle_vars[cat] = var

    def _on_toggle_change(self):
        """Update filters and rebuild list when a toggle changes."""
        filters = {cat: var.get() for cat, var in self.toggle_vars.items()}
        self.data.source_filters["species"] = filters
        save_settings(self.data.source_filters)
        self._populate_list()

    def _populate_list(self):
        filters = self.data.source_filters.get("species", {})
        enabled = {cat for cat, on in filters.items() if on}

        # Group species by category, only include enabled sections
        grouped = group_by_category(self.data.species, "species")
        sections = [(cat, [s["name"] for s in items])
                     for cat, items in grouped if cat in enabled]
        self.species_list.set_sectioned_items(sections)

    def _on_select(self, name: str):
        sp = self.data.species_by_name.get(name)
        if not sp:
            return

        self.character.species = sp
        self.detail_name.configure(text=sp["name"])
        self.detail_source.configure(text=f"Source: {sp.get('source', 'Unknown')}")
        self.detail_desc.configure(text=sp.get("description", "")[:300])

        # Stats
        for w in self.stats_frame.winfo_children():
            w.destroy()

        stats_text = f"Type: {sp.get('creature_type', 'Humanoid')}  |  Speed: {sp.get('speed', 30)} ft"
        ttk.Label(self.stats_frame, text=stats_text, style="Subheading.TLabel").pack(anchor="w")

        # Size choice
        for w in self.size_frame.winfo_children():
            w.destroy()
        self.size_frame.pack_forget()

        size_data = sp.get("size", {})
        size_options = size_data.get("options", ["Medium"])
        if len(size_options) > 1:
            self.size_frame.pack(fill=tk.X, pady=(8, 0))
            ttk.Label(self.size_frame, text="Size:", style="Subheading.TLabel").pack(anchor="w")
            for opt in size_options:
                ttk.Radiobutton(self.size_frame, text=opt, variable=self.size_var, value=opt).pack(anchor="w", padx=16)
            self.size_var.set(size_options[0])
        else:
            self.character.size_choice = size_options[0]
            ttk.Label(self.stats_frame, text=f"  |  Size: {size_options[0]}", style="Subheading.TLabel").pack(side=tk.LEFT)

        # Sub-choices
        for w in self.sub_frame.winfo_children():
            w.destroy()
        self.sub_frame.pack_forget()

        if sp.get("sub_choices"):
            self.sub_frame.pack(fill=tk.X, pady=(8, 0))
            choices = sp["sub_choices"]
            if choices and isinstance(choices[0], dict):
                first_key = list(choices[0].keys())[0]
                ttk.Label(self.sub_frame, text=f"Choose {first_key}:", style="Subheading.TLabel").pack(anchor="w")
                choice_names = [c.get(first_key, "Unknown") for c in choices]
                combo = ttk.Combobox(self.sub_frame, textvariable=self.sub_var,
                                     values=choice_names, state="readonly", width=30)
                combo.pack(anchor="w", padx=16, pady=4)
                if choice_names:
                    self.sub_var.set(choice_names[0])
                    self.character.species_sub_choice = choice_names[0]

        # Traits
        for w in self.traits_frame.winfo_children():
            w.destroy()

        traits = sp.get("traits", [])
        if traits:
            ttk.Label(self.traits_frame, text="Traits", style="Subheading.TLabel").pack(anchor="w", pady=(0, 4))
            for trait in traits:
                tf = ttk.Frame(self.traits_frame)
                tf.pack(fill=tk.X, pady=2)
                ttk.Label(tf, text=f"  {trait['name']}.", font=FONTS["subheading"],
                          foreground=COLORS["accent"]).pack(anchor="w")
                WrappingLabel(tf, text=f"    {trait.get('description', '')[:200]}",
                          foreground=COLORS["fg_dim"]).pack(fill=tk.X, anchor="w")

        self.notify_change()

    def _on_size_change(self, *args):
        self.character.size_choice = self.size_var.get()
        self.notify_change()

    def _on_sub_change(self, *args):
        self.character.species_sub_choice = self.sub_var.get()
        self.notify_change()
