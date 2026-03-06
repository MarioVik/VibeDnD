"""Run all parsers, write output to data/, and validate cross-references."""

import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.spell_parser import parse_spells
from parsers.class_parser import parse_classes
from parsers.species_parser import parse_species
from parsers.background_parser import parse_backgrounds
from parsers.feat_parser import parse_feats

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dnd2024_data.json")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def load_raw_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data, filename):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def validate(spells, classes, species, backgrounds, feats):
    """Cross-reference validation."""
    warnings = []

    # Build lookup sets
    spell_names = {s["name"].lower() for s in spells}
    class_names = {c["name"].lower() for c in classes}
    feat_names = {f["name"].lower() for f in feats}

    # Check: background feats should exist in feats data
    for bg in backgrounds:
        if bg["feat"]:
            # Normalize: "Magic Initiate (Cleric)" -> check "Magic Initiate"
            feat_base = bg["feat"].split("(")[0].strip().lower()
            if feat_base not in feat_names:
                warnings.append(f"Background '{bg['name']}' references feat '{bg['feat']}' not found in feats data")

    # Check: spell classes should be known classes
    known_class_names = {"artificer", "bard", "cleric", "druid", "fighter", "monk",
                         "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard"}
    for spell in spells:
        for cls in spell["classes"]:
            if cls.lower() not in known_class_names:
                warnings.append(f"Spell '{spell['name']}' references unknown class '{cls}'")

    return warnings


def main():
    print("Loading raw data...")
    raw = load_raw_data()

    # Run parsers
    print("\n--- Parsing Spells ---")
    spells = parse_spells(raw.get("spells", []))
    print(f"  Parsed {len(spells)} spells")

    print("\n--- Parsing Classes ---")
    classes = parse_classes(raw.get("classes", []))
    print(f"  Parsed {len(classes)} classes")

    print("\n--- Parsing Species ---")
    species = parse_species(raw.get("species", []))
    print(f"  Parsed {len(species)} species")

    print("\n--- Parsing Backgrounds ---")
    backgrounds = parse_backgrounds(raw.get("backgrounds", []))
    print(f"  Parsed {len(backgrounds)} backgrounds")

    print("\n--- Parsing Feats ---")
    feats = parse_feats(raw.get("feats", []))
    print(f"  Parsed {len(feats)} feats")

    # Save output
    print("\n--- Saving to data/ ---")
    for data, filename in [
        (spells, "spells.json"),
        (classes, "classes.json"),
        (species, "species.json"),
        (backgrounds, "backgrounds.json"),
        (feats, "feats.json"),
    ]:
        path = save_json(data, filename)
        print(f"  Saved {path}")

    # Validate
    print("\n--- Cross-reference validation ---")
    warnings = validate(spells, classes, species, backgrounds, feats)
    if warnings:
        print(f"  {len(warnings)} warnings:")
        for w in warnings[:20]:
            print(f"    - {w}")
        if len(warnings) > 20:
            print(f"    ... and {len(warnings) - 20} more")
    else:
        print("  All cross-references valid!")

    # Summary
    print(f"\n=== Summary ===")
    print(f"  Spells:      {len(spells)}")
    print(f"  Classes:     {len(classes)}")
    print(f"  Species:     {len(species)}")
    print(f"  Backgrounds: {len(backgrounds)}")
    print(f"  Feats:       {len(feats)}")
    print(f"  Total:       {len(spells) + len(classes) + len(species) + len(backgrounds) + len(feats)}")

    # Spot checks
    print(f"\n=== Spot Checks ===")
    for s in spells:
        if s["name"].lower() == "fireball":
            print(f"  Fireball: level={s['level']}, school={s['school']}, classes={s['classes']}")
            break

    for c in classes:
        if c["name"].lower() == "fighter":
            print(f"  Fighter: hit_die=d{c['hit_die']}, saves={c['saving_throws']}, caster={c['caster_type']}")
            break

    for c in classes:
        if c["name"].lower() == "wizard":
            print(f"  Wizard: hit_die=d{c['hit_die']}, cantrips={c['cantrips_known']}, prepared={c['spells_prepared']}, slots={c['spell_slots']}")
            break

    for bg in backgrounds:
        if bg["name"].lower() == "acolyte":
            print(f"  Acolyte: abilities={bg['ability_scores']}, feat={bg['feat']}, skills={bg['skill_proficiencies']}")
            break

    for sp in species:
        if sp["name"].lower() == "human":
            print(f"  Human: size={sp['size']}, speed={sp['speed']}, traits={len(sp['traits'])}")
            break

    for sp in species:
        if sp["name"].lower() == "elf":
            print(f"  Elf: sub_choices={'Yes' if sp['sub_choices'] else 'No'}, traits={len(sp['traits'])}")
            break


if __name__ == "__main__":
    main()
