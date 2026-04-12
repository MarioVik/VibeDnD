# Level 2→3 Level-Up Rules

This document specifies every wizard step, feature, choice, and validation rule
that must be verified when leveling any class from 2 to 3. It is the
human-readable companion to the BDD feature files in `tests/bdd/features/`.

---

## Key Difference from Level 2

**Every class gains a subclass at level 3.** This is the defining event of this
level-up. The subclass step becomes visible and mandatory.

---

## Wizard Step Visibility

Every level-up shows: **Class**, **Hit Points**, **Features**, **Subclass**.
Additional steps appear conditionally:

| Step Key | Condition at Level 3 | Classes |
|----------|---------------------|---------|
| lu_class | Always (character has ≥1 level) | All 13 |
| lu_hp | Always | All 13 |
| lu_features | Always | All 13 |
| lu_subclass | All classes gain subclass at 3 | All 13 |
| lu_asi | None at level 3 | None |
| lu_proficiencies | Subclass grants non-auto proficiency | None at level 3 |
| lu_languages | Deft Explorer feature | None at level 3 |
| lu_choices | Subclass-specific (Battle Master, Arcane Archer, Tattooed Warrior, Hunter) | Fighter (2/9), Monk (1/7), Ranger (1/6) |
| lu_spells | new cantrips > 0 or new prepared > 0 | Artificer, Bard, Cleric, Druid, Paladin, Ranger, Sorcerer, Warlock, Wizard |
| lu_swap | class in {bard, sorcerer, warlock} AND has spells | Bard, Sorcerer, Warlock |

---

## Level 3 Feature Matrix

| Class | Features (excluding subclass) | Extra Columns |
|-------|-------------------------------|---------------|
| Artificer | (none besides subclass) | Plans Known: 4, Magic Items: 2 |
| Barbarian | Primal Knowledge | Rages: 3, Rage Damage: 2, Weapon Mastery: 2 |
| Bard | (none besides subclass) | Bardic Die: D6 |
| Cleric | (none besides subclass) | Channel Divinity: 2 |
| Druid | (none besides subclass) | Wild Shape: 2 |
| Fighter | (none besides subclass) | Second Wind: 2, Weapon Mastery: 3 |
| Monk | Deflect Attacks | Martial Arts: 1d6, Focus Points: 3, Unarmored Movement: +10 ft |
| Paladin | Channel Divinity | Channel Divinity: 2 |
| Ranger | (none besides subclass) | Favored Enemy: 2 |
| Rogue | Steady Aim | Sneak Attack: 2d6 |
| Sorcerer | (none besides subclass) | Sorcery Points: 3 |
| Warlock | (none besides subclass) | Eldritch Invocations: 3 |
| Wizard | (none besides subclass) | (none) |

---

## Spell Deltas at Level 3

| Class | New Cantrips | New Prepared Spells |
|-------|-------------|-------------------|
| Artificer | 0 | 1 |
| Barbarian | 0 | 0 |
| Bard | 0 | 1 |
| Cleric | 0 | 1 |
| Druid | 0 | 1 |
| Fighter | 0 | 0 |
| Monk | 0 | 0 |
| Paladin | 0 | 1 |
| Ranger | 0 | 1 |
| Rogue | 0 | 0 |
| Sorcerer | 0 | 2 |
| Warlock | 0 | 1 |
| Wizard | 0 | 1 |

---

## Subclass Selection (All Classes)

Every class must select a subclass at level 3. Subclass selection is mandatory.
The number of available subclasses varies per class (93 total across all 13).

---

## Class Choices at Level 3 (Subclass-Specific)

| Class/Subclass | Choice Label | Gains |
|---------------|-------------|-------|
| Fighter / Battle Master | Maneuver | 3 |
| Fighter / Arcane Archer | Arcane Shot Option | 2 |
| Monk / Tattooed Warrior | Magic Tattoo | 2 |
| Ranger / Hunter | Feature Option | 1 |

---

## Validation Rules

| Step | Valid When |
|------|-----------|
| lu_class | Multiclass prereqs met (or same class) |
| lu_hp | average mode OR manual value ≥ 1 |
| lu_features | Always valid (informational) |
| lu_subclass | Subclass name/slug selected |
| lu_choices | Required number of choices selected |
| lu_spells | Required cantrips + spells selected |
| lu_swap | No half-finished swaps |

---

## apply_level_up Persistence

After `build_class_level()` + `apply_level_up()`:

- `character.class_levels` has 3 entries
- `character.level` == 3
- HP roll is recorded
- Subclass slug stored in `ClassLevel.subclass_slug`
- New spells added to `character.selected_spells`
- Class choices stored in `ClassLevel.new_choices` (subclass-specific)
