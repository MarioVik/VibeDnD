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
    CardFrame,
    GradientHeader,
    PillBadge,
)
from gui.sidebar import Sidebar
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
    {"key": _COMBAT, "text": "Combat", "icon": "\u2694"},
    {"key": _SPELLBOOK, "text": "Spellbook", "icon": "\u2728"},
    {"key": _INVENTORY, "text": "Inventory", "icon": "\u1F4E6"},
    {"key": _FEATURES, "text": "Features", "icon": "\u2605"},
    {"key": _BACKSTORY, "text": "Backstory", "icon": "\u270E"},
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

        bottom_buttons = [
            {"text": "Export PDF", "command": self._export_pdf},
            {"text": "Export JSON", "command": self._export_json},
            {"text": "Respec Character", "command": self._on_edit},
            {"text": "\u25c0  Back to Menu", "command": self._on_back},
        ]

        self.sidebar = Sidebar(
            self,
            nav_items=nav_items,
            on_navigate=self._on_navigate,
            bottom_buttons=bottom_buttons,
            show_character_info=True,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # Set character info in sidebar
        summary = self.character.summary_text()
        self.sidebar.set_character_info(
            name=self.character.name or "Unnamed",
            summary=summary,
            image_data=getattr(self.character, "biography_image_data", "") or None,
            image_format=getattr(self.character, "biography_image_format", "png"),
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
        self.sidebar.set_active(_DASHBOARD)
        self._show_view(_DASHBOARD)

    def _on_navigate(self, key: str):
        self._show_view(key)

    def _show_view(self, key: str):
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
        for w in frame.winfo_children():
            w.destroy()
        self._view_built[key] = False
        self._build_view(key)
        self._view_built[key] = True

    def _character_has_spells(self) -> bool:
        return bool(self.character.selected_cantrips or self.character.selected_spells)

    # ================================================================
    # DASHBOARD VIEW
    # ================================================================

    def _build_dashboard(self):
        parent = self._views[_DASHBOARD]
        scroll = ScrollableFrame(parent)
        scroll.pack(fill=tk.BOTH, expand=True)
        inner = scroll.inner

        c = self.character

        # ── Hero section (gradient) ──
        hero = GradientHeader(inner, min_height=100)
        hero.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        hero_inner = hero.inner

        _hero_bg = COLORS["bg_hero"]

        # Name and level badge row
        name_frame = tk.Frame(hero_inner, bg=_hero_bg)
        name_frame.pack(fill=tk.X, padx=SPACING["card_pad"], pady=(SPACING["xl"], 0))

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
        summary_frame.pack(fill=tk.X, padx=SPACING["card_pad"], pady=(4, SPACING["xl"]))

        tk.Label(
            summary_frame,
            text=c.summary_text(),
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=_hero_bg,
        ).pack(anchor="w")

        if c.background_name:
            tk.Label(
                summary_frame,
                text=f"Background: {c.background_name}",
                font=FONTS["label_upper"],
                fg=COLORS["fg_dim"],
                bg=_hero_bg,
            ).pack(anchor="w")

        # HP and AC row
        hp_ac = tk.Frame(inner, bg=COLORS["bg"])
        hp_ac.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))

        # AC card (CardFrame)
        ac_cf = CardFrame(hp_ac, pad=SPACING["card_pad"])
        ac_cf.pack(side=tk.LEFT, fill=tk.Y, padx=(0, SPACING["card_gap"]))
        tk.Label(
            ac_cf.inner,
            text="ARMOR CLASS",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack()
        tk.Label(
            ac_cf.inner,
            text=str(c.armor_class),
            font=FONTS["stat_large"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack()

        # HP card (CardFrame with accent left border)
        hp_cf = CardFrame(hp_ac, accent_left=True, pad=SPACING["card_pad"])
        hp_cf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        hp_top = tk.Frame(hp_cf.inner, bg=COLORS["bg_surface"])
        hp_top.pack(fill=tk.X)
        tk.Label(
            hp_top,
            text="HIT POINTS",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(side=tk.LEFT)

        hp_val = tk.Frame(hp_cf.inner, bg=COLORS["bg_surface"])
        hp_val.pack(fill=tk.X, pady=(4, 0))
        tk.Label(
            hp_val,
            text=str(c.hit_points),
            font=FONTS["stat_large"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(side=tk.LEFT)
        tk.Label(
            hp_val,
            text=f"/ {c.hit_points}",
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(side=tk.LEFT, padx=(4, 0))

        hp_bar = HPBar(hp_cf.inner, width=300, height=6)
        hp_bar.pack(fill=tk.X, pady=(8, 0))
        hp_bar.set_hp(c.hit_points, c.hit_points)

        # ── Ability Scores ──
        SectionHeader(inner, text="Ability Scores").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        ab_row = tk.Frame(inner, bg=COLORS["bg"])
        ab_row.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        ab_row.columnconfigure(list(range(6)), weight=1)

        saving_throws = (c.character_class or {}).get("saving_throws", [])
        saving_throws_lower = [s.lower() for s in saving_throws]

        for i, ability_name in enumerate(
            ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
        ):
            total = c.ability_scores.total(ability_name)
            mod_str = c.ability_scores.modifier_str(ability_name)
            is_save_prof = ability_name.lower() in saving_throws_lower

            card = StatCard(
                ab_row,
                label=ability_name[:3],
                value=str(total),
                modifier=mod_str,
                highlight=is_save_prof,
            )
            card.grid(row=0, column=i, padx=3, sticky="nsew")

            # Add save info below modifier
            save_mod = c.ability_scores.modifier(ability_name)
            if is_save_prof:
                save_mod += c.proficiency_bonus
            save_str = f"+{save_mod}" if save_mod >= 0 else str(save_mod)
            save_prefix = "\u2713 " if is_save_prof else ""

            save_lbl = tk.Label(
                card,
                text=f"{save_prefix}{save_str} SAVE",
                font=FONTS["label_tiny"],
                fg=COLORS["accent_text"] if is_save_prof else COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            )
            save_lbl.pack(pady=(4, 0))

        # ── Secondary vitals ──
        vitals_row = tk.Frame(inner, bg=COLORS["bg"])
        vitals_row.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        vitals_row.columnconfigure(list(range(4)), weight=1)

        vitals = [
            ("Proficiency", f"+{c.proficiency_bonus}"),
            ("Initiative", f"+{c.initiative}" if c.initiative >= 0 else str(c.initiative)),
            ("Speed", str(c.speed), "ft"),
            ("Hit Dice", str(c.level), f"d{(c.character_class or {}).get('hit_die', 8)}"),
        ]

        for i, v in enumerate(vitals):
            label = v[0]
            value = v[1]
            suffix = v[2] if len(v) > 2 else ""
            sc = StatCard(vitals_row, label=label, value=value, suffix=suffix)
            sc.grid(row=0, column=i, padx=3, sticky="nsew")

        # ── Skills ──
        SectionHeader(inner, text="Skills").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        skills_card = CardFrame(inner, pad=SPACING["lg"])
        skills_card.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        skills_frame = skills_card.inner
        skills_frame.columnconfigure(0, weight=1)
        skills_frame.columnconfigure(1, weight=1)

        all_profs = c.all_skill_proficiencies
        all_expertise = getattr(c, "all_skill_expertise", set())

        for idx, skill_enum in enumerate(ALL_SKILLS):
            skill_display = skill_enum.display_name
            ability = skill_enum.ability
            col = idx % 2
            row_idx = idx // 2

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

            # Proficiency indicator
            indicator = "\u25cf" if is_prof else "\u25cb"
            if is_expert:
                indicator = "\u25c9"
            fg_color = COLORS["accent_text"] if is_prof else COLORS["fg_dim"]

            tk.Label(
                skill_row,
                text=indicator,
                font=FONTS["body_small"],
                fg=fg_color,
                bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT, padx=(0, 4))

            tk.Label(
                skill_row,
                text=skill_display.upper(),
                font=FONTS["label_upper_bold"] if is_prof else FONTS["label_upper"],
                fg=fg_color,
                bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT)

            tk.Label(
                skill_row,
                text=f"({ability.value[:3].upper()})",
                font=FONTS["label_tiny"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT, padx=(4, 0))

            mod_val = c.skill_modifier(skill_display)
            mod_text = f"+{mod_val}" if mod_val >= 0 else str(mod_val)
            tk.Label(
                skill_row,
                text=mod_text,
                font=FONTS["heading_serif_sm"],
                fg=fg_color,
                bg=COLORS["bg_surface"],
            ).pack(side=tk.RIGHT)

        # ── Senses ──
        SectionHeader(inner, text="Senses").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        senses_card = CardFrame(inner, pad=SPACING["lg"])
        senses_card.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        senses_frame = senses_card.inner

        wis_mod = c.ability_scores.modifier("Wisdom")
        int_mod = c.ability_scores.modifier("Intelligence")
        perception_prof = "Perception" in all_profs
        insight_prof = "Insight" in all_profs
        investigation_prof = "Investigation" in all_profs

        senses = [
            ("Passive Perception", 10 + wis_mod + (c.proficiency_bonus if perception_prof else 0)),
            ("Passive Insight", 10 + wis_mod + (c.proficiency_bonus if insight_prof else 0)),
            ("Passive Investigation", 10 + int_mod + (c.proficiency_bonus if investigation_prof else 0)),
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

        # ── Proficiencies ──
        SectionHeader(inner, text="Proficiencies").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        prof_card = CardFrame(inner, pad=SPACING["lg"])
        prof_card.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        prof_frame = prof_card.inner

        cls = c.character_class or {}
        weapon_profs = cls.get("weapon_proficiencies", [])
        armor_profs = cls.get("armor_proficiencies", [])

        if weapon_profs or armor_profs:
            chip_frame = tk.Frame(prof_frame, bg=COLORS["bg_surface"])
            chip_frame.pack(fill=tk.X, anchor="w")

            for p in weapon_profs + armor_profs:
                Chip(chip_frame, text=p, style="gold").pack(
                    side=tk.LEFT, padx=(0, 4), pady=2
                )

        # Languages
        species = c.species or {}
        languages = []
        for feat in species.get("features", []):
            if "language" in feat.get("name", "").lower():
                desc = feat.get("description", "")
                languages.append(desc if desc else feat.get("name", ""))
        if languages:
            lang_frame = tk.Frame(prof_frame, bg=COLORS["bg_surface"])
            lang_frame.pack(fill=tk.X, anchor="w", pady=(8, 0))
            for lang in languages:
                for l_part in lang.split(","):
                    l_part = l_part.strip()
                    if l_part:
                        Chip(lang_frame, text=l_part, style="default").pack(
                            side=tk.LEFT, padx=(0, 4), pady=2
                        )

        # ── Action buttons ──
        action_frame = tk.Frame(inner, bg=COLORS["bg"])
        action_frame.pack(fill=tk.X, pady=(8, 16))

        if c.level < 20:
            ttk.Button(
                action_frame,
                text="Level Up",
                style="Accent.TButton",
                command=self._on_level_up,
            ).pack(side=tk.LEFT, padx=(0, 8))

        short_state = tk.NORMAL if can_short_rest(c) else tk.DISABLED
        long_state = tk.NORMAL if can_long_rest(c) else tk.DISABLED

        ttk.Button(
            action_frame,
            text="Short Rest",
            command=self._on_short_rest,
            state=short_state,
        ).pack(side=tk.LEFT, padx=(0, 4))

        ttk.Button(
            action_frame,
            text="Long Rest",
            command=self._on_long_rest,
            state=long_state,
        ).pack(side=tk.LEFT, padx=(0, 4))

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
            text="Combat & Actions",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xl"], 4))

        info_text = f"Initiative +{c.initiative}  \u2022  Speed {c.speed}ft  \u2022  AC {c.armor_class}  \u2022  HP {c.hit_points}"
        tk.Label(
            combat_hero.inner,
            text=info_text,
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(0, SPACING["xl"]))

        # ── Weapon Attacks ──
        SectionHeader(inner, text="Weapon Attacks").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        attacks_card = CardFrame(inner, pad=SPACING["md"])
        attacks_card.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        attacks_frame = attacks_card.inner

        actions = build_standard_actions(
            c,
            spells_by_name=self._spell_index,
            equipped_weapon_keys=set(c.equipped_weapons or []),
        )

        if actions:
            for action in actions:
                row = tk.Frame(attacks_frame, bg=COLORS["bg_container"], padx=12, pady=10)
                row.pack(fill=tk.X, pady=3)

                # Name and properties
                name_col = tk.Frame(row, bg=COLORS["bg_container"])
                name_col.pack(side=tk.LEFT, fill=tk.X, expand=True)

                tk.Label(
                    name_col,
                    text=action.get("name", "Unknown"),
                    font=FONTS["heading_serif_sm"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_container"],
                ).pack(anchor="w")

                props = action.get("properties", "")
                if props:
                    tk.Label(
                        name_col,
                        text=props.upper(),
                        font=FONTS["label_tiny"],
                        fg=COLORS["fg_dim"],
                        bg=COLORS["bg_container"],
                    ).pack(anchor="w")

                # To Hit
                attack_bonus = action.get("attack_bonus", 0)
                hit_str = f"+{attack_bonus}" if attack_bonus >= 0 else str(attack_bonus)

                hit_col = tk.Frame(row, bg=COLORS["bg_container"])
                hit_col.pack(side=tk.RIGHT, padx=(16, 0))

                tk.Label(
                    hit_col,
                    text="TO HIT",
                    font=FONTS["label_tiny"],
                    fg=COLORS["fg_dim"],
                    bg=COLORS["bg_container"],
                ).pack()
                tk.Label(
                    hit_col,
                    text=hit_str,
                    font=FONTS["heading_serif_sm"],
                    fg=COLORS["accent_text"],
                    bg=COLORS["bg_container"],
                ).pack()

                # Damage
                damage = action.get("damage", "")
                dmg_type = action.get("damage_type", "")

                dmg_col = tk.Frame(row, bg=COLORS["bg_container"])
                dmg_col.pack(side=tk.RIGHT, padx=(16, 0))

                tk.Label(
                    dmg_col,
                    text="DAMAGE",
                    font=FONTS["label_tiny"],
                    fg=COLORS["fg_dim"],
                    bg=COLORS["bg_container"],
                ).pack()
                tk.Label(
                    dmg_col,
                    text=f"{damage} {dmg_type}",
                    font=FONTS["heading_serif_sm"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_container"],
                ).pack()
        else:
            tk.Label(
                attacks_frame,
                text="No weapon attacks available.",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(pady=8)

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

            card = CardFrame(actions_grid, bg=COLORS["bg_container"],
                             border_color=COLORS["border_subtle"], pad=SPACING["lg"])
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

        # ── Spell slots (if caster) ──
        if self._character_has_spells():
            SectionHeader(inner, text="Spell Slots").pack(
                fill=tk.X, pady=(SPACING["sm"], SPACING["sm"])
            )
            self._build_spell_slot_display(inner)

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
        slots_card.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        slots_frame = slots_card.inner

        for slot_level, count in sorted(spell_slots.items(), key=lambda x: x[0]):
            if count <= 0:
                continue
            row = tk.Frame(slots_frame, bg=COLORS["bg_surface"])
            row.pack(fill=tk.X, pady=3)

            tk.Label(
                row,
                text=f"LEVEL {slot_level}".replace("st", "").replace("nd", "").replace("rd", "").replace("th", "").upper(),
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
                    dots_frame, width=12, height=12,
                    bg=COLORS["bg_surface"], highlightthickness=0,
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
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xl"], SPACING["xl"]))

        c = self.character
        cls = c.character_class or {}

        # Spellcasting stats header
        cast_ability = cls.get("spellcasting_ability")
        if cast_ability:
            stats_frame = tk.Frame(wrapper, bg=COLORS["bg"])
            stats_frame.pack(fill=tk.X, pady=(SPACING["sm"], SPACING["section_gap"]))

            spell_mod = c.ability_scores.modifier(cast_ability)
            attack_bonus = spell_mod + c.proficiency_bonus
            save_dc = 8 + spell_mod + c.proficiency_bonus
            ability_score = c.ability_scores.total(cast_ability)

            for label, value, sub in [
                ("Spell Attack", f"+{attack_bonus}", f"PROF + {cast_ability[:3].upper()}"),
                ("Save DC", str(save_dc), "BASE 8"),
                ("Spell Ability", cast_ability[:3].upper(), f"{ability_score} (+{spell_mod})"),
            ]:
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

        # Spell list (reuse existing pattern with split view)
        spell_area = tk.Frame(wrapper, bg=COLORS["bg"])
        spell_area.pack(fill=tk.BOTH, expand=True)
        spell_area.columnconfigure(0, weight=0)
        spell_area.columnconfigure(1, weight=1)
        spell_area.rowconfigure(0, weight=1)

        # Left: spell list
        left = tk.Frame(spell_area, bg=COLORS["bg_surface"], width=280)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_propagate(False)

        tk.Label(
            left,
            text="Known Spells",
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
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xl"], SPACING["xl"]))

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
                    AlertDialog(self.winfo_toplevel(), "Wealth", "Please enter whole numbers only.")
                    _refresh_coin_display()
                    return False
                parsed[coin_key] = int(raw)
            new_total_cp = parsed["gp"] * 100 + parsed["sp"] * 10 + parsed["cp"]
            self.character.wealth_adjust_cp = int(new_total_cp - base_wealth_cp(self.character))
            _refresh_coin_display()
            self._on_sheet_changed()
            return True

        def _adjust_wealth(delta_cp: int):
            if not _commit_coins():
                return
            cur = current_wealth_cp(self.character)
            if delta_cp < 0 and cur < abs(delta_cp):
                AlertDialog(self.winfo_toplevel(), "Wealth", "You do not have enough wealth for that reduction.")
                return
            self.character.wealth_adjust_cp = int(getattr(self.character, "wealth_adjust_cp", 0)) + int(delta_cp)
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
                bg=COLORS["bg_container"],
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

            btn_frame = tk.Frame(val_row, bg=COLORS["bg_surface"])
            btn_frame.pack(side=tk.LEFT, padx=(6, 0))
            ttk.Button(
                btn_frame, text="+", width=2,
                command=lambda d=unit_cp: _adjust_wealth(d),
            ).pack(side=tk.LEFT, padx=(0, 2))
            ttk.Button(
                btn_frame, text="\u2212", width=2,
                command=lambda d=unit_cp: _adjust_wealth(-d),
            ).pack(side=tk.LEFT)

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
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xl"], SPACING["xl"]))

        # ── Species Traits ──
        if c.species and c.species.get("traits"):
            SectionHeader(inner, text=f"{c.species_name} Traits").pack(
                fill=tk.X, pady=(0, SPACING["sm"])
            )
            traits_grid = tk.Frame(inner, bg=COLORS["bg"])
            traits_grid.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
            traits_grid.columnconfigure(0, weight=1)
            traits_grid.columnconfigure(1, weight=1)
            for i, trait in enumerate(c.species["traits"]):
                card = CardFrame(traits_grid, bg=COLORS["bg_container"],
                                 border_color=COLORS["border_subtle"], pad=SPACING["lg"])
                card.grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky="nsew")
                tk.Label(
                    card.inner,
                    text=trait["name"],
                    font=FONTS["heading_serif_sm"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_container"],
                ).pack(anchor="w")
                if trait.get("description"):
                    WrappingLabel(
                        card.inner,
                        text=trait["description"],
                        font=FONTS["body_small"],
                        foreground=COLORS["fg_dim"],
                        background=COLORS["bg_container"],
                    ).pack(fill=tk.X, pady=(6, 0))

        # ── Class Features ──
        if c.character_class and c.class_levels:
            feat_title = "Class Features" if c.is_multiclass else f"{c.class_name} Features"
            SectionHeader(inner, text=feat_title).pack(
                fill=tk.X, pady=(0, SPACING["sm"])
            )
            features_grid = tk.Frame(inner, bg=COLORS["bg"])
            features_grid.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
            features_grid.columnconfigure(0, weight=1)
            features_grid.columnconfigure(1, weight=1)
            card_idx = 0
            for cl in c.class_levels:
                level_data = self.data.get_level_data(cl.class_slug, cl.class_level) if self.data else None
                feature_details = []
                if level_data:
                    feature_details = [
                        f for f in level_data.get("feature_details", [])
                        if isinstance(f, dict) and f.get("name") not in ("-", "Ability Score Improvement")
                    ]
                    if not feature_details:
                        for name in level_data.get("features", []):
                            if name not in ("-", "Ability Score Improvement"):
                                feature_details.append({"name": name, "description": ""})
                extra = []
                if cl.feat_choice:
                    asi_desc = ""
                    if cl.asi_increases:
                        asi_desc = ", ".join(f"{a} +{v}" for a, v in cl.asi_increases.items())
                    extra.append({"name": f"Feat: {cl.feat_choice}", "description": asi_desc})
                if cl.subclass_slug:
                    extra.append({"name": f"Subclass: {cl.subclass_slug.replace('-', ' ').title()}", "description": ""})
                all_items = feature_details + extra
                if not all_items:
                    continue
                prefix = f"{cl.class_slug.title()} " if c.is_multiclass else ""
                level_label = f"{prefix}Level {cl.class_level}"
                for feat in all_items:
                    card = CardFrame(features_grid, bg=COLORS["bg_container"],
                                     border_color=COLORS["border_subtle"], pad=SPACING["lg"])
                    card.grid(row=card_idx // 2, column=card_idx % 2, padx=4, pady=4, sticky="nsew")
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
                        text=level_label.upper(),
                        bg_color=COLORS["badge_glass_dim"],
                        fg_color=COLORS["gold"],
                    ).pack(side=tk.RIGHT)
                    if feat.get("description"):
                        WrappingLabel(
                            card.inner,
                            text=feat["description"],
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
                    (s for s in subclasses_for_class if s.get("slug") == c.current_subclass), None
                )
            if subclass_data:
                desc = (subclass_data.get("description") or "").strip()
                if desc:
                    intro = re.split(r"\bLevel\s+\d+\s*:", desc, maxsplit=1)[0].strip()
                    if intro:
                        WrappingLabel(
                            inner, text=intro, font=FONTS["body_small"],
                            foreground=COLORS["fg_dim"],
                        ).pack(fill=tk.X, pady=(0, SPACING["sm"]))
                sub_grid = tk.Frame(inner, bg=COLORS["bg"])
                sub_grid.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
                sub_grid.columnconfigure(0, weight=1)
                sub_grid.columnconfigure(1, weight=1)
                sub_idx = 0
                features_by_level = subclass_data.get("features", {})
                for lvl in sorted(features_by_level.keys(), key=lambda x: int(x) if str(x).isdigit() else 99):
                    try:
                        lvl_int = int(lvl)
                    except (ValueError, TypeError):
                        continue
                    if lvl_int > c.level:
                        continue
                    for feat in features_by_level.get(lvl, []):
                        card = CardFrame(sub_grid, bg=COLORS["bg_container"],
                                         border_color=COLORS["border_subtle"], pad=SPACING["lg"])
                        card.grid(row=sub_idx // 2, column=sub_idx % 2, padx=4, pady=4, sticky="nsew")
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
                            WrappingLabel(
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
            SectionHeader(inner, text="Feats").pack(
                fill=tk.X, pady=(0, SPACING["sm"])
            )
            feats_grid = tk.Frame(inner, bg=COLORS["bg"])
            feats_grid.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
            feats_grid.columnconfigure(0, weight=1)
            feats_grid.columnconfigure(1, weight=1)
            feat_idx = 0
            if c.feat:
                feat_name = (
                    c.background.get("feat", c.feat.get("name", ""))
                    if c.background else c.feat.get("name", "")
                )
                card = CardFrame(feats_grid, bg=COLORS["bg_container"],
                                 border_color=COLORS["border_subtle"], pad=SPACING["lg"])
                card.grid(row=feat_idx // 2, column=feat_idx % 2, padx=4, pady=4, sticky="nsew")
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
                benefits = [f"{b['name']}: {b.get('description', '')}" for b in c.feat.get("benefits", [])]
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
                card = CardFrame(feats_grid, bg=COLORS["bg_container"],
                                 border_color=COLORS["border_subtle"], pad=SPACING["lg"])
                card.grid(row=feat_idx // 2, column=feat_idx % 2, padx=4, pady=4, sticky="nsew")
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
                benefits = [f"{b['name']}: {b.get('description', '')}" for b in c.species_origin_feat.get("benefits", [])]
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
        back_hero.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, SPACING["section_gap"]))
        tk.Label(
            back_hero.inner,
            text="Biography",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xl"], SPACING["xl"]))

        # 2x2 grid layout: 4 even tiles
        inner.columnconfigure(0, weight=1)
        inner.columnconfigure(1, weight=1)
        inner.rowconfigure(1, weight=1)
        inner.rowconfigure(2, weight=1)

        # Top-left: Backstory
        tl = tk.Frame(inner, bg=COLORS["bg"])
        tl.grid(row=1, column=0, sticky="nsew", padx=(SPACING["lg"], SPACING["sm"]), pady=(0, SPACING["sm"]))
        tl.columnconfigure(0, weight=1)
        tl.rowconfigure(1, weight=1)
        SectionHeader(tl, text="Character Backstory").pack(fill=tk.X, pady=(0, 4))
        self.bio_backstory_text = self._make_bio_textbox(tl)
        self.bio_backstory_text.pack(fill=tk.BOTH, expand=True)

        # Top-right: Personality
        tr = tk.Frame(inner, bg=COLORS["bg"])
        tr.grid(row=1, column=1, sticky="nsew", padx=(SPACING["sm"], 16), pady=(0, SPACING["sm"]))
        tr.columnconfigure(0, weight=1)
        tr.rowconfigure(1, weight=1)
        SectionHeader(tr, text="Personality").pack(fill=tk.X, pady=(0, 4))
        self.bio_personality_text = self._make_bio_textbox(tr)
        self.bio_personality_text.pack(fill=tk.BOTH, expand=True)

        # Bottom-left: Portrait
        right = tk.Frame(inner, bg=COLORS["bg_surface"])
        right.grid(row=2, column=0, sticky="nsew", padx=(SPACING["lg"], SPACING["sm"]), pady=(SPACING["sm"], SPACING["lg"]))
        right.columnconfigure(0, weight=1)
        self._bio_portrait_frame = right

        tk.Label(
            right,
            text="Portrait",
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", padx=12, pady=(12, 8))

        self.bio_image_canvas = tk.Canvas(
            right,
            width=260,
            height=100,
            bg=COLORS["bg_container"],
            highlightthickness=0,
            relief=tk.FLAT,
        )
        self.bio_image_canvas.pack(padx=12, pady=(0, 8))
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
        right.bind("<Configure>", self._on_bio_portrait_frame_configure)

        btns = tk.Frame(right, bg=COLORS["bg_surface"])
        btns.pack(pady=(0, 12))
        ttk.Button(
            btns, text="Choose Image...", command=self._choose_biography_image
        ).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btns, text="Clear Image", command=self._clear_biography_image).pack(
            side=tk.LEFT, padx=(4, 0)
        )

        # Bottom-right: Physical Description
        br = tk.Frame(inner, bg=COLORS["bg"])
        br.grid(row=2, column=1, sticky="nsew", padx=(SPACING["sm"], 16), pady=(SPACING["sm"], SPACING["lg"]))
        br.columnconfigure(0, weight=1)
        br.rowconfigure(1, weight=1)
        SectionHeader(br, text="Physical Description").pack(fill=tk.X, pady=(0, 4))
        self.bio_description_text = self._make_bio_textbox(br)
        self.bio_description_text.pack(fill=tk.BOTH, expand=True)

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
        for p in (self.character.character_class or {}).get("armor_proficiencies", []):
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
        cls = self.character.character_class or {}
        profs = [str(p).lower() for p in cls.get("weapon_proficiencies", [])]
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
        split.columnconfigure(0, weight=0)
        split.columnconfigure(1, weight=1)
        split.rowconfigure(0, weight=1)

        # Left: item list (fixed width, matching spellbook)
        left = tk.Frame(split, bg=COLORS["bg_surface"], width=280)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_propagate(False)

        tk.Label(
            left,
            text="Items",
            font=FONTS["heading_serif_sm"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", padx=8, pady=(8, 4))

        self.inv_list = SectionedListbox(left, on_select=self._on_inv_list_select)
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
        self.inventory_detail_title.grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))

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
        self.inventory_detail_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

        actions = tk.Frame(right, bg=COLORS["bg_surface"])
        actions.grid(row=2, column=0, sticky="e", pady=(0, 8), padx=8)

        self._inv_equip_btn = ttk.Button(
            actions,
            text="Equip",
            command=self._toggle_equip_selected,
            state=tk.DISABLED,
        )
        self._inv_equip_btn.pack(side=tk.LEFT, padx=(0, 6))

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
                    sub_display = f"{clean_sub_name} (x{remaining_sub_qty})" if remaining_sub_qty > 1 else clean_sub_name
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
        self._inv_equip_btn.configure(state=tk.DISABLED)
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
        else:
            self._inv_equip_btn.configure(state=tk.DISABLED, text="Equip")
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

    def _mark_all_dirty(self):
        for key in self._view_dirty:
            self._view_dirty[key] = True

    # ================================================================
    # Navigation and actions
    # ================================================================

    def _on_back(self):
        self._save_biography_fields_to_character()
        self.app.show_home()

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
