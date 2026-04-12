# Level 1 Species, Background & Feat Creation Rules

This document specifies every species trait, background grant, and feat mechanic
that must be verified during character creation. It is the human-readable
companion to the BDD feature files in `tests/bdd/features/`.

---

## Species Matrix

Every species grants traits automatically. Some species also require a sub-choice
(lineage, ancestry, or trait option) and/or offer a size selection.

| Name | Source | Trait Count | Sub-Choice Type | Size Options | Grants Origin Feat |
|------|--------|-------------|-----------------|--------------|-------------------|
| Aasimar | Player's Handbook | 8 | none | Medium, Small | no |
| Boggart | Lorwyn - First Light | 4 | none | Medium | no |
| Changeling | Eberron - Forge of the Artificer | 2 | none | Medium, Small | no |
| Deep Gnome | Player's Handbook (2014) | 5 | none | Medium | no |
| Dhampir | Astarion's Book of Hungers | 6 | none | Medium, Small | no |
| Dragonborn | Player's Handbook | 5 | none | Medium | no |
| Dwarf | Player's Handbook | 4 | none | Medium | no |
| Elf | Player's Handbook | 5 | lineage | Medium | no |
| Faerie | Lorwyn - First Light | 2 | none | Medium | no |
| Flamekin | Lorwyn - First Light | 3 | none | Medium | no |
| Gnome | Player's Handbook | 5 | trait-option (Gnomish Lineage) | Medium | no |
| Goliath | Player's Handbook | 9 | trait-option (Giant Ancestry) | Medium | no |
| Halfling | Player's Handbook | 4 | none | Medium | no |
| Human | Player's Handbook | 3 | none | Medium, Small | yes (Versatile) |
| Kalashtar | Eberron - Forge of the Artificer | 4 | none | Medium | no |
| Khoravar | Eberron - Forge of the Artificer | 5 | none | Medium, Small | no |
| Lorwyn Changeling | Lorwyn - First Light | 4 | none | Medium, Small | no |
| Orc | Player's Handbook | 3 | none | Medium | no |
| Rimekin | Lorwyn - First Light | 3 | none | Medium, Small | no |
| Shifter | Eberron - Forge of the Artificer | 7 | trait-option (Shifting Option) | Medium, Small | no |
| Tiefling | Player's Handbook | 3 | lineage | Medium, Small | no |
| Warforged | Eberron - Forge of the Artificer | 4 | none | Medium, Small | no |

### Sub-Choice Details

| Species | Label | Options |
|---------|-------|---------|
| Elf | Lineage | Drow, High Elf, Wood Elf, Lorwyn Elf, Shadowmoor Elf |
| Tiefling | Lineage | Abyssal, Chthonic, Infernal |
| Gnome | Gnomish Lineage | Forest Gnome, Rock Gnome |
| Goliath | Giant Ancestry | Cloud's Jaunt, Fire's Burn, Frost's Chill, Hill's Tumble, Stone's Endurance, Storm's Thunder |
| Shifter | Shifting Option | Beasthide, Longtooth, Swiftstride, Wildhunt |

### Creation Rules

1. Every character must select a species (`character.species is not None`).
2. Species with sub-choices block completion until one is selected.
3. Species with multiple size options default to the first option; the player may change it.
4. Human's Versatile trait grants one origin feat (handled on the Feat step).
5. Species traits are displayed via `get_species_trait_cards()` on the character sheet.
6. Trait option choices (Gnome/Goliath/Shifter) are excluded from the general trait card list and shown as radio buttons instead.

---

## Background Matrix

Every background grants: 2 skill proficiencies, 1 tool proficiency, 1 origin feat,
ability score options (usually 3 abilities for 2/1 or 1/1/1 distribution), and
equipment choices.

### Creation Rules

1. Every character must select a background (`character.background is not None`).
2. Background skill proficiencies are automatically added to the character's proficiency set.
3. The background feat is set on `character.feat`.
4. Ability bonuses are applied via `apply_background_ability_bonuses()` in either "2/1" or "1/1/1" mode.
5. The one background with no ability scores (Shadowmasters Exile) clears all bonuses.
6. Equipment choices default to option "A".

---

## Origin Feat Matrix

Origin feats are available for species feat selection (Human Versatile) and
background feat assignment.

| Feat Name | Source |
|-----------|--------|
| Alert | Player's Handbook |
| Crafter | Player's Handbook |
| Healer | Player's Handbook |
| Lucky | Player's Handbook |
| Magic Initiate | Player's Handbook |
| Musician | Player's Handbook |
| Savage Attacker | Player's Handbook |
| Skilled | Player's Handbook |
| Tavern Brawler | Player's Handbook |
| Tough | Player's Handbook |
| Child Of The Sun | Lorwyn - First Light |
| Cult Of The Dragon Initiate | Forgotten Realms - Heroes of Faerun |
| Emerald Enclave Fledgling | Forgotten Realms - Heroes of Faerun |
| Harper Agent | Forgotten Realms - Heroes of Faerun |
| Lords Alliance Agent | Forgotten Realms - Heroes of Faerun |
| Purple Dragon Rook | Forgotten Realms - Heroes of Faerun |
| Shadowmoor Hexer | Lorwyn - First Light |
| Spellfire Spark | Forgotten Realms - Heroes of Faerun |
| Tireless Reveler | Astarion's Book of Hungers |
| Tyro Of The Gauntlet | Forgotten Realms - Heroes of Faerun |
| Vampire Hunter | Astarion's Book of Hungers |
| Vampire S Plaything | Astarion's Book of Hungers |
| Zhentarim Ruffian | Forgotten Realms - Heroes of Faerun |

### Feat Creation Rules

1. The feat step is visible only when the selected species grants an origin feat.
2. The feat step blocks completion until a feat is selected (when visible).
3. `get_owned_feat_names()` tracks background feat, species origin feat, and warlock lessons feat.
4. Duplicate feats across sources are detected and the species origin feat is cleared if it conflicts.
5. Feat benefits are displayed on the character sheet and in the summary step.
