"""Shared character sheet renderer used by the Summary wizard step and the
Character Viewer screen."""

import tkinter as tk
from tkinter import ttk

from gui.theme import COLORS, FONTS
from models.enums import ALL_SKILLS


def build_character_sheet(parent: tk.Widget, character):
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

    ttk.Label(header, text=c.summary_text(), style="CardHeading.TLabel").pack(anchor="w", padx=8)
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
        ttk.Label(sf, text=value, font=FONTS["stat"], foreground=COLORS["fg_bright"],
                  background=COLORS["bg_card"]).pack()
        ttk.Label(sf, text=label, foreground=COLORS["fg_dim"],
                  background=COLORS["bg_card"]).pack()

    # ── Ability Scores ──────────────────────────────────────────
    abilities_frame = ttk.LabelFrame(parent, text="Ability Scores")
    abilities_frame.pack(fill=tk.X, pady=4)

    ab_row = ttk.Frame(abilities_frame)
    ab_row.pack(fill=tk.X, padx=8, pady=4)

    for ability_name in ["Strength", "Dexterity", "Constitution",
                         "Intelligence", "Wisdom", "Charisma"]:
        af = ttk.Frame(ab_row)
        af.pack(side=tk.LEFT, padx=12)

        short = ability_name[:3].upper()
        total = c.ability_scores.total(ability_name)
        mod_str = c.ability_scores.modifier_str(ability_name)

        ttk.Label(af, text=short, foreground=COLORS["fg_dim"]).pack()
        ttk.Label(af, text=str(total), font=FONTS["stat"],
                  foreground=COLORS["fg_bright"]).pack()

        mod_val = c.ability_scores.modifier(ability_name)
        color = (COLORS["positive"] if mod_val > 0
                 else COLORS["negative"] if mod_val < 0
                 else COLORS["fg_dim"])
        ttk.Label(af, text=mod_str, foreground=color).pack()

    # ── Saving Throws ───────────────────────────────────────────
    saves_frame = ttk.LabelFrame(parent, text="Saving Throws")
    saves_frame.pack(fill=tk.X, pady=4)

    saves_row = ttk.Frame(saves_frame)
    saves_row.pack(fill=tk.X, padx=8, pady=4)

    for ability_name in ["Strength", "Dexterity", "Constitution",
                         "Intelligence", "Wisdom", "Charisma"]:
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
        ttk.Label(row, text=f"{marker} {mod_str:>3}  {skill.display_name}",
                  foreground=color, font=FONTS["mono"]).pack(anchor="w")

    # ── Species Traits ──────────────────────────────────────────
    if c.species and c.species.get("traits"):
        traits_frame = ttk.LabelFrame(parent, text=f"{c.species_name} Traits")
        traits_frame.pack(fill=tk.X, pady=4)
        for trait in c.species["traits"]:
            ttk.Label(traits_frame,
                      text=f"  {trait['name']}: {trait.get('description', '')[:150]}",
                      wraplength=600, foreground=COLORS["fg_dim"]).pack(
                          anchor="w", padx=8, pady=1)

    # ── Class Features ──────────────────────────────────────────
    if c.character_class and c.character_class.get("level_1_features"):
        feat_frame = ttk.LabelFrame(parent, text=f"{c.class_name} Features")
        feat_frame.pack(fill=tk.X, pady=4)
        for feat in c.character_class["level_1_features"]:
            ttk.Label(feat_frame, text=f"  {feat['name']}",
                      foreground=COLORS["accent"], font=FONTS["subheading"]).pack(
                          anchor="w", padx=8)
            if feat.get("description"):
                ttk.Label(feat_frame,
                          text=f"    {feat['description'][:200]}",
                          wraplength=600, foreground=COLORS["fg_dim"]).pack(
                              anchor="w", padx=8, pady=(0, 4))

    # ── Feats ───────────────────────────────────────────────────
    has_any_feat = c.feat or c.species_origin_feat
    if has_any_feat:
        feat_sec = ttk.LabelFrame(parent, text="Feats")
        feat_sec.pack(fill=tk.X, pady=4)

        # Background feat
        if c.feat:
            feat_name = (c.background.get("feat", c.feat.get("name", ""))
                         if c.background else c.feat.get("name", ""))
            ttk.Label(feat_sec, text=f"  {feat_name}  (from Background)",
                      foreground=COLORS["accent"], font=FONTS["subheading"]).pack(
                          anchor="w", padx=8)
            for b in c.feat.get("benefits", []):
                ttk.Label(feat_sec,
                          text=f"    {b['name']}: {b.get('description', '')[:150]}",
                          wraplength=600, foreground=COLORS["fg_dim"]).pack(
                              anchor="w", padx=8, pady=1)

        # Species origin feat (Human Versatile)
        if c.species_origin_feat:
            if c.feat:
                ttk.Separator(feat_sec, orient=tk.HORIZONTAL).pack(
                    fill=tk.X, padx=8, pady=4)
            sp_name = c.species_name if c.species else "Species"
            ttk.Label(feat_sec,
                      text=f"  {c.species_origin_feat['name']}  (from {sp_name})",
                      foreground=COLORS["accent"], font=FONTS["subheading"]).pack(
                          anchor="w", padx=8)
            for b in c.species_origin_feat.get("benefits", []):
                ttk.Label(feat_sec,
                          text=f"    {b['name']}: {b.get('description', '')[:150]}",
                          wraplength=600, foreground=COLORS["fg_dim"]).pack(
                              anchor="w", padx=8, pady=1)

    # ── Spells ──────────────────────────────────────────────────
    if c.selected_cantrips or c.selected_spells:
        spell_sec = ttk.LabelFrame(parent, text="Spells")
        spell_sec.pack(fill=tk.X, pady=4)
        if c.selected_cantrips:
            ttk.Label(spell_sec,
                      text=f"  Cantrips: {', '.join(c.selected_cantrips)}",
                      wraplength=600).pack(anchor="w", padx=8, pady=2)
        if c.selected_spells:
            ttk.Label(spell_sec,
                      text=f"  Level 1: {', '.join(c.selected_spells)}",
                      wraplength=600).pack(anchor="w", padx=8, pady=2)

    # ── Equipment ───────────────────────────────────────────────
    equip_sec = ttk.LabelFrame(parent, text="Equipment")
    equip_sec.pack(fill=tk.X, pady=4)
    has_equip = False
    if c.character_class:
        for opt in c.character_class.get("starting_equipment", []):
            if opt["option"] == c.equipment_choice_class:
                ttk.Label(equip_sec, text=f"  {opt['items'][:200]}",
                          wraplength=600, foreground=COLORS["fg_dim"]).pack(
                              anchor="w", padx=8, pady=2)
                has_equip = True
    if c.background:
        for opt in c.background.get("equipment", []):
            if opt["option"] == c.equipment_choice_background:
                ttk.Label(equip_sec, text=f"  {opt['items'][:200]}",
                          wraplength=600, foreground=COLORS["fg_dim"]).pack(
                              anchor="w", padx=8, pady=2)
                has_equip = True
    if not has_equip:
        ttk.Label(equip_sec, text="  No equipment selected",
                  style="Dim.TLabel").pack(anchor="w", padx=8)
