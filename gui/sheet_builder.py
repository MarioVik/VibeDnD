"""Shared character sheet renderer used by the Summary wizard step and the
Character Viewer screen."""

from decimal import Decimal
import tkinter as tk
from tkinter import ttk

from gui.theme import COLORS, FONTS
from models.enums import ALL_SKILLS
from models.standard_actions import build_standard_actions
from gui.widgets import WrappingLabel
from gui.equipment_utils import extract_gp, gp_to_coins, strip_wealth


def _show_level_features(parent: tk.Widget, character, game_data=None):
    """Show features from all class levels in a compact list."""
    for cl in character.class_levels:
        level_data = None
        if game_data:
            level_data = game_data.get_level_data(cl.class_slug, cl.class_level)

        features = []
        if level_data:
            features = [
                f
                for f in level_data.get("features", [])
                if f != "-" and f != "Ability Score Improvement"
            ]

        if not features and not cl.feat_choice and not cl.subclass_slug:
            continue

        # Level header
        items = []
        for f in features:
            items.append(f)
        if cl.feat_choice:
            items.append(f"Feat: {cl.feat_choice}")
        if cl.subclass_slug:
            items.append(f"Subclass: {cl.subclass_slug.replace('-', ' ').title()}")

        # Show class name prefix for multiclass characters
        prefix = ""
        if character.is_multiclass:
            prefix = f"{cl.class_slug.title()} "
        text = f"  {prefix}Level {cl.class_level}: {', '.join(items)}"
        WrappingLabel(parent, text=text, foreground=COLORS["fg"]).pack(
            fill=tk.X, anchor="w", padx=8, pady=1
        )


