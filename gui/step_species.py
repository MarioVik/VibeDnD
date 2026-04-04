"""Step 1: Species selection with grid tile view and detail substep."""

import os
import tkinter as tk
from tkinter import ttk

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover
    Image = None
    ImageTk = None

from gui.base_step import WizardStep
from gui.widgets import (
    ScrollableFrame,
    WrappingLabel,
    FormattedDescription,
    GradientHeader,
    SectionHeader,
    CardFrame,
    TileGrid,
)
from gui.species_trait_utils import get_species_trait_cards
from gui.theme import COLORS, FONTS, SPACING
from gui.source_config import (
    SECTION_ORDER,
    UA_CATEGORY,
    group_by_category,
    handle_ua_toggle,
    save_settings,
)
from paths import images_dir

CARD_RADIO_STYLE = "Card.TRadiobutton"
CONTAINER_RADIO_STYLE = "Container.TRadiobutton"


def _first_sentence(text: str) -> str:
    """Return the first sentence of a description."""
    if not text:
        return ""
    for end in (".", "!", "?"):
        idx = text.find(end)
        if idx != -1:
            return text[: idx + 1]
    return text[:120] + ("..." if len(text) > 120 else "")


def _slug(name: str) -> str:
    return name.lower().replace(" ", "_").replace("'", "")


def _species_image_path(species_name: str) -> str | None:
    """Return the image asset path for a species if one exists."""
    img_path = os.path.join(images_dir(), "species", f"{_slug(species_name)}.png")
    return img_path if os.path.isfile(img_path) else None


