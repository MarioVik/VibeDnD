"""Character viewer with Mythic Modern sidebar + 6-view layout."""

import base64
import io
import re
import tkinter as tk

from tkinter import ttk, filedialog

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover
    Image = None
    ImageTk = None

from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import (
    ScrollableFrame,
    AlertDialog,
    SectionedListbox,
    StatCard,
    SectionHeader,
    Chip,
    HPBar,
    WrappingLabel,
    FormattedDescription,
    CardFrame,
    GradientHeader,
    PillBadge,
    HoverTooltip,
    StepperPair,
    configure_modal_dialog,
)
from gui.sidebar import Sidebar
from gui.species_trait_utils import get_species_trait_cards
from gui.sheet_builder import build_character_sheet, _container_contents
from models.character_store import save_character
from paths import characters_dir
from gui.add_inventory_dialog import AddInventoryDialog, ARMOR_AC_ORDER
from models.inventory_service import (
    format_coins,
    normalize_item_key,
    remove_item,
    base_wealth_cp,
    current_wealth_cp,
    cp_to_coins,
)
from models.enums import ALL_SKILLS
from models.language_utils import all_languages
from models.level1_class_rules import (
    augment_level1_feature_description,
)
from models.spell_grant_utils import (
    format_spellbook_entry_label,
    get_free_spell_summary_entries,
    get_spellbook_sections,
    has_spellbook_entries,
)
from models.standard_actions import (
    WEAPON_DATA,
    build_standard_actions,
    get_selected_armor_counts,
    get_selected_non_weapon_items,
    get_selected_weapon_counts,
)
from gui.rest_dialog import RestDialog, can_short_rest, can_long_rest


# View keys
_DASHBOARD = "dashboard"
_COMBAT = "combat"
_SPELLBOOK = "spellbook"
_INVENTORY = "inventory"
_FEATURES = "features"
_BACKSTORY = "backstory"

_NAV_ITEMS = [
    {"key": _DASHBOARD, "text": "Dashboard", "icon": "\u25a3"},
    {"key": _COMBAT, "text": "Combat", "icon": "\u2694\ufe0e"},
    {"key": _FEATURES, "text": "Features", "icon": "\u2605"},
    {"key": _SPELLBOOK, "text": "Spellbook", "icon": "\u2726"},
    {"key": _INVENTORY, "text": "Inventory", "icon": "\u229e"},
    {"key": _BACKSTORY, "text": "Biography", "icon": "\u270e"},
]


