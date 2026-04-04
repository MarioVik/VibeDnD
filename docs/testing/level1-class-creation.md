# Level 1 Class Creation Specification

This document is the human-readable spec for level 1 class behavior during character creation.

Scope:
- Covers every level 1 feature listed in `class_progressions.json`.
- Distinguishes between documented runtime features and creation-time requirements.
- Tracks which wizard surface owns each player choice.
- Matches the executable rules in `models/level1_class_rules.py`.

Categories:
- `document-only`: runtime feature, no creation-time choice
- `auto grant`: granted automatically, no player choice
- `existing-step choice`: resolved on an existing wizard step
- `new class-feature choice`: resolved on the dedicated Class Features step

## Feature Matrix

| Class | Feature | Category | Wizard Surface | Persisted State | Completion Rule | Coverage |
| --- | --- | --- | --- | --- | --- | --- |
| Artificer | Spellcasting | existing-step choice | spells | `selected_cantrips`, `selected_spells` | Creation stays blocked until the required cantrip and prepared-spell choices are selected. | `catalog`, `completion` |
| Artificer | Tinker's Magic | auto grant | none | derived only | No creation-time choice. The feature is documented and excluded from finish-gating. | `catalog` |
| Barbarian | Rage | document-only | none | derived only | No creation-time choice. The feature is documented and excluded from finish-gating. | `catalog` |
| Barbarian | Unarmored Defense | document-only | none | derived only | No creation-time choice. The feature is documented and excluded from finish-gating. | `catalog` |
| Barbarian | Weapon Mastery | new class-feature choice | class_features | `level1_class_choices.weapon_mastery` | Creation stays blocked until 2 valid weapon masteries are selected. | `catalog`, `completion`, `weapon-mastery` |
| Bard | Bardic Inspiration | document-only | none | derived only | No creation-time choice. The feature is documented and excluded from finish-gating. | `catalog` |
| Bard | Spellcasting | existing-step choice | spells | `selected_cantrips`, `selected_spells` | Creation stays blocked until the required cantrip and prepared-spell choices are selected. | `catalog`, `completion` |
| Cleric | Spellcasting | existing-step choice | spells | `selected_cantrips`, `selected_spells` | Creation stays blocked until the required cantrip and prepared-spell choices are selected, including the extra cantrip from Thaumaturge. | `catalog`, `completion`, `cleric-order` |
| Cleric | Divine Order | new class-feature choice | class_features | `level1_class_choices.divine_order` | Creation stays blocked until a Divine Order is selected. | `catalog`, `completion`, `cleric-order` |
| Druid | Spellcasting | existing-step choice | spells | `selected_cantrips`, `selected_spells` | Creation stays blocked until the required cantrip and prepared-spell choices are selected, including the extra cantrip from Magician. | `catalog`, `completion`, `druid-order` |
| Druid | Druidic | auto grant | languages | derived only | No creation-time choice. The feature is documented and excluded from finish-gating. | `catalog` |
| Druid | Primal Order | new class-feature choice | class_features | `level1_class_choices.primal_order` | Creation stays blocked until a Primal Order is selected. | `catalog`, `completion`, `druid-order` |
| Fighter | Fighting Style | new class-feature choice | class_features | `level1_class_choices.fighting_style` | Creation stays blocked until a Fighting Style is selected. | `catalog`, `completion` |
| Fighter | Second Wind | document-only | none | derived only | No creation-time choice. The feature is documented and excluded from finish-gating. | `catalog` |
| Fighter | Weapon Mastery | new class-feature choice | class_features | `level1_class_choices.weapon_mastery` | Creation stays blocked until 3 valid weapon masteries are selected. | `catalog`, `completion`, `weapon-mastery` |
| Monk | Martial Arts | document-only | none | derived only | No creation-time choice. The feature is documented and excluded from finish-gating. | `catalog` |
| Monk | Unarmored Defense | document-only | none | derived only | No creation-time choice. The feature is documented and excluded from finish-gating. | `catalog` |
| Paladin | Lay On Hands | document-only | none | derived only | No creation-time choice. The feature is documented and excluded from finish-gating. | `catalog` |
| Paladin | Spellcasting | existing-step choice | spells | `selected_spells` | Creation stays blocked until the required prepared spells are selected. | `catalog`, `completion` |
| Paladin | Weapon Mastery | new class-feature choice | class_features | `level1_class_choices.weapon_mastery` | Creation stays blocked until 2 valid weapon masteries are selected. | `catalog`, `completion`, `weapon-mastery` |
| Ranger | Spellcasting | existing-step choice | spells | `selected_spells` | Creation stays blocked until the required prepared spells are selected. | `catalog`, `completion` |
| Ranger | Favored Enemy | auto grant | none | derived only | No creation-time choice. The feature is documented and excluded from finish-gating. | `catalog` |
| Ranger | Weapon Mastery | new class-feature choice | class_features | `level1_class_choices.weapon_mastery` | Creation stays blocked until 2 valid weapon masteries are selected. | `catalog`, `completion`, `weapon-mastery` |
| Rogue | Expertise | existing-step choice | skills | `class_levels[0].new_expertise` | Creation stays blocked until 2 valid expertise picks are selected from proficient skills. | `catalog`, `completion`, `rogue-expertise` |
| Rogue | Sneak Attack | document-only | none | derived only | No creation-time choice. The feature is documented and excluded from finish-gating. | `catalog` |
| Rogue | Thieves' Cant | existing-step choice | languages | `chosen_languages` | Creation stays blocked until the Rogue extra language choice is selected alongside the base language choices. | `catalog`, `rogue-expertise` |
| Rogue | Weapon Mastery | new class-feature choice | class_features | `level1_class_choices.weapon_mastery` | Creation stays blocked until 2 valid weapon masteries are selected. | `catalog`, `completion`, `weapon-mastery` |
| Sorcerer | Spellcasting | existing-step choice | spells | `selected_cantrips`, `selected_spells` | Creation stays blocked until the required cantrip and prepared-spell choices are selected. | `catalog`, `completion` |
| Sorcerer | Innate Sorcery | document-only | none | derived only | No creation-time choice. The feature is documented and excluded from finish-gating. | `catalog` |
| Warlock | Eldritch Invocations | new class-feature choice | class_features | `level1_class_choices.warlock_invocation` and nested `level1_class_choices.*` fields | Creation stays blocked until an invocation is selected and any creation-time nested choice is resolved. | `catalog`, `completion`, `warlock` |
| Warlock | Pact Magic | existing-step choice | spells | `selected_cantrips`, `selected_spells`, `level1_class_choices.warlock_invocation_cantrip` | Creation stays blocked until the required cantrip and prepared-spell choices are selected and any blast-invocation cantrip binding is resolved. | `catalog`, `completion`, `warlock` |
| Wizard | Spellcasting | existing-step choice | spells | `selected_cantrips`, `selected_spells` | Creation stays blocked until the required cantrip and prepared-spell choices are selected. | `catalog`, `completion` |
| Wizard | Ritual Adept | document-only | none | derived only | No creation-time choice. The feature is documented and excluded from finish-gating. | `catalog` |
| Wizard | Arcane Recovery | document-only | none | derived only | No creation-time choice. The feature is documented and excluded from finish-gating. | `catalog` |

## Creation-Relevant Rules By Class

| Class | Required creation-time choices at level 1 |
| --- | --- |
| Artificer | Class skills, class equipment, cantrips, prepared spells |
| Barbarian | Class skills, class equipment, weapon masteries |
| Bard | Class skills, class equipment, cantrips, prepared spells |
| Cleric | Class skills, class equipment, Divine Order, cantrips, prepared spells |
| Druid | Class skills, class equipment, Primal Order, cantrips, prepared spells |
| Fighter | Class skills, class equipment, Fighting Style, weapon masteries |
| Monk | Class skills, class equipment |
| Paladin | Class skills, class equipment, weapon masteries, prepared spells |
| Ranger | Class skills, class equipment, weapon masteries, prepared spells |
| Rogue | Class skills, class equipment, expertise, weapon masteries, extra language |
| Sorcerer | Class skills, class equipment, cantrips, prepared spells |
| Warlock | Class skills, class equipment, invocation, any invocation nested choice, cantrips, prepared spells |
| Wizard | Class skills, class equipment, cantrips, prepared spells |
