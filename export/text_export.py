"""Export character as formatted text character sheet."""

from models.character import Character
from models.enums import ALL_SKILLS


def generate_text(character: Character) -> str:
    """Generate a formatted plain-text character sheet."""
    c = character
    lines = []

    # Header
    border = "=" * 60
    lines.append(border)
    lines.append(f"  {c.name.upper()}")
    lines.append(f"  {c.summary_text()}")
    if c.background:
        lines.append(f"  Background: {c.background_name}")
    if c.species_sub_choice:
        lines.append(f"  {c.species_sub_choice}")
    lines.append(border)

    # Combat Stats
    lines.append("")
    lines.append("COMBAT STATS")
    lines.append(f"  HP: {c.hit_points}  |  AC: {c.armor_class}  |  Speed: {c.speed} ft  |  Initiative: {'+' if c.initiative >= 0 else ''}{c.initiative}")
    lines.append(f"  Proficiency Bonus: +{c.proficiency_bonus}")

    # Ability Scores
    lines.append("")
    lines.append("ABILITY SCORES")
    row1 = []
    row2 = []
    for name in ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]:
        short = name[:3].upper()
        total = c.ability_scores.total(name)
        mod_str = c.ability_scores.modifier_str(name)
        row1.append(f"  {short}: {total:2d} ({mod_str})")
    lines.append("  " + "  ".join(f"{name[:3].upper()}: {c.ability_scores.total(name):2d} ({c.ability_scores.modifier_str(name)})"
                                   for name in ["Strength", "Dexterity", "Constitution"]))
    lines.append("  " + "  ".join(f"{name[:3].upper()}: {c.ability_scores.total(name):2d} ({c.ability_scores.modifier_str(name)})"
                                   for name in ["Intelligence", "Wisdom", "Charisma"]))

    # Saving Throws
    lines.append("")
    lines.append("SAVING THROWS")
    for name in ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]:
        prof = c.is_proficient_save(name)
        mod_str = c.saving_throw_str(name)
        marker = "* " if prof else "  "
        lines.append(f"  {marker}{name}: {mod_str}")
    lines.append("  (* = proficient)")

    # Skills
    lines.append("")
    lines.append("SKILLS")
    profs = c.all_skill_proficiencies
    for skill in ALL_SKILLS:
        is_prof = skill.display_name in profs
        mod_str = c.skill_modifier_str(skill.display_name)
        marker = "* " if is_prof else "  "
        lines.append(f"  {marker}{mod_str:>3}  {skill.display_name} ({skill.ability.value[:3].upper()})")

    # Features & Traits
    if c.species and c.species.get("traits"):
        lines.append("")
        lines.append(f"{c.species_name.upper()} TRAITS")
        for trait in c.species["traits"]:
            lines.append(f"  {trait['name']}: {trait.get('description', '')[:200]}")

    if c.character_class:
        lines.append("")
        if c.level == 1 and c.character_class.get("level_1_features"):
            lines.append(f"{c.class_name.upper()} FEATURES (LEVEL 1)")
            for feat in c.character_class["level_1_features"]:
                lines.append(f"  {feat['name']}")
                if feat.get("description"):
                    lines.append(f"    {feat['description'][:200]}")
        elif c.class_levels:
            header = f"{c.class_name.upper()} FEATURES" if not c.is_multiclass else "CLASS FEATURES"
            lines.append(header)
            for cl in c.class_levels:
                items = []
                if cl.feat_choice:
                    items.append(f"Feat: {cl.feat_choice}")
                if cl.subclass_slug:
                    items.append(f"Subclass: {cl.subclass_slug.replace('-', ' ').title()}")
                if items:
                    prefix = f"{cl.class_slug.title()} " if c.is_multiclass else ""
                    lines.append(f"  {prefix}Level {cl.class_level}: {', '.join(items)}")

    # Feats
    if c.feat or c.species_origin_feat:
        lines.append("")
        lines.append("FEATS")
        if c.feat:
            feat_name = c.background.get("feat", c.feat.get("name", "")) if c.background else c.feat.get("name", "")
            lines.append(f"  {feat_name}  (from Background)")
            for b in c.feat.get("benefits", []):
                lines.append(f"    {b['name']}: {b.get('description', '')[:150]}")
        if c.species_origin_feat:
            sp_name = c.species_name if c.species else "Species"
            lines.append(f"  {c.species_origin_feat['name']}  (from {sp_name})")
            for b in c.species_origin_feat.get("benefits", []):
                lines.append(f"    {b['name']}: {b.get('description', '')[:150]}")

    # Spells
    if c.selected_cantrips or c.selected_spells:
        lines.append("")
        lines.append("SPELLS")
        if c.selected_cantrips:
            lines.append(f"  Cantrips: {', '.join(c.selected_cantrips)}")
        if c.selected_spells:
            lines.append(f"  Level 1: {', '.join(c.selected_spells)}")

    # Equipment
    lines.append("")
    lines.append("EQUIPMENT")
    if c.character_class:
        for opt in c.character_class.get("starting_equipment", []):
            if opt["option"] == c.equipment_choice_class:
                lines.append(f"  {opt['items'][:200]}")
    if c.background:
        for opt in c.background.get("equipment", []):
            if opt["option"] == c.equipment_choice_background:
                lines.append(f"  {opt['items'][:200]}")

    lines.append("")
    lines.append(border)

    return "\n".join(lines)


def export_text(character: Character, path: str):
    """Save character as text file."""
    text = generate_text(character)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