class CharacterViewer(ttk.Frame):
    """Full-screen character sheet with sidebar navigation and six views."""

    def __init__(self, parent, character, save_path, game_data, app):
        super().__init__(parent)
        self.character = character
        self.save_path = save_path
        self.data = game_data
        self.app = app
        self._spell_index = {
            s.get("name", ""): s for s in (self.data.spells if self.data else [])
        }
        self._item_by_norm_name = {
            normalize_item_key(name): item
            for name, item in (
                (self.data.items_by_name or {}).items() if self.data else []
            )
        }
        self._inventory_entries_by_name = {}
        self._selected_inventory_name = ""
        self._hover_tooltips: list[HoverTooltip] = []
        self._spell_entries_by_label: dict[str, dict] = {}

        self._view_dirty = {
            _DASHBOARD: True,
            _COMBAT: True,
            _SPELLBOOK: True,
            _INVENTORY: True,
            _FEATURES: True,
            _BACKSTORY: True,
        }
        self._view_built = {k: False for k in self._view_dirty}
        self._current_view = _DASHBOARD

        self._bio_loading = False
        self._bio_photo = None
        self._bio_photo_display = None

        self._build_ui()

    # ================================================================
    # UI construction
    # ================================================================

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ── Sidebar ──
        nav_items = list(_NAV_ITEMS)
        # Hide spellbook if no spells
        if not self._character_has_spells():
            nav_items = [n for n in nav_items if n["key"] != _SPELLBOOK]

        c = self.character
        short_state = tk.NORMAL if can_short_rest(c) else tk.DISABLED
        long_state = tk.NORMAL if can_long_rest(c) else tk.DISABLED

        bottom_buttons = [
            {
                "text": "Short Rest",
                "command": self._on_short_rest,
                "state": short_state,
                "key": "short_rest",
            },
            {
                "text": "Long Rest",
                "command": self._on_long_rest,
                "state": long_state,
                "key": "long_rest",
            },
        ]
        if c.level < 20:
            bottom_buttons.append(
                {"text": "Level Up", "command": self._on_level_up, "key": "level_up"},
            )
        bottom_buttons.append(
            {
                "text": "Export  \u25be",
                "key": "export_dropdown",
                "submenu": [
                    {"text": "Export PDF", "command": self._export_pdf},
                    {"text": "Export Character", "command": self._export_json},
                ],
            },
        )
        # TODO: Add back "Respec Character" button (command: self._on_edit) when the respec feature is fully working

        self.sidebar = Sidebar(
            self,
            nav_items=nav_items,
            on_navigate=self._on_navigate,
            bottom_buttons=bottom_buttons,
            show_character_info=True,
            on_back=self._on_back,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Set character info in sidebar
        c = self.character
        if c.is_multiclass:
            from collections import Counter

            _counts = Counter(cl.class_slug for cl in c.class_levels)
            _sidebar_summary = f"{c.species_name} " + "/".join(
                f"{s.title()} {n}" for s, n in _counts.items()
            )
        else:
            _parts = []
            if c.species:
                _parts.append(c.species_name)
            if c.character_class:
                _parts.append(c.class_name)
            _sidebar_summary = " ".join(_parts) if _parts else "No selections"
        self.sidebar.set_character_info(
            name=c.name or "Unnamed",
            summary=_sidebar_summary,
            level=f"Level {c.level}",
        )

        # ── Content area ──
        self._content = tk.Frame(self, bg=COLORS["bg"])
        self._content.grid(row=0, column=1, sticky="nsew")

        # Create view frames
        self._views: dict[str, tk.Frame] = {}
        for key in self._view_dirty:
            frame = tk.Frame(self._content, bg=COLORS["bg"])
            self._views[key] = frame

        # Show initial view
        self._show_view(_DASHBOARD)

    def _on_navigate(self, key: str):
        self._show_view(key)

    def destroy(self):
        self._dispose_hover_tooltips()
        super().destroy()

    def _show_view(self, key: str):
        self.sidebar.set_active(key)

        # Hide current
        for name, frame in self._views.items():
            frame.pack_forget()

        self._current_view = key
        view = self._views[key]
        view.pack(fill=tk.BOTH, expand=True)

        # Build or refresh if needed
        if not self._view_built.get(key):
            self._build_view(key)
            self._view_built[key] = True
            self._view_dirty[key] = False
        elif self._view_dirty.get(key):
            self._refresh_view(key)
            self._view_dirty[key] = False

    def _build_view(self, key: str):
        builders = {
            _DASHBOARD: self._build_dashboard,
            _COMBAT: self._build_combat,
            _SPELLBOOK: self._build_spellbook,
            _INVENTORY: self._build_inventory,
            _FEATURES: self._build_features,
            _BACKSTORY: self._build_backstory,
        }
        builder = builders.get(key)
        if builder:
            builder()

    def _refresh_view(self, key: str):
        # Destroy children and rebuild
        frame = self._views[key]
        if key == _DASHBOARD:
            self._dispose_hover_tooltips()
        for w in frame.winfo_children():
            try:
                w.destroy()
            except tk.TclError:
                pass
        self._view_built[key] = False
        self._build_view(key)
        self._view_built[key] = True

    def _register_hover_tooltip(self, tooltip: HoverTooltip):
        self._hover_tooltips.append(tooltip)
        return tooltip

    def _dispose_hover_tooltips(self):
        for tooltip in self._hover_tooltips:
            try:
                tooltip.dispose()
            except Exception:
                pass
        self._hover_tooltips.clear()

    def _character_has_spells(self) -> bool:
        return has_spellbook_entries(self.character, self.data)

    # ================================================================
    # DASHBOARD VIEW
    # ================================================================

    def _build_dashboard(self):
        parent = self._views[_DASHBOARD]
        self._dispose_hover_tooltips()
        scroll = ScrollableFrame(parent)
        scroll.pack(fill=tk.BOTH, expand=True)
        inner = scroll.inner

        c = self.character

        # ── Top wrapper: portrait (left) + hero & HP/AC (right) ──
        self._dash_portrait_photo = None  # prevent GC
        self._dash_portrait_pil = None
        portrait_data = getattr(c, "biography_image_data", "") or ""
        has_portrait = bool(portrait_data) and Image is not None and ImageTk is not None

        if has_portrait:
            top_wrapper = tk.Frame(inner, bg=COLORS["bg"])
            top_wrapper.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))

            # Load and pre-crop image to square
            try:
                raw = base64.b64decode(portrait_data)
                pil_img = Image.open(io.BytesIO(raw))
                w, h = pil_img.size
                side = min(w, h)
                left = (w - side) // 2
                top = (h - side) // 2
                self._dash_portrait_pil = pil_img.crop(
                    (left, top, left + side, top + side)
                )
                # Frame wrapper with accent stripe for portrait
                portrait_card = tk.Frame(
                    top_wrapper,
                    bg="#222222",
                )
                portrait_card.pack(
                    side=tk.LEFT, fill=tk.Y, padx=(0, SPACING["card_gap"])
                )
                # Canvas inside the card; starts 1x1, resizes to match right_col
                portrait_canvas = tk.Canvas(
                    portrait_card,
                    width=1,
                    height=1,
                    bg="#222222",
                    highlightthickness=0,
                    bd=0,
                )
                portrait_canvas.pack(
                    side=tk.LEFT, fill=tk.BOTH, expand=True, padx=9, pady=9
                )
                self._dash_portrait_canvas = portrait_canvas
            except Exception:
                has_portrait = False
                self._dash_portrait_pil = None

        if has_portrait:
            right_col = tk.Frame(top_wrapper, bg=COLORS["bg"])
            right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            def _fit_portrait():
                """Resize portrait to match the right column's rendered height."""
                right_col.update_idletasks()
                h = right_col.winfo_reqheight()
                if h < 30:
                    return
                # Subtract card padding (9px top + 9px bottom)
                img_sz = max(h - 18, 32)
                resized = self._dash_portrait_pil.resize(
                    (img_sz, img_sz), Image.LANCZOS
                )
                self._dash_portrait_photo = ImageTk.PhotoImage(resized)
                self._dash_portrait_canvas.configure(width=img_sz, height=img_sz)
                self._dash_portrait_canvas.delete("all")
                self._dash_portrait_canvas.create_image(
                    img_sz // 2, img_sz // 2, image=self._dash_portrait_photo
                )

            # Delay until layout is fully settled
            right_col.after(100, _fit_portrait)
        else:
            right_col = inner

        # ── Hero section (gradient) ──
        hero = GradientHeader(right_col, min_height=100)
        hero.pack(
            fill=tk.X,
            pady=(0, SPACING["card_gap"] if has_portrait else SPACING["section_gap"]),
        )
        hero_inner = hero.inner

        _hero_bg = COLORS["bg_hero"]

        # Name and level badge row
        name_frame = tk.Frame(hero_inner, bg=_hero_bg)
        name_frame.pack(fill=tk.X, padx=SPACING["card_pad"], pady=(SPACING["2xl"], 0))

        tk.Label(
            name_frame,
            text=c.name or "Unnamed",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=_hero_bg,
        ).pack(side=tk.LEFT)

        level_pill = PillBadge(
            name_frame,
            text=f"LEVEL {c.level}",
            bg_color=COLORS["badge_glass"],
            fg_color=COLORS["gold"],
        )
        level_pill.pack(side=tk.RIGHT, padx=8)

        summary_frame = tk.Frame(hero_inner, bg=_hero_bg)
        summary_frame.pack(
            fill=tk.X, padx=SPACING["card_pad"], pady=(4, SPACING["2xl"])
        )

        if c.is_multiclass:
            from collections import Counter

            counts = Counter(cl.class_slug for cl in c.class_levels)
            _class_line = f"{c.species_name} " + "/".join(
                f"{slug.title()} {n}" for slug, n in counts.items()
            )
        else:
            _identity_parts = []
            if c.species:
                _identity_parts.append(c.species_name)
            if c.character_class:
                _identity_parts.append(c.class_name)
            _subclass_slug = c.current_subclass
            if _subclass_slug and self.data:
                _sc = self.data.get_subclass(
                    c.character_class.get("slug", ""), _subclass_slug
                )
                if _sc:
                    _identity_parts.append(_sc["name"])
            _class_line = (
                " ".join(_identity_parts) if _identity_parts else "No selections"
            )
        if c.background_name:
            _class_line += f" - {c.background_name}"

        tk.Label(
            summary_frame,
            text=_class_line,
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=_hero_bg,
        ).pack(anchor="w")

        # ── Proficiency, Hit Dice, Saving Throws (in right_col, next to portrait) ──
        saving_throws_early = (c.character_class or {}).get("saving_throws", [])
        saving_throws_lower_early = [s.lower() for s in saving_throws_early]

        sub_hero_row = tk.Frame(right_col, bg=COLORS["bg"])
        sub_hero_row.pack(fill=tk.X)
        sub_hero_row.columnconfigure(0, weight=0)
        sub_hero_row.columnconfigure(1, weight=0)
        sub_hero_row.columnconfigure(2, weight=1)

        # Build hit dice pool data
        _hd_pool = c.hit_dice_pool
        # Sort by die size descending
        _hd_sorted = (
            sorted(_hd_pool, key=lambda s: _hd_pool[s][2], reverse=True)
            if _hd_pool
            else []
        )
        _hd_is_multi = len(_hd_sorted) > 1

        # Proficiency box — square (width = height)
        prof_frame = tk.Frame(sub_hero_row, bg=COLORS["bg_surface"])
        prof_frame.grid(row=0, column=0, padx=(0, 3), sticky="ns")
        prof_frame.pack_propagate(False)
        prof_frame.grid_propagate(False)

        def _keep_prof_square(event, f=prof_frame):
            if event.height > 1:
                f.configure(width=event.height)

        prof_frame.bind("<Configure>", _keep_prof_square)

        tk.Label(
            prof_frame,
            text="PROFICIENCY",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(side=tk.TOP, pady=(6, 0))
        _prof_center = tk.Frame(prof_frame, bg=COLORS["bg_surface"])
        _prof_center.pack(expand=True)
        tk.Label(
            _prof_center,
            text=f"+{c.proficiency_bonus}",
            font=FONTS["stat_large"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack()
        # Invisible spacer to match the die badge height in the Hit Dice box
        tk.Frame(_prof_center, bg=COLORS["bg_surface"], height=24).pack()

        # Hit Dice box — stacked: remaining/total on top, die type below (like ability scores)
        hd_frame = tk.Frame(sub_hero_row, bg=COLORS["bg_surface"])
        hd_frame.grid(row=0, column=1, padx=(3, 3), sticky="ns")
        hd_frame.pack_propagate(False)
        hd_frame.grid_propagate(False)

        _hd_width_mult = 1.6 if _hd_is_multi else 1.0

        def _keep_hd_sized(event, f=hd_frame, m=_hd_width_mult):
            if event.height > 1:
                f.configure(width=int(event.height * m))

        hd_frame.bind("<Configure>", _keep_hd_sized)

        tk.Label(
            hd_frame,
            text="HIT DICE",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(side=tk.TOP, pady=(6, 0))

        if _hd_sorted:
            _hd_bg = COLORS["bg_surface"]
            _hd_center = tk.Frame(hd_frame, bg=_hd_bg)
            _hd_center.pack(expand=True)

            if _hd_is_multi:
                # Multiclass: side-by-side columns, each with value + die label
                _hd_center.columnconfigure(list(range(len(_hd_sorted))), weight=1)
                for col_i, _slug in enumerate(_hd_sorted):
                    _rem, _tot, _die = _hd_pool[_slug]
                    _col_f = tk.Frame(_hd_center, bg=_hd_bg)
                    _col_f.grid(row=0, column=col_i, padx=4)
                    tk.Label(
                        _col_f,
                        text=f"{_rem}/{_tot}",
                        font=FONTS["stat_large"],
                        fg=COLORS["fg"],
                        bg=_hd_bg,
                    ).pack()
                    _badge_bg = COLORS["bg_container"]
                    _badge = tk.Frame(_col_f, bg=_badge_bg, padx=6, pady=1)
                    _badge.pack(pady=(2, 0))
                    tk.Label(
                        _badge,
                        text=f"d{_die}",
                        font=FONTS["body_bold"],
                        fg=COLORS["fg_dim"],
                        bg=_badge_bg,
                    ).pack()
            else:
                # Single class: value on top, die badge below
                _slug = _hd_sorted[0]
                _rem, _tot, _die = _hd_pool[_slug]
                tk.Label(
                    _hd_center,
                    text=f"{_rem}/{_tot}",
                    font=FONTS["stat_large"],
                    fg=COLORS["fg"],
                    bg=_hd_bg,
                ).pack()
                _badge_bg = COLORS["bg_container"]
                _badge = tk.Frame(_hd_center, bg=_badge_bg, padx=8, pady=2)
                _badge.pack(pady=(2, 0))
                tk.Label(
                    _badge,
                    text=f"d{_die}",
                    font=FONTS["body_bold"],
                    fg=COLORS["fg_dim"],
                    bg=_badge_bg,
                ).pack()
        else:
            # Fallback for no class levels
            _die = (c.character_class or {}).get("hit_die", 8)
            tk.Label(
                hd_frame,
                text=f"{c.level}/{c.level}",
                font=FONTS["stat_large"],
                fg=COLORS["fg"],
                bg=COLORS["bg_surface"],
            ).pack(expand=True)

        # Saving Throws box
        saves_cf = CardFrame(sub_hero_row, pad=SPACING["sm"])
        saves_cf.grid(row=0, column=2, padx=(3, 0), sticky="nsew")

        tk.Label(
            saves_cf.inner,
            text="SAVING THROWS",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w")

        saves_grid = tk.Frame(saves_cf.inner, bg=COLORS["bg_surface"])
        saves_grid.pack(fill=tk.X, pady=(4, 0))
        saves_grid.columnconfigure(0, weight=1)
        saves_grid.columnconfigure(1, weight=1)

        _save_order = [
            "Strength",
            "Intelligence",
            "Dexterity",
            "Wisdom",
            "Constitution",
            "Charisma",
        ]
        for i, ability_name in enumerate(_save_order):
            col = i % 2
            row = i // 2
            is_prof = ability_name.lower() in saving_throws_lower_early
            save_mod = c.ability_scores.modifier(ability_name)
            if is_prof:
                save_mod += c.proficiency_bonus
            save_str = f"+{save_mod}" if save_mod >= 0 else str(save_mod)
            indicator = "●" if is_prof else "○"
            color = COLORS["accent_text"] if is_prof else COLORS["fg_dim"]

            save_row_f = tk.Frame(saves_grid, bg=COLORS["bg_surface"])
            save_row_f.grid(row=row, column=col, sticky="ew", padx=(0, 12), pady=2)

            tk.Label(
                save_row_f,
                text=indicator,
                font=FONTS["body"],
                fg=color,
                bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT, padx=(0, 4))
            tk.Label(
                save_row_f,
                text=ability_name[:3].upper(),
                font=FONTS["body"],
                fg=COLORS["fg"] if is_prof else COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT)
            tk.Label(
                save_row_f,
                text=save_str,
                font=FONTS["heading_serif_sm"],
                fg=color,
                bg=COLORS["bg_surface"],
            ).pack(side=tk.RIGHT)

        # ── Ability Scores ──
        SectionHeader(inner, text="Ability Scores").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        ab_row = tk.Frame(inner, bg=COLORS["bg"])
        ab_row.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        ab_row.columnconfigure(list(range(6)), weight=1)

        for i, ability_name in enumerate(
            [
                "Strength",
                "Dexterity",
                "Constitution",
                "Intelligence",
                "Wisdom",
                "Charisma",
            ]
        ):
            total = c.ability_scores.total(ability_name)
            mod_str = c.ability_scores.modifier_str(ability_name)

            card = StatCard(
                ab_row,
                label=ability_name,
                value=mod_str,
                modifier=str(total),
            )
            card.grid(row=0, column=i, padx=3, sticky="nsew")

        # ── Skills ──
        SectionHeader(
            inner,
            text="Skills",
            right_text="● = proficiency   ◉ = expertise   ★ = advantage",
        ).pack(fill=tk.X, pady=(0, SPACING["sm"]))

        skills_card = CardFrame(inner, pad=SPACING["lg"])
        skills_card.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        skills_frame = skills_card.inner
        skills_frame.columnconfigure(0, weight=1)
        skills_frame.columnconfigure(1, weight=1)

        all_profs = c.all_skill_proficiencies
        all_expertise = getattr(c, "all_skill_expertise", set())
        all_advantages = c.all_skill_advantages

        half = (len(ALL_SKILLS) + 1) // 2
        for idx, skill_enum in enumerate(ALL_SKILLS):
            skill_display = skill_enum.display_name
            ability = skill_enum.ability
            col = 0 if idx < half else 1
            row_idx = idx if col == 0 else idx - half

            skill_row = tk.Frame(skills_frame, bg=COLORS["bg_surface"])
            skill_row.grid(row=row_idx, column=col, sticky="ew", padx=4, pady=3)

            # Hover effect on skill rows
            def _hover_in(e, w=skill_row):
                w.configure(bg=COLORS["bg_container"])
                for ch in w.winfo_children():
                    try:
                        ch.configure(bg=COLORS["bg_container"])
                    except tk.TclError:
                        pass

            def _hover_out(e, w=skill_row):
                w.configure(bg=COLORS["bg_surface"])
                for ch in w.winfo_children():
                    try:
                        ch.configure(bg=COLORS["bg_surface"])
                    except tk.TclError:
                        pass

            skill_row.bind("<Enter>", _hover_in)
            skill_row.bind("<Leave>", _hover_out)

            is_prof = skill_display in all_profs
            is_expert = skill_display in all_expertise
            has_advantage = skill_display in all_advantages

            # Proficiency indicator
            indicator = "\u25cf" if is_prof else "\u25cb"
            if is_expert:
                indicator = "\u25c9"
            fg_color = COLORS["accent_text"] if is_prof else COLORS["fg_dim"]

            indicator_label = tk.Label(
                skill_row,
                text=indicator,
                font=FONTS["body_small"],
                fg=fg_color,
                bg=COLORS["bg_surface"],
            )
            indicator_label.pack(side=tk.LEFT, padx=(0, 0 if has_advantage else 4))

            # Advantage star indicator
            if has_advantage:
                adv_label = tk.Label(
                    skill_row,
                    text="\u2605",
                    font=FONTS["body_small"],
                    fg=COLORS["gold"],
                    bg=COLORS["bg_surface"],
                )
                adv_label.pack(side=tk.LEFT, padx=(0, 4))
            else:
                adv_label = None

            name_label = tk.Label(
                skill_row,
                text=skill_display.upper(),
                font=FONTS["label_upper_bold"] if is_prof else FONTS["label_upper"],
                fg=fg_color,
                bg=COLORS["bg_surface"],
            )
            name_label.pack(side=tk.LEFT)

            ability_label = tk.Label(
                skill_row,
                text=f"({ability.value[:3].upper()})",
                font=FONTS["label_tiny"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            )
            ability_label.pack(side=tk.LEFT, padx=(4, 0))

            mod_val = c.skill_modifier(skill_display)
            mod_text = f"+{mod_val}" if mod_val >= 0 else str(mod_val)
            value_label = tk.Label(
                skill_row,
                text=mod_text,
                font=FONTS["heading_serif_sm"],
                fg=fg_color,
                bg=COLORS["bg_surface"],
            )
            value_label.pack(side=tk.RIGHT)

            tooltip_widgets = [
                skill_row,
                indicator_label,
                name_label,
                ability_label,
                value_label,
            ]
            if adv_label is not None:
                tooltip_widgets.insert(2, adv_label)

            skill_row._tooltip = self._register_hover_tooltip(
                HoverTooltip(
                    tooltip_widgets,
                    lambda s=skill_display, char=c: char.skill_modifier_breakdown_text(
                        s
                    ),
                )
            )

        # ── Senses & Proficiencies (side-by-side) ──
        senses_prof_row = tk.Frame(inner, bg=COLORS["bg"])
        senses_prof_row.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        senses_prof_row.columnconfigure(0, weight=1, uniform="sp")
        senses_prof_row.columnconfigure(1, weight=1, uniform="sp")

        # Left column — Senses
        senses_col = tk.Frame(senses_prof_row, bg=COLORS["bg"])
        senses_col.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["sm"] // 2))

        SectionHeader(senses_col, text="Senses").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        senses_card = CardFrame(senses_col, pad=SPACING["lg"])
        senses_card.pack(fill=tk.BOTH, expand=True)
        senses_frame = senses_card.inner

        senses = [
            ("Passive Perception", 10 + c.skill_modifier("Perception")),
            ("Passive Insight", 10 + c.skill_modifier("Insight")),
            ("Passive Investigation", 10 + c.skill_modifier("Investigation")),
        ]

        for label, value in senses:
            row = tk.Frame(senses_frame, bg=COLORS["bg_surface"])
            row.pack(fill=tk.X, pady=2)
            tk.Label(
                row,
                text=label.upper(),
                font=FONTS["label_upper"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT)
            tk.Label(
                row,
                text=str(value),
                font=FONTS["heading_serif_sm"],
                fg=COLORS["gold"] if label == "Passive Perception" else COLORS["fg"],
                bg=COLORS["bg_surface"],
            ).pack(side=tk.RIGHT)

        # Right column — Proficiencies
        prof_col = tk.Frame(senses_prof_row, bg=COLORS["bg"])
        prof_col.grid(row=0, column=1, sticky="nsew", padx=(SPACING["sm"] // 2, 0))

        SectionHeader(prof_col, text="Proficiencies").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        prof_card = CardFrame(prof_col, pad=SPACING["lg"])
        prof_card.pack(fill=tk.BOTH, expand=True)
        prof_frame = prof_card.inner

        weapon_profs = list(getattr(c, "effective_weapon_proficiencies", []))
        armor_profs = list(getattr(c, "effective_armor_proficiencies", []))

        if weapon_profs or armor_profs:
            chip_frame = tk.Frame(prof_frame, bg=COLORS["bg_surface"])
            chip_frame.pack(fill=tk.X, anchor="w")

            for p in weapon_profs + armor_profs:
                Chip(chip_frame, text=p, style="gold").pack(
                    side=tk.LEFT, padx=(0, 4), pady=2
                )

        # Languages
        lang_list = all_languages(c)
        if lang_list:
            lang_header = tk.Frame(prof_frame, bg=COLORS["bg_surface"])
            lang_header.pack(fill=tk.X, anchor="w", pady=(8, 2))
            tk.Label(
                lang_header,
                text="LANGUAGES",
                font=FONTS["label_upper"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w")
            lang_frame = tk.Frame(prof_frame, bg=COLORS["bg_surface"])
            lang_frame.pack(fill=tk.X, anchor="w")
            for lang in lang_list:
                Chip(lang_frame, text=lang, style="default").pack(
                    side=tk.LEFT, padx=(0, 4), pady=2
                )

    # ================================================================
    # COMBAT VIEW
    # ================================================================

    def _build_combat(self):
        parent = self._views[_COMBAT]
        scroll = ScrollableFrame(parent)
        scroll.pack(fill=tk.BOTH, expand=True)
        inner = scroll.inner
        c = self.character

        # ── Header (gradient) ──
        combat_hero = GradientHeader(inner, min_height=80)
        combat_hero.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))

        tk.Label(
            combat_hero.inner,
            text="Combat",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(
            anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xl"], SPACING["xl"])
        )

        # ── Two-column layout: Vital Stats (left 20%) | Attacks (right 80%) ──
        combat_columns = tk.Frame(inner, bg=COLORS["bg"], height=200)
        combat_columns.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))

        gap = SPACING["card_gap"]
        right_col = tk.Frame(combat_columns, bg=COLORS["bg"])
        right_col.place(relx=0, relwidth=0.35, rely=0, relheight=1.0, width=-gap // 2)

        left_col = tk.Frame(combat_columns, bg=COLORS["bg"])
        left_col.place(
            relx=0.35, relwidth=0.65, rely=0, relheight=1.0, x=gap // 2, width=-gap // 2
        )

        # Propagate height from children
        def _update_combat_height(event=None):
            combat_columns.update_idletasks()
            h = max(left_col.winfo_reqheight(), right_col.winfo_reqheight())
            if h > 1:
                combat_columns.configure(height=h)

        left_col.bind("<Configure>", _update_combat_height)
        right_col.bind("<Configure>", _update_combat_height)

        # ── Left: Attacks ──
        SectionHeader(left_col, text="Attacks").pack(fill=tk.X, pady=(0, SPACING["sm"]))

        attacks_card = CardFrame(left_col, accent_left=True, pad=SPACING["md"])
        attacks_card.pack(fill=tk.BOTH, expand=True)
        attacks_frame = attacks_card.inner

        # Cogwheel button — placed on the CardFrame so it survives grid rebuilds
        gear_btn = tk.Label(
            attacks_card,
            text="\u2699",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
            cursor="hand2",
        )
        # Initially hidden; shown after first render when useful
        gear_visible = False

        def _action_sort_key(action: dict) -> int:
            """Return sort position based on saved attack_order."""
            order = c.attack_order or []
            key = action.get("weapon_key") or action.get("name", "")
            try:
                return order.index(key)
            except ValueError:
                return len(order)

        def _render_attacks():
            nonlocal gear_visible
            for w in attacks_frame.winfo_children():
                w.destroy()

            actions = build_standard_actions(
                c,
                spells_by_name=self._spell_index,
                game_data=self.data,
                weapon_options=dict(c.standard_action_options or {}),
                equipped_weapon_keys=set(c.equipped_weapons or []),
            )

            # Sort by saved order
            actions.sort(key=_action_sort_key)

            # Show cogwheel when there are configurable weapons or 2+ attacks to reorder
            has_configurable = any(
                a.get("kind") == "weapon"
                and (a.get("can_true_strike") or a.get("versatile"))
                for a in actions
            )
            should_show = has_configurable or len(actions) >= 2
            if should_show and not gear_visible:
                gear_btn.place(relx=1.0, rely=0, anchor="ne", x=-4, y=4)
                gear_visible = True
            elif not should_show and gear_visible:
                gear_btn.place_forget()
                gear_visible = False

            if not actions:
                tk.Label(
                    attacks_frame,
                    text="No attacks available.",
                    font=FONTS["body"],
                    fg=COLORS["fg_dim"],
                    bg=COLORS["bg_surface"],
                ).pack(pady=8)
                return

            # Use grid layout so columns align vertically
            attacks_frame.columnconfigure(0, weight=1)
            attacks_frame.columnconfigure(1, weight=0)
            attacks_frame.columnconfigure(2, weight=0)
            attacks_frame.columnconfigure(3, weight=0)

            # Column headers
            tk.Label(
                attacks_frame,
                text="NAME",
                font=FONTS["label_tiny"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).grid(row=0, column=0, sticky="w", padx=12, pady=(4, 0))
            tk.Label(
                attacks_frame,
                text="RANGE",
                font=FONTS["label_tiny"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).grid(row=0, column=1, padx=(16, 0), pady=(4, 0))
            tk.Label(
                attacks_frame,
                text="ATK BONUS",
                font=FONTS["label_tiny"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).grid(row=0, column=2, padx=(16, 0), pady=(4, 0))
            tk.Label(
                attacks_frame,
                text="DAMAGE",
                font=FONTS["label_tiny"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).grid(row=0, column=3, padx=(16, 0), pady=(4, 0))

            for i in range(len(actions)):
                attacks_frame.rowconfigure(i + 1, weight=1)

            for i, action in enumerate(actions):
                grid_row = i + 1

                name_col = tk.Frame(attacks_frame, bg=COLORS["bg_surface"])
                name_col.grid(row=grid_row, column=0, sticky="w", padx=12, pady=6)

                display_name = action.get("name", "Unknown")
                if action.get("true_strike_active"):
                    display_name = f"{display_name} (True Strike)"

                tk.Label(
                    name_col,
                    text=display_name,
                    font=FONTS["heading_serif_sm"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_surface"],
                ).pack(anchor="w")

                props = action.get("properties", "")
                if props:
                    tk.Label(
                        name_col,
                        text=props.upper(),
                        font=FONTS["label_tiny"],
                        fg=COLORS["fg_dim"],
                        bg=COLORS["bg_surface"],
                    ).pack(anchor="w")

                range_str = action.get("range", "")
                if not range_str and action.get("kind") == "cantrip":
                    range_str = action.get("notes", "")

                tk.Label(
                    attacks_frame,
                    text=range_str,
                    font=FONTS["heading_serif_sm"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_surface"],
                ).grid(row=grid_row, column=1, padx=(16, 0), pady=6)

                hit_str = action.get("attack", "+0")
                tk.Label(
                    attacks_frame,
                    text=hit_str,
                    font=FONTS["heading_serif_sm"],
                    fg=COLORS["accent_text"],
                    bg=COLORS["bg_surface"],
                ).grid(row=grid_row, column=2, padx=(16, 0), pady=6)

                damage = action.get("damage", "")
                tk.Label(
                    attacks_frame,
                    text=damage,
                    font=FONTS["heading_serif_sm"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_surface"],
                ).grid(row=grid_row, column=3, padx=(16, 0), pady=6)

        def _open_weapon_options(event=None):
            """Open a dialog to configure attack order and weapon modifiers."""
            actions = build_standard_actions(
                c,
                spells_by_name=self._spell_index,
                game_data=self.data,
                weapon_options=dict(c.standard_action_options or {}),
                equipped_weapon_keys=set(c.equipped_weapons or []),
            )
            if not actions:
                return

            actions.sort(key=_action_sort_key)

            dialog = tk.Toplevel(attacks_card)
            dialog.title("Attack Options")
            dialog.configure(bg=COLORS["bg"])
            dialog.resizable(False, False)

            saved_opts = dict(c.standard_action_options or {})
            check_vars: list[tuple[str, str, tk.BooleanVar]] = []

            # Header
            header = ttk.Frame(dialog)
            header.pack(fill=tk.X, padx=16, pady=(12, 4))

            ttk.Label(
                header,
                text="Attack Options",
                font=FONTS["heading"],
                foreground=COLORS["accent"],
            ).pack(anchor="w")

            ttk.Label(
                header,
                text="Reorder attacks and configure weapon modifiers.",
                foreground=COLORS["fg_dim"],
            ).pack(anchor="w")

            # Content — list of draggable rows
            content = ttk.Frame(dialog)
            content.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 4))

            # Each row: (frame_widget, action_key)
            row_widgets: list[tuple[tk.Frame, str]] = []

            def _action_key(a: dict) -> str:
                return a.get("weapon_key") or a.get("name", "")

            def _rebuild_rows():
                """Re-pack rows in current order."""
                for rw, _ in row_widgets:
                    rw.pack_forget()
                for rw, _ in row_widgets:
                    rw.pack(fill=tk.X, pady=2)

            def _move_row(row_frame, direction: int):
                """Move a row up (-1) or down (+1)."""
                idx = next(
                    (i for i, (rw, _) in enumerate(row_widgets) if rw is row_frame),
                    -1,
                )
                if idx < 0:
                    return
                new = idx + direction
                if new < 0 or new >= len(row_widgets):
                    return
                row_widgets.insert(new, row_widgets.pop(idx))
                _rebuild_rows()

            for i, a in enumerate(actions):
                akey = _action_key(a)
                weapon_key = a.get("weapon_key", "")
                weapon_saved = saved_opts.get(weapon_key, {})
                is_configurable = a.get("kind") == "weapon" and (
                    a.get("can_true_strike") or a.get("versatile")
                )

                row = tk.Frame(content, bg=COLORS["bg_surface"], padx=8, pady=6)
                row.pack(fill=tk.X, pady=2)

                # Up / Down arrows
                arrows = tk.Frame(row, bg=COLORS["bg_surface"])
                arrows.pack(side=tk.LEFT, padx=(0, 8))

                def _make_arrow(parent, text, rf, direction):
                    lbl = tk.Label(
                        parent,
                        text=text,
                        font=FONTS["body"],
                        fg=COLORS["fg_dim"],
                        bg=COLORS["bg_surface"],
                        cursor="hand2",
                    )
                    lbl.pack()
                    lbl.bind("<Button-1>", lambda e: _move_row(rf, direction))
                    return lbl

                _make_arrow(arrows, "\u25b2", row, -1)
                _make_arrow(arrows, "\u25bc", row, 1)

                # Name and kind
                info_col = tk.Frame(row, bg=COLORS["bg_surface"])
                info_col.pack(side=tk.LEFT, fill=tk.X, expand=True)

                display_name = a.get("name", "Unknown")
                kind_label = "Cantrip" if a.get("kind") == "cantrip" else "Weapon"

                tk.Label(
                    info_col,
                    text=display_name,
                    font=FONTS["body_bold"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_surface"],
                ).pack(anchor="w")

                tk.Label(
                    info_col,
                    text=kind_label,
                    fg=COLORS["fg_dim"],
                    bg=COLORS["bg_surface"],
                    font=FONTS["label_tiny"],
                ).pack(anchor="w")

                # Weapon option checkboxes (inline, right side)
                if is_configurable:
                    opts_frame = tk.Frame(row, bg=COLORS["bg_surface"])
                    opts_frame.pack(side=tk.RIGHT, padx=(8, 0))

                    _cb_kw = dict(
                        font=FONTS["body"],
                        fg=COLORS["fg"],
                        bg=COLORS["bg_surface"],
                        activebackground=COLORS["bg_surface"],
                        activeforeground=COLORS["fg"],
                        selectcolor=COLORS["bg_surface"],
                        highlightthickness=0,
                        bd=0,
                    )

                    if a.get("can_true_strike"):
                        var = tk.BooleanVar(
                            value=bool(weapon_saved.get("true_strike", False))
                        )
                        check_vars.append((weapon_key, "true_strike", var))
                        tk.Checkbutton(
                            opts_frame,
                            text="True Strike",
                            variable=var,
                            **_cb_kw,
                        ).pack(side=tk.LEFT, padx=(0, 8))

                    if a.get("versatile"):
                        var = tk.BooleanVar(
                            value=bool(weapon_saved.get("two_handed", False))
                        )
                        check_vars.append((weapon_key, "two_handed", var))
                        tk.Checkbutton(
                            opts_frame,
                            text="Two-Handed",
                            variable=var,
                            **_cb_kw,
                        ).pack(side=tk.LEFT)

                row_widgets.append((row, akey))

            # Footer
            def _apply_and_close():
                # Save attack order
                new_order = [akey for _, akey in row_widgets]
                c.attack_order = new_order

                # Save weapon options
                new_opts: dict[str, dict[str, bool]] = {}
                for wkey, opt_name, var in check_vars:
                    new_opts.setdefault(wkey, {})[opt_name] = var.get()
                c.standard_action_options = new_opts

                save_character(c, characters_dir(), existing_filename=self.save_path)
                dialog.destroy()
                _render_attacks()

            footer = ttk.Frame(dialog)
            footer.pack(fill=tk.X, padx=16, pady=(8, 12))

            ttk.Button(
                footer,
                text="Done",
                style="Accent.TButton",
                command=_apply_and_close,
            ).pack(side=tk.RIGHT)

            ttk.Button(
                footer,
                text="Cancel",
                command=dialog.destroy,
            ).pack(side=tk.LEFT)

            dialog.protocol("WM_DELETE_WINDOW", _apply_and_close)
            dialog.bind("<Escape>", lambda e: dialog.destroy())

            # Center over parent and make modal
            configure_modal_dialog(dialog, attacks_card)
            dialog.update_idletasks()
            w = dialog.winfo_reqwidth()
            h = dialog.winfo_reqheight()
            parent_top = attacks_card.winfo_toplevel()
            px = parent_top.winfo_rootx()
            py = parent_top.winfo_rooty()
            pw = parent_top.winfo_width()
            ph = parent_top.winfo_height()
            dialog.geometry(f"{w}x{h}+{px + (pw - w) // 2}+{py + (ph - h) // 2}")

        gear_btn.bind("<Button-1>", _open_weapon_options)

        _render_attacks()

        # ── Right: Vital Stats ──
        SectionHeader(right_col, text="Vital Stats").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        # ── HP row: Regular HP (left) | Temp HP (right, pinned to Speed width) ──
        hp_row = tk.Frame(right_col, bg=COLORS["bg"])
        hp_row.pack(fill=tk.X, pady=(0, SPACING["card_gap"]))

        # Temp HP on the right with a fixed pixel width (updated after layout)
        temp_cf = CardFrame(hp_row, pad=SPACING["md"])
        temp_cf.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Label(
            temp_cf.inner,
            text="TEMP HP",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w")

        temp_val = tk.Frame(temp_cf.inner, bg=COLORS["bg_surface"])
        temp_val.pack(fill=tk.X, pady=(4, 0))

        temp_label = tk.Label(
            temp_val,
            text=str(c.temp_hit_points),
            font=FONTS["stat_large"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
            anchor="w",
        )
        temp_label.pack(side=tk.LEFT)

        def _adjust_temp_hp(delta: int):
            new_val = max(0, c.temp_hit_points + delta)
            c.temp_hit_points = new_val
            temp_label.config(text=str(new_val))
            save_character(c, characters_dir(), existing_filename=self.save_path)

        StepperPair(
            temp_val,
            on_increment=lambda: _adjust_temp_hp(1),
            on_decrement=lambda: _adjust_temp_hp(-1),
        ).pack(side=tk.RIGHT, padx=(4, 0))

        # Regular HP fills the remaining space to the left
        hp_cf = CardFrame(hp_row, accent_left=True, pad=SPACING["md"])
        hp_cf.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, SPACING["card_gap"])
        )

        tk.Label(
            hp_cf.inner,
            text="HIT POINTS",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w")

        current_hp = c.effective_current_hp
        max_hp = c.hit_points

        hp_val = tk.Frame(hp_cf.inner, bg=COLORS["bg_surface"])
        hp_val.pack(fill=tk.X, pady=(4, 0))

        hp_label = tk.Label(
            hp_val,
            text=str(current_hp),
            font=FONTS["stat_large"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        )
        hp_label.pack(side=tk.LEFT)
        tk.Label(
            hp_val,
            text=f"/ {max_hp}",
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(side=tk.LEFT, padx=(4, 0))

        hp_bar = HPBar(hp_cf.inner, width=300, height=6)
        hp_bar.pack(fill=tk.X, pady=(8, 0))
        hp_bar.set_hp(current_hp, max_hp)

        def _adjust_hp(delta: int):
            cur = c.effective_current_hp
            new_val = max(0, min(c.hit_points, cur + delta))
            c.current_hit_points = new_val
            hp_label.config(text=str(new_val))
            hp_bar.set_hp(new_val, c.hit_points)
            save_character(c, characters_dir(), existing_filename=self.save_path)

        StepperPair(
            hp_val,
            on_increment=lambda: _adjust_hp(1),
            on_decrement=lambda: _adjust_hp(-1),
        ).pack(side=tk.RIGHT, padx=(4, 0))

        # ── Stats row: Initiative, Armor Class, Speed ──
        stats_row = tk.Frame(right_col, bg=COLORS["bg"])
        stats_row.pack(fill=tk.X)
        stats_row.columnconfigure(0, weight=1, uniform="stats")
        stats_row.columnconfigure(1, weight=1, uniform="stats")
        stats_row.columnconfigure(2, weight=1, uniform="stats")

        init_str = f"+{c.initiative}" if c.initiative >= 0 else str(c.initiative)
        speed_cf = None
        for col_i, (stat_label, stat_value) in enumerate(
            [
                ("INITIATIVE", init_str),
                ("ARMOR CLASS", str(c.armor_class)),
                ("SPEED", f"{c.speed} ft"),
            ]
        ):
            cf = CardFrame(stats_row, accent_left=(col_i == 0), pad=SPACING["md"])
            cf.grid(
                row=0,
                column=col_i,
                sticky="nsew",
                padx=(0 if col_i == 0 else SPACING["card_gap"], 0),
            )
            if col_i == 2:
                speed_cf = cf
            tk.Label(
                cf.inner,
                text=stat_label,
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w")
            tk.Label(
                cf.inner,
                text=stat_value,
                font=FONTS["stat_large"],
                fg=COLORS["fg"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w")

        # Sync Temp HP width to Speed box width
        def _sync_temp_width(event=None):
            w = speed_cf.winfo_width()
            if w > 1:
                temp_cf.configure(width=w)
                temp_cf.pack_propagate(False)

        if speed_cf:
            speed_cf.bind("<Configure>", _sync_temp_width)

        # ── Standard Actions ──
        SectionHeader(inner, text="Actions").pack(
            fill=tk.X, pady=(SPACING["sm"], SPACING["sm"])
        )

        from models.standard_actions import STANDARD_ACTIONS

        actions_grid = tk.Frame(inner, bg=COLORS["bg"])
        actions_grid.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        actions_grid.columnconfigure(0, weight=1)
        actions_grid.columnconfigure(1, weight=1)

        selected = getattr(c, "standard_action_options", {}) or {}

        row_idx = 0
        col_idx = 0
        for action in STANDARD_ACTIONS:
            name = action.get("name", "")
            desc = action.get("description", "")
            action_type = action.get("type", "Action")

            card = CardFrame(
                actions_grid,
                bg=COLORS["bg_container"],
                border_color=COLORS["border_subtle"],
                pad=SPACING["lg"],
            )
            card.grid(row=row_idx, column=col_idx, padx=4, pady=4, sticky="nsew")
            card.set_hover()

            header = tk.Frame(card.inner, bg=COLORS["bg_container"])
            header.pack(fill=tk.X)

            tk.Label(
                header,
                text=name,
                font=FONTS["heading_serif_sm"],
                fg=COLORS["fg"],
                bg=COLORS["bg_container"],
            ).pack(side=tk.LEFT)

            PillBadge(
                header,
                text=action_type.upper(),
                bg_color=COLORS["badge_glass_dim"],
                fg_color=COLORS["gold"],
            ).pack(side=tk.RIGHT)

            WrappingLabel(
                card.inner,
                text=desc,
                font=FONTS["body_small"],
                foreground=COLORS["fg_dim"],
                background=COLORS["bg_container"],
            ).pack(fill=tk.X, pady=(6, 0))

            col_idx += 1
            if col_idx >= 2:
                col_idx = 0
                row_idx += 1

    def _build_spell_slot_display(self, parent):
        """Build spell slot indicators."""
        c = self.character
        cls = c.character_class or {}
        if not cls:
            return

        # Get spell slots from class data
        spell_slots = cls.get("spell_slots", {})
        if not spell_slots:
            # Try progression data
            if self.data:
                level_data = self.data.get_level_data(
                    cls.get("slug", ""),
                    c.level,
                )
                if level_data:
                    spell_slots = level_data.get("spell_slots", {})

        if not spell_slots:
            return

        slots_card = CardFrame(parent, pad=SPACING["lg"])
        slots_card.pack(side=tk.LEFT, fill=tk.Y, padx=(SPACING["card_gap"], 0))
        slots_frame = slots_card.inner

        for slot_level, count in sorted(spell_slots.items(), key=lambda x: x[0]):
            if count <= 0:
                continue
            row = tk.Frame(slots_frame, bg=COLORS["bg_surface"])
            row.pack(fill=tk.X, pady=3)

            tk.Label(
                row,
                text=f"LEVEL {slot_level}".replace("st", "")
                .replace("nd", "")
                .replace("rd", "")
                .replace("th", "")
                .upper(),
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg"],
                bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT)

            tk.Label(
                row,
                text=f"{count} / {count}",
                font=FONTS["heading_serif_sm"],
                fg=COLORS["accent_text"],
                bg=COLORS["bg_surface"],
            ).pack(side=tk.RIGHT)

            # Slot indicator dots (rounded via Canvas)
            dots_frame = tk.Frame(row, bg=COLORS["bg_surface"])
            dots_frame.pack(side=tk.RIGHT, padx=(0, 8))
            for j in range(count):
                dot = tk.Canvas(
                    dots_frame,
                    width=12,
                    height=12,
                    bg=COLORS["bg_surface"],
                    highlightthickness=0,
                )
                dot.create_oval(1, 1, 11, 11, fill=COLORS["accent_text"], outline="")
                dot.pack(side=tk.LEFT, padx=2)

    # ================================================================
    # SPELLBOOK VIEW
    # ================================================================

    def _build_spellbook(self):
        parent = self._views[_SPELLBOOK]

        # Outer padding to match ScrollableFrame inner_padding (16px)
        wrapper = tk.Frame(parent, bg=COLORS["bg"])
        wrapper.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        # Header (gradient)
        spell_hero = GradientHeader(wrapper, min_height=60)
        spell_hero.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))

        tk.Label(
            spell_hero.inner,
            text="Spellbook",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(
            anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xl"], SPACING["xl"])
        )

        c = self.character
        cls = c.character_class or {}
        free_spell_entries = get_free_spell_summary_entries(c, self.data)

        # Spellcasting stats header
        cast_ability = cls.get("spellcasting_ability")
        if cast_ability or free_spell_entries:
            stats_frame = tk.Frame(wrapper, bg=COLORS["bg"])
            stats_frame.pack(fill=tk.X, pady=(SPACING["sm"], SPACING["section_gap"]))

            if cast_ability:
                spell_mod = c.ability_scores.modifier(cast_ability)
                attack_bonus = spell_mod + c.proficiency_bonus
                save_dc = 8 + spell_mod + c.proficiency_bonus
                ability_score = c.ability_scores.total(cast_ability)
                stat_specs = [
                    (
                        "Spell Attack",
                        f"+{attack_bonus}",
                        f"PROF + {cast_ability[:3].upper()}",
                    ),
                    ("Save DC", str(save_dc), "BASE 8"),
                ]
            else:
                stat_specs = []

            for label, value, sub in stat_specs:
                stat_cf = CardFrame(stats_frame, pad=SPACING["md"])
                stat_cf.pack(side=tk.LEFT, padx=(0, SPACING["card_gap"]))

                tk.Label(
                    stat_cf.inner,
                    text=label.upper(),
                    font=FONTS["label_upper_bold"],
                    fg=COLORS["fg_dim"],
                    bg=COLORS["bg_surface"],
                ).pack(anchor="w")

                val_row = tk.Frame(stat_cf.inner, bg=COLORS["bg_surface"])
                val_row.pack(anchor="w")

                tk.Label(
                    val_row,
                    text=value,
                    font=FONTS["stat_large"],
                    fg=COLORS["accent_text"],
                    bg=COLORS["bg_surface"],
                ).pack(side=tk.LEFT)

                PillBadge(
                    val_row,
                    text=sub,
                    bg_color=COLORS["badge_glass_dim"],
                    fg_color=COLORS["gold"],
                ).pack(side=tk.LEFT, padx=(8, 0))

            if free_spell_entries:
                free_cf = CardFrame(stats_frame, pad=SPACING["md"])
                free_cf.pack(side=tk.LEFT, padx=(0, SPACING["card_gap"]))

                tk.Label(
                    free_cf.inner,
                    text="FREE SPELLS",
                    font=FONTS["label_upper_bold"],
                    fg=COLORS["fg_dim"],
                    bg=COLORS["bg_surface"],
                ).pack(anchor="w")

                for entry in free_spell_entries:
                    tk.Label(
                        free_cf.inner,
                        text=f"{entry['label']} - {entry['cadence']}",
                        font=FONTS["body"],
                        fg=COLORS["fg"],
                        bg=COLORS["bg_surface"],
                        anchor="w",
                        justify=tk.LEFT,
                    ).pack(anchor="w")

            if cast_ability:
                stat_cf = CardFrame(stats_frame, pad=SPACING["md"])
                stat_cf.pack(side=tk.LEFT, padx=(0, SPACING["card_gap"]))

                tk.Label(
                    stat_cf.inner,
                    text="SPELL ABILITY",
                    font=FONTS["label_upper_bold"],
                    fg=COLORS["fg_dim"],
                    bg=COLORS["bg_surface"],
                ).pack(anchor="w")

                val_row = tk.Frame(stat_cf.inner, bg=COLORS["bg_surface"])
                val_row.pack(anchor="w")

                tk.Label(
                    val_row,
                    text=cast_ability[:3].upper(),
                    font=FONTS["stat_large"],
                    fg=COLORS["accent_text"],
                    bg=COLORS["bg_surface"],
                ).pack(side=tk.LEFT)

                PillBadge(
                    val_row,
                    text=f"{ability_score} (+{spell_mod})",
                    bg_color=COLORS["badge_glass_dim"],
                    fg_color=COLORS["gold"],
                ).pack(side=tk.LEFT, padx=(8, 0))

                # Spell slots inline with stats
                self._build_spell_slot_display(stats_frame)

        # Spell list (reuse existing pattern with split view)
        spell_area = tk.Frame(wrapper, bg=COLORS["bg"])
        spell_area.pack(fill=tk.BOTH, expand=True)
        spell_area.columnconfigure(0, weight=3)
        spell_area.columnconfigure(1, weight=6)
        spell_area.rowconfigure(0, weight=1)

        # Left: spell list
        left = tk.Frame(spell_area, bg=COLORS["bg_surface"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        tk.Label(
            left,
            text="Spell List",
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", padx=8, pady=(8, 4))

        self.spells_list = SectionedListbox(left, on_select=self._on_spell_select)
        self.spells_list.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 8))

        # Right: spell details
        right = tk.Frame(spell_area, bg=COLORS["bg_surface"])
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.spell_title = tk.Label(
            right,
            text="Select a spell",
            font=FONTS["heading_serif"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        )
        self.spell_title.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))

        self.spell_detail_text = tk.Text(
            right,
            wrap=tk.WORD,
            bg=COLORS["bg_container"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            state=tk.DISABLED,
            spacing1=2,
            spacing3=2,
            padx=12,
            pady=8,
        )
        self.spell_detail_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.spell_detail_text.tag_configure(
            "label", font=(FONTS["body"][0], FONTS["body"][1], "bold")
        )

        self._refresh_spells_tab()

    # ================================================================
    # INVENTORY VIEW
    # ================================================================

    def _build_inventory(self):
        parent = self._views[_INVENTORY]

        # Outer padding to match ScrollableFrame inner_padding (16px)
        wrapper = tk.Frame(parent, bg=COLORS["bg"])
        wrapper.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        c = self.character

        # ── Header (gradient) ──
        inv_hero = GradientHeader(wrapper, min_height=60)
        inv_hero.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))

        tk.Label(
            inv_hero.inner,
            text="Inventory",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(
            anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xl"], SPACING["xl"])
        )

        # ── Currency (editable, spellbook-card style) ──
        currency_frame = tk.Frame(wrapper, bg=COLORS["bg"])
        currency_frame.pack(fill=tk.X, pady=(SPACING["sm"], SPACING["section_gap"]))

        coin_defs = [
            ("Gold", "gp", 100, COLORS["gold"]),
            ("Silver", "sp", 10, COLORS["fg"]),
            ("Copper", "cp", 1, "#cd7f32"),
        ]

        gp, sp, cp_val = cp_to_coins(current_wealth_cp(c))
        coin_values = {"gp": gp, "sp": sp, "cp": cp_val}
        self._coin_vars: dict[str, tk.StringVar] = {}

        def _refresh_coin_display():
            g, s, co = cp_to_coins(current_wealth_cp(self.character))
            for k, v in {"gp": g, "sp": s, "cp": co}.items():
                self._coin_vars[k].set(str(v))

        def _commit_coins(event=None):
            parsed = {}
            for _, coin_key, _, _ in coin_defs:
                raw = self._coin_vars[coin_key].get().strip()
                if raw == "":
                    raw = "0"
                if not raw.isdigit():
                    AlertDialog(
                        self.winfo_toplevel(),
                        "Wealth",
                        "Please enter whole numbers only.",
                    )
                    _refresh_coin_display()
                    return False
                parsed[coin_key] = int(raw)
            new_total_cp = parsed["gp"] * 100 + parsed["sp"] * 10 + parsed["cp"]
            self.character.wealth_adjust_cp = int(
                new_total_cp - base_wealth_cp(self.character)
            )
            _refresh_coin_display()
            self._on_sheet_changed()
            return True

        def _adjust_wealth(delta_cp: int):
            if not _commit_coins():
                return
            cur = current_wealth_cp(self.character)
            if delta_cp < 0 and cur < abs(delta_cp):
                AlertDialog(
                    self.winfo_toplevel(),
                    "Wealth",
                    "You do not have enough wealth for that reduction.",
                )
                return
            self.character.wealth_adjust_cp = int(
                getattr(self.character, "wealth_adjust_cp", 0)
            ) + int(delta_cp)
            _refresh_coin_display()
            self._on_sheet_changed()

        for label, coin_key, unit_cp, color in coin_defs:
            stat_cf = CardFrame(currency_frame, pad=SPACING["md"])
            stat_cf.pack(side=tk.LEFT, padx=(0, SPACING["card_gap"]))

            tk.Label(
                stat_cf.inner,
                text=label.upper(),
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w")

            val_row = tk.Frame(stat_cf.inner, bg=COLORS["bg_surface"])
            val_row.pack(anchor="w", fill=tk.X)

            var = tk.StringVar(value=str(coin_values.get(coin_key, 0)))
            self._coin_vars[coin_key] = var

            entry = tk.Entry(
                val_row,
                textvariable=var,
                font=FONTS["stat_large"],
                bg=COLORS["bg_surface"],
                fg=color,
                insertbackground=color,
                relief=tk.FLAT,
                borderwidth=0,
                highlightthickness=0,
                width=4,
            )
            entry.pack(side=tk.LEFT)
            entry.bind("<FocusOut>", _commit_coins)
            entry.bind("<Return>", _commit_coins)

            StepperPair(
                val_row,
                on_increment=lambda d=unit_cp: _adjust_wealth(d),
                on_decrement=lambda d=unit_cp: _adjust_wealth(-d),
            ).pack(side=tk.LEFT, padx=(2, 0))

        # ── Inventory split view ──
        self._inventory_parent = wrapper
        self._render_inventory_split_view()

    # ================================================================
    # FEATURES VIEW
    # ================================================================

    def _build_features(self):
        parent = self._views[_FEATURES]
        scroll = ScrollableFrame(parent)
        scroll.pack(fill=tk.BOTH, expand=True)
        inner = scroll.inner
        c = self.character

        feat_hero = GradientHeader(inner, min_height=60)
        feat_hero.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        tk.Label(
            feat_hero.inner,
            text="Features & Traits",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(
            anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xl"], SPACING["xl"])
        )

        # ── Species Traits ──
        if c.species and c.species.get("traits"):
            SectionHeader(inner, text=f"{c.species_name} Traits").pack(
                fill=tk.X, pady=(0, SPACING["sm"])
            )
            traits_grid = tk.Frame(inner, bg=COLORS["bg"])
            traits_grid.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
            traits_grid.columnconfigure(0, weight=1)
            traits_grid.columnconfigure(1, weight=1)
            for i, trait in enumerate(get_species_trait_cards(c.species)):
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

        # ── Class Features ──
        if c.character_class and c.class_levels:
            feat_title = (
                "Class Features" if c.is_multiclass else f"{c.class_name} Features"
            )
            SectionHeader(inner, text=feat_title).pack(
                fill=tk.X, pady=(0, SPACING["sm"])
            )
            features_grid = tk.Frame(inner, bg=COLORS["bg"])
            features_grid.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
            features_grid.columnconfigure(0, weight=1)
            features_grid.columnconfigure(1, weight=1)
            card_idx = 0
            for cl in c.class_levels:
                level_data = (
                    self.data.get_level_data(cl.class_slug, cl.class_level)
                    if self.data
                    else None
                )
                feature_details = []
                if level_data:
                    feature_details = [
                        f
                        for f in level_data.get("feature_details", [])
                        if isinstance(f, dict)
                        and f.get("name") not in ("-", "Ability Score Improvement")
                    ]
                    if not feature_details:
                        for name in level_data.get("features", []):
                            if name not in ("-", "Ability Score Improvement"):
                                feature_details.append(
                                    {"name": name, "description": ""}
                                )
                extra = []
                if cl.feat_choice:
                    asi_desc = ""
                    if cl.asi_increases:
                        asi_desc = ", ".join(
                            f"{a} +{v}" for a, v in cl.asi_increases.items()
                        )
                    extra.append(
                        {"name": f"Feat: {cl.feat_choice}", "description": asi_desc}
                    )
                if cl.subclass_slug:
                    extra.append(
                        {
                            "name": f"Subclass: {cl.subclass_slug.replace('-', ' ').title()}",
                            "description": "",
                        }
                    )
                all_items = feature_details + extra
                if not all_items:
                    continue
                prefix = f"{cl.class_slug.title()} " if c.is_multiclass else ""
                level_label = f"{prefix}Level {cl.class_level}"
                for feat in all_items:
                    feat_name = feat.get("name", "")
                    feat_desc = augment_level1_feature_description(
                        feat_name,
                        feat.get("description", ""),
                        c,
                        self.data,
                    )
                    card = CardFrame(
                        features_grid,
                        bg=COLORS["bg_container"],
                        border_color=COLORS["border_subtle"],
                        pad=SPACING["lg"],
                    )
                    card.grid(
                        row=card_idx // 2,
                        column=card_idx % 2,
                        padx=4,
                        pady=4,
                        sticky="nsew",
                    )
                    header = tk.Frame(card.inner, bg=COLORS["bg_container"])
                    header.pack(fill=tk.X)
                    tk.Label(
                        header,
                        text=feat_name,
                        font=FONTS["heading_serif_sm"],
                        fg=COLORS["fg"],
                        bg=COLORS["bg_container"],
                    ).pack(side=tk.LEFT)
                    PillBadge(
                        header,
                        text=level_label.upper(),
                        bg_color=COLORS["badge_glass_dim"],
                        fg_color=COLORS["gold"],
                    ).pack(side=tk.RIGHT)
                    if feat_desc:
                        FormattedDescription(
                            card.inner,
                            text=feat_desc,
                            font=FONTS["body_small"],
                            foreground=COLORS["fg_dim"],
                            background=COLORS["bg_container"],
                        ).pack(fill=tk.X, pady=(6, 0))
                    card_idx += 1

        # ── Subclass Features ──
        if c.current_subclass:
            sub_name = c.current_subclass.replace("-", " ").title()
            SectionHeader(inner, text=f"Subclass: {sub_name}").pack(
                fill=tk.X, pady=(0, SPACING["sm"])
            )
            subclass_data = None
            if self.data and c.character_class:
                primary_slug = c.character_class.get("slug", "")
                subclasses_for_class = self.data.get_subclasses_for_class(primary_slug)
                subclass_data = next(
                    (
                        s
                        for s in subclasses_for_class
                        if s.get("slug") == c.current_subclass
                    ),
                    None,
                )
            if subclass_data:
                desc = (subclass_data.get("description") or "").strip()
                if desc:
                    intro = re.split(r"\bLevel\s+\d+\s*:", desc, maxsplit=1)[0].strip()
                    if intro:
                        WrappingLabel(
                            inner,
                            text=intro,
                            font=FONTS["body_small"],
                            foreground=COLORS["fg_dim"],
                        ).pack(fill=tk.X, pady=(0, SPACING["sm"]))
                sub_grid = tk.Frame(inner, bg=COLORS["bg"])
                sub_grid.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
                sub_grid.columnconfigure(0, weight=1)
                sub_grid.columnconfigure(1, weight=1)
                sub_idx = 0
                features_by_level = subclass_data.get("features", {})
                for lvl in sorted(
                    features_by_level.keys(),
                    key=lambda x: int(x) if str(x).isdigit() else 99,
                ):
                    try:
                        lvl_int = int(lvl)
                    except (ValueError, TypeError):
                        continue
                    if lvl_int > c.level:
                        continue
                    for feat in features_by_level.get(lvl, []):
                        card = CardFrame(
                            sub_grid,
                            bg=COLORS["bg_container"],
                            border_color=COLORS["border_subtle"],
                            pad=SPACING["lg"],
                        )
                        card.grid(
                            row=sub_idx // 2,
                            column=sub_idx % 2,
                            padx=4,
                            pady=4,
                            sticky="nsew",
                        )
                        header = tk.Frame(card.inner, bg=COLORS["bg_container"])
                        header.pack(fill=tk.X)
                        tk.Label(
                            header,
                            text=feat.get("name", ""),
                            font=FONTS["heading_serif_sm"],
                            fg=COLORS["fg"],
                            bg=COLORS["bg_container"],
                        ).pack(side=tk.LEFT)
                        PillBadge(
                            header,
                            text=f"LEVEL {lvl}",
                            bg_color=COLORS["badge_glass_dim"],
                            fg_color=COLORS["gold"],
                        ).pack(side=tk.RIGHT)
                        if feat.get("description"):
                            FormattedDescription(
                                card.inner,
                                text=feat["description"],
                                font=FONTS["body_small"],
                                foreground=COLORS["fg_dim"],
                                background=COLORS["bg_container"],
                            ).pack(fill=tk.X, pady=(6, 0))
                        sub_idx += 1

        # ── Feats ──
        has_any_feat = c.feat or c.species_origin_feat
        if has_any_feat:
            SectionHeader(inner, text="Feats").pack(fill=tk.X, pady=(0, SPACING["sm"]))
            feats_grid = tk.Frame(inner, bg=COLORS["bg"])
            feats_grid.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
            feats_grid.columnconfigure(0, weight=1)
            feats_grid.columnconfigure(1, weight=1)
            feat_idx = 0
            if c.feat:
                feat_name = (
                    c.background.get("feat", c.feat.get("name", ""))
                    if c.background
                    else c.feat.get("name", "")
                )
                card = CardFrame(
                    feats_grid,
                    bg=COLORS["bg_container"],
                    border_color=COLORS["border_subtle"],
                    pad=SPACING["lg"],
                )
                card.grid(
                    row=feat_idx // 2,
                    column=feat_idx % 2,
                    padx=4,
                    pady=4,
                    sticky="nsew",
                )
                header = tk.Frame(card.inner, bg=COLORS["bg_container"])
                header.pack(fill=tk.X)
                tk.Label(
                    header,
                    text=feat_name,
                    font=FONTS["heading_serif_sm"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_container"],
                ).pack(side=tk.LEFT)
                PillBadge(
                    header,
                    text="BACKGROUND",
                    bg_color=COLORS["badge_glass_dim"],
                    fg_color=COLORS["gold"],
                ).pack(side=tk.RIGHT)
                benefits = [
                    f"{b['name']}: {b.get('description', '')}"
                    for b in c.feat.get("benefits", [])
                ]
                if benefits:
                    WrappingLabel(
                        card.inner,
                        text="\n".join(benefits),
                        font=FONTS["body_small"],
                        foreground=COLORS["fg_dim"],
                        background=COLORS["bg_container"],
                    ).pack(fill=tk.X, pady=(6, 0))
                feat_idx += 1
            if c.species_origin_feat:
                sp_name = c.species_name if c.species else "Species"
                card = CardFrame(
                    feats_grid,
                    bg=COLORS["bg_container"],
                    border_color=COLORS["border_subtle"],
                    pad=SPACING["lg"],
                )
                card.grid(
                    row=feat_idx // 2,
                    column=feat_idx % 2,
                    padx=4,
                    pady=4,
                    sticky="nsew",
                )
                header = tk.Frame(card.inner, bg=COLORS["bg_container"])
                header.pack(fill=tk.X)
                tk.Label(
                    header,
                    text=c.species_origin_feat["name"],
                    font=FONTS["heading_serif_sm"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_container"],
                ).pack(side=tk.LEFT)
                PillBadge(
                    header,
                    text=sp_name.upper(),
                    bg_color=COLORS["badge_glass_dim"],
                    fg_color=COLORS["gold"],
                ).pack(side=tk.RIGHT)
                benefits = [
                    f"{b['name']}: {b.get('description', '')}"
                    for b in c.species_origin_feat.get("benefits", [])
                ]
                if benefits:
                    WrappingLabel(
                        card.inner,
                        text="\n".join(benefits),
                        font=FONTS["body_small"],
                        foreground=COLORS["fg_dim"],
                        background=COLORS["bg_container"],
                    ).pack(fill=tk.X, pady=(6, 0))

    # ================================================================
    # BACKSTORY VIEW
    # ================================================================

    def _build_backstory(self):
        parent = self._views[_BACKSTORY]
        c = self.character

        scroll = ScrollableFrame(parent)
        scroll.pack(fill=tk.BOTH, expand=True)
        inner = scroll.inner

        # Hero header (full width)
        back_hero = GradientHeader(inner, min_height=50)
        back_hero.grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, SPACING["section_gap"])
        )
        tk.Label(
            back_hero.inner,
            text="Biography",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(
            anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xl"], SPACING["xl"])
        )

        # Grid layout: Portrait + desc/personality on top, backstory full-width bottom
        inner.columnconfigure(0, weight=1)
        inner.columnconfigure(1, weight=1)
        inner.rowconfigure(1, weight=1)
        inner.rowconfigure(2, weight=1)

        # Top-left: Portrait
        portrait = tk.Frame(inner, bg=COLORS["bg_surface"])
        portrait.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(SPACING["lg"], SPACING["sm"]),
            pady=(0, SPACING["sm"]),
        )
        portrait.columnconfigure(0, weight=1)
        self._bio_portrait_frame = portrait

        SectionHeader(portrait, text="Portrait").pack(fill=tk.X, pady=(0, 4))

        self.bio_image_canvas = tk.Canvas(
            portrait,
            width=260,
            height=100,
            bg=COLORS["bg_container"],
            highlightthickness=0,
            relief=tk.FLAT,
        )
        self.bio_image_canvas.pack(padx=12, pady=(0, 8), fill=tk.BOTH, expand=True)
        self.bio_image_canvas.create_text(
            130,
            50,
            text="No image selected",
            fill=COLORS["fg_dim"],
            font=FONTS["body"],
            justify=tk.CENTER,
            tags=("placeholder",),
        )
        self._last_bio_portrait_width = 0
        portrait.bind("<Configure>", self._on_bio_portrait_frame_configure)

        btns = tk.Frame(portrait, bg=COLORS["bg_surface"])
        btns.pack(pady=(0, 12))
        ttk.Button(
            btns, text="Choose Image...", command=self._choose_biography_image
        ).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btns, text="Clear Image", command=self._clear_biography_image).pack(
            side=tk.LEFT, padx=(4, 0)
        )

        # Top-right: Physical Description + Personality stacked
        right_stack = tk.Frame(inner, bg=COLORS["bg"])
        right_stack.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=(SPACING["sm"], 16),
            pady=(0, SPACING["sm"]),
        )
        right_stack.columnconfigure(0, weight=1)
        right_stack.rowconfigure(1, weight=1)
        right_stack.rowconfigure(3, weight=1)

        SectionHeader(right_stack, text="Physical Description").grid(
            row=0, column=0, sticky="ew", pady=(0, 4)
        )
        self.bio_description_text = self._make_bio_textbox(right_stack)
        self.bio_description_text.configure(height=4)
        self.bio_description_text.grid(
            row=1, column=0, sticky="nsew", pady=(0, SPACING["sm"])
        )

        SectionHeader(right_stack, text="Personality").grid(
            row=2, column=0, sticky="ew", pady=(0, 4)
        )
        self.bio_personality_text = self._make_bio_textbox(right_stack)
        self.bio_personality_text.configure(height=4)
        self.bio_personality_text.grid(row=3, column=0, sticky="nsew")

        # Bottom: Character Backstory (full width)
        bottom = tk.Frame(inner, bg=COLORS["bg"])
        bottom.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="nsew",
            padx=(SPACING["lg"], 16),
            pady=(SPACING["sm"], SPACING["lg"]),
        )
        bottom.columnconfigure(0, weight=1)
        bottom.rowconfigure(1, weight=1)
        SectionHeader(bottom, text="Character Backstory").pack(fill=tk.X, pady=(0, 4))
        self.bio_backstory_text = self._make_bio_textbox(bottom)
        self.bio_backstory_text.pack(fill=tk.BOTH, expand=True)

        for widget in (
            self.bio_backstory_text,
            self.bio_personality_text,
            self.bio_description_text,
        ):
            widget.bind("<FocusOut>", self._on_biography_focus_out)

        self._biography_tab_built = True
        self._refresh_biography_tab()

    # ================================================================
    # Shared biography helpers
    # ================================================================

    def _make_bio_textbox(self, parent) -> tk.Text:
        text = tk.Text(
            parent,
            wrap=tk.WORD,
            bg=COLORS["bg_container"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            spacing1=2,
            spacing3=2,
            padx=10,
            pady=8,
        )
        return text

    def _refresh_biography_tab(self):
        if not getattr(self, "_biography_tab_built", False):
            return
        self._bio_loading = True
        try:
            self._set_text_widget(
                self.bio_backstory_text,
                getattr(self.character, "biography_backstory", "") or "",
            )
            self._set_text_widget(
                self.bio_personality_text,
                getattr(self.character, "biography_personality", "") or "",
            )
            self._set_text_widget(
                self.bio_description_text,
                getattr(self.character, "biography_description", "") or "",
            )
        finally:
            self._bio_loading = False
        self._refresh_biography_image_preview()

    def _set_text_widget(self, widget: tk.Text, value: str):
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)

    def _text_value(self, widget: tk.Text) -> str:
        return widget.get("1.0", tk.END).rstrip("\n")

    def _save_biography_fields_to_character(self) -> bool:
        if self._bio_loading or not getattr(self, "_biography_tab_built", False):
            return False
        updates = {
            "biography_backstory": self._text_value(self.bio_backstory_text),
            "biography_personality": self._text_value(self.bio_personality_text),
            "biography_description": self._text_value(self.bio_description_text),
        }
        changed = False
        for attr, value in updates.items():
            if getattr(self.character, attr, "") != value:
                setattr(self.character, attr, value)
                changed = True
        return changed

    def _on_biography_focus_out(self, _event=None):
        if self._save_biography_fields_to_character():
            self._on_sheet_changed()

    def _on_bio_portrait_frame_configure(self, event):
        new_width = event.width
        if new_width > 1 and new_width != self._last_bio_portrait_width:
            self._last_bio_portrait_width = new_width
            self._refresh_biography_image_preview()

    def _get_bio_portrait_width(self):
        fw = self._bio_portrait_frame.winfo_width()
        if fw > 1:
            return max(100, fw - 24)
        return 260

    def _refresh_biography_image_preview(self):
        if not getattr(self, "_biography_tab_built", False):
            return
        self.bio_image_canvas.delete("all")
        self._bio_photo = None
        self._bio_photo_display = None
        cw = self._get_bio_portrait_width()

        data = getattr(self.character, "biography_image_data", "") or ""
        img_format = (
            getattr(self.character, "biography_image_format", "") or ""
        ).lower()
        if not data:
            self.bio_image_canvas.configure(height=100)
            self.bio_image_canvas.create_text(
                cw // 2,
                50,
                text="No image selected",
                fill=COLORS["fg_dim"],
                font=FONTS["body"],
                justify=tk.CENTER,
            )
            return

        try:
            raw = base64.b64decode(data)
        except Exception:
            self.bio_image_canvas.configure(height=100)
            self.bio_image_canvas.create_text(
                cw // 2,
                50,
                text="Image data is invalid",
                fill=COLORS["fg_dim"],
                font=FONTS["body_small"],
                justify=tk.CENTER,
            )
            return

        try:
            if Image is not None and ImageTk is not None:
                pil_img = Image.open(io.BytesIO(raw))
                pil_img.thumbnail((cw, cw * 4))
                iw, ih = pil_img.size
                self.bio_image_canvas.configure(width=iw, height=ih)
                display = ImageTk.PhotoImage(pil_img)
                self._bio_photo_display = display
                self.bio_image_canvas.create_image(iw // 2, ih // 2, image=display)
                return

            if img_format in {"png", ""}:
                photo = tk.PhotoImage(data=base64.b64encode(raw).decode("ascii"))
            else:
                raise tk.TclError("Unsupported preview format")
        except Exception:
            self.bio_image_canvas.configure(height=100)
            self.bio_image_canvas.create_text(
                cw // 2,
                50,
                text="Image loaded for export\nbut preview is unavailable",
                fill=COLORS["fg_dim"],
                font=FONTS["body_small"],
                justify=tk.CENTER,
            )
            return

        w = max(1, int(photo.width()))
        h = max(1, int(photo.height()))
        scale = max((w + cw - 1) // cw, 1)
        display = photo.subsample(scale) if scale > 1 else photo
        dw, dh = int(display.width()), int(display.height())
        self.bio_image_canvas.configure(width=dw, height=dh)
        self._bio_photo = photo
        self._bio_photo_display = display
        self.bio_image_canvas.create_image(dw // 2, dh // 2, image=display)

    def _choose_biography_image(self):
        path = filedialog.askopenfilename(
            title="Choose Character Portrait",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError as e:
            AlertDialog(
                self.winfo_toplevel(), "Biography Image", f"Could not load image:\n{e}"
            )
            return

        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        img_format = "jpeg" if ext in {"jpg", "jpeg"} else "png"
        if Image is not None:
            try:
                pil_img = Image.open(io.BytesIO(raw))
                fmt = (pil_img.format or "").lower()
                if fmt in {"jpg", "jpeg"}:
                    img_format = "jpeg"
                elif fmt == "png":
                    img_format = "png"
            except Exception:
                pass
        self.character.biography_image_data = base64.b64encode(raw).decode("ascii")
        self.character.biography_image_format = img_format
        self._refresh_biography_image_preview()
        self._on_sheet_changed()

    def _clear_biography_image(self):
        if not (
            getattr(self.character, "biography_image_data", "")
            or getattr(self.character, "biography_image_format", "")
        ):
            return
        self.character.biography_image_data = ""
        self.character.biography_image_format = ""
        self._refresh_biography_image_preview()
        self._on_sheet_changed()

    # ================================================================
    # Shared spell helpers
    # ================================================================

    def _refresh_spells_tab(self):
        self._spell_entries_by_label = {}
        sections: list[tuple[str, list[str]]] = []
        sub_items: dict[str, list[str]] = {}

        for section_name, entries in get_spellbook_sections(self.character, self.data):
            labels: list[str] = []
            for entry in entries:
                label = format_spellbook_entry_label(entry)
                labels.append(label)
                self._spell_entries_by_label[label] = entry
                details: list[str] = []
                if entry.get("free_casts"):
                    details.append(f"Free: {', '.join(entry['free_casts'])}")
                if entry.get("ritual_only"):
                    details.append("Ritual only")
                if entry.get("detail_notes"):
                    details.extend(entry["detail_notes"])
                if details:
                    sub_items[label] = details
            if labels:
                sections.append((section_name, labels))

        self.spells_list.set_sectioned_items(sections, sub_items=sub_items)

        if sections and sections[0][1]:
            first_label = sections[0][1][0]
            self.spells_list.select_item(first_label)
            self._show_spell_details(self._spell_entries_by_label.get(first_label))
        else:
            self._show_spell_details(None)

    def _on_spell_select(self, spell_label: str):
        self._show_spell_details(self._spell_entries_by_label.get(spell_label))

    def _show_spell_details(self, entry: dict | None):
        if not entry:
            self.spell_title.configure(text="No spells known")
            self._set_spell_detail_text(
                "This character has no spells or magical grants to display."
            )
            return

        spell_name = str(entry.get("spell_name", "") or "").strip()
        spell = self._spell_index.get(spell_name, {})
        if not spell:
            self.spell_title.configure(text=format_spellbook_entry_label(entry))
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

        self.spell_title.configure(text=format_spellbook_entry_label(entry))
        body = [
            f"Level: {level_text}",
            f"School: {school}",
            f"Casting Time: {spell.get('casting_time', 'Unknown')}",
            f"Range: {spell.get('range', 'Unknown')}",
            f"Duration: {spell.get('duration', 'Unknown')}",
            f"Components: {components}",
        ]
        source_labels = entry.get("source_labels", []) or []
        if source_labels:
            body.append(f"Granted By: {', '.join(source_labels)}")
        free_casts = entry.get("free_casts", []) or []
        if free_casts:
            body.append(f"Free Casting: {', '.join(free_casts)}")
        if entry.get("ritual_only"):
            body.append("Special: Ritual only")
        if entry.get("dragonmark_eligible"):
            body.append("Special: Dragonmark spell")
        for note in entry.get("detail_notes", []) or []:
            body.append(f"Special: {note}")
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
        if (
            not getattr(self, "spell_detail_text", None)
            or not self.spell_detail_text.winfo_exists()
        ):
            return
        label_prefixes = {
            "Level",
            "School",
            "Casting Time",
            "Range",
            "Duration",
            "Components",
            "Granted By",
            "Free Casting",
            "Special",
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

    # ================================================================
    # Inventory helpers (preserved from original)
    # ================================================================

    def _parse_item_qty(self, text: str) -> tuple[str, int]:
        raw = str(text or "").strip()
        parts = raw.split(" ", 1)
        qty = 1
        name = raw
        if len(parts) == 2 and parts[0].isdigit():
            qty = max(1, int(parts[0]))
            name = parts[1].strip()

        m = re.match(r"^(.*)\((\d+)(?:\s+([^)]+))?\)\s*$", name)
        if m:
            stripped = m.group(1).strip()
            paren_qty = max(1, int(m.group(2)))
            qualifier = str(m.group(3) or "").strip().lower()
            is_quantity_suffix = (not qualifier) or qualifier in {"day", "days"}
            if not is_quantity_suffix:
                return name, qty
            if stripped:
                name = stripped
            qty *= paren_qty

        return name, qty

    def _effective_inventory_pools(self):
        c = self.character
        weapon_counts = dict(get_selected_weapon_counts(c))
        armor_counts = dict(get_selected_armor_counts(c))
        inventory_items = list(get_selected_non_weapon_items(c))

        for ent in getattr(c, "custom_inventory", []) or []:
            name = str(ent.get("name", "")).strip()
            if not name:
                continue
            qty = max(1, int(ent.get("qty", 1)))
            category = str(ent.get("category", "Adventuring Gear"))
            key = normalize_item_key(name)
            if category == "Weapons":
                weapon_counts[key] = weapon_counts.get(key, 0) + qty
            elif category == "Armor":
                armor_counts[key] = armor_counts.get(key, 0) + qty
            else:
                inventory_items.append(f"{qty} {name}" if qty > 1 else name)

        removed = {
            normalize_item_key(k): int(v)
            for k, v in (getattr(c, "removed_items", {}) or {}).items()
            if int(v) > 0
        }

        for key, rem in removed.items():
            if key in weapon_counts:
                weapon_counts[key] = max(0, weapon_counts[key] - rem)
                if weapon_counts[key] <= 0:
                    weapon_counts.pop(key, None)
            if key in armor_counts:
                armor_counts[key] = max(0, armor_counts[key] - rem)
                if armor_counts[key] <= 0:
                    armor_counts.pop(key, None)

        inv_map: dict[str, int] = {}
        inv_name: dict[str, str] = {}
        order: list[str] = []
        for line in inventory_items:
            base_name, qty = self._parse_item_qty(line)
            if not base_name:
                continue
            key = normalize_item_key(base_name)
            if key not in inv_map:
                order.append(key)
                inv_name[key] = base_name
            inv_map[key] = inv_map.get(key, 0) + qty

        for key, rem in removed.items():
            if key in inv_map:
                inv_map[key] = max(0, inv_map[key] - rem)

        inv_entries = []
        for key in order:
            qty = inv_map.get(key, 0)
            if qty <= 0:
                continue
            inv_entries.append({"name": inv_name[key], "key": key, "qty": qty})

        return weapon_counts, armor_counts, inv_entries

    # ── Armor proficiency helpers ──

    ARMOR_REQUIRED = {
        "padded armor": "light",
        "leather armor": "light",
        "studded leather armor": "light",
        "hide armor": "medium",
        "chain shirt": "medium",
        "scale mail": "medium",
        "breastplate": "medium",
        "half plate armor": "medium",
        "ring mail": "heavy",
        "chain mail": "heavy",
        "splint armor": "heavy",
        "plate armor": "heavy",
        "shield": "shield",
    }

    def _armor_profs(self) -> set[str]:
        out: set[str] = set()
        for p in self.character.effective_armor_proficiencies:
            t = str(p).lower()
            for k in ("shield", "heavy", "medium", "light"):
                if k in t:
                    out.add(k)
        return out

    def _can_equip_armor(self, armor_key: str) -> tuple[bool, str]:
        req = self.ARMOR_REQUIRED.get(armor_key, "light")
        if req in self._armor_profs():
            return True, ""
        label = "Shields" if req == "shield" else f"{req.title()} armor"
        return False, f"{self.character.class_name} is not proficient with {label}."

    def _has_weapon_proficiency(self, weapon_key: str) -> bool:
        profs = [str(p).lower() for p in self.character.effective_weapon_proficiencies]
        if any(weapon_key in p for p in profs):
            return True
        meta = WEAPON_DATA.get(weapon_key, {})
        cat = meta.get("category", "")
        if cat == "simple" and any("simple" in p for p in profs):
            return True
        if cat == "martial" and any("martial" in p for p in profs):
            return True
        return False

    # ── Inventory split view ──

    def _render_inventory_split_view(self):
        parent = self._inventory_parent

        split = tk.Frame(parent, bg=COLORS["bg"])
        split.pack(fill=tk.BOTH, expand=True)
        split.columnconfigure(0, weight=3)
        split.columnconfigure(1, weight=6)
        split.rowconfigure(0, weight=1)

        # Left: item list
        left = tk.Frame(split, bg=COLORS["bg_surface"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        tk.Label(
            left,
            text="Items",
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", padx=8, pady=(8, 4))

        self.inv_list = SectionedListbox(
            left,
            on_select=self._on_inv_list_select,
            on_sub_select=self._on_inv_sub_select,
        )
        self.inv_list.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        btn_row = tk.Frame(left, bg=COLORS["bg_surface"])
        btn_row.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(
            btn_row,
            text="Add Item",
            style="Accent.TButton",
            command=self._on_add_inventory,
        ).pack(fill=tk.X)

        self._inv_list_entries: dict[str, dict] = {}

        # Right: detail panel
        right = tk.Frame(split, bg=COLORS["bg_surface"])
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.inventory_detail_title = tk.Label(
            right,
            text="Select an item",
            font=FONTS["heading_serif"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        )
        self.inventory_detail_title.grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 4)
        )

        self.inventory_detail_text = tk.Text(
            right,
            wrap=tk.WORD,
            bg=COLORS["bg_container"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            state=tk.DISABLED,
            spacing1=2,
            spacing3=2,
            padx=12,
            pady=8,
        )
        self.inventory_detail_text.grid(
            row=1, column=0, sticky="nsew", padx=8, pady=(0, 8)
        )

        actions = tk.Frame(right, bg=COLORS["bg_surface"])
        actions.grid(row=2, column=0, sticky="e", pady=(0, 8), padx=8)

        self._inv_equip_btn = ttk.Button(
            actions,
            text="Equip",
            command=self._toggle_equip_selected,
            state=tk.DISABLED,
        )
        # Starts hidden; shown only when an equippable item is selected

        self.remove_one_btn = ttk.Button(
            actions,
            text="Remove one",
            command=self._remove_one_selected_item,
            state=tk.DISABLED,
        )
        self.remove_one_btn.pack(side=tk.LEFT)

        self.remove_all_btn = ttk.Button(
            actions,
            text="Remove all",
            command=self._remove_all_selected_item,
            state=tk.DISABLED,
        )
        self.remove_all_btn.pack(side=tk.LEFT, padx=(6, 0))

        self._refresh_inventory_split_items()

    _EQUIP_CHECK = "\u2611"
    _EQUIP_UNCHECK = "\u2610"

    def _refresh_inventory_split_items(self):
        weapon_counts, armor_counts, inv_entries = self._effective_inventory_pools()
        equipped_weapons = set(self.character.equipped_weapons or [])
        equipped_armor = set(self.character.equipped_armor or [])

        self._inv_list_entries: dict[str, dict] = {}
        sections: list[tuple[str, list[str]]] = []
        sub_items: dict[str, list[str]] = {}

        # Weapons section
        weapon_names = []
        for key in sorted(weapon_counts.keys()):
            qty = weapon_counts[key]
            name = key.title()
            equipped = key in equipped_weapons
            check = self._EQUIP_CHECK if equipped else self._EQUIP_UNCHECK
            display = f"{check} {name} (x{qty})" if qty > 1 else f"{check} {name}"
            weapon_names.append(display)
            self._inv_list_entries[display] = {
                "name": name,
                "key": key,
                "qty": qty,
                "category": "Weapons",
                "equippable": True,
                "equipped": equipped,
            }
        if weapon_names:
            sections.append(("Weapons", weapon_names))

        # Armor section
        armor_names = []
        ac_order_keys = [normalize_item_key(n) for n in ARMOR_AC_ORDER]
        ordered_armor_keys = [k for k in ac_order_keys if k in armor_counts]
        remaining_armor_keys = sorted(
            k for k in armor_counts if k not in set(ac_order_keys)
        )
        for key in ordered_armor_keys + remaining_armor_keys:
            qty = armor_counts[key]
            name = key.title()
            equipped = key in equipped_armor
            check = self._EQUIP_CHECK if equipped else self._EQUIP_UNCHECK
            display = f"{check} {name} (x{qty})" if qty > 1 else f"{check} {name}"
            armor_names.append(display)
            self._inv_list_entries[display] = {
                "name": name,
                "key": key,
                "qty": qty,
                "category": "Armor",
                "equippable": True,
                "equipped": equipped,
            }
        if armor_names:
            sections.append(("Armor & Shields", armor_names))

        # General inventory section
        inv_names = []
        for e in sorted(inv_entries, key=lambda x: x.get("name", "").casefold()):
            name = e["name"]
            qty = e["qty"]
            display = f"{name} (x{qty})" if qty > 1 else name
            inv_names.append(display)
            self._inv_list_entries[display] = {
                "name": name,
                "key": e["key"],
                "qty": qty,
                "category": "Inventory",
                "equippable": False,
                "equipped": False,
            }
            container = _container_contents(name)
            if container:
                _, contents = container
                sub_list = []
                for sub in contents:
                    sub_name = sub.strip()
                    clean_sub_name, sub_qty = self._parse_item_qty(sub_name)
                    total_sub_qty = max(1, int(e.get("qty", 1))) * sub_qty
                    sub_key = normalize_item_key(clean_sub_name)
                    removed_sub_qty = int(
                        (getattr(self.character, "removed_items", {}) or {}).get(
                            sub_key, 0
                        )
                    )
                    remaining_sub_qty = max(0, total_sub_qty - removed_sub_qty)
                    if remaining_sub_qty <= 0:
                        continue
                    sub_display = (
                        f"{clean_sub_name} (x{remaining_sub_qty})"
                        if remaining_sub_qty > 1
                        else clean_sub_name
                    )
                    sub_list.append(sub_display)
                    self._inv_list_entries[sub_display] = {
                        "name": clean_sub_name,
                        "key": sub_key,
                        "qty": remaining_sub_qty,
                        "category": "Inventory",
                        "equippable": False,
                        "equipped": False,
                        "is_subitem": True,
                        "parent_name": name,
                    }
                if sub_list:
                    sub_items[display] = sub_list
        if inv_names:
            sections.append(("Inventory", inv_names))

        self.inv_list.set_sectioned_items(sections, sub_items=sub_items)

        # Restore selection
        if self._selected_inventory_name:
            for display, entry in self._inv_list_entries.items():
                if entry.get("name") == self._selected_inventory_name:
                    self._select_inv_list_item(display)
                    self._on_inventory_select_entry(entry)
                    return

        # Select first item
        for display, entry in self._inv_list_entries.items():
            self._select_inv_list_item(display)
            self._on_inventory_select_entry(entry)
            return

        self._selected_inventory_name = ""
        self.remove_one_btn.configure(state=tk.DISABLED)
        self.remove_all_btn.configure(state=tk.DISABLED)
        self._inv_equip_btn.pack_forget()
        self.inventory_detail_title.configure(text="No items")
        self._set_inventory_detail_text("No inventory items available.")

    def _select_inv_list_item(self, display_name: str):
        """Programmatically select an item in the inventory SectionedListbox."""
        lb = self.inv_list.listbox
        for i in range(lb.size()):
            if lb.get(i) == display_name:
                lb.selection_clear(0, tk.END)
                lb.selection_set(i)
                lb.see(i)
                return

    def _on_inv_list_select(self, item_name: str):
        """Handle selection in the inventory SectionedListbox."""
        entry = self._inv_list_entries.get(item_name)
        if not entry:
            return
        self._on_inventory_select_entry(entry)

    def _on_inv_sub_select(self, parent_item: str, sub_item: str):
        """Handle sub-item selection (e.g. items inside a pack)."""
        # sub_item text comes with the SUB_ITEM_PREFIX stripped by SectionedListbox
        # Try to match against our entries
        entry = self._inv_list_entries.get(sub_item)
        if not entry:
            # Try stripping leading whitespace/prefix
            clean = sub_item.strip().lstrip("- ")
            entry = self._inv_list_entries.get(clean)
        if entry:
            self._on_inventory_select_entry(entry)

    def _toggle_equip_selected(self):
        """Toggle equip on the currently selected inventory item."""
        if not self._selected_inventory_name:
            return
        # Find the entry by name
        entry = None
        for e in self._inv_list_entries.values():
            if e.get("name") == self._selected_inventory_name:
                entry = e
                break
        if not entry or not entry.get("equippable"):
            return

        key = entry["key"]
        cat = entry["category"]
        currently_equipped = entry.get("equipped", False)
        new_state = not currently_equipped

        if cat == "Weapons":
            equipped = list(self.character.equipped_weapons or [])
            if new_state:
                if not self._has_weapon_proficiency(key):
                    AlertDialog(
                        self.winfo_toplevel(),
                        "Weapon Proficiency",
                        f"You are not proficient with {key.title()}. "
                        "You can still equip it, but your proficiency bonus "
                        "will not be added to attack rolls.",
                    )
                if key not in equipped:
                    equipped.append(key)
            else:
                equipped = [w for w in equipped if w != key]
            self.character.equipped_weapons = sorted(equipped)

        elif cat == "Armor":
            equipped = list(self.character.equipped_armor or [])
            if new_state:
                ok, reason = self._can_equip_armor(key)
                if not ok:
                    AlertDialog(
                        self.winfo_toplevel(),
                        "Armor Training Required",
                        reason,
                    )
                    return
                if key != "shield":
                    equipped = [a for a in equipped if a == "shield"]
                if key not in equipped:
                    equipped.append(key)
            else:
                equipped = [a for a in equipped if a != key]
            self.character.equipped_armor = self._normalize_equipped_armor(
                set(equipped)
            )

        self._on_sheet_changed()
        self._refresh_inventory_split_items()

    def _on_inventory_select_entry(self, entry: dict):
        self._selected_inventory_name = entry.get("name", "")
        qty = int(entry.get("qty", 1) or 1)
        self.remove_one_btn.configure(state=tk.NORMAL)
        self.remove_all_btn.configure(state=tk.DISABLED if qty <= 1 else tk.NORMAL)
        if entry.get("equippable"):
            btn_text = "Unequip" if entry.get("equipped") else "Equip"
            self._inv_equip_btn.configure(state=tk.NORMAL, text=btn_text)
            self._inv_equip_btn.pack(
                side=tk.LEFT, padx=(0, 6), before=self.remove_one_btn
            )
        else:
            self._inv_equip_btn.pack_forget()
        self._show_inventory_details(entry)

    def _find_item_record(self, entry: dict) -> dict | None:
        key = entry.get("key", "")
        for ent in getattr(self.character, "custom_inventory", []) or []:
            if normalize_item_key(ent.get("name", "")) != key:
                continue
            item_id = str(ent.get("item_id", ""))
            if (
                item_id
                and self.data
                and item_id in getattr(self.data, "items_by_id", {})
            ):
                return self.data.items_by_id[item_id]

        raw_name = str(entry.get("name", "")).strip()
        variants = {key, normalize_item_key(raw_name)}

        no_paren = re.sub(r"\s*\([^)]*\)", "", raw_name).strip()
        if no_paren:
            variants.add(normalize_item_key(no_paren))

        no_comma = raw_name.replace(",", " ")
        if no_comma:
            variants.add(normalize_item_key(no_comma))

        for var in list(variants):
            if var.endswith("s") and len(var) > 3:
                variants.add(var[:-1])

        for var in variants:
            if var in self._item_by_norm_name:
                return self._item_by_norm_name[var]

        for var in sorted(variants, key=len, reverse=True):
            if len(var) < 4:
                continue
            for item_key, item in self._item_by_norm_name.items():
                if var in item_key or item_key in var:
                    return item

        return None

    def _show_inventory_details(self, entry: dict):
        self.inventory_detail_title.configure(text=entry.get("name", "Item"))
        record = self._find_item_record(entry)

        lines = []
        if entry.get("is_subitem"):
            lines.append(f"Part of: {entry.get('parent_name', 'Unknown')}")
        else:
            lines.append(f"Category: {entry.get('category', 'Unknown')}")
            lines.append(f"Quantity: {entry.get('qty', 1)}")
        if entry.get("equippable"):
            lines.append(f"Equipped: {'Yes' if entry.get('equipped') else 'No'}")
        if record:
            item_type = str(record.get("type", "")).strip() or "Item"
            lines.append(f"Type: {item_type}")
            if record.get("category") == "Magic Items":
                lines.append(f"Rarity: {record.get('rarity', 'Unknown')}")
                attune_raw = record.get("description", "")
                if attune_raw.startswith("Attuned:"):
                    attune_val = attune_raw.split(":", 1)[1].strip()
                    if attune_val and attune_val != "-":
                        lines.append("Attunement: Required")
                    else:
                        lines.append("Attunement: Not required")
            cost_cp = int(record.get("cost_cp", 0))
            if cost_cp > 0:
                lines.append(f"Cost: {format_coins(cost_cp, compact=True)}")
            else:
                lines.append("Cost: Varies/Unavailable")
            lines.append("")
            desc = record.get("full_description") or record.get("description") or ""
            desc = desc.strip()
            cat = str(record.get("category", "")).lower()
            if desc and cat in ("weapons", "armor"):
                for part in desc.split(";"):
                    part = part.strip()
                    if part:
                        lines.append(part)
            else:
                lines.append(
                    desc.replace("; Function:", "\nFunction:")
                    if desc
                    else "No description available."
                )
            sub = record.get("sub_items") or []
            if sub:
                lines.append("")
                lines.append("Contains:")
                lines.extend([f"- {s}" for s in sub])
        else:
            weapon_meta = WEAPON_DATA.get(entry.get("key", ""), {})
            container = _container_contents(entry.get("name", ""))
            lines.append("")
            if weapon_meta:
                dmg = weapon_meta.get("damage", "-")
                props = ", ".join(weapon_meta.get("properties", []) or []) or "None"
                mastery = weapon_meta.get("mastery") or "-"
                lines.append(f"Damage: {dmg}")
                lines.append(f"Properties: {props}")
                lines.append(f"Mastery: {mastery}")
            elif container:
                _, contents = container
                lines.append("Contains:")
                lines.extend([f"- {c}" for c in contents])
            else:
                lines.append(
                    "No description available for this item in the current data set."
                )

        self._set_inventory_detail_text("\n".join(lines))

    def _set_inventory_detail_text(self, text: str):
        self.inventory_detail_text.configure(state=tk.NORMAL)
        self.inventory_detail_text.delete("1.0", tk.END)
        self.inventory_detail_text.insert("1.0", text)
        self.inventory_detail_text.configure(state=tk.DISABLED)

    def _normalize_equipped_armor(self, keys: set[str]) -> list[str]:
        has_shield = "shield" in keys
        body = sorted(k for k in keys if k != "shield")
        out = []
        if has_shield:
            out.append("shield")
        out.extend(body[:1])
        return out

    def _remove_one_selected_item(self):
        self._remove_selected_item_qty(remove_all=False)

    def _remove_all_selected_item(self):
        self._remove_selected_item_qty(remove_all=True)

    def _remove_selected_item_qty(self, remove_all: bool):
        if not self._selected_inventory_name:
            return
        entry = None
        for e in self._inv_list_entries.values():
            if e.get("name") == self._selected_inventory_name:
                entry = e
                break
        if not entry:
            return
        qty = max(1, int(entry.get("qty", 1) or 1)) if remove_all else 1

        ok, msg = remove_item(self.character, entry.get("name", ""), qty=qty)
        if not ok:
            AlertDialog(self.winfo_toplevel(), "Remove Item", msg)
            return

        weapon_counts, armor_counts, _ = self._effective_inventory_pools()
        self.character.equipped_weapons = [
            w for w in (self.character.equipped_weapons or []) if w in weapon_counts
        ]
        self.character.equipped_armor = self._normalize_equipped_armor(
            {a for a in (self.character.equipped_armor or []) if a in armor_counts}
        )

        self._on_sheet_changed()
        self._view_dirty[_INVENTORY] = True
        self._show_view(_INVENTORY)

    # ================================================================
    # State management
    # ================================================================

    def _on_sheet_changed(self):
        if self.save_path:
            save_character(
                self.character, characters_dir(), existing_filename=self.save_path
            )
        # Mark all views dirty except current
        for key in self._view_dirty:
            if key != self._current_view:
                self._view_dirty[key] = True
        self._refresh_sidebar_action_states()

    def _refresh_sidebar_action_states(self):
        """Update rest button enabled/disabled states in the sidebar."""
        c = self.character
        short_btn = self.sidebar.get_action_button("short_rest")
        long_btn = self.sidebar.get_action_button("long_rest")
        if short_btn:
            short_btn.configure(state=tk.NORMAL if can_short_rest(c) else tk.DISABLED)
        if long_btn:
            long_btn.configure(state=tk.NORMAL if can_long_rest(c) else tk.DISABLED)

    def _mark_all_dirty(self):
        for key in self._view_dirty:
            self._view_dirty[key] = True

    # ================================================================
    # Navigation and actions
    # ================================================================

    def _on_back(self):
        self._save_biography_fields_to_character()
        self.app.show_archive()

    def _on_edit(self):
        self._save_biography_fields_to_character()
        self.app.show_wizard(self.character, self.save_path)

    def _on_add_inventory(self):
        AddInventoryDialog(
            self,
            self.character,
            self.data,
            on_changed=lambda: (
                self._on_sheet_changed(),
                self._mark_all_dirty(),
                self._show_view(self._current_view),
            ),
        )

    def _on_short_rest(self):
        RestDialog(
            self,
            self.character,
            self.data,
            rest_type="short",
            on_changed=lambda: (
                self._on_sheet_changed(),
                self._mark_all_dirty(),
                self._show_view(self._current_view),
            ),
        )

    def _on_long_rest(self):
        RestDialog(
            self,
            self.character,
            self.data,
            rest_type="long",
            on_changed=lambda: (
                self._on_sheet_changed(),
                self._mark_all_dirty(),
                self._show_view(self._current_view),
            ),
        )

    def _on_level_up(self):
        from gui.level_up_wizard import LevelUpWizard

        def on_complete():
            save_character(
                self.character, characters_dir(), existing_filename=self.save_path
            )
            self.app.show_viewer(self.character, self.save_path)

        LevelUpWizard(self, self.character, self.data, on_complete=on_complete)

    # ── Exports ──

    def _export_json(self):
        from models.character_store import character_to_save_dict
        import json

        self._save_biography_fields_to_character()

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
        try:
            from export.pdf_export import export_pdf
        except ImportError as e:
            AlertDialog(
                self.winfo_toplevel(),
                "Export Error",
                f"PDF export is not available:\n{e}",
            )
            return

        self._save_biography_fields_to_character()

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"{self.character.name}.pdf",
        )
        if path:
            try:
                export_pdf(self.character, path, game_data=self.data)
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
