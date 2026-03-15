"""Shared character sheet renderer used by the Summary wizard step and the
Character Viewer screen."""

import re
import tkinter as tk
from tkinter import ttk

from gui.theme import COLORS, FONTS
from models.enums import ALL_SKILLS
from models.standard_actions import (
    WEAPON_DATA,
    build_standard_actions,
    get_selected_armor_counts,
    get_selected_non_weapon_items,
    get_selected_weapon_counts,
)
from gui.widgets import AlertDialog, WrappingLabel
from models.inventory_service import cp_to_coins, current_wealth_cp


CONTAINER_CONTENTS = {
    "Burglar's Pack": [
        "Backpack",
        "Ball Bearings (1,000)",
        "String (10 ft)",
        "Bell",
        "Candles (5)",
        "Crowbar",
        "Hammer",
        "Piton (10)",
        "Hooded Lantern",
        "Oil Flask (2)",
        "Rations (5 days)",
        "Tinderbox",
        "Waterskin",
        "Hempen Rope (50 ft)",
    ],
    "Dungeoneer's Pack": [
        "Backpack",
        "Crowbar",
        "Hammer",
        "Piton (10)",
        "Torch (10)",
        "Tinderbox",
        "Rations (10 days)",
        "Waterskin",
        "Hempen Rope (50 ft)",
    ],
    "Explorer's Pack": [
        "Backpack",
        "Bedroll",
        "Mess Kit",
        "Tinderbox",
        "Torch (10)",
        "Rations (10 days)",
        "Waterskin",
        "Hempen Rope (50 ft)",
    ],
    "Priest's Pack": [
        "Backpack",
        "Blanket",
        "Candle (10)",
        "Tinderbox",
        "Alms Box",
        "Incense Block (2)",
        "Censer",
        "Vestments",
        "Rations (2 days)",
        "Waterskin",
    ],
    "Scholar's Pack": [
        "Backpack",
        "Book of Lore",
        "Ink Bottle",
        "Ink Pen",
        "Parchment (10)",
        "Sand Bag",
        "Small Knife",
    ],
    "Disguise Kit": ["Cosmetics", "Hair Dye", "Small Props", "Cloth Pieces"],
    "Forgery Kit": ["Ink", "Parchment", "Seals", "Quills"],
    "Healer's Kit": ["Bandages (10 uses)", "Salves", "Splints"],
    "Herbalism Kit": ["Pouches", "Clippers", "Mortar and Pestle", "Vials"],
}


def _normalize_container_key(text: str) -> str:
    t = (text or "").lower()
    t = t.replace("’", "'").replace("‘", "'").replace("�", "")
    t = t.replace("'", "")
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


_CONTAINER_NORM = {
    _normalize_container_key(name): (name, contents)
    for name, contents in CONTAINER_CONTENTS.items()
}


def _container_contents(item_text: str) -> tuple[str, list[str]] | None:
    norm_item = _normalize_container_key(item_text)
    for norm_name, (container, contents) in _CONTAINER_NORM.items():
        if norm_name and norm_name in norm_item:
            return container, contents
    return None


def _show_level_features(parent: tk.Widget, character, game_data=None):
    """Show features from all class levels with full descriptions."""
    for cl in character.class_levels:
        level_data = None
        if game_data:
            level_data = game_data.get_level_data(cl.class_slug, cl.class_level)

        feature_details = []
        if level_data:
            feature_details = [
                f
                for f in level_data.get("feature_details", [])
                if isinstance(f, dict)
                and f.get("name") not in ("-", "Ability Score Improvement")
            ]
            # Fall back to name-only list if no details available
            if not feature_details:
                for name in level_data.get("features", []):
                    if name not in ("-", "Ability Score Improvement"):
                        feature_details.append({"name": name, "description": ""})

        extra = []
        if cl.feat_choice:
            extra.append({"name": f"Feat: {cl.feat_choice}", "description": ""})
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

        prefix = f"{cl.class_slug.title()} " if character.is_multiclass else ""
        ttk.Label(
            parent,
            text=f"  {prefix}Level {cl.class_level}",
            foreground=COLORS["accent"],
            font=FONTS["subheading"],
        ).pack(anchor="w", padx=8, pady=(6, 2))

        for feat in all_items:
            feat_name = feat.get("name", "")
            feat_desc = feat.get("description", "")
            ttk.Label(
                parent,
                text=f"    • {feat_name}",
                foreground=COLORS["fg_bright"],
                font=FONTS["body"],
            ).pack(anchor="w", padx=8)
            if feat_desc:
                WrappingLabel(
                    parent,
                    text=f"      {feat_desc}",
                    foreground=COLORS["fg_dim"],
                ).pack(fill=tk.X, anchor="w", padx=8, pady=(0, 4))


