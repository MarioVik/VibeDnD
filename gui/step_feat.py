"""Feat step for optional species origin feat selection."""

import tkinter as tk
from tkinter import ttk

from gui.base_step import WizardStep
from gui.widgets import (
    SectionedListbox,
    FormattedDescription,
    GradientHeader,
    SectionHeader,
    CardFrame,
)
from gui.theme import COLORS, FONTS, SPACING
from gui.source_config import (
    SECTION_ORDER,
    UA_CATEGORY,
    group_by_category,
    handle_ua_toggle,
    save_settings,
)
from models.feat_utils import get_owned_feat_names


class FeatStep(WizardStep):
    tab_title = "Feat"

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        hero = GradientHeader(self.frame, min_height=60)
        hero.grid(row=0, column=0, sticky="ew")

        hero_inner = tk.Frame(hero.inner, bg=COLORS["bg_hero"])
        hero_inner.pack(fill=tk.X, padx=SPACING["card_pad"], pady=(SPACING["xl"], 0))

        tk.Label(
            hero_inner,
            text="Feat",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        tk.Label(
            hero.inner,
            text=(
                "Choose an additional origin feat here only if your species grants one, "
                "such as Human."
            ),
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
            wraplength=760,
            justify=tk.LEFT,
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xs"], SPACING["xl"]))

        self.content = tk.Frame(self.frame, bg=COLORS["bg"])
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self.empty_state = CardFrame(self.content, pad=SPACING["lg"])
        tk.Label(
            self.empty_state.inner,
            text="No additional feat to choose",
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w")
        self.empty_body = tk.Label(
            self.empty_state.inner,
            text="Your selected species does not grant an origin feat.",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
            wraplength=700,
            justify=tk.LEFT,
        )
        self.empty_body.pack(anchor="w", pady=(SPACING["xs"], 0))

        self.sp_section = tk.Frame(self.content, bg=COLORS["bg"])
        self.sp_section.columnconfigure(1, weight=1)
        self.sp_section.rowconfigure(1, weight=1)

        self.sp_section_header = SectionHeader(self.sp_section, text="Species Feat")
        self.sp_section_header.grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, SPACING["sm"])
        )

        self.sp_section.columnconfigure(0, minsize=260)

        self.sp_list_frame = tk.Frame(self.sp_section, bg=COLORS["bg"], width=260)
        self.sp_list_frame.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(0, SPACING["xs"]),
            pady=0,
        )
        self.sp_list_frame.columnconfigure(0, weight=1)
        self.sp_list_frame.rowconfigure(2, weight=1)

        tk.Label(
            self.sp_list_frame,
            text="Choose an Origin Feat:",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 2))

        self.feat_toggle_frame = tk.Frame(self.sp_list_frame, bg=COLORS["bg"])
        self.feat_toggle_frame.grid(row=1, column=0, sticky="ew", pady=(0, SPACING["xs"]))
        self.feat_toggle_vars: dict[str, tk.BooleanVar] = {}
        self._ua_prev_enabled = False
        self._build_feat_toggles()

        self.origin_feat_list = SectionedListbox(
            self.sp_list_frame,
            on_select=self._on_species_feat_select,
        )
        self.origin_feat_list.grid(row=2, column=0, sticky="nsew")

        self.sp_detail_scroll = tk.Frame(self.sp_section, bg=COLORS["bg"])
        self.sp_detail_scroll.grid(row=1, column=1, sticky="nsew", padx=0, pady=0)
        self.sp_detail_scroll.columnconfigure(0, weight=1)
        self.sp_detail_scroll.rowconfigure(0, weight=1)

        self.sp_detail_card = CardFrame(self.sp_detail_scroll, pad=SPACING["lg"])
        self.sp_detail_card.grid(row=0, column=0, sticky="nsew")

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

        self.sp_benefits_frame = tk.Frame(
            self.sp_detail_card.inner,
            bg=COLORS["bg_surface"],
        )
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

        # Compute owned feat names (case-insensitive) and allow the current
        # species origin feat to remain visible so existing selections persist.
        owned = get_owned_feat_names(self.character)
        current_name = ""
        if self.character.species_origin_feat:
            current_name = str(
                self.character.species_origin_feat.get("name", "") or ""
            ).strip()
        current_key = current_name.casefold() if current_name else ""

        origin_feats = []
        for feat in self.data.feats:
            if feat.get("category") != "origin":
                continue
            name = str(feat.get("name", "") or "").strip()
            key = name.casefold()
            if key in owned and key != current_key:
                continue
            origin_feats.append(feat)

        grouped = group_by_category(origin_feats, "feats")
        sections = [
            (cat, [f["name"] for f in items])
            for cat, items in grouped
            if cat in enabled
        ]
        self.origin_feat_list.set_sectioned_items(sections)

    def on_enter(self):
        self._refresh_species_feat()

    def is_valid(self) -> bool:
        return not self._species_grants_origin_feat()[0] or self.character.species_origin_feat is not None

    def _species_grants_origin_feat(self) -> tuple[bool, str, str]:
        species = self.character.species or {}
        species_name = species.get("name", "Species")
        for trait in species.get("traits", []):
            if "origin feat" in trait.get("description", "").lower():
                return True, species_name, trait.get("name", "")
        return False, species_name, ""

    def _set_species_section_title(self, text: str):
        self.sp_section_header.destroy()
        self.sp_section_header = SectionHeader(self.sp_section, text=text)
        self.sp_section_header.grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, SPACING["sm"])
        )

    def _clear_species_feat_details(self):
        self.sp_feat_label.configure(text="Select a feat")
        self.sp_feat_source.configure(text="")
        for w in self.sp_benefits_frame.winfo_children():
            w.destroy()

    def _refresh_species_feat(self):
        grants_feat, sp_name, trait_name = self._species_grants_origin_feat()

        if grants_feat:
            # If the stored species origin feat duplicates another source (such
            # as the background feat or Warlock Lessons origin feat), clear it.
            if self.character.species_origin_feat:
                sp_feat_name = str(
                    self.character.species_origin_feat.get("name", "") or ""
                ).strip()
                bg_name = str(
                    (getattr(self.character, "feat", None) or {}).get("name", "")
                    or ""
                ).strip()
                lessons_name = str(
                    (
                        getattr(self.character, "level1_class_choices", {}) or {}
                    ).get("warlock_lessons_feat", "")
                    or ""
                ).strip()
                if sp_feat_name and sp_feat_name in {bg_name, lessons_name}:
                    self.character.species_origin_feat = None

            self.empty_state.grid_forget()
            if not self.sp_section.winfo_manager():
                self.sp_section.grid(
                    row=0,
                    column=0,
                    sticky="nsew",
                    padx=SPACING["lg"],
                    pady=(SPACING["sm"], SPACING["sm"]),
                )

            title = f"Species Feat ({sp_name})"
            if trait_name:
                title = f"Species Feat ({sp_name} - {trait_name})"
            self._set_species_section_title(title)
            self._populate_origin_feats()
            self._clear_species_feat_details()

            if self.character.species_origin_feat:
                self.origin_feat_list.select_item(
                    self.character.species_origin_feat.get("name", "")
                )
        else:
            self.sp_section.grid_forget()
            self.character.species_origin_feat = None
            self._clear_species_feat_details()

            body = "Your selected species does not grant an origin feat."
            if self.character.species:
                body = (
                    f"{self.character.species.get('name', 'Your species')} does not "
                    "grant an origin feat."
                )
            self.empty_body.configure(text=body)

            if not self.empty_state.winfo_manager():
                self.empty_state.grid(
                    row=0,
                    column=0,
                    sticky="new",
                    padx=SPACING["lg"],
                    pady=(SPACING["sm"], SPACING["sm"]),
                )

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