def build_character_sheet(parent: tk.Widget, character, game_data=None):
    """Render a read-only character sheet into *parent*.

    Clears any existing children first so it can safely be called
    multiple times (e.g. on every ``on_enter``).
    """
    for w in parent.winfo_children():
        w.destroy()

    c = character

    # ── Header ──────────────────────────────────────────────────
    header = ttk.Frame(parent, style="Card.TFrame")
    header.pack(fill=tk.X, pady=(0, 8), ipady=8, ipadx=8)

    ttk.Label(header, text=c.summary_text(), style="CardHeading.TLabel").pack(
        anchor="w", padx=8
    )
    details = f"Background: {c.background_name}"
    if c.species_sub_choice:
        details += f"  |  {c.species_sub_choice}"
    ttk.Label(header, text=details, style="Card.TLabel").pack(anchor="w", padx=8)

    # ── Combat stats row ────────────────────────────────────────
    combat = ttk.Frame(parent, style="Card.TFrame")
    combat.pack(fill=tk.X, pady=4, ipady=6)

    stats = [
        ("HP", str(c.hit_points)),
        ("AC", str(c.armor_class)),
        ("Speed", f"{c.speed} ft"),
        ("Initiative", f"+{c.initiative}" if c.initiative >= 0 else str(c.initiative)),
        ("Prof. Bonus", f"+{c.proficiency_bonus}"),
    ]

    for label, value in stats:
        sf = ttk.Frame(combat, style="Card.TFrame")
        sf.pack(side=tk.LEFT, padx=16, pady=4)
        ttk.Label(
            sf,
            text=value,
            font=FONTS["stat"],
            foreground=COLORS["fg_bright"],
            background=COLORS["bg_card"],
        ).pack()
        ttk.Label(
            sf, text=label, foreground=COLORS["fg_dim"], background=COLORS["bg_card"]
        ).pack()

    # ── Ability Scores ──────────────────────────────────────────
    abilities_frame = ttk.LabelFrame(parent, text="Ability Scores")
    abilities_frame.pack(fill=tk.X, pady=4)

    ab_row = ttk.Frame(abilities_frame)
    ab_row.pack(fill=tk.X, padx=8, pady=4)

    for ability_name in [
        "Strength",
        "Dexterity",
        "Constitution",
        "Intelligence",
        "Wisdom",
        "Charisma",
    ]:
        af = ttk.Frame(ab_row)
        af.pack(side=tk.LEFT, padx=12)

        short = ability_name[:3].upper()
        total = c.ability_scores.total(ability_name)
        mod_str = c.ability_scores.modifier_str(ability_name)

        ttk.Label(af, text=short, foreground=COLORS["fg_dim"]).pack()
        ttk.Label(
            af, text=str(total), font=FONTS["stat"], foreground=COLORS["fg_bright"]
        ).pack()

        mod_val = c.ability_scores.modifier(ability_name)
        color = (
            COLORS["positive"]
            if mod_val > 0
            else COLORS["negative"]
            if mod_val < 0
            else COLORS["fg_dim"]
        )
        ttk.Label(af, text=mod_str, foreground=color).pack()

    # ── Saving Throws ───────────────────────────────────────────
    saves_frame = ttk.LabelFrame(parent, text="Saving Throws")
    saves_frame.pack(fill=tk.X, pady=4)

    saves_row = ttk.Frame(saves_frame)
    saves_row.pack(fill=tk.X, padx=8, pady=4)

    for ability_name in [
        "Strength",
        "Dexterity",
        "Constitution",
        "Intelligence",
        "Wisdom",
        "Charisma",
    ]:
        sf = ttk.Frame(saves_row)
        sf.pack(side=tk.LEFT, padx=8)

        is_prof = c.is_proficient_save(ability_name)
        mod_str = c.saving_throw_str(ability_name)
        marker = "\u25c6 " if is_prof else "  "

        text = f"{marker}{ability_name[:3].upper()} {mod_str}"
        color = COLORS["accent"] if is_prof else COLORS["fg_dim"]
        ttk.Label(sf, text=text, foreground=color).pack()

    # ── Skills ──────────────────────────────────────────────────
    skills_frame = ttk.LabelFrame(parent, text="Skills")
    skills_frame.pack(fill=tk.X, pady=4)

    skill_cols = ttk.Frame(skills_frame)
    skill_cols.pack(fill=tk.X, padx=8, pady=4)

    col_left = ttk.Frame(skill_cols)
    col_left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 16))
    col_right = ttk.Frame(skill_cols)
    col_right.pack(side=tk.LEFT, fill=tk.Y)

    profs = c.all_skill_proficiencies
    for i, skill in enumerate(ALL_SKILLS):
        target = col_left if i < 9 else col_right
        is_prof = skill.display_name in profs
        mod_str = c.skill_modifier_str(skill.display_name)
        marker = "\u25c6" if is_prof else " "
        color = COLORS["accent"] if is_prof else COLORS["fg_dim"]

        row = ttk.Frame(target)
        row.pack(fill=tk.X, pady=1)
        ttk.Label(
            row,
            text=f"{marker} {mod_str:>3}  {skill.display_name}",
            foreground=color,
            font=FONTS["mono"],
        ).pack(anchor="w")

    # ── Species Traits ──────────────────────────────────────────
    if c.species and c.species.get("traits"):
        traits_frame = ttk.LabelFrame(parent, text=f"{c.species_name} Traits")
        traits_frame.pack(fill=tk.X, pady=4)
        for trait in c.species["traits"]:
            WrappingLabel(
                traits_frame,
                text=f"  {trait['name']}: {trait.get('description', '')}",
                foreground=COLORS["fg_dim"],
            ).pack(fill=tk.X, anchor="w", padx=8, pady=1)

    # ── Class Features ──────────────────────────────────────────
    if c.character_class:
        feat_title = f"{c.class_name} Features"
        if c.is_multiclass:
            feat_title = "Class Features"
        feat_frame = ttk.LabelFrame(parent, text=feat_title)
        feat_frame.pack(fill=tk.X, pady=4)

        # Show level 1 features from class data
        if c.character_class.get("level_1_features") and c.level == 1:
            for feat in c.character_class["level_1_features"]:
                ttk.Label(
                    feat_frame,
                    text=f"  {feat['name']}",
                    foreground=COLORS["accent"],
                    font=FONTS["subheading"],
                ).pack(anchor="w", padx=8)
                if feat.get("description"):
                    WrappingLabel(
                        feat_frame,
                        text=f"    {feat['description']}",
                        foreground=COLORS["fg_dim"],
                    ).pack(fill=tk.X, anchor="w", padx=8, pady=(0, 4))
        elif c.class_levels:
            # Multi-level: show features gained at each level
            _show_level_features(feat_frame, c, game_data)

    # ── Subclass ──────────────────────────────────────────────
    if c.current_subclass:
        sub_name = c.current_subclass.replace("-", " ").title()
        sub_frame = ttk.LabelFrame(parent, text=f"Subclass: {sub_name}")
        sub_frame.pack(fill=tk.X, pady=4)
        ttk.Label(sub_frame, text=f"  {sub_name}", foreground=COLORS["accent"]).pack(
            anchor="w", padx=8, pady=4
        )

    # ── Feats ───────────────────────────────────────────────────
    has_any_feat = c.feat or c.species_origin_feat
    if has_any_feat:
        feat_sec = ttk.LabelFrame(parent, text="Feats")
        feat_sec.pack(fill=tk.X, pady=4)

        # Background feat
        if c.feat:
            feat_name = (
                c.background.get("feat", c.feat.get("name", ""))
                if c.background
                else c.feat.get("name", "")
            )
            ttk.Label(
                feat_sec,
                text=f"  {feat_name}  (from Background)",
                foreground=COLORS["accent"],
                font=FONTS["subheading"],
            ).pack(anchor="w", padx=8)
            for b in c.feat.get("benefits", []):
                WrappingLabel(
                    feat_sec,
                    text=f"    {b['name']}: {b.get('description', '')}",
                    foreground=COLORS["fg_dim"],
                ).pack(fill=tk.X, anchor="w", padx=8, pady=1)

        # Species origin feat (Human Versatile)
        if c.species_origin_feat:
            if c.feat:
                ttk.Separator(feat_sec, orient=tk.HORIZONTAL).pack(
                    fill=tk.X, padx=8, pady=4
                )
            sp_name = c.species_name if c.species else "Species"
            ttk.Label(
                feat_sec,
                text=f"  {c.species_origin_feat['name']}  (from {sp_name})",
                foreground=COLORS["accent"],
                font=FONTS["subheading"],
            ).pack(anchor="w", padx=8)
            for b in c.species_origin_feat.get("benefits", []):
                WrappingLabel(
                    feat_sec,
                    text=f"    {b['name']}: {b.get('description', '')}",
                    foreground=COLORS["fg_dim"],
                ).pack(fill=tk.X, anchor="w", padx=8, pady=1)

    # ── Spells ──────────────────────────────────────────────────
    if c.selected_cantrips or c.selected_spells:
        spell_sec = ttk.LabelFrame(parent, text="Spells")
        spell_sec.pack(fill=tk.X, pady=4)
        if c.selected_cantrips:
            WrappingLabel(
                spell_sec, text=f"  Cantrips: {', '.join(c.selected_cantrips)}"
            ).pack(fill=tk.X, anchor="w", padx=8, pady=2)
        if c.selected_spells:
            WrappingLabel(
                spell_sec, text=f"  Level 1: {', '.join(c.selected_spells)}"
            ).pack(fill=tk.X, anchor="w", padx=8, pady=2)

    # ── Standard Actions ────────────────────────────────────────
    base_actions = build_standard_actions(c)
    actions_sec = ttk.LabelFrame(parent, text="Standard Actions")
    actions_sec.pack(fill=tk.X, pady=4)

    rows_frame = ttk.Frame(actions_sec)
    rows_frame.pack(fill=tk.X, padx=8, pady=(2, 2))

    option_vars: dict[str, dict[str, tk.BooleanVar]] = {}
    saved_opts = (
        c.standard_action_options if isinstance(c.standard_action_options, dict) else {}
    )

    def _weapon_options() -> dict[str, dict]:
        out: dict[str, dict] = {}
        for key, vars_for_weapon in option_vars.items():
            out[key] = {
                "true_strike": bool(
                    vars_for_weapon.get("true_strike")
                    and vars_for_weapon["true_strike"].get()
                ),
                "two_handed": bool(
                    vars_for_weapon.get("two_handed")
                    and vars_for_weapon["two_handed"].get()
                ),
            }
        return out

    def _persist_weapon_options():
        c.standard_action_options = _weapon_options()

    def _render_action_rows():
        for w in rows_frame.winfo_children():
            w.destroy()

        options = _weapon_options()
        actions = build_standard_actions(c, weapon_options=options)
        if not actions:
            ttk.Label(
                rows_frame,
                text="No standard attack actions detected.",
                style="Dim.TLabel",
            ).pack(anchor="w", pady=2)
            return

        ttk.Label(
            rows_frame,
            text="Name                    Atk      Damage                 Notes",
            foreground=COLORS["fg_dim"],
            font=FONTS["mono"],
        ).pack(anchor="w")

        for a in actions:
            line = (
                f"{a['name'][:22]:22}  "
                f"{a['attack'][:7]:7}  "
                f"{a['damage'][:21]:21}  "
                f"{a['notes']}"
            )
            ttk.Label(
                rows_frame,
                text=line,
                foreground=COLORS["fg"],
                font=FONTS["mono"],
            ).pack(anchor="w", pady=1)

    configurable_weapons = [
        a
        for a in base_actions
        if a.get("kind") == "weapon"
        and (a.get("can_true_strike") or a.get("versatile"))
    ]
    if configurable_weapons:
        ttk.Separator(actions_sec, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=8, pady=4)
        ttk.Label(
            actions_sec,
            text="Weapon Options",
            style="Subheading.TLabel",
        ).pack(anchor="w", padx=8)

        for a in configurable_weapons:
            key = a.get("weapon_key", "")
            vars_for_weapon = option_vars.setdefault(key, {})

            row = ttk.Frame(actions_sec)
            row.pack(fill=tk.X, padx=8, pady=1)
            ttk.Label(row, text=a["name"], foreground=COLORS["fg_dim"]).pack(
                side=tk.LEFT
            )

            if a.get("can_true_strike"):
                vars_for_weapon["true_strike"] = tk.BooleanVar(value=False)
                if isinstance(saved_opts.get(key), dict):
                    vars_for_weapon["true_strike"].set(
                        bool(saved_opts[key].get("true_strike", False))
                    )
                ttk.Checkbutton(
                    row,
                    text="Use True Strike",
                    variable=vars_for_weapon["true_strike"],
                    command=lambda: (_persist_weapon_options(), _render_action_rows()),
                ).pack(side=tk.LEFT, padx=(12, 6))

            if a.get("versatile"):
                vars_for_weapon["two_handed"] = tk.BooleanVar(value=False)
                if isinstance(saved_opts.get(key), dict):
                    vars_for_weapon["two_handed"].set(
                        bool(saved_opts[key].get("two_handed", False))
                    )
                ttk.Checkbutton(
                    row,
                    text="Use Two Hands",
                    variable=vars_for_weapon["two_handed"],
                    command=lambda: (_persist_weapon_options(), _render_action_rows()),
                ).pack(side=tk.LEFT, padx=6)

    _persist_weapon_options()
    _render_action_rows()

    # ── Equipment ───────────────────────────────────────────────
    equip_sec = ttk.LabelFrame(parent, text="Equipment")
    equip_sec.pack(fill=tk.X, pady=4)
    has_equip = False
    total_gp = Decimal("0")
    if c.character_class:
        for opt in c.character_class.get("starting_equipment", []):
            if opt["option"] == c.equipment_choice_class:
                total_gp += extract_gp(opt["items"])
                items_text = strip_wealth(opt["items"])
                if items_text:
                    WrappingLabel(
                        equip_sec, text=f"  {items_text}", foreground=COLORS["fg_dim"]
                    ).pack(fill=tk.X, anchor="w", padx=8, pady=2)
                    has_equip = True
    if c.background:
        for opt in c.background.get("equipment", []):
            if opt["option"] == c.equipment_choice_background:
                total_gp += extract_gp(opt["items"])
                items_text = strip_wealth(opt["items"])
                if items_text:
                    WrappingLabel(
                        equip_sec, text=f"  {items_text}", foreground=COLORS["fg_dim"]
                    ).pack(fill=tk.X, anchor="w", padx=8, pady=2)
                    has_equip = True
    if not has_equip:
        ttk.Label(equip_sec, text="  No equipment selected", style="Dim.TLabel").pack(
            anchor="w", padx=8
        )

    # ── Wealth ──────────────────────────────────────────────────
    wealth_sec = ttk.LabelFrame(parent, text="Wealth")
    wealth_sec.pack(fill=tk.X, pady=4)
    gp, sp, cp = gp_to_coins(total_gp)
    WrappingLabel(
        wealth_sec,
        text=(f"  Gold: {gp} gp\n  Silver: {sp} sp\n  Copper: {cp} cp"),
        foreground=COLORS["fg_dim"],
    ).pack(fill=tk.X, anchor="w", padx=8, pady=2)