def build_character_sheet(
    parent: tk.Widget,
    character,
    game_data=None,
    on_change=None,
    include_sections: set[str] | None = None,
):
    """Render a read-only character sheet into *parent*.

    Clears any existing children first so it can safely be called
    multiple times (e.g. on every ``on_enter``).
    """
    for w in parent.winfo_children():
        w.destroy()

    c = character

    def _emit_change():
        if callable(on_change):
            on_change()

    def _show(section: str) -> bool:
        return include_sections is None or section in include_sections

    # ── Header ──────────────────────────────────────────────────
    if _show("header"):
        header = ttk.Frame(parent, style="Card.TFrame")
        header.pack(fill=tk.X, pady=(0, 8), ipady=8, ipadx=8)

        ttk.Label(header, text=c.summary_text(), style="CardHeading.TLabel").pack(
            anchor="w", padx=8
        )
        details = f"Background: {c.background_name}"
        if c.species_sub_choice:
            details += f"  |  {c.species_sub_choice}"
        ttk.Label(header, text=details, style="Card.TLabel").pack(anchor="w", padx=8)

    stat_value_labels: dict[str, ttk.Label] = {}
    if _show("combat"):
        combat = ttk.Frame(parent, style="Card.TFrame")
        combat.pack(fill=tk.X, pady=4, ipady=6)

        stats = [
            ("HP", str(c.hit_points)),
            ("AC", str(c.armor_class)),
            ("Speed", f"{c.speed} ft"),
            (
                "Initiative",
                f"+{c.initiative}" if c.initiative >= 0 else str(c.initiative),
            ),
            ("Prof. Bonus", f"+{c.proficiency_bonus}"),
        ]

        for label, value in stats:
            sf = ttk.Frame(combat, style="Card.TFrame")
            sf.pack(side=tk.LEFT, padx=16, pady=4)
            value_lbl = ttk.Label(
                sf,
                text=value,
                font=FONTS["stat"],
                foreground=COLORS["fg_bright"],
                background=COLORS["bg_card"],
            )
            value_lbl.pack()
            stat_value_labels[label] = value_lbl
            ttk.Label(
                sf,
                text=label,
                foreground=COLORS["fg_dim"],
                background=COLORS["bg_card"],
            ).pack()

    # ── Ability Scores ──────────────────────────────────────────
    if _show("abilities"):
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
                af,
                text=str(total),
                font=FONTS["stat"],
                foreground=COLORS["fg_bright"],
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
    if _show("saving_throws"):
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
    if _show("skills"):
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

    rows_frame = None
    options_frame = None
    if _show("standard_actions"):
        actions_sec = ttk.LabelFrame(parent, text="Standard Actions")
        actions_sec.pack(fill=tk.X, pady=4)
        rows_frame = ttk.Frame(actions_sec)
        rows_frame.pack(fill=tk.X, padx=8, pady=(2, 2))
        options_frame = ttk.Frame(actions_sec)
        options_frame.pack(fill=tk.X, padx=8, pady=(0, 2))

    # ── Species Traits ──────────────────────────────────────────
    if _show("species_traits") and c.species and c.species.get("traits"):
        traits_frame = ttk.LabelFrame(parent, text=f"{c.species_name} Traits")
        traits_frame.pack(fill=tk.X, pady=4)
        for trait in c.species["traits"]:
            WrappingLabel(
                traits_frame,
                text=f"  {trait['name']}: {trait.get('description', '')}",
                foreground=COLORS["fg_dim"],
            ).pack(fill=tk.X, anchor="w", padx=8, pady=1)

    # ── Class Features ──────────────────────────────────────────
    if _show("class_features") and c.character_class:
        feat_title = f"{c.class_name} Features"
        if c.is_multiclass:
            feat_title = "Class Features"
        feat_frame = ttk.LabelFrame(parent, text=feat_title)
        feat_frame.pack(fill=tk.X, pady=4)

        if c.class_levels:
            _show_level_features(feat_frame, c, game_data)
        elif c.character_class.get("level_1_features"):
            # Fallback: no class_levels data, use raw level_1_features from class JSON
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

    # ── Subclass ──────────────────────────────────────────────
    if _show("subclass") and c.current_subclass:
        sub_name = c.current_subclass.replace("-", " ").title()
        sub_frame = ttk.LabelFrame(parent, text=f"Subclass: {sub_name}")
        sub_frame.pack(fill=tk.X, pady=4)

        # Resolve subclass data and show features by level
        subclass_data = None
        if game_data:
            primary_slug = (
                c.character_class.get("slug", "") if c.character_class else ""
            )
            subclasses_for_class = game_data.get_subclasses_for_class(primary_slug)
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
                        sub_frame, text=f"  {intro}", foreground=COLORS["fg_dim"]
                    ).pack(fill=tk.X, anchor="w", padx=8, pady=(4, 0))

            features_by_level = subclass_data.get("features", {})
            for lvl in sorted(
                features_by_level.keys(),
                key=lambda x: int(x) if str(x).isdigit() else 99,
            ):
                # Only show features up to character's current level
                try:
                    lvl_int = int(lvl)
                except ValueError, TypeError:
                    continue
                if lvl_int > c.level:
                    continue
                ttk.Label(
                    sub_frame,
                    text=f"  Level {lvl}",
                    foreground=COLORS["accent"],
                    font=FONTS["subheading"],
                ).pack(anchor="w", padx=8, pady=(6, 2))
                for feat in features_by_level.get(lvl, []):
                    feat_name = feat.get("name", "")
                    feat_desc = feat.get("description", "")
                    ttk.Label(
                        sub_frame,
                        text=f"    • {feat_name}",
                        foreground=COLORS["fg_bright"],
                        font=FONTS["body"],
                    ).pack(anchor="w", padx=8)
                    if feat_desc:
                        WrappingLabel(
                            sub_frame,
                            text=f"      {feat_desc}",
                            foreground=COLORS["fg_dim"],
                        ).pack(fill=tk.X, anchor="w", padx=8, pady=(0, 4))
        else:
            ttk.Label(
                sub_frame, text=f"  {sub_name}", foreground=COLORS["accent"]
            ).pack(anchor="w", padx=8, pady=4)

    # ── Feats ───────────────────────────────────────────────────
    has_any_feat = c.feat or c.species_origin_feat
    if _show("feats") and has_any_feat:
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
    if _show("spells") and (c.selected_cantrips or c.selected_spells):
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

    # Parsed equipment/inventory
    weapon_counts = get_selected_weapon_counts(c)
    armor_counts = get_selected_armor_counts(c)
    inventory_items = get_selected_non_weapon_items(c)

    def _normalized_armor_profs() -> set[str]:
        out: set[str] = set()
        for p in (c.character_class or {}).get("armor_proficiencies", []):
            t = str(p).lower()
            if "shield" in t:
                out.add("shield")
            if "heavy" in t:
                out.add("heavy")
            if "medium" in t:
                out.add("medium")
            if "light" in t:
                out.add("light")
        return out

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

    def _can_equip_armor(armor_key: str) -> tuple[bool, str]:
        req = ARMOR_REQUIRED.get(armor_key, "light")
        profs = _normalized_armor_profs()
        if req in profs:
            return True, ""
        req_label = "Shields" if req == "shield" else f"{req.title()} armor"
        class_name = c.class_name
        return (
            False,
            f"{class_name} is not proficient with {req_label}."
            " You can't equip this item.",
        )

    def _has_weapon_proficiency_local(weapon_key: str) -> bool:
        cls = c.character_class or {}
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

    # Merge custom inventory entries (added via item browser).
    for ent in getattr(c, "custom_inventory", []) or []:
        name = str(ent.get("name", "")).strip()
        if not name:
            continue
        qty = max(1, int(ent.get("qty", 1)))
        category = str(ent.get("category", "Adventuring Gear"))
        key = name.lower()
        if category == "Weapons":
            weapon_counts[key] = weapon_counts.get(key, 0) + qty
        elif category == "Armor":
            armor_counts[key] = armor_counts.get(key, 0) + qty
        else:
            inventory_items.append(f"{qty} {name}" if qty > 1 else name)

    # Default: all weapons are equipped unless character has explicitly set state.
    if c.equipped_weapons is None:
        c.equipped_weapons = sorted(weapon_counts.keys())
    else:
        c.equipped_weapons = [w for w in c.equipped_weapons if w in weapon_counts]
    if c.equipped_armor is None:
        default_armor = []
        if "shield" in armor_counts and _can_equip_armor("shield")[0]:
            default_armor.append("shield")
        body_armor = sorted(a for a in armor_counts.keys() if a != "shield")
        for armor_key in body_armor:
            if _can_equip_armor(armor_key)[0]:
                default_armor.append(armor_key)
                break
        c.equipped_armor = default_armor
    else:
        c.equipped_armor = [
            a for a in c.equipped_armor if a in armor_counts and _can_equip_armor(a)[0]
        ]
        body = [a for a in c.equipped_armor if a != "shield"]
        c.equipped_armor = (["shield"] if "shield" in c.equipped_armor else []) + body[
            :1
        ]

    # ── Wealth ──────────────────────────────────────────────────
    if _show("wealth"):
        wealth_sec = ttk.LabelFrame(parent, text="Wealth")
        wealth_sec.pack(fill=tk.X, pady=4)
        gp, sp, cp = cp_to_coins(current_wealth_cp(c))
        WrappingLabel(
            wealth_sec,
            text=(f"  Gold: {gp} gp\n  Silver: {sp} sp\n  Copper: {cp} cp"),
            foreground=COLORS["fg_dim"],
        ).pack(fill=tk.X, anchor="w", padx=8, pady=2)

    # ── Equipment ───────────────────────────────────────────────
    equip_sec = None
    if _show("equipment"):
        equip_sec = ttk.LabelFrame(parent, text="Equipment")
        equip_sec.pack(fill=tk.X, pady=4)

    equip_vars: dict[str, tk.BooleanVar] = {}
    armor_vars: dict[str, tk.BooleanVar] = {}

    def _col_header(parent_frame):
        h = ttk.Frame(parent_frame)
        h.pack(fill=tk.X)
        ttk.Label(h, text="Equipped", style="Dim.TLabel", width=9).pack(side=tk.LEFT)
        ttk.Label(h, text="Item", style="Dim.TLabel").pack(side=tk.LEFT)

    if _show("equipment") and equip_sec is not None:
        # ── Weapons sub-section ──────────────────────────────────────
        weapons_frame = ttk.LabelFrame(equip_sec, text="Weapons")
        weapons_frame.pack(fill=tk.X, padx=8, pady=(6, 2))
        weapons_inner = ttk.Frame(weapons_frame)
        weapons_inner.pack(fill=tk.X, padx=8, pady=4)

        if weapon_counts:
            _col_header(weapons_inner)
            for weapon_key in sorted(weapon_counts.keys()):
                qty = weapon_counts[weapon_key]
                var = tk.BooleanVar(value=weapon_key in set(c.equipped_weapons or []))
                equip_vars[weapon_key] = var

                row = ttk.Frame(weapons_inner)
                row.pack(fill=tk.X, pady=1)
                ttk.Checkbutton(
                    row,
                    variable=var,
                    command=lambda k=weapon_key: _on_weapon_toggle(k),
                ).pack(side=tk.LEFT)
                label = weapon_key.title()
                if qty > 1:
                    label += f" (x{qty})"
                ttk.Label(row, text=label, foreground=COLORS["fg_dim"]).pack(
                    side=tk.LEFT
                )
        else:
            ttk.Label(
                weapons_inner,
                text="No weapons in selected equipment.",
                style="Dim.TLabel",
            ).pack(anchor="w")

        # ── Armor sub-section (incl. shields) ───────────────────────
        armor_frame = ttk.LabelFrame(equip_sec, text="Armor & Shields")
        armor_frame.pack(fill=tk.X, padx=8, pady=(2, 6))
        armor_inner = ttk.Frame(armor_frame)
        armor_inner.pack(fill=tk.X, padx=8, pady=4)

        if armor_counts:
            _col_header(armor_inner)
            for armor_key in sorted(armor_counts.keys()):
                qty = armor_counts[armor_key]
                var = tk.BooleanVar(value=armor_key in set(c.equipped_armor or []))
                armor_vars[armor_key] = var

                row = ttk.Frame(armor_inner)
                row.pack(fill=tk.X, pady=1)
                ttk.Checkbutton(
                    row,
                    variable=var,
                    command=lambda k=armor_key: _on_armor_toggle(k),
                ).pack(side=tk.LEFT)
                label = armor_key.title()
                if qty > 1:
                    label += f" (x{qty})"
                ttk.Label(row, text=label, foreground=COLORS["fg_dim"]).pack(
                    side=tk.LEFT
                )
        else:
            ttk.Label(
                armor_inner,
                text="No armor in selected equipment.",
                style="Dim.TLabel",
            ).pack(anchor="w")
    else:
        for weapon_key in sorted(weapon_counts.keys()):
            equip_vars[weapon_key] = tk.BooleanVar(
                value=weapon_key in set(c.equipped_weapons or [])
            )
        for armor_key in sorted(armor_counts.keys()):
            armor_vars[armor_key] = tk.BooleanVar(
                value=armor_key in set(c.equipped_armor or [])
            )

    if _show("inventory"):
        inv_sec = ttk.LabelFrame(parent, text="Inventory")
        inv_sec.pack(fill=tk.X, pady=4)
        if inventory_items:
            for item in inventory_items:
                container_info = _container_contents(item)
                if not container_info:
                    WrappingLabel(
                        inv_sec, text=f"  {item}", foreground=COLORS["fg_dim"]
                    ).pack(fill=tk.X, anchor="w", padx=8, pady=1)
                    continue

                container_name, contents = container_info
                WrappingLabel(
                    inv_sec,
                    text=f"  {container_name}",
                    foreground=COLORS["fg_dim"],
                ).pack(fill=tk.X, anchor="w", padx=8, pady=(1, 0))
                for sub in contents:
                    WrappingLabel(
                        inv_sec,
                        text=f"    - {sub}",
                        foreground=COLORS["fg_dim"],
                    ).pack(fill=tk.X, anchor="w", padx=8, pady=0)
        else:
            ttk.Label(inv_sec, text="  No inventory items.", style="Dim.TLabel").pack(
                anchor="w", padx=8
            )

    option_vars: dict[str, dict[str, tk.BooleanVar]] = {}
    saved_opts = (
        c.standard_action_options if isinstance(c.standard_action_options, dict) else {}
    )
    all_weapon_actions = build_standard_actions(
        c,
        weapon_options=saved_opts,
        equipped_weapon_keys=set(weapon_counts.keys()),
    )

    def _equipped_keys() -> set[str]:
        return {k for k, v in equip_vars.items() if v.get()}

    def _equipped_armor_keys() -> set[str]:
        return {k for k, v in armor_vars.items() if v.get()}

    def _sync_equipped_state():
        prev_weapons = list(c.equipped_weapons or [])
        prev_armor = list(c.equipped_armor or [])
        c.equipped_weapons = sorted(_equipped_keys())
        c.equipped_armor = sorted(_equipped_armor_keys())
        ac_lbl = stat_value_labels.get("AC")
        if ac_lbl is not None:
            ac_lbl.configure(text=str(c.armor_class))
        if prev_weapons != c.equipped_weapons or prev_armor != c.equipped_armor:
            _emit_change()

    def _on_armor_toggle(changed_key: str):
        """Allow only one body armor at a time; shield is independent."""
        changed_var = armor_vars.get(changed_key)
        if changed_var is not None and changed_var.get():
            ok, reason = _can_equip_armor(changed_key)
            if not ok:
                changed_var.set(False)
                AlertDialog(parent.winfo_toplevel(), "Armor Training Required", reason)
                return

            if changed_key != "shield":
                for key, var in armor_vars.items():
                    if key != changed_key and key != "shield" and var.get():
                        var.set(False)
        _render_action_rows()

    def _on_weapon_toggle(changed_key: str):
        var = equip_vars.get(changed_key)
        if (
            var is not None
            and var.get()
            and not _has_weapon_proficiency_local(changed_key)
        ):
            AlertDialog(
                parent.winfo_toplevel(),
                "Weapon Proficiency",
                f"You are not proficient with {changed_key.title()}. "
                "You can still equip it, but your proficiency bonus will not be added to attack rolls.",
            )
        _render_action_rows()

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
        next_opts = _weapon_options()
        if c.standard_action_options != next_opts:
            c.standard_action_options = next_opts
            _emit_change()

    def _render_weapon_option_rows():
        if options_frame is None:
            return
        assert options_frame is not None
        for w in options_frame.winfo_children():
            w.destroy()

        configurable_weapons = [
            a
            for a in all_weapon_actions
            if a.get("kind") == "weapon"
            and (a.get("can_true_strike") or a.get("versatile"))
        ]
        if not configurable_weapons:
            return

        ttk.Separator(options_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=4)
        ttk.Label(options_frame, text="Weapon Options", style="Subheading.TLabel").pack(
            anchor="w"
        )

        for a in configurable_weapons:
            key = a.get("weapon_key", "")
            vars_for_weapon = option_vars.setdefault(key, {})
            row = ttk.Frame(options_frame)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=a["name"], foreground=COLORS["fg_dim"]).pack(
                side=tk.LEFT
            )

            if a.get("can_true_strike") and "true_strike" not in vars_for_weapon:
                vars_for_weapon["true_strike"] = tk.BooleanVar(
                    value=bool(saved_opts.get(key, {}).get("true_strike", False))
                )
            if a.get("versatile") and "two_handed" not in vars_for_weapon:
                vars_for_weapon["two_handed"] = tk.BooleanVar(
                    value=bool(saved_opts.get(key, {}).get("two_handed", False))
                )

            if a.get("can_true_strike"):
                ttk.Checkbutton(
                    row,
                    text="Use True Strike",
                    variable=vars_for_weapon["true_strike"],
                    command=lambda: (_persist_weapon_options(), _render_action_rows()),
                ).pack(side=tk.LEFT, padx=(12, 6))
            if a.get("versatile"):
                ttk.Checkbutton(
                    row,
                    text="Use Two Hands",
                    variable=vars_for_weapon["two_handed"],
                    command=lambda: (_persist_weapon_options(), _render_action_rows()),
                ).pack(side=tk.LEFT, padx=6)

    def _render_action_rows():
        if rows_frame is None:
            _sync_equipped_state()
            return
        assert rows_frame is not None
        for w in rows_frame.winfo_children():
            w.destroy()

        _sync_equipped_state()
        actions = build_standard_actions(
            c,
            weapon_options=_weapon_options(),
            equipped_weapon_keys=_equipped_keys(),
        )

        if not actions:
            ttk.Label(
                rows_frame,
                text="No standard attack actions detected.",
                style="Dim.TLabel",
            ).pack(anchor="w", pady=2)
            _render_weapon_option_rows()
            return

        ttk.Label(
            rows_frame,
            text="Name                    Atk      Damage                 Notes",
            foreground=COLORS["fg_dim"],
            font=FONTS["mono"],
        ).pack(anchor="w")

        for a in actions:
            line = f"{a['name'][:22]:22}  {a['attack'][:7]:7}  {a['damage'][:21]:21}  {a['notes']}"
            ttk.Label(
                rows_frame, text=line, foreground=COLORS["fg"], font=FONTS["mono"]
            ).pack(anchor="w", pady=1)

        _render_weapon_option_rows()

    _render_action_rows()
