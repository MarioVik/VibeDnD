"""Level-up step: Class choices (maneuvers, invocations, plans, arcane shots)."""

import re
import tkinter as tk
from tkinter import ttk

from gui.lu_base_step import LevelUpStep
from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import (
    CardFrame,
    GradientHeader,
    SectionHeader,
    ModernSectionedListbox,
    ScrollableFrame,
    WrappingLabel,
    FormattedDescription,
    register_mousewheel_target,
)
from models.level_up_logic import (
    CLASS_CHOICES,
    DAMAGE_TYPES,
    get_active_pool,
    get_available_options,
    get_choices_config,
    get_known_choices,
    get_sub_choice_options,
    validate_choices_step,
)


class LuChoicesStep(LevelUpStep):
    tab_title = "Class Choices"

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        hero = GradientHeader(self.frame, min_height=60)
        hero.grid(row=0, column=0, sticky="ew")

        hero_row = tk.Frame(hero.inner, bg=COLORS["bg_hero"])
        hero_row.pack(
            fill=tk.X,
            padx=SPACING["card_pad"],
            pady=(SPACING["xl"], SPACING["xl"]),
        )

        self._title_label = tk.Label(
            hero_row,
            text="Class Choices",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        )
        self._title_label.pack(side=tk.LEFT)

        self._info_label = tk.Label(
            hero_row,
            text="",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        )
        self._info_label.pack(side=tk.RIGHT)

        self._content = tk.Frame(self.frame, bg=COLORS["bg"])
        self._content.grid(row=1, column=0, sticky="nsew")

        self._updating_choices = False
        self._choice_vars: dict[str, dict] = {}
        self._choice_list: ModernSectionedListbox | None = None
        self._choice_options_by_name: dict[str, dict] = {}

    def on_enter(self):
        self._rebuild()

    def _rebuild(self):
        for w in self._content.winfo_children():
            w.destroy()
        self._choice_vars.clear()
        self._choice_options_by_name.clear()

        config = get_choices_config(self.ctx, self.character, self.data)
        if not config:
            return

        # Determine key
        choice_key = self.ctx.class_slug
        for k, v in CLASS_CHOICES.items():
            if v is config:
                choice_key = k
                break

        choice_label = config.get("choice_label", "Choice")
        choice_plural = config.get("choice_plural", "Choices")
        level_str = str(self.ctx.new_class_level)
        new_count = config.get("gains_by_level", {}).get(level_str, 0)
        known = get_known_choices(self.character, choice_key)
        available = get_available_options(config, self.ctx, self.character)

        for opt in config.get("options", []):
            self._choice_options_by_name[opt["name"]] = opt

        active_pool = get_active_pool(config, self.ctx.new_class_level)
        pool_heading = (
            f"{active_pool} {choice_plural}" if active_pool else choice_plural
        )
        pool_subtext = f"{active_pool} {choice_label}" if active_pool else choice_label

        self._title_label.configure(text=f"Select {pool_heading}")
        self._info_label.configure(text=f"Choose {new_count} new {pool_subtext}(s)")

        # Two-column layout
        cols = tk.Frame(self._content, bg=COLORS["bg"])
        cols.pack(fill=tk.BOTH, expand=True, padx=SPACING["lg"], pady=SPACING["sm"])
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)
        cols.rowconfigure(0, weight=1)

        # LEFT: choices list
        left = tk.Frame(cols, bg=COLORS["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["xs"]))

        self._count_label = tk.Label(
            left,
            text=f"0 / {new_count} selected",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
        )
        self._count_label.pack(anchor="w", padx=SPACING["xs"], pady=(0, SPACING["xs"]))

        if config.get("can_swap_on_rest"):
            tk.Label(
                left,
                text="\u21ba These choices can be changed on a Short or Long Rest.",
                font=FONTS["body_small"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg"],
            ).pack(anchor="w", padx=SPACING["xs"], pady=(0, SPACING["xs"]))

        self._choice_list = ModernSectionedListbox(
            left,
            multiselect=True,
            on_hover=self._show_choice_detail,
            on_select=lambda name: self._on_choice_toggle_manual(name, new_count),
        )
        self._choice_list.pack(fill=tk.BOTH, expand=True, pady=(SPACING["xs"], 0))

        # Prepare sections
        cat_names = [opt["name"] for opt in sorted(available, key=lambda o: o["name"])]
        for opt in available:
            self._choice_vars[opt["name"]] = {
                "var": tk.BooleanVar(value=opt["name"] in self.ctx.selected_new_choices),
                "opt": opt,
            }

        self._choice_list.set_sectioned_items([(f"Available {choice_plural}", cat_names)])
        # Initial selection state
        self._updating_choices = True
        self._choice_list.set_selected_items(self.ctx.selected_new_choices)
        self._updating_choices = False

        # Replace section
        self._replace_out_var = tk.StringVar(value=self.ctx.replace_out)
        self._replace_in_var = tk.StringVar(value=self.ctx.replace_in)

        if known and config.get("can_replace"):
            SectionHeader(left, text="Replace one (optional)").pack(
                fill=tk.X,
                pady=(SPACING["sm"], SPACING["xs"]),
            )

            replace_cols = tk.Frame(left, bg=COLORS["bg"])
            replace_cols.pack(fill=tk.X, pady=SPACING["xs"])
            replace_cols.columnconfigure(0, weight=1)
            replace_cols.columnconfigure(1, weight=1)

            # Remove column
            remove_card = CardFrame(replace_cols, pad=SPACING["sm"])
            remove_card.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["xs"]))
            tk.Label(
                remove_card.inner,
                text="Remove",
                font=FONTS["body_bold"],
                fg=COLORS["fg"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w")

            ttk.Radiobutton(
                remove_card.inner,
                text="Don\u2019t replace",
                variable=self._replace_out_var,
                value="",
                style="Card.TRadiobutton",
                command=self._on_replace_change,
            ).pack(anchor="w", pady=1)

            existing_sub_sels: dict[str, str] = {}
            for _cl in self.character.class_levels:
                if _cl.class_slug == choice_key or _cl.subclass_slug == choice_key:
                    existing_sub_sels.update(_cl.choice_sub_selections)

            for name in sorted(known):
                sub = existing_sub_sels.get(name, "")
                if sub and "|" in sub:
                    parts = sub.split("|", 1)
                    display = f"{name} ({parts[0]} \u2014 {parts[1]})"
                elif sub:
                    display = f"{name} ({sub})"
                else:
                    display = name
                ttk.Radiobutton(
                    remove_card.inner,
                    text=display,
                    variable=self._replace_out_var,
                    value=name,
                    style="Card.TRadiobutton",
                    command=self._on_replace_change,
                ).pack(anchor="w", pady=1, padx=(SPACING["sm"], 0))

            # Replace with column
            learn_card = CardFrame(replace_cols, pad=SPACING["sm"])
            learn_card.grid(row=0, column=1, sticky="nsew", padx=(SPACING["xs"], 0))
            tk.Label(
                learn_card.inner,
                text="Replace with",
                font=FONTS["body_bold"],
                fg=COLORS["fg"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w")

            ttk.Radiobutton(
                learn_card.inner,
                text="Nothing",
                variable=self._replace_in_var,
                value="",
                style="Card.TRadiobutton",
                command=self._on_replace_change,
            ).pack(anchor="w", pady=1)

            for opt in sorted(
                get_available_options(config, self.ctx, self.character),
                key=lambda o: o["name"],
            ):
                ttk.Radiobutton(
                    learn_card.inner,
                    text=opt["name"],
                    variable=self._replace_in_var,
                    value=opt["name"],
                    style="Card.TRadiobutton",
                    command=self._on_replace_change,
                ).pack(anchor="w", pady=1, padx=(SPACING["sm"], 0))

        # RIGHT: detail panel
        right = tk.Frame(cols, bg=COLORS["bg"])
        right.grid(row=0, column=1, sticky="nsew", padx=(SPACING["xs"], 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        SectionHeader(right, text="Details").pack(
            fill=tk.X,
            pady=(0, SPACING["sm"]),
        )

        detail_card = CardFrame(right, pad=SPACING["lg"])
        detail_card.pack(fill=tk.BOTH, expand=True)
        detail_card.inner.rowconfigure(0, weight=1)
        detail_card.inner.rowconfigure(1, weight=1)
        detail_card.inner.columnconfigure(0, weight=1)

        self._detail_text = tk.Text(
            detail_card.inner,
            wrap=tk.WORD,
            bg=COLORS["bg_surface"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            state=tk.DISABLED,
            height=10,
        )
        self._detail_text.grid(row=0, column=0, sticky="nsew")

        # ── Sub-choice split view ──────────────────────────────
        # Appears in the bottom half of the detail card when the
        # hovered/selected choice requires a secondary selection
        # (e.g. pick a weapon for "Returning Weapon").
        self._sub_split = tk.Frame(detail_card.inner, bg=COLORS["bg_surface"])
        # Not gridded yet — shown/hidden dynamically
        self._sub_split.columnconfigure(0, weight=1)
        self._sub_split.rowconfigure(1, weight=1)  # Card grid row

        self._sub_choice_for: str | None = None
        self._sub_choice_options: list[str] = []
        self._sub_choice_selected: str = ""
        self._sub_choice_type: str = ""

        # Heading label
        self._sub_heading = tk.Label(
            self._sub_split,
            text="Select item:",
            font=FONTS["body_bold"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
            anchor="w",
        )
        self._sub_heading.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(SPACING["xs"], SPACING["sm"]),
        )

        # Scrollable area for tiles
        self._sub_scroll = ScrollableFrame(self._sub_split, inner_padding=0)
        self._sub_scroll.grid(row=1, column=0, sticky="nsew")
        self._sub_tile_refs = {}

        # Damage type row (for armor_and_damage_type)
        self._dmg_row = tk.Frame(self._sub_split, bg=COLORS["bg_surface"])
        self._dmg_type_var = tk.StringVar(value="")
        self._dmg_type_var.trace_add("write", lambda *_: self._on_sub_choice_changed())
        tk.Label(
            self._dmg_row,
            text="Damage type:",
            font=FONTS["body"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(side=tk.LEFT, padx=(0, SPACING["xs"]))
        self._dmg_type_combo = ttk.Combobox(
            self._dmg_row,
            textvariable=self._dmg_type_var,
            state="readonly",
            values=DAMAGE_TYPES,
            width=18,
        )
        self._dmg_type_combo.pack(side=tk.LEFT)
        # dmg_row gridded only when needed

        self._hide_sub_choice_ui()

        # Update count
        self._update_count(new_count)

    def _update_counts(self):
        # Placeholder for sub-class logic if needed, but LuChoicesStep doesn't use it much
        pass

    def _on_choice_toggle_manual(self, name: str, max_count: int):
        if self._updating_choices:
            return
        self._updating_choices = True
        try:
            curr = list(self.ctx.selected_new_choices)
            if name in curr:
                curr.remove(name)
            else:
                if len(curr) < max_count:
                    curr.append(name)
                else:
                    self._choice_list.deselect_item(name)
                    return
            
            self.ctx.selected_new_choices = curr
            self._update_count(max_count)
            
            opt = self._choice_options_by_name.get(name)
            if opt and opt.get("sub_choice") and name in self.ctx.selected_new_choices:
                self._show_sub_choice_ui(name, opt["sub_choice"])
            else:
                self._hide_sub_choice_ui()

            self.notify_change()
        finally:
            self._updating_choices = False

    def _update_count(self, max_count: int):
        count = len(self.ctx.selected_new_choices)
        self._count_label.configure(text=f"{count} / {max_count} selected")

    def _on_replace_change(self):
        self.ctx.replace_out = self._replace_out_var.get()
        self.ctx.replace_in = self._replace_in_var.get()
        self.notify_change()

    def _show_choice_detail(self, name: str):
        if isinstance(name, dict): # Handle legacy calls if any
            opt = name
            name = opt.get("name", "")
        else:
            opt = self._choice_options_by_name.get(name)
            if not opt:
                return

        self._hide_sub_choice_ui()
        self._detail_text.configure(state=tk.NORMAL)
        self._detail_text.delete("1.0", tk.END)
        lines = [name, ""]
        prereq = opt.get("prerequisite_level")
        if prereq:
            lines.append(f"Requires level {prereq}+")
        prereq_feat = opt.get("prerequisite_feature")
        if prereq_feat:
            lines.append(f"Requires: {prereq_feat}")
        min_lvl = opt.get("min_level")
        if min_lvl:
            lines.append(f"Available at level {min_lvl}+")
        desc = opt.get("description", "")

        # Artificer magic item full description
        config = get_choices_config(self.ctx, self.character, self.data)
        if (
            config
            and config.get("choice_label") == "Magic Item Plan"
            and self.ctx.class_slug == "artificer"
            and self.data
        ):
            item = self.data.items_by_name.get(opt.get("name", ""))
            if item:
                desc = item.get("full_description") or item.get("description") or desc

        attune_match = re.match(
            r"^((?:No )?(?:attunement|Attunement) required|Requires (?:attunement|Attunement)(?:\s+by\s+[^.]+)?|Varies)[.\s]*",
            opt.get("description", ""),
        )
        if attune_match:
            attune_text = attune_match.group(1).strip()
            lines.append(f"Attunement: {attune_text}")
            desc_prefix = attune_match.group(0).strip().lower()
            if desc.strip().lower().startswith(desc_prefix):
                desc = desc[attune_match.end() :].strip()

        if prereq or prereq_feat or min_lvl or attune_match:
            lines.append("")
        lines.append(desc)
        self._detail_text.insert("1.0", "\n".join(lines))
        self._detail_text.configure(state=tk.DISABLED)

        sub_choice = opt.get("sub_choice")
        name = opt.get("name", "")
        is_selected = name in self.ctx.selected_new_choices
        is_replace_in = self.ctx.replace_in == name
        if sub_choice and (is_selected or is_replace_in):
            self._show_sub_choice_ui(name, sub_choice)

    def _hide_sub_choice_ui(self):
        self._sub_split.grid_forget()
        self._dmg_row.grid_forget()
        self._sub_choice_for = None
        self._sub_choice_options = []
        self._sub_choice_selected = ""
        self._sub_choice_type = ""
        self._sub_tile_refs = {}

    def _show_sub_choice_ui(self, choice_name: str, sub_choice: dict):
        self._hide_sub_choice_ui()
        self._sub_choice_for = choice_name
        sc_type = sub_choice.get("type", "")
        self._sub_choice_type = sc_type

        options = get_sub_choice_options(sub_choice, self.data)
        if not options:
            return
        self._sub_choice_options = options

        if sc_type == "weapon":
            label_text = "Select weapon:"
        elif sc_type in ("armor", "armor_and_damage_type"):
            label_text = "Select armor:"
        elif sc_type == "magic_item":
            label_text = "Select magic item:"
        else:
            label_text = "Select item:"
        self._sub_heading.configure(text=label_text)

        # Restore previous selection
        prev = self.ctx.choice_sub_selections.get(choice_name, "")
        if sc_type == "armor_and_damage_type" and "|" in prev:
            armor_part, dmg_part = prev.split("|", 1)
            self._sub_choice_selected = armor_part
            self._dmg_type_var.set(dmg_part)
        else:
            self._sub_choice_selected = prev if prev in options else ""
            self._dmg_type_var.set("")

        # Render Tiles
        self._render_sub_choice_tiles(options)

        # Show the split view
        self._sub_split.grid(
            row=1,
            column=0,
            sticky="nsew",
            pady=(SPACING["sm"], 0),
        )

        # Show damage type row if needed
        if sc_type == "armor_and_damage_type":
            self._dmg_row.grid(
                row=2,
                column=0,
                columnspan=2,
                sticky="ew",
                pady=(SPACING["xs"], 0),
            )

    def _render_sub_choice_tiles(self, options: list[str]):
        """Render the sub-choice options as card tiles."""
        for w in self._sub_scroll.inner.winfo_children():
            w.destroy()
        self._sub_tile_refs = {}
        
        for name in options:
            self._create_sub_tile(name, self._sub_scroll.inner)
        
        self._update_sub_tile_styles()

    def _create_sub_tile(self, name: str, parent):
        """Create a single interactive card tile for a sub-choice option."""
        bg_hex = COLORS["bg_surface"]
        
        tile_border = tk.Frame(parent, bg=COLORS["border_medium"], cursor="hand2")
        tile_border.pack(fill=tk.X, padx=SPACING["xs"], pady=SPACING["xs"])
        
        tile = tk.Frame(tile_border, bg=bg_hex, cursor="hand2")
        tile.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        title_lbl = tk.Label(
            tile,
            text=name,
            font=FONTS["body_bold"],
            fg=COLORS["fg"],
            bg=bg_hex,
            cursor="hand2",
            anchor="w"
        )
        title_lbl.pack(fill=tk.X, padx=SPACING["sm"], pady=(SPACING["sm"], 0))

        # Metadata (Level, Attunement) if it's a magic item
        meta_lbl = None
        desc = ""
        if self.data:
            item = self.data.items_by_name.get(name)
            if item:
                meta_parts = []
                min_lvl = item.get("min_level")
                if min_lvl:
                    meta_parts.append(f"Level {min_lvl}+")
                
                # Check for attunement in description or dedicated field
                desc = item.get("full_description") or item.get("description") or ""
                if "attunement" in desc.lower():
                    if "no attunement" in desc.lower():
                        meta_parts.append("No Attunement")
                    else:
                        meta_parts.append("Attunement Required")
                
                if meta_parts:
                    meta_lbl = tk.Label(
                        tile,
                        text=" \u2022 ".join(meta_parts),
                        font=FONTS["label_upper"],
                        fg=COLORS["gold"],
                        bg=bg_hex,
                        cursor="hand2",
                        anchor="w"
                    )
                    meta_lbl.pack(fill=tk.X, padx=SPACING["sm"], pady=0)
        
        if not desc:
            desc = name

        desc_lbl = FormattedDescription(
            tile,
            text=desc,
            font=FONTS["body_small"],
            foreground=COLORS["fg_dim"],
            background=bg_hex,
            cursor="hand2"
        )
        desc_lbl.pack(fill=tk.X, padx=SPACING["sm"], pady=(SPACING["xs"], SPACING["sm"]))

        self._sub_tile_refs[name] = {
            "border": tile_border,
            "tile": tile,
            "title": title_lbl,
            "meta": meta_lbl,
            "desc": desc_lbl
        }

        # Bind events
        def on_click(_e):
            self._sub_choice_selected = name
            self._update_sub_tile_styles()
            self._on_sub_choice_changed()

        def on_enter(_e):
            if self._sub_choice_selected != name:
                tile_border.configure(bg=COLORS["accent"])
                tile.configure(bg=COLORS["bg_high"])
                title_lbl.configure(bg=COLORS["bg_high"])
                if meta_lbl: meta_lbl.configure(bg=COLORS["bg_high"])
                desc_lbl.configure(background=COLORS["bg_high"])

        def on_leave(_e):
            if self._sub_choice_selected != name:
                self._update_sub_tile_styles() # Restoration is easier this way

        for w in [tile_border, tile, title_lbl, meta_lbl, desc_lbl]:
            if w:
                w.bind("<Button-1>", on_click)
                w.bind("<Enter>", on_enter)
                w.bind("<Leave>", on_leave)

    def _update_sub_tile_styles(self):
        """Update all tile visual states based on selection."""
        for name, widgets in self._sub_tile_refs.items():
            is_sel = (self._sub_choice_selected == name)
            border_c = COLORS["accent"] if is_sel else COLORS["border_medium"]
            bg_c = COLORS["bg_high"] if is_sel else COLORS["bg_surface"]
            fg_title = COLORS["accent_text"] if is_sel else COLORS["fg"]
            
            widgets["border"].configure(bg=border_c)
            widgets["tile"].configure(bg=bg_c)
            widgets["title"].configure(bg=bg_c, fg=fg_title)
            if widgets["meta"]:
                widgets["meta"].configure(bg=bg_c)
            widgets["desc"].configure(background=bg_c)

    def _on_sub_choice_changed(self):
        name = self._sub_choice_for
        if not name:
            return
        opt = self._choice_options_by_name.get(name)
        if not opt or "sub_choice" not in opt:
            return
        val = self._sub_choice_selected
        if self._sub_choice_type == "armor_and_damage_type":
            dmg = self._dmg_type_var.get()
            if val and dmg:
                self.ctx.choice_sub_selections[name] = f"{val}|{dmg}"
            elif val:
                self.ctx.choice_sub_selections[name] = val
            else:
                self.ctx.choice_sub_selections.pop(name, None)
        elif val:
            self.ctx.choice_sub_selections[name] = val
        else:
            self.ctx.choice_sub_selections.pop(name, None)
        self.notify_change()

    def is_valid(self) -> bool:
        ok, _, _ = validate_choices_step(self.ctx, self.character, self.data)
        return ok
