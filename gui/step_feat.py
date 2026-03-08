"""Step 5: Feat display and origin feat selection (from background + species)."""

import re
import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import ScrollableFrame, SectionedListbox, WrappingLabel
from gui.theme import COLORS, FONTS
from gui.source_config import SECTION_ORDER, group_by_category, save_settings


class FeatStep(WizardStep):
    tab_title = "Feat"

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        ttk.Label(self.frame, text="Feats", style="Heading.TLabel").pack(
            anchor="w", padx=12, pady=(12, 4))
        ttk.Label(self.frame,
                  text="Your background grants a feat. Some species (Human) also grant an origin feat.",
                  style="Dim.TLabel").pack(anchor="w", padx=12)

        self.content = ScrollableFrame(self.frame)
        self.content.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        self.inner = self.content.inner

        # Section 1: Background feat (fixed)
        self.bg_section = ttk.LabelFrame(self.inner, text="From Background")
        self.bg_section.pack(fill=tk.X, pady=(0, 12))

        self.bg_feat_label = ttk.Label(self.bg_section, text="No background selected",
                                        style="Subheading.TLabel")
        self.bg_feat_label.pack(anchor="w", padx=8, pady=(4, 0))

        self.bg_feat_source = ttk.Label(self.bg_section, text="", style="Dim.TLabel")
        self.bg_feat_source.pack(anchor="w", padx=8)

        self.bg_benefits_frame = ttk.Frame(self.bg_section)
        self.bg_benefits_frame.pack(fill=tk.X, padx=8, pady=(4, 8))

        self.bg_note_frame = ttk.Frame(self.bg_section)
        self.bg_note_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        # Section 2: Species feat (Human Versatile)
        self.sp_section = ttk.LabelFrame(self.inner, text="From Species (Human — Versatile)")
        # Not packed by default — only shown for Human

        self.sp_top = ttk.Frame(self.sp_section)
        self.sp_top.pack(fill=tk.BOTH, expand=True)
        self.sp_top.columnconfigure(1, weight=1)
        self.sp_top.rowconfigure(0, weight=1)

        # Left: source toggles + searchable sectioned list of origin feats
        self.sp_list_frame = ttk.Frame(self.sp_top, width=220, height=300)
        self.sp_list_frame.grid(row=0, column=0, sticky="nsew", padx=(4, 4), pady=4)
        self.sp_list_frame.grid_propagate(False)

        ttk.Label(self.sp_list_frame, text="Choose an Origin Feat:",
                  style="Dim.TLabel").pack(anchor="w", pady=(0, 2))

        # Source filter toggles for origin feats
        self.feat_toggle_frame = ttk.Frame(self.sp_list_frame)
        self.feat_toggle_frame.pack(fill=tk.X, pady=(0, 4))
        self.feat_toggle_vars: dict[str, tk.BooleanVar] = {}
        self._build_feat_toggles()

        self.origin_feat_list = SectionedListbox(self.sp_list_frame, on_select=self._on_species_feat_select)
        self.origin_feat_list.pack(fill=tk.BOTH, expand=True)

        # Right: detail panel for selected origin feat
        self.sp_detail = ttk.Frame(self.sp_top)
        self.sp_detail.grid(row=0, column=1, sticky="nsew", padx=(4, 4), pady=4)

        self.sp_feat_label = ttk.Label(self.sp_detail, text="Select a feat",
                                        style="Subheading.TLabel")
        self.sp_feat_label.pack(anchor="w", pady=(0, 2))

        self.sp_feat_source = ttk.Label(self.sp_detail, text="", style="Dim.TLabel")
        self.sp_feat_source.pack(anchor="w")

        self.sp_benefits_frame = ttk.Frame(self.sp_detail)
        self.sp_benefits_frame.pack(fill=tk.X, pady=(4, 0))

    def _build_feat_toggles(self):
        """Build source filter checkboxes for origin feats."""
        for w in self.feat_toggle_frame.winfo_children():
            w.destroy()
        self.feat_toggle_vars.clear()

        filters = self.data.source_filters.get("feats", {})
        sections = SECTION_ORDER["feats"]

        for cat in sections:
            var = tk.BooleanVar(value=filters.get(cat, True))
            cb = ttk.Checkbutton(self.feat_toggle_frame, text=cat, variable=var,
                                 command=self._on_feat_toggle_change)
            cb.pack(side=tk.LEFT, padx=(0, 4))
            self.feat_toggle_vars[cat] = var

    def _on_feat_toggle_change(self):
        """Update filters and rebuild origin feat list."""
        filters = {cat: var.get() for cat, var in self.feat_toggle_vars.items()}
        self.data.source_filters["feats"] = filters
        save_settings(self.data.source_filters)
        self._populate_origin_feats()

    def _populate_origin_feats(self):
        """Build sectioned origin feat list based on current filters."""
        filters = self.data.source_filters.get("feats", {})
        enabled = {cat for cat, on in filters.items() if on}

        origin_feats = [f for f in self.data.feats if f.get("category") == "origin"]
        grouped = group_by_category(origin_feats, "feats")
        sections = [(cat, [f["name"] for f in items])
                     for cat, items in grouped if cat in enabled]
        self.origin_feat_list.set_sectioned_items(sections)

    def on_enter(self):
        """Refresh based on current background and species."""
        self._refresh_background_feat()
        self._refresh_species_feat()

    def _refresh_background_feat(self):
        """Show the fixed feat granted by the background."""
        for w in self.bg_benefits_frame.winfo_children():
            w.destroy()
        for w in self.bg_note_frame.winfo_children():
            w.destroy()

        bg = self.character.background
        if not bg or not bg.get("feat"):
            self.bg_feat_label.configure(text="No background selected")
            self.bg_feat_source.configure(text="")
            return

        feat_name = bg["feat"]
        feat = self.data.find_feat(feat_name)
        self.character.feat = feat

        self.bg_feat_label.configure(text=feat_name)
        if feat:
            self.bg_feat_source.configure(text=f"Source: {feat.get('source', 'Unknown')}")
            self._render_benefits(feat, self.bg_benefits_frame)

            # Magic Initiate note
            if "Magic Initiate" in feat_name:
                m = re.search(r'\((\w+)\)', feat_name)
                if m:
                    spell_class = m.group(1)
                    WrappingLabel(self.bg_note_frame,
                              text=f"This grants 2 cantrips and 1 level 1 spell from the {spell_class} list. "
                                   f"Select them in the Spells tab.",
                              foreground=COLORS["accent"]).pack(fill=tk.X, anchor="w")
        else:
            self.bg_feat_source.configure(text="(Feat data not found)")

    def _refresh_species_feat(self):
        """Show origin feat chooser if species grants one (Human Versatile)."""
        species = self.character.species
        grants_feat = False

        if species:
            for t in species.get("traits", []):
                if "origin feat" in t.get("description", "").lower():
                    grants_feat = True
                    break

        if grants_feat:
            self.sp_section.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

            # Update the label to reflect the actual species name
            sp_name = species.get("name", "Species")
            trait_name = ""
            for t in species.get("traits", []):
                if "origin feat" in t.get("description", "").lower():
                    trait_name = t["name"]
                    break
            self.sp_section.configure(text=f"From Species ({sp_name} — {trait_name})")

            # Populate origin feat list with sections
            self._populate_origin_feats()

            # Re-select if we already had one
            if self.character.species_origin_feat:
                self.origin_feat_list.select_item(self.character.species_origin_feat.get("name", ""))
        else:
            self.sp_section.pack_forget()
            self.character.species_origin_feat = None

    def _on_species_feat_select(self, name: str):
        feat = self.data.feats_by_name.get(name)
        if not feat:
            return

        self.character.species_origin_feat = feat

        # Update detail panel
        self.sp_feat_label.configure(text=feat["name"])
        self.sp_feat_source.configure(text=f"Source: {feat.get('source', 'Unknown')}")

        for w in self.sp_benefits_frame.winfo_children():
            w.destroy()
        self._render_benefits(feat, self.sp_benefits_frame)
        self.notify_change()

    def _render_benefits(self, feat: dict, parent: ttk.Frame):
        """Render feat benefits into a frame."""
        for benefit in feat.get("benefits", []):
            bf = ttk.Frame(parent)
            bf.pack(fill=tk.X, pady=2)
            ttk.Label(bf, text=benefit.get("name", ""),
                      foreground=COLORS["accent"], font=FONTS["subheading"]).pack(anchor="w")
            desc = benefit.get("description", "")
            if desc:
                WrappingLabel(bf, text=desc[:300],
                          foreground=COLORS["fg_dim"]).pack(fill=tk.X, anchor="w", padx=(16, 0))
