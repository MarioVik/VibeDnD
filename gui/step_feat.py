"""Step 7: Feat display and origin feat selection (from background + species)."""

import re
import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import (
    ScrollableFrame,
    SectionedListbox,
    WrappingLabel,
    FormattedDescription,
    GradientHeader,
    SectionHeader,
    CardFrame,
    PillBadge,
)
from gui.theme import COLORS, FONTS, SPACING
from gui.source_config import (
    SECTION_ORDER,
    UA_CATEGORY,
    group_by_category,
    handle_ua_toggle,
    save_settings,
)


class FeatStep(WizardStep):
    tab_title = "Feat"

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # ── Hero header ─────────────────────────────────────────
        hero = GradientHeader(self.frame, min_height=60)
        hero.grid(row=0, column=0, sticky="ew")

        hero_inner = tk.Frame(hero.inner, bg=COLORS["bg_hero"])
        hero_inner.pack(fill=tk.X, padx=SPACING["card_pad"], pady=(SPACING["xl"], 0))

        tk.Label(
            hero_inner,
            text="Feats",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        tk.Label(
            hero.inner,
            text="Your background grants a feat. Some species (Human) also grant an origin feat.",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xs"], SPACING["xl"]))

        # ── Scrollable content ──────────────────────────────────
        self.content = ScrollableFrame(self.frame)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.inner = self.content.inner

        # Section 1: Background feat (fixed)
        self.bg_section = tk.Frame(self.inner, bg=COLORS["bg"])
        self.bg_section.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"]))

        SectionHeader(self.bg_section, text="Background Feat").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        self.bg_card = CardFrame(self.bg_section, pad=SPACING["lg"])
        self.bg_card.pack(fill=tk.X)

        self.bg_feat_label = tk.Label(
            self.bg_card.inner,
            text="No background selected",
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        )
        self.bg_feat_label.pack(anchor="w")

        self.bg_feat_source = tk.Label(
            self.bg_card.inner,
            text="",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        )
        self.bg_feat_source.pack(anchor="w")

        self.bg_benefits_frame = tk.Frame(self.bg_card.inner, bg=COLORS["bg_surface"])
        self.bg_benefits_frame.pack(fill=tk.X, pady=(SPACING["xs"], 0))

        self.bg_note_frame = tk.Frame(self.bg_card.inner, bg=COLORS["bg_surface"])
        self.bg_note_frame.pack(fill=tk.X)

        # Section 2: Species feat (Human Versatile)
        self.sp_section = tk.Frame(self.inner, bg=COLORS["bg"])
        # Not packed by default — only shown for Human

        self.sp_section_header = SectionHeader(self.sp_section, text="Species Feat")
        self.sp_section_header.pack(fill=tk.X, pady=(0, SPACING["sm"]))

        self.sp_top = tk.Frame(self.sp_section, bg=COLORS["bg"])
        self.sp_top.pack(fill=tk.BOTH, expand=True)
        self.sp_top.columnconfigure(1, weight=1)
        self.sp_top.rowconfigure(0, weight=1)

        # Left: source toggles + searchable sectioned list
        self.sp_list_frame = tk.Frame(self.sp_top, bg=COLORS["bg"], width=220, height=300)
        self.sp_list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["xs"]), pady=0)
        self.sp_list_frame.grid_propagate(False)

        tk.Label(
            self.sp_list_frame,
            text="Choose an Origin Feat:",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
        ).pack(anchor="w", pady=(0, 2))

        self.feat_toggle_frame = tk.Frame(self.sp_list_frame, bg=COLORS["bg"])
        self.feat_toggle_frame.pack(fill=tk.X, pady=(0, SPACING["xs"]))
        self.feat_toggle_vars: dict[str, tk.BooleanVar] = {}
        self._ua_prev_enabled = False
        self._build_feat_toggles()

        self.origin_feat_list = SectionedListbox(
            self.sp_list_frame, on_select=self._on_species_feat_select
        )
        self.origin_feat_list.pack(fill=tk.BOTH, expand=True)

        # Right: detail panel for selected origin feat
        self.sp_detail_card = CardFrame(self.sp_top, pad=SPACING["lg"])
        self.sp_detail_card.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        self.sp_feat_label = tk.Label(
            self.sp_detail_card.inner,
            text="Select a feat",
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        )
        self.sp_feat_label.pack(anchor="w")

        self.sp_feat_source = tk.Label(
            self.sp_detail_card.inner,
            text="",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        )
        self.sp_feat_source.pack(anchor="w")

        self.sp_benefits_frame = tk.Frame(self.sp_detail_card.inner, bg=COLORS["bg_surface"])
        self.sp_benefits_frame.pack(fill=tk.X, pady=(SPACING["xs"], 0))

    def _build_feat_toggles(self):
        """Build source filter checkboxes for origin feats."""
        for w in self.feat_toggle_frame.winfo_children():
            w.destroy()
        self.feat_toggle_vars.clear()

        filters = self.data.source_filters.get("feats", {})
        sections = SECTION_ORDER["feats"]
        self._ua_prev_enabled = filters.get(UA_CATEGORY, False)

        for cat in sections:
            label = "UA" if cat == UA_CATEGORY else cat
            var = tk.BooleanVar(value=filters.get(cat, cat != UA_CATEGORY))
            cb = ttk.Checkbutton(
                self.feat_toggle_frame,
                text=label,
                variable=var,
                command=self._on_feat_toggle_change,
            )
            cb.pack(side=tk.LEFT, padx=(0, 4))
            self.feat_toggle_vars[cat] = var

    def _on_feat_toggle_change(self):
        ua_var = self.feat_toggle_vars.get(UA_CATEGORY)
        proceed, _ = handle_ua_toggle(self.frame, ua_var, self._ua_prev_enabled)
        if not proceed:
            return

        filters = {cat: var.get() for cat, var in self.feat_toggle_vars.items()}
        self.data.source_filters["feats"] = filters
        self._ua_prev_enabled = filters.get(UA_CATEGORY, False)
        save_settings(self.data.source_filters)
        self._populate_origin_feats()

    def _populate_origin_feats(self):
        filters = self.data.source_filters.get("feats", {})
        enabled = {cat for cat, on in filters.items() if on}

        origin_feats = [f for f in self.data.feats if f.get("category") == "origin"]
        grouped = group_by_category(origin_feats, "feats")
        sections = [
            (cat, [f["name"] for f in items])
            for cat, items in grouped
            if cat in enabled
        ]
        self.origin_feat_list.set_sectioned_items(sections)

    def on_enter(self):
        self._refresh_background_feat()
        self._refresh_species_feat()

    def _refresh_background_feat(self):
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
            self.bg_feat_source.configure(
                text=f"Source: {feat.get('source', 'Unknown')}"
            )
            self._render_benefits(feat, self.bg_benefits_frame)

            if "Magic Initiate" in feat_name:
                m = re.search(r"\((\w+)\)", feat_name)
                if m:
                    spell_class = m.group(1)
                    tk.Label(
                        self.bg_note_frame,
                        text=f"This grants 2 cantrips and 1 level 1 spell from the {spell_class} list. "
                        f"Select them in the Spells tab.",
                        font=FONTS["body"],
                        fg=COLORS["accent_text"],
                        bg=COLORS["bg_surface"],
                        wraplength=500,
                        justify=tk.LEFT,
                    ).pack(fill=tk.X, anchor="w", pady=(SPACING["xs"], 0))
        else:
            self.bg_feat_source.configure(text="(Feat data not found)")

    def _refresh_species_feat(self):
        species = self.character.species
        grants_feat = False

        if species:
            for t in species.get("traits", []):
                if "origin feat" in t.get("description", "").lower():
                    grants_feat = True
                    break

        if grants_feat:
            self.sp_section.pack(fill=tk.BOTH, expand=True, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

            sp_name = species.get("name", "Species")
            trait_name = ""
            for t in species.get("traits", []):
                if "origin feat" in t.get("description", "").lower():
                    trait_name = t["name"]
                    break
            self.sp_section_header.set_bg(COLORS["bg"])
            # Update section header text by destroying and rebuilding
            for w in self.sp_section_header.winfo_children():
                w.destroy()
            self.sp_section_header.__init__(self.sp_section, text=f"Species Feat ({sp_name} \u2014 {trait_name})")
            self.sp_section_header.pack(fill=tk.X, pady=(0, SPACING["sm"]))

            self._populate_origin_feats()

            if self.character.species_origin_feat:
                self.origin_feat_list.select_item(
                    self.character.species_origin_feat.get("name", "")
                )
        else:
            self.sp_section.pack_forget()
            self.character.species_origin_feat = None

    def _on_species_feat_select(self, name: str):
        feat = self.data.feats_by_name.get(name)
        if not feat:
            return

        self.character.species_origin_feat = feat

        self.sp_feat_label.configure(text=feat["name"])
        self.sp_feat_source.configure(text=f"Source: {feat.get('source', 'Unknown')}")

        for w in self.sp_benefits_frame.winfo_children():
            w.destroy()
        self._render_benefits(feat, self.sp_benefits_frame)
        self.notify_change()

    def _render_benefits(self, feat: dict, parent):
        """Render feat benefits into a frame."""
        _bg = parent.cget("bg") if hasattr(parent, "cget") else COLORS["bg_surface"]
        for benefit in feat.get("benefits", []):
            bf = tk.Frame(parent, bg=_bg)
            bf.pack(fill=tk.X, pady=2)
            tk.Label(
                bf,
                text=benefit.get("name", ""),
                font=FONTS["body_bold"],
                fg=COLORS["accent_text"],
                bg=_bg,
            ).pack(anchor="w")
            desc = benefit.get("description", "")
            if desc:
                FormattedDescription(
                    bf,
                    text=desc,
                    font=FONTS["body_small"],
                    foreground=COLORS["fg_dim"],
                    background=_bg,
                ).pack(fill=tk.X, anchor="w", padx=(SPACING["lg"], 0))