class SpeciesStep(WizardStep):
    tab_title = "Species"

    # Species whose feature block includes a required "choose one" option.
    TRAIT_OPTION_CHOICES = {
        "Gnome": {
            "label": "Gnomish Lineage",
            "options": ["Forest Gnome", "Rock Gnome"],
        },
        "Goliath": {
            "label": "Giant Ancestry",
            "options": [
                "Cloud's Jaunt (Cloud Giant)",
                "Fire's Burn (Fire Giant)",
                "Frost's Chill (Frost Giant)",
                "Hill's Tumble (Hill Giant)",
                "Stone's Endurance (Stone Giant)",
                "Storm's Thunder (Storm Giant)",
            ],
        },
        "Shifter": {
            "label": "Shifting Option",
            "options": ["Beasthide", "Longtooth", "Swiftstride", "Wildhunt"],
        },
    }

    def build_ui(self):
        self._edit_initialized = False
        self._requires_sub_choice = False
        self._current_substep = 0
        self._selected_species_name = ""
        self._species_portrait_path: str | None = None
        self._species_portrait_source = None
        self._species_portrait_photo = None
        self._species_portrait_pending = False

        # Two containers: grid view (substep 0) and detail view (substep 1)
        self._grid_frame = tk.Frame(self.frame, bg=COLORS["bg"])
        self._detail_frame = tk.Frame(self.frame, bg=COLORS["bg"])

        self._build_grid_view()
        self._build_detail_view()

        # Start on grid
        self._grid_frame.pack(fill=tk.BOTH, expand=True)

    # ── Substep protocol ──────────────────────────────────────────

    def has_substeps(self) -> bool:
        return True

    def get_current_substep(self) -> int:
        return self._current_substep

    def get_substep_count(self) -> int:
        return 2

    def go_to_substep(self, index: int):
        if index == self._current_substep:
            return
        self._current_substep = index
        if index == 0:
            self._detail_frame.pack_forget()
            self._grid_frame.pack(fill=tk.BOTH, expand=True)
        else:
            self._grid_frame.pack_forget()
            self._detail_frame.pack(fill=tk.BOTH, expand=True)
        self.notify_substep_change()

    def get_next_label(self) -> str | None:
        if self._current_substep == 1 and self.is_valid():
            return "Next: Choose Class  \u25b6"
        return None

    def is_primary_action_enabled(self) -> bool:
        return self.get_current_substep() > 0

    # ── Grid View (substep 0) ─────────────────────────────────────

    def _build_grid_view(self):
        # Header
        header = tk.Frame(self._grid_frame, bg=COLORS["bg"])
        header.pack(fill=tk.X, padx=SPACING["xl"], pady=(SPACING["xl"], 0))

        tk.Label(
            header,
            text="Choose Your Species",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Your species represents your heritage and inherent biological traits. "
            "Select the bloodline that will define your hero\u2019s physical prowess "
            "and mystical connection to the world.",
            font=FONTS["body_large"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
            wraplength=800,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(SPACING["sm"], 0))

        # Keep filter state plumbing available, but the species screen no longer
        # exposes filter controls in the character creator UI.
        self._grid_toggle_frame = tk.Frame(self._grid_frame, bg=COLORS["bg"])
        self.toggle_vars: dict[str, tk.BooleanVar] = {}
        self._ua_prev_enabled = False

        # Tile grid
        self._tile_grid = TileGrid(
            self._grid_frame,
            on_select=self._on_tile_click,
            preferred_cols=4,
            min_tile_width=180,
            expand_tiles_to_fill=True,
            expand_gap_with_tile=True,
            responsive_tile_height=True,
            content_side_padding=SPACING["xl"],
        )
        self._tile_grid.pack(fill=tk.BOTH, expand=True, padx=SPACING["sm"], pady=SPACING["sm"])

        self._populate_tiles()

    def _build_toggles(self):
        """Build source filter checkboxes."""
        for w in self._grid_toggle_frame.winfo_children():
            w.destroy()
        self.toggle_vars.clear()

        filters = self.data.source_filters.get("species", {})
        sections = SECTION_ORDER["species"]
        self._ua_prev_enabled = filters.get(UA_CATEGORY, False)

        for cat in sections:
            label = "UA" if cat == UA_CATEGORY else cat
            var = tk.BooleanVar(value=filters.get(cat, cat != UA_CATEGORY))
            cb = ttk.Checkbutton(
                self._grid_toggle_frame,
                text=label,
                variable=var,
                command=self._on_toggle_change,
            )
            cb.pack(side=tk.LEFT, padx=(0, 6))
            self.toggle_vars[cat] = var

    def _on_toggle_change(self):
        """Update filters and rebuild tiles when a toggle changes."""
        ua_var = self.toggle_vars.get(UA_CATEGORY)
        proceed, _ = handle_ua_toggle(self.frame, ua_var, self._ua_prev_enabled)
        if not proceed:
            return

        filters = {cat: var.get() for cat, var in self.toggle_vars.items()}
        self.data.source_filters["species"] = filters
        self._ua_prev_enabled = filters.get(UA_CATEGORY, False)
        save_settings(self.data.source_filters)
        self._populate_tiles()

    def _populate_tiles(self):
        grouped = group_by_category(self.data.species, "species")

        sections = []
        for cat, items in grouped:
            cat_tiles = []
            for sp in items:
                trait_choice = self.TRAIT_OPTION_CHOICES.get(sp.get("name", ""))
                excluded_traits = set()
                if trait_choice and not sp.get("sub_choices"):
                    excluded_traits = set(trait_choice.get("options", []))

                traits = [
                    trait["name"]
                    for trait in get_species_trait_cards(
                        sp,
                        excluded_names=excluded_traits,
                    )
                ]
                cat_tiles.append({
                    "name": sp["name"],
                    "description": _first_sentence(sp.get("description", "")),
                    "traits": traits,
                    "image_path": _species_image_path(sp["name"]),
                })
            if cat_tiles:
                sections.append((cat, cat_tiles))
        self._tile_grid.set_sectioned_tiles(sections)

    def _on_tile_click(self, name: str):
        """Handle tile click: select species and switch to detail view."""
        sp = self.data.species_by_name.get(name)
        if not sp:
            return
        self._on_select(name)
        self.go_to_substep(1)

    # ── Detail View (substep 1) — existing layout ─────────────────

    def _build_detail_view(self):
        self._detail_frame.columnconfigure(0, weight=1)
        self._detail_frame.rowconfigure(0, weight=1)

        right = ScrollableFrame(self._detail_frame)
        right.grid(row=0, column=0, sticky="nsew", padx=SPACING["sm"], pady=0)
        self.detail = right.inner

        self._detail_top = tk.Frame(self.detail, bg=COLORS["bg"])
        self._detail_top.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        self._detail_top.columnconfigure(0, weight=7, uniform="species_detail_top")
        self._detail_top.columnconfigure(1, weight=3, uniform="species_detail_top")
        self._detail_top.rowconfigure(0, weight=1)

        self._detail_text = tk.Frame(self._detail_top, bg=COLORS["bg"])
        self._detail_text.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, SPACING["lg"]),
        )

        self._detail_portrait = tk.Frame(self._detail_top, bg=COLORS["bg"])
        self._detail_portrait.grid(row=0, column=1, sticky="nsew")
        self._detail_portrait.rowconfigure(0, weight=1)
        self._detail_portrait.columnconfigure(0, weight=1)

        self._portrait_shell = tk.Frame(
            self._detail_portrait,
            bg=COLORS["bg_surface"],
            highlightbackground=COLORS["border_subtle_bg"],
            highlightthickness=1,
        )
        self._portrait_shell.grid(row=0, column=0, sticky="nsew")
        self._portrait_shell.rowconfigure(0, weight=1)
        self._portrait_shell.columnconfigure(0, weight=1)

        self._portrait_canvas = tk.Canvas(
            self._portrait_shell,
            bg=COLORS["bg_surface"],
            highlightthickness=0,
            bd=0,
        )
        self._portrait_canvas.grid(row=0, column=0, sticky="nsew")
        self._portrait_canvas.bind("<Configure>", self._on_species_portrait_configure)

        # Hero header for selected species
        self._hero = GradientHeader(self._detail_text, min_height=60)
        self._hero.pack(fill=tk.X, pady=(0, SPACING["sm"]))

        self.detail_name = tk.Label(
            self._hero.inner,
            text="Select a species",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        )
        self.detail_name.pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xl"], 0))

        self.detail_source = tk.Label(
            self._hero.inner,
            text="",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        )
        self.detail_source.pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xs"], SPACING["xl"]))

        self.detail_desc = WrappingLabel(
            self._detail_text, text="", foreground=COLORS["fg_dim"]
        )
        self.detail_desc.pack(fill=tk.X, anchor="w", padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        # Stats card
        self.stats_frame = tk.Frame(self._detail_text, bg=COLORS["bg"])
        self.stats_frame.pack(fill=tk.X, padx=SPACING["lg"])

        # Size choice (for species with options)
        self.size_frame = tk.Frame(self.detail, bg=COLORS["bg"])
        self.size_var = tk.StringVar(value="Medium")
        self.size_var.trace_add("write", self._on_size_change)

        # Sub-choice (lineages etc)
        self.sub_frame = tk.Frame(self.detail, bg=COLORS["bg"])
        self.sub_var = tk.StringVar()
        self.sub_var.trace_add("write", self._on_sub_change)

        # Traits
        self.traits_frame = tk.Frame(self.detail, bg=COLORS["bg"])
        self.traits_frame.pack(fill=tk.X, pady=(SPACING["xl"], 0))

    def on_enter(self):
        """Pre-select species when editing an existing character."""
        if not self._edit_initialized and self.character.species:
            self._edit_initialized = True
            name = self.character.species.get("name", "")
            # Snapshot values that _on_select will reset
            saved_sub = self.character.species_sub_choice
            saved_size = self.character.size_choice
            self._on_select(name)
            # Restore saved choices
            if saved_sub:
                self.sub_var.set(saved_sub)
            if saved_size:
                self.size_var.set(saved_size)
            # Go to detail view
            self.go_to_substep(1)

    def _on_select(self, name: str):
        sp = self.data.species_by_name.get(name)
        if not sp:
            return

        self.character.species = sp
        self._selected_species_name = sp.get("name", "")
        self._requires_sub_choice = False
        self.character.species_sub_choice = None
        self.character.species_origin_feat = None
        self.sub_var.set("")
        self.detail_name.configure(text=sp["name"])
        self.detail_source.configure(text=f"Source: {sp.get('source', 'Unknown')}")
        self.detail_desc.configure(text=sp.get("description", ""))
        self._set_species_portrait(sp.get("name", ""))

        # Size choice
        for w in self.size_frame.winfo_children():
            w.destroy()
        self.size_frame.pack_forget()

        size_data = sp.get("size", {})
        size_options = size_data.get("options", ["Medium"])
        self.character.size_choice = size_options[0]

        self._build_species_stats_card(sp)

        if len(size_options) > 1:
            self.size_frame.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], 0))

            SectionHeader(self.size_frame, text="Size").pack(fill=tk.X, pady=(0, SPACING["xs"]))

            size_card = CardFrame(self.size_frame, pad=SPACING["md"])
            size_card.pack(fill=tk.X)
            for opt in size_options:
                ttk.Radiobutton(
                    size_card.inner,
                    text=opt,
                    variable=self.size_var,
                    value=opt,
                    style=CARD_RADIO_STYLE,
                ).pack(anchor="w", padx=SPACING["sm"])
            self.size_var.set(size_options[0])

        # Sub-choices
        for w in self.sub_frame.winfo_children():
            w.destroy()
        self.sub_frame.pack_forget()

        if sp.get("sub_choices"):
            choices = sp["sub_choices"]
            if choices and isinstance(choices[0], dict):
                self.sub_frame.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], 0))
                self._requires_sub_choice = True

                SectionHeader(self.sub_frame, text="Choose One (Required)").pack(
                    fill=tk.X, pady=(0, SPACING["xs"])
                )

                for choice in choices:
                    cname = choice.get("name", "Unknown")
                    desc = choice.get("description", "")

                    card = CardFrame(self.sub_frame, bg=COLORS["bg_container"],
                                     border_color=COLORS["border_subtle"], pad=SPACING["md"])
                    card.pack(fill=tk.X, pady=SPACING["xs"])

                    ttk.Radiobutton(
                        card.inner,
                        text=cname,
                        variable=self.sub_var,
                        value=cname,
                        style=CONTAINER_RADIO_STYLE,
                    ).pack(anchor="w")

                    if desc:
                        FormattedDescription(
                            card.inner,
                            text=desc,
                            font=FONTS["body_small"],
                            foreground=COLORS["fg_dim"],
                            background=COLORS["bg_container"],
                        ).pack(fill=tk.X, pady=(SPACING["xs"], 0))

        # Trait option choices (e.g. Gnome lineage, Goliath ancestry, Shifter form)
        if not sp.get("sub_choices"):
            trait_choice = self.TRAIT_OPTION_CHOICES.get(sp.get("name", ""))
            if trait_choice:
                available = {t.get("name", "") for t in sp.get("traits", [])}
                option_names = [
                    opt for opt in trait_choice["options"] if opt in available
                ]
                if option_names:
                    self.sub_frame.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], 0))
                    self._requires_sub_choice = True

                    SectionHeader(
                        self.sub_frame, text=f"{trait_choice['label']} (Required)"
                    ).pack(fill=tk.X, pady=(0, SPACING["xs"]))

                    # Find matching trait descriptions
                    trait_descs = {
                        t.get("name", ""): t.get("description", "")
                        for t in sp.get("traits", [])
                    }

                    for opt_name in option_names:
                        card = CardFrame(self.sub_frame, bg=COLORS["bg_container"],
                                         border_color=COLORS["border_subtle"], pad=SPACING["md"])
                        card.pack(fill=tk.X, pady=SPACING["xs"])

                        ttk.Radiobutton(
                            card.inner,
                            text=opt_name,
                            variable=self.sub_var,
                            value=opt_name,
                            style=CONTAINER_RADIO_STYLE,
                        ).pack(anchor="w")

                        opt_desc = trait_descs.get(opt_name, "")
                        if opt_desc:
                            FormattedDescription(
                                card.inner,
                                text=opt_desc,
                                font=FONTS["body_small"],
                                foreground=COLORS["fg_dim"],
                                background=COLORS["bg_container"],
                            ).pack(fill=tk.X, pady=(SPACING["xs"], 0))

        # Traits — exclude any that are shown as radio button sub-choices
        for w in self.traits_frame.winfo_children():
            w.destroy()

        trait_choice = self.TRAIT_OPTION_CHOICES.get(sp.get("name", ""))
        radio_trait_names = set()
        if trait_choice and not sp.get("sub_choices"):
            radio_trait_names = set(trait_choice.get("options", []))

        visible_traits = get_species_trait_cards(
            sp,
            excluded_names=radio_trait_names,
        )
        if visible_traits:
            SectionHeader(self.traits_frame, text="Traits").pack(
                fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"])
            )
            traits_grid = tk.Frame(self.traits_frame, bg=COLORS["bg"])
            traits_grid.pack(fill=tk.X, padx=SPACING["lg"])
            traits_grid.columnconfigure(0, weight=1)
            traits_grid.columnconfigure(1, weight=1)

            for i, trait in enumerate(visible_traits):
                card = CardFrame(
                    traits_grid,
                    bg=COLORS["bg_container"],
                    border_color=COLORS["border_subtle"],
                    pad=SPACING["lg"],
                )
                card.grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky="nsew")

                tk.Label(
                    card.inner,
                    text=trait["name"],
                    font=FONTS["heading_serif_sm"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_container"],
                ).pack(anchor="w")

                if trait.get("description"):
                    FormattedDescription(
                        card.inner,
                        text=trait["description"],
                        font=FONTS["body_small"],
                        foreground=COLORS["fg_dim"],
                        background=COLORS["bg_container"],
                    ).pack(fill=tk.X, pady=(6, 0))

                for subtrait in trait.get("subtraits", []):
                    tk.Label(
                        card.inner,
                        text=subtrait["name"],
                        font=FONTS["label_upper_bold"],
                        fg=COLORS["gold"],
                        bg=COLORS["bg_container"],
                    ).pack(anchor="w", pady=(SPACING["md"], 0))

                    if subtrait.get("description"):
                        FormattedDescription(
                            card.inner,
                            text=subtrait["description"],
                            font=FONTS["body_small"],
                            foreground=COLORS["fg_dim"],
                            background=COLORS["bg_container"],
                        ).pack(fill=tk.X, pady=(SPACING["xs"], 0))

        self.notify_change()

    def is_valid(self) -> bool:
        if self.character.species is None:
            return False
        if (
            self._requires_sub_choice
            and not (self.character.species_sub_choice or "").strip()
        ):
            return False
        return True

    def _on_size_change(self, *args):
        self.character.size_choice = self.size_var.get()
        species = self.character.species
        if species and species.get("name", "") == self._selected_species_name:
            self._build_species_stats_card(species)
        self.notify_change()

    def _on_sub_change(self, *args):
        self.character.species_sub_choice = self.sub_var.get()
        self.notify_change()

    def _set_species_portrait(self, species_name: str):
        """Load the selected species portrait and schedule a redraw."""
        self._species_portrait_path = _species_image_path(species_name)
        self._species_portrait_source = None
        self._species_portrait_photo = None

        if self._species_portrait_path and Image is not None:
            try:
                self._species_portrait_source = Image.open(
                    self._species_portrait_path
                ).convert("RGBA")
            except Exception:
                self._species_portrait_source = None

        self._schedule_species_portrait_render()

    def _on_species_portrait_configure(self, _event=None):
        """Redraw portrait when its container size changes."""
        self._schedule_species_portrait_render()

    def _schedule_species_portrait_render(self):
        """Throttle portrait redraws to the next idle cycle."""
        if self._species_portrait_pending:
            return
        widget = getattr(self, "_portrait_canvas", None)
        if widget is None:
            return
        self._species_portrait_pending = True
        try:
            widget.after_idle(self._render_species_portrait)
        except tk.TclError:
            self._species_portrait_pending = False

    def _render_species_portrait(self):
        """Render the portrait using cover-style cropping when available."""
        self._species_portrait_pending = False

        if not hasattr(self, "_portrait_canvas"):
            return

        canvas = self._portrait_canvas
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 2 or height < 2:
            return

        canvas.delete("all")
        canvas.create_rectangle(
            0,
            0,
            width,
            height,
            fill=COLORS["bg_surface"],
            outline="",
        )

        if self._species_portrait_source is not None and ImageTk is not None:
            image = self._cover_crop_species_portrait(width, height)
            if image is not None:
                self._species_portrait_photo = ImageTk.PhotoImage(image)
                canvas.create_image(
                    width // 2,
                    height // 2,
                    image=self._species_portrait_photo,
                )
                return

        if self._species_portrait_path:
            try:
                self._species_portrait_photo = tk.PhotoImage(
                    file=self._species_portrait_path
                )
                canvas.create_image(
                    width // 2,
                    height // 2,
                    image=self._species_portrait_photo,
                )
                return
            except tk.TclError:
                pass

        canvas.create_text(
            width // 2,
            height // 2,
            text=self._selected_species_name or "Species",
            font=FONTS["heading_serif_sm"],
            fill=COLORS["fg_dim"],
        )

    def _cover_crop_species_portrait(self, width: int, height: int):
        """Resize the portrait to fill the target area with top-biased cropping."""
        source = self._species_portrait_source
        if source is None:
            return None

        src_w, src_h = source.size
        if src_w <= 0 or src_h <= 0:
            return None

        target_ratio = width / float(height)
        source_ratio = src_w / float(src_h)

        if source_ratio > target_ratio:
            crop_w = int(src_h * target_ratio)
            left = max((src_w - crop_w) // 2, 0)
            box = (left, 0, left + crop_w, src_h)
        else:
            crop_h = int(src_w / target_ratio)
            box = (0, 0, src_w, min(crop_h, src_h))

        try:
            cropped = source.crop(box).resize((width, height), Image.LANCZOS)
        except Exception:
            return None

        background = Image.new(
            "RGBA",
            (width, height),
            self._hex_to_rgb(COLORS["bg_surface"]) + (255,),
        )
        return Image.alpha_composite(background, cropped)

    def _hex_to_rgb(self, color: str) -> tuple[int, int, int]:
        """Convert a hex color string into an RGB tuple."""
        value = color.lstrip("#")
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))

    def _build_species_stats_card(self, species: dict):
        """Render the stitched stat strip for the selected species."""
        for w in self.stats_frame.winfo_children():
            w.destroy()

        label_font = FONTS["label_tiny"]
        value_font = (FONTS["archive_title"][0], 18)

        strip = tk.Frame(self.stats_frame, bg=COLORS["bg"])
        strip.pack(fill=tk.X)

        tk.Frame(
            strip,
            bg=COLORS["border_subtle_bg"],
            height=1,
        ).pack(fill=tk.X, padx=SPACING["sm"])

        stat_row = tk.Frame(strip, bg=COLORS["bg"])
        stat_row.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["md"], SPACING["md"]))

        stat_row.columnconfigure(0, weight=1, uniform="species_stats")
        stat_row.columnconfigure(2, weight=1, uniform="species_stats")
        stat_row.columnconfigure(4, weight=1, uniform="species_stats")

        stats = [
            ("Creature Type", species.get("creature_type", "Humanoid"), COLORS["fg"]),
            ("Speed", f"{species.get('speed', 30)} ft", COLORS["fg"]),
            ("Size", self._species_size_value(species), COLORS["fg"]),
        ]

        for index, (label, value, value_color) in enumerate(stats):
            column = index * 2
            stat_cell = tk.Frame(stat_row, bg=COLORS["bg"])
            stat_cell.grid(row=0, column=column, sticky="nsew")

            tk.Label(
                stat_cell,
                text=label.upper(),
                font=label_font,
                fg=COLORS["fg_dim"],
                bg=COLORS["bg"],
            ).pack(anchor="w")

            tk.Label(
                stat_cell,
                text=value,
                font=value_font,
                fg=value_color,
                bg=COLORS["bg"],
            ).pack(anchor="w", pady=(2, 0))

            if index < len(stats) - 1:
                divider = tk.Frame(
                    stat_row,
                    bg=COLORS["border_medium_bg"],
                    width=1,
                    height=52,
                )
                divider.grid(row=0, column=column + 1, padx=SPACING["xl"], sticky="ns")
                divider.grid_propagate(False)

        tk.Frame(
            strip,
            bg=COLORS["border_subtle_bg"],
            height=1,
        ).pack(fill=tk.X, padx=SPACING["sm"])

    def _species_size_value(self, species: dict) -> str:
        """Return the currently displayed size label for the selected species."""
        size_options = (species.get("size", {}) or {}).get("options", ["Medium"])
        if len(size_options) <= 1:
            return size_options[0]

        selected_size = (self.character.size_choice or "").strip()
        if selected_size in size_options:
            return selected_size
        return size_options[0]
