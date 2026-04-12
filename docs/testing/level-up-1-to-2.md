# Level 1→2 Level-Up Rules

This document specifies every wizard step, feature, choice, and validation rule
that must be verified when leveling any class from 1 to 2. It is the
human-readable companion to the BDD feature files in `tests/bdd/features/`.

---

## Wizard Step Visibility

Every level-up shows: **Class** (multiclass selector), **Hit Points**, **Features**.
Additional steps appear conditionally:

| Step Key | Condition at Level 2 | Classes |
|----------|---------------------|---------|
| lu_class | Always (character has ≥1 level) | All 13 |
| lu_hp | Always | All 13 |
| lu_features | Always | All 13 |
| lu_subclass | level grants "Subclass" | None at level 2 |
| lu_asi | level grants "Ability Score Improvement" | None at level 2 |
| lu_proficiencies | subclass grants non-automatic proficiency/expertise | None at level 2 |
| lu_languages | Deft Explorer feature | Ranger |
| lu_choices | class_choices gains_by_level has entry for "2" | Artificer, Sorcerer, Warlock |
| lu_spells | new cantrips > 0 or new prepared > 0 | Artificer, Bard, Cleric, Druid, Paladin, Ranger, Sorcerer, Warlock, Wizard |
| lu_swap | class in {bard, sorcerer, warlock} AND has cantrips/spells | Bard, Sorcerer, Warlock |

---

## Level 2 Feature Matrix

| Class | Features | Extra Columns |
|-------|----------|---------------|
| Artificer | Replicate Magic Item | Plans Known: 4, Magic Items: 2 |
| Barbarian | Danger Sense, Reckless Attack | Rages: 2, Rage Damage: 2, Weapon Mastery: 2 |
| Bard | Expertise, Jack of all Trades | Bardic Die: D6 |
| Cleric | Channel Divinity | Channel Divinity: 2 |
| Druid | Wild Shape, Wild Companion | Wild Shape: 2 |
| Fighter | Action Surge (One Use), Tactical Mind | Second Wind: 2, Weapon Mastery: 3 |
| Monk | Monk's Focus, Unarmored Movement, Uncanny Metabolism | Martial Arts: 1d6, Focus Points: 2, Unarmored Movement: +10 ft |
| Paladin | Fighting Style, Paladin's Smite | Channel Divinity: None |
| Ranger | Deft Explorer, Fighting Style | Favored Enemy: 2 |
| Rogue | Cunning Action | Sneak Attack: 1d6 |
| Sorcerer | Font of Magic, Metamagic | Sorcery Points: 2 |
| Warlock | Magical Cunning | Eldritch Invocations: 3 |
| Wizard | Scholar | (none) |

---

## Spell Deltas at Level 2

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

## Class Choices at Level 2

| Class | Choice Label | Gains at Level 2 |
|-------|-------------|------------------|
| Artificer | Magic Item Plan | 4 |
| Sorcerer | Metamagic Option | 2 |
| Warlock | Eldritch Invocation | 2 |

---

## Spell Swap Eligibility

Bard, Sorcerer, and Warlock may swap one cantrip and/or one spell if they
already know any. At level 2 (coming from level 1), they will have spells
selected during creation, so the swap step should be visible.

---

## Deft Explorer Languages (Ranger Level 2)

Ranger gains the Deft Explorer feature at level 2, which grants 2 language
proficiencies. The language step validates that exactly 2 are selected.

---

## HP Step

- Mode: "average" or "manual"
- Average = hit_die / 2 + 1
- Manual must be a valid integer ≥ 1
- HP is recorded in `ClassLevel.hp_roll`

---

## Validation Rules

| Step | Valid When |
|------|-----------|
| lu_class | Multiclass prereqs met (or same class) |
| lu_hp | average mode OR manual value ≥ 1 |
| lu_features | Always valid (informational) |
| lu_subclass | Subclass selected (N/A at level 2) |
| lu_asi | Feat selected + ASI configured (N/A at level 2) |
| lu_proficiencies | All required picks made (N/A at level 2) |
| lu_languages | 2 languages selected |
| lu_choices | Required number of choices selected |
| lu_spells | Required cantrips + spells selected |
| lu_swap | No half-finished swaps |

---

## apply_level_up Persistence

After `build_class_level()` + `apply_level_up()`:

- `character.class_levels` has 2 entries
- `character.level` == 2
- HP roll is recorded
- New spells added to `character.selected_spells`
- New cantrips added to `character.selected_cantrips`
- Class choices stored in `ClassLevel.new_choices`
- ASI increases applied (N/A at level 2)
- Languages added to `character.chosen_languages` (Ranger)
