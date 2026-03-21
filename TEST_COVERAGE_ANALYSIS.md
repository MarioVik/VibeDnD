# Test Coverage Analysis

## Current State

**VibeDnD has zero test coverage.** There are no test files, no testing framework configured, and no CI testing stage — only automated build pipelines.

This document identifies the highest-value areas to add tests, ordered by priority.

---

## Priority 1: Models — Pure Business Logic (Highest ROI)

These modules contain no GUI dependencies and can be unit-tested in isolation with standard `pytest`.

### `models/ability_scores.py` — `AbilityScores`

The math here is foundational — every stat on the character sheet derives from it.

**Gaps to cover:**
- `modifier()` boundary conditions: score 10 → `+0`, score 11 → `+0`, score 1 → `-5`, score 30 → `+10`
- `modifier()` uses integer division: score 9 → `-1` (not `0`)
- `point_buy_total()` with out-of-range scores (e.g. 16) — `POINT_BUY_COSTS.get(score, 0)` silently returns 0
- `is_valid_point_buy()` does not catch scores above 15 that aren't in the cost table (a score of 16 would pass the budget check but fail the range check)
- `is_valid_standard_array()` accepts any permutation of `[15,14,13,12,10,8]` — verify ordering doesn't matter
- `total()` correctly sums base + bonus

### `models/character.py` — `Character`

The most complex model. Many properties have non-trivial conditional logic.

**Gaps to cover:**
- `proficiency_bonus`: levels 1–4 → `+2`, 5–8 → `+3`, 17–20 → `+6`
- `hit_points` with `class_levels` empty (legacy path) vs populated
- `hit_points` first-level max vs subsequent-level average: `(hit_die // 2 + 1) + con_mod`
- `hit_points` multiclass scenario: fighter d10 levels + wizard d6 levels
- `hit_points` minimum of 1 even with very negative CON modifier
- `armor_class` unarmored baseline: standard vs Barbarian (`+CON`) vs Monk (`+WIS`)
- `armor_class` with shield only (no body armor) — should be `unarmored_ac + 2`
- `armor_class` with body armor + shield
- `armor_class` DEX cap: hide armor caps DEX at +2, plate caps at +0
- `multiclass_prereqs_met()` OR-logic for Fighter (STR or DEX), AND-logic for Monk (DEX and WIS)
- `multiclass_prereqs_met()` with unknown class (no entry in dict → always `True`)
- `all_skill_proficiencies` aggregates from class + background + level-up `new_proficiencies`
- `all_skill_expertise` only from `class_levels`
- `skill_modifier()` with/without proficiency, with/without expertise (note: expertise is tracked but not applied to `skill_modifier` — this may be a bug worth a test to document)
- `summary_text()` for single-class vs multiclass vs no selections

### `models/character_store.py` — Serialization / Persistence

Round-trip correctness is critical — a serialization bug silently corrupts saved characters.

**Gaps to cover:**
- `character_to_save_dict()` → `save_dict_to_character()` round-trip preserves all fields
- `_slugify()`: spaces, special chars, unicode, empty string, all-special-char string
- `_make_filename()` always produces a valid filesystem name
- `save_dict_to_character()` with missing optional keys (graceful defaults)
- `import_character_from_export()` with export-format JSON (key translation)
- `import_character_from_export()` with native save-format JSON (passthrough path)
- `list_saved_characters()` with empty directory, non-existent directory, corrupt JSON files
- `save_character()` creates directory if missing (`os.makedirs`)
- Backward-compat v1 load: dict without `class_levels` constructs a single `ClassLevel`

### `models/inventory_service.py` — Inventory & Wealth

Pure functions with clear inputs/outputs — very easy to test.

**Gaps to cover:**
- `cp_to_coins()`: 0 cp, 100 cp (= 1 gp), 1234 cp (= 12 gp 3 sp 4 cp), negative input
- `format_coins()` compact vs non-compact, zero case
- `add_item()` mode `"free"`: wealth unchanged, item added to inventory
- `add_item()` mode `"buy"` with sufficient funds: wealth decremented correctly
- `add_item()` mode `"buy"` with insufficient funds: returns `(False, ...)`
- `add_item()` mode `"buy"` with zero-cost item: returns `(False, ...)`
- `add_item()` stacking: adding same `item_id` twice increments `qty`
- `remove_item()` from custom inventory: reduces qty, removes entry at 0
- `remove_item()` quantity exceeding inventory: excess goes to `removed_items` overlay
- `normalize_item_key()`: whitespace normalization, case folding

---

## Priority 2: Export — Output Correctness

### `export/json_export.py`

`character_to_dict()` is a pure function that serializes to dict — straightforward to test.

**Gaps to cover:**
- All six ability scores are present with `base`, `bonus`, `total`, `modifier` keys
- `modifier` values are correct (cross-check against `AbilityScores.modifier()`)
- `saving_throws` marks proficient abilities correctly
- `skills` dict contains all skills with correct ability associations
- Fields like `hit_points`, `armor_class`, `speed`, `proficiency_bonus` match character properties
- `background_feat` is `None` when no background set
- Export then import via `import_character_from_export()` reconstructs an equivalent character

---

## Priority 3: Parsers — Data Integrity

Parsers run offline to regenerate `data/*.json`. Testing them guards against regressions when scraper data changes.

**Gaps to cover:**
- `base_parser.py`: `_slug()` function with edge cases (spaces, apostrophes, unicode)
- `class_parser.py`: parsed class dict contains required keys (`name`, `slug`, `hit_die`, `saving_throws`, `caster_type`)
- `spell_parser.py`: spell dicts have `name`, `level`, `school`, `casting_time`, `range`, `components`, `duration`
- Integration: run parsers against a small fixture of scraped JSON and verify output structure
- `run_all_parsers.py`: orchestration doesn't error with valid input

---

## Priority 4: GUI Data Loader — Integration Boundary

`gui/data_loader.py` is the boundary between the GUI and the data files. While the GUI itself is hard to test headlessly, the data loader's lookup logic is pure and testable.

**Gaps to cover:**
- `species_by_name`, `classes_by_name`, `backgrounds_by_name` dicts are populated from real data files
- `find_feat()` by exact name and by fuzzy/lowercase name
- Missing name returns `None` gracefully (not a `KeyError`)

---

## Recommended Test Infrastructure Setup

```
# Install test dependencies
pip install pytest pytest-cov

# Project layout
tests/
├── conftest.py                  # Shared fixtures (minimal Character, mock GameData)
├── models/
│   ├── test_ability_scores.py
│   ├── test_character.py
│   ├── test_character_store.py
│   └── test_inventory_service.py
├── export/
│   └── test_json_export.py
└── parsers/
    └── test_base_parser.py
```

Add to `pyproject.toml`:
```toml
[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=5.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.coverage.run]
source = ["models", "export"]
omit = ["gui/*", "parsers/*", "build*.py"]
```

Run with:
```bash
pytest --cov --cov-report=term-missing
```

---

## What NOT to Test (Yet)

- **`gui/`** — Tkinter widgets require a display. Mock-based GUI testing has poor ROI for this type of application. Focus on testing the models/logic that the GUI calls.
- **`export/pdf_export.py`** — 60 KB of fpdf2 layout code. Snapshot/golden-file testing is possible but brittle. Better to add smoke tests that verify the PDF is generated without errors before investing in content assertions.
- **`parsers/`** — The parsers depend on live web scraping or large fixture files. Integration tests are possible but should come after the model layer has coverage.
