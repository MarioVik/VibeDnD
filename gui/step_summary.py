"""Step 11: Dashboard-style character summary (replaces old summary sheet)."""

import tkinter as tk
from tkinter import ttk

from gui.base_step import WizardStep
from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import (
    ScrollableFrame,
    GradientHeader,
    SectionHeader,
    CardFrame,
    StatCard,
    PillBadge,
    Chip,
)
from models.enums import ALL_SKILLS
from models.language_utils import all_languages
from models.level1_class_rules import summarize_level1_class_choices


class SummaryStep(WizardStep):
    tab_title = "Summary"

    def __init__(self, parent_notebook, character, game_data, app=None, save_path=None):
        self.app = app
        self.save_path = save_path
        super().__init__(parent_notebook, character, game_data)

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)

        # Placeholder — rebuilt on each on_enter
        self._scroll = None

    def on_enter(self):
        self._build_dashboard()

    def _build_dashboard(self):
        """Build a read-only Dashboard preview of the character."""
        # Tear down previous content
        if self._scroll:
            self._scroll.destroy()

        self._scroll = ScrollableFrame(self.frame)
        self._scroll.grid(row=0, column=0, sticky="nsew")
        inner = self._scroll.inner

        c = self.character

        # ── Hero header ─────────────────────────────────────────
        hero = GradientHeader(inner, min_height=100)
        hero.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        _hero_bg = COLORS["bg_hero"]

        name_frame = tk.Frame(hero.inner, bg=_hero_bg)
        name_frame.pack(fill=tk.X, padx=SPACING["card_pad"], pady=(SPACING["2xl"], 0))

        tk.Label(
            name_frame,
            text=c.name or "Unnamed",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=_hero_bg,
        ).pack(side=tk.LEFT)

        PillBadge(
            name_frame,
            text=f"LEVEL {c.level}",
            bg_color=COLORS["badge_glass"],
            fg_color=COLORS["gold"],
        ).pack(side=tk.RIGHT, padx=8)

        # Summary line
        summary_frame = tk.Frame(hero.inner, bg=_hero_bg)
        summary_frame.pack(fill=tk.X, padx=SPACING["card_pad"], pady=(4, SPACING["2xl"]))

        _identity_parts = []
        if c.species:
            _identity_parts.append(c.species_name)
        if c.character_class:
            _identity_parts.append(c.class_name)
        _class_line = " ".join(_identity_parts) if _identity_parts else "No selections"
        if c.background_name:
            _class_line += f" - {c.background_name}"

        tk.Label(
            summary_frame,
            text=_class_line,
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=_hero_bg,
        ).pack(anchor="w")

        # ── Sub-hero row: Proficiency, Hit Dice, Saving Throws ──
        sub_hero_row = tk.Frame(inner, bg=COLORS["bg"])
        sub_hero_row.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        sub_hero_row.columnconfigure(0, weight=0)
        sub_hero_row.columnconfigure(1, weight=0)
        sub_hero_row.columnconfigure(2, weight=1)

        # Proficiency box
        prof_frame = tk.Frame(sub_hero_row, bg=COLORS["bg_surface"])
        prof_frame.grid(row=0, column=0, padx=(0, 3), sticky="ns")
        prof_frame.pack_propagate(False)
        prof_frame.grid_propagate(False)

        def _keep_prof_square(event, f=prof_frame):
            if event.height > 1:
                f.configure(width=event.height)
        prof_frame.bind("<Configure>", _keep_prof_square)

        tk.Label(
            prof_frame, text="PROFICIENCY",
            font=FONTS["label_upper_bold"], fg=COLORS["fg_dim"], bg=COLORS["bg_surface"],
        ).pack(side=tk.TOP, pady=(6, 0))
        _prof_center = tk.Frame(prof_frame, bg=COLORS["bg_surface"])
        _prof_center.pack(expand=True)
        tk.Label(
            _prof_center, text=f"+{c.proficiency_bonus}",
            font=FONTS["stat_large"], fg=COLORS["fg"], bg=COLORS["bg_surface"],
        ).pack()
        tk.Frame(_prof_center, bg=COLORS["bg_surface"], height=24).pack()

        # Hit Dice box
        hd_frame = tk.Frame(sub_hero_row, bg=COLORS["bg_surface"])
        hd_frame.grid(row=0, column=1, padx=(3, 3), sticky="ns")
        hd_frame.pack_propagate(False)
        hd_frame.grid_propagate(False)

        def _keep_hd_sized(event, f=hd_frame):
            if event.height > 1:
                f.configure(width=event.height)
        hd_frame.bind("<Configure>", _keep_hd_sized)

        tk.Label(
            hd_frame, text="HIT DICE",
            font=FONTS["label_upper_bold"], fg=COLORS["fg_dim"], bg=COLORS["bg_surface"],
        ).pack(side=tk.TOP, pady=(6, 0))

        _die = (c.character_class or {}).get("hit_die", 8)
        _hd_bg = COLORS["bg_surface"]
        _hd_center = tk.Frame(hd_frame, bg=_hd_bg)
        _hd_center.pack(expand=True)
        tk.Label(
            _hd_center, text=f"{c.level}/{c.level}",
            font=FONTS["stat_large"], fg=COLORS["fg"], bg=_hd_bg,
        ).pack()
        _badge_bg = COLORS["bg_container"]
        _badge = tk.Frame(_hd_center, bg=_badge_bg, padx=8, pady=2)
        _badge.pack(pady=(2, 0))
        tk.Label(
            _badge, text=f"d{_die}",
            font=FONTS["body_bold"], fg=COLORS["fg_dim"], bg=_badge_bg,
        ).pack()

        # Saving Throws box
        saving_throws = (c.character_class or {}).get("saving_throws", [])
        saving_throws_lower = [s.lower() for s in saving_throws]

        saves_cf = CardFrame(sub_hero_row, pad=SPACING["sm"])
        saves_cf.grid(row=0, column=2, padx=(3, 0), sticky="nsew")

        tk.Label(
            saves_cf.inner, text="SAVING THROWS",
            font=FONTS["label_upper_bold"], fg=COLORS["fg_dim"], bg=COLORS["bg_surface"],
        ).pack(anchor="w")

        saves_grid = tk.Frame(saves_cf.inner, bg=COLORS["bg_surface"])
        saves_grid.pack(fill=tk.X, pady=(4, 0))
        saves_grid.columnconfigure(0, weight=1)
        saves_grid.columnconfigure(1, weight=1)

        _save_order = [
            "Strength", "Intelligence",
            "Dexterity", "Wisdom",
            "Constitution", "Charisma",
        ]
        for i, ability_name in enumerate(_save_order):
            col = i % 2
            row = i // 2
            is_prof = ability_name.lower() in saving_throws_lower
            save_mod = c.ability_scores.modifier(ability_name)
            if is_prof:
                save_mod += c.proficiency_bonus
            save_str = f"+{save_mod}" if save_mod >= 0 else str(save_mod)
            indicator = "\u25cf" if is_prof else "\u25cb"
            color = COLORS["accent_text"] if is_prof else COLORS["fg_dim"]

            save_row_f = tk.Frame(saves_grid, bg=COLORS["bg_surface"])
            save_row_f.grid(row=row, column=col, sticky="ew", padx=(0, 12), pady=2)

            tk.Label(
                save_row_f, text=indicator,
                font=FONTS["body"], fg=color, bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT, padx=(0, 4))
            tk.Label(
                save_row_f, text=ability_name[:3].upper(),
                font=FONTS["body"],
                fg=COLORS["fg"] if is_prof else COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT)
            tk.Label(
                save_row_f, text=save_str,
                font=FONTS["heading_serif_sm"], fg=color, bg=COLORS["bg_surface"],
            ).pack(side=tk.RIGHT)

        # ── Ability Scores ──────────────────────────────────────
        SectionHeader(inner, text="Ability Scores").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        ab_row = tk.Frame(inner, bg=COLORS["bg"])
        ab_row.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        ab_row.columnconfigure(list(range(6)), weight=1)

        for i, ability_name in enumerate(
            ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
        ):
            total = c.ability_scores.total(ability_name)
            mod_str = c.ability_scores.modifier_str(ability_name)
            card = StatCard(ab_row, label=ability_name, value=mod_str, modifier=str(total))
            card.grid(row=0, column=i, padx=3, sticky="nsew")

        # ── Skills ──────────────────────────────────────────────
        SectionHeader(
            inner,
            text="Skills",
            right_text="● = proficiency   ◉ = expertise",
        ).pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        skills_card = CardFrame(inner, pad=SPACING["lg"])
        skills_card.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        skills_frame = skills_card.inner
        skills_frame.columnconfigure(0, weight=1)
        skills_frame.columnconfigure(1, weight=1)

        all_profs = c.all_skill_proficiencies
        all_expertise = c.all_skill_expertise

        half = (len(ALL_SKILLS) + 1) // 2
        for idx, skill_enum in enumerate(ALL_SKILLS):
            skill_display = skill_enum.display_name
            ability = skill_enum.ability
            col = 0 if idx < half else 1
            row_idx = idx if col == 0 else idx - half

            skill_row = tk.Frame(skills_frame, bg=COLORS["bg_surface"])
            skill_row.grid(row=row_idx, column=col, sticky="ew", padx=4, pady=3)

            is_prof = skill_display in all_profs
            is_expert = skill_display in all_expertise
            indicator = "\u25c9" if is_expert else ("\u25cf" if is_prof else "\u25cb")
            fg_color = COLORS["accent_text"] if is_prof else COLORS["fg_dim"]

            tk.Label(
                skill_row, text=indicator,
                font=FONTS["body_small"], fg=fg_color, bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT, padx=(0, 4))

            tk.Label(
                skill_row,
                text=skill_display.upper(),
                font=FONTS["label_upper_bold"] if is_prof else FONTS["label_upper"],
                fg=fg_color, bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT)

            tk.Label(
                skill_row,
                text=f"({ability.value[:3].upper()})",
                font=FONTS["label_tiny"],
                fg=COLORS["fg_dim"], bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT, padx=(4, 0))

            mod_val = c.skill_modifier(skill_display)
            mod_text = f"+{mod_val}" if mod_val >= 0 else str(mod_val)
            tk.Label(
                skill_row, text=mod_text,
                font=FONTS["heading_serif_sm"], fg=fg_color, bg=COLORS["bg_surface"],
            ).pack(side=tk.RIGHT)

        # ── Senses & Proficiencies (side-by-side) ───────────────
        senses_prof_row = tk.Frame(inner, bg=COLORS["bg"])
        senses_prof_row.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        senses_prof_row.columnconfigure(0, weight=1, uniform="sp")
        senses_prof_row.columnconfigure(1, weight=1, uniform="sp")

        # Left: Senses
        senses_col = tk.Frame(senses_prof_row, bg=COLORS["bg"])
        senses_col.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["sm"] // 2))

        SectionHeader(senses_col, text="Senses").pack(fill=tk.X, pady=(0, SPACING["sm"]))
        senses_card = CardFrame(senses_col, pad=SPACING["lg"])
        senses_card.pack(fill=tk.BOTH, expand=True)

        senses = [
            ("Passive Perception", 10 + c.skill_modifier("Perception")),
            ("Passive Insight", 10 + c.skill_modifier("Insight")),
            ("Passive Investigation", 10 + c.skill_modifier("Investigation")),
        ]

        for label, value in senses:
            row = tk.Frame(senses_card.inner, bg=COLORS["bg_surface"])
            row.pack(fill=tk.X, pady=2)
            tk.Label(
                row, text=label.upper(),
                font=FONTS["label_upper"], fg=COLORS["fg_dim"], bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT)
            tk.Label(
                row, text=str(value),
                font=FONTS["heading_serif_sm"],
                fg=COLORS["gold"] if label == "Passive Perception" else COLORS["fg"],
                bg=COLORS["bg_surface"],
            ).pack(side=tk.RIGHT)

        # Right: Proficiencies
        prof_col = tk.Frame(senses_prof_row, bg=COLORS["bg"])
        prof_col.grid(row=0, column=1, sticky="nsew", padx=(SPACING["sm"] // 2, 0))

        SectionHeader(prof_col, text="Proficiencies").pack(fill=tk.X, pady=(0, SPACING["sm"]))
        prof_card = CardFrame(prof_col, pad=SPACING["lg"])
        prof_card.pack(fill=tk.BOTH, expand=True)

        weapon_profs = list(getattr(c, "effective_weapon_proficiencies", []))
        armor_profs = list(getattr(c, "effective_armor_proficiencies", []))

        if weapon_profs or armor_profs:
            chip_frame = tk.Frame(prof_card.inner, bg=COLORS["bg_surface"])
            chip_frame.pack(fill=tk.X, anchor="w")
            for p in weapon_profs + armor_profs:
                Chip(chip_frame, text=p, style="gold").pack(
                    side=tk.LEFT, padx=(0, 4), pady=2
                )

        lang_list = all_languages(c)
        if lang_list:
            lang_header = tk.Frame(prof_card.inner, bg=COLORS["bg_surface"])
            lang_header.pack(fill=tk.X, anchor="w", pady=(8, 2))
            tk.Label(
                lang_header, text="LANGUAGES",
                font=FONTS["label_upper"], fg=COLORS["fg_dim"], bg=COLORS["bg_surface"],
            ).pack(anchor="w")
            lang_frame = tk.Frame(prof_card.inner, bg=COLORS["bg_surface"])
            lang_frame.pack(fill=tk.X, anchor="w")
            for lang in lang_list:
                Chip(lang_frame, text=lang, style="default").pack(
                    side=tk.LEFT, padx=(0, 4), pady=2
                )

        class_choice_lines = summarize_level1_class_choices(c)
        if class_choice_lines:
            SectionHeader(inner, text="Class Choices").pack(
                fill=tk.X, pady=(0, SPACING["sm"])
            )
            class_choices_card = CardFrame(inner, pad=SPACING["lg"])
            class_choices_card.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
            for line in class_choice_lines:
                tk.Label(
                    class_choices_card.inner,
                    text=line,
                    font=FONTS["body"],
                    fg=COLORS["fg"],
                    bg=COLORS["bg_surface"],
                    anchor="w",
                    justify=tk.LEFT,
                ).pack(fill=tk.X, pady=2)

        # ── Spells (if caster) ──────────────────────────────────
        if c.is_caster:
            SectionHeader(inner, text="Spells").pack(
                fill=tk.X, pady=(0, SPACING["sm"])
            )
            spells_card = CardFrame(inner, pad=SPACING["lg"])
            spells_card.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))

            cantrips = c.selected_cantrips
            spells = c.selected_spells

            _bg = COLORS["bg_surface"]
            if cantrips:
                tk.Label(
                    spells_card.inner, text="CANTRIPS",
                    font=FONTS["label_upper_bold"], fg=COLORS["fg_dim"], bg=_bg,
                ).pack(anchor="w", pady=(0, 2))
                cantrip_row = tk.Frame(spells_card.inner, bg=_bg)
                cantrip_row.pack(fill=tk.X, anchor="w", pady=(0, SPACING["sm"]))
                for name in cantrips:
                    Chip(cantrip_row, text=name, style="default").pack(
                        side=tk.LEFT, padx=(0, 4), pady=2
                    )

            if spells:
                tk.Label(
                    spells_card.inner, text="1ST-LEVEL SPELLS",
                    font=FONTS["label_upper_bold"], fg=COLORS["fg_dim"], bg=_bg,
                ).pack(anchor="w", pady=(0, 2))
                spell_row = tk.Frame(spells_card.inner, bg=_bg)
                spell_row.pack(fill=tk.X, anchor="w")
                for name in spells:
                    Chip(spell_row, text=name, style="accent").pack(
                        side=tk.LEFT, padx=(0, 4), pady=2
                    )

        # ── Equipment ───────────────────────────────────────────
        self._build_equipment_section(inner, c)

        # ── Feats ───────────────────────────────────────────────
        self._build_feats_section(inner, c)

    def _build_equipment_section(self, inner, c):
        """Render equipment summary."""
        cls = c.character_class
        bg_data = c.background

        class_items = None
        bg_items = None

        if cls:
            choice = c.equipment_choice_class
            for opt in cls.get("starting_equipment", []):
                if opt["option"] == choice:
                    class_items = opt["items"]
                    break

        if bg_data:
            choice = c.equipment_choice_background
            for opt in bg_data.get("equipment", []):
                if opt["option"] == choice:
                    bg_items = opt["items"]
                    break

        if class_items or bg_items:
            SectionHeader(inner, text="Equipment").pack(
                fill=tk.X, pady=(0, SPACING["sm"])
            )
            equip_card = CardFrame(inner, pad=SPACING["lg"])
            equip_card.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
            _bg = COLORS["bg_surface"]

            if class_items:
                tk.Label(
                    equip_card.inner,
                    text=f"FROM {c.class_name.upper()}",
                    font=FONTS["label_upper_bold"], fg=COLORS["fg_dim"], bg=_bg,
                ).pack(anchor="w", pady=(0, 2))
                tk.Label(
                    equip_card.inner,
                    text=class_items,
                    font=FONTS["body"], fg=COLORS["fg"], bg=_bg,
                    wraplength=600, justify=tk.LEFT,
                ).pack(anchor="w", pady=(0, SPACING["sm"]))

            if bg_items:
                tk.Label(
                    equip_card.inner,
                    text=f"FROM {c.background_name.upper()}",
                    font=FONTS["label_upper_bold"], fg=COLORS["fg_dim"], bg=_bg,
                ).pack(anchor="w", pady=(0, 2))
                tk.Label(
                    equip_card.inner,
                    text=bg_items,
                    font=FONTS["body"], fg=COLORS["fg"], bg=_bg,
                    wraplength=600, justify=tk.LEFT,
                ).pack(anchor="w")

    def _build_feats_section(self, inner, c):
        """Render feat summary."""
        feats = []
        if c.feat:
            feats.append(("Background", c.feat))
        if c.species_origin_feat:
            feats.append(("Species", c.species_origin_feat))

        if not feats:
            return

        SectionHeader(inner, text="Feats").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )
        feats_card = CardFrame(inner, pad=SPACING["lg"])
        feats_card.pack(fill=tk.X, pady=(0, SPACING["section_gap"]))
        _bg = COLORS["bg_surface"]

        for source_label, feat in feats:
            row = tk.Frame(feats_card.inner, bg=_bg)
            row.pack(fill=tk.X, pady=(0, SPACING["sm"]))

            tk.Label(
                row, text=feat["name"],
                font=FONTS["heading_serif_sm"], fg=COLORS["fg"], bg=_bg,
            ).pack(side=tk.LEFT)

            PillBadge(
                row,
                text=source_label.upper(),
                bg_color=COLORS["badge_glass"],
                fg_color=COLORS["fg_dim"],
            ).pack(side=tk.LEFT, padx=(SPACING["sm"], 0))
