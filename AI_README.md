# AI Documentation: VibeDnD Repository

This document is intended for AI agents (Claude, Cursor, GPT, etc.) to understand the repository structure and avoid reading large data files unnecessarily.

## Project Overview
VibeDnD is a D&D 2024 Character Creator desktop app built with Python and Tkinter.

## Repository Structure
- `main.py`: Entry point.
- `paths.py`: Resolves paths for both source and PyInstaller-packaged contexts. Always use this for file paths.
- `gui/`: Tkinter UI (see **GUI Architecture** below).
- `models/`: Character data models (see **Models** below).
- `export/`: Export to PDF (`pdf_export.py`) and JSON (`json_export.py`).
- `data/`: Structured JSON game data. **DO NOT READ THESE ENTIRELY.** Use the schemas below.
- `parsers/`: Scripts that regenerate `data/*.json` from raw sources. Edit these instead of the JSON files directly.
- `dnd2024_data.json`: 1.25MB raw scraped data. **DO NOT READ.**
- `build.py`, `build_macos.py`, `build_ubuntu.py`: PyInstaller build scripts per platform.
- `installer.iss`: Inno Setup script for Windows installer. Runs after `build.py --onefile`.
- `settings.json`: User preferences (source filters). Lives next to the executable; created at runtime.

## GUI Architecture (`gui/`)
The app uses a **screen-manager pattern**: `app.py` switches between three screens:
- `home_screen.py` — Character list, create/import/delete.
- **Wizard** (character creation) — `base_step.py` defines the `WizardStep` base class. Each step is a separate file:
  - `step_species.py` → `step_class.py` → `step_background.py` → `step_ability_scores.py` → `step_feat.py` → `step_spells.py` → `step_equipment.py` → `step_summary.py`
- `character_viewer.py` — View/level-up/export a finished character.

Supporting modules:
- `data_loader.py` — `GameData` class wrapping all JSON data access.
- `level_up_wizard.py` — Multi-step level-up dialog (HP, ASI/feat, subclass, spells).
- `add_inventory_dialog.py` — Item browser with category/cost filtering.
- `sheet_builder.py` — Builds the character sheet display.
- `equipment_utils.py` — Equipment formatting helpers.
- `source_config.py` — Source filter toggle UI.
- `theme.py` — `COLORS` and `FONTS` constants (dark parchment theme).
- `widgets.py` — Reusable widgets: `ScrollableFrame`, `WrappingLabel`, `AlertDialog`.

## Models (`models/`)
- `character.py` — `Character` dataclass: identity, abilities, class levels, equipment, inventory, spells, feats.
- `ability_scores.py` — `AbilityScores`: base scores, modifiers, racial bonuses.
- `class_level.py` — `ClassLevel`: tracks class slug + level for multiclass.
- `enums.py` — `Ability`, `Skill` enums and `ALL_SKILLS` constant.
- `character_store.py` — Save/load/delete characters as JSON files.
- `inventory_service.py` — Add/remove items, wealth tracking, transaction history.
- `standard_actions.py` — D&D standard action definitions.

## Data Schemas (`data/*.json`)

### `classes.json`
```json
{
  "name": "Artificer", "slug": "artificer", "source": "Eberron - ...",
  "description": "...",
  "primary_ability": ["Intelligence"],
  "hit_die": 8,
  "saving_throws": ["Constitution", "Intelligence"],
  "skill_choices": { "count": 2, "options": ["Arcana", "History", ...] },
  "weapon_proficiencies": ["Simple weapons"],
  "armor_proficiencies": ["Light", "Medium armor", "Shields"],
  "starting_equipment": [{ "option": "A", "items": "..." }, { "option": "B", "items": "150 GP" }],
  "caster_type": "half",  // "full", "half", "third", or null
  "spellcasting_ability": "Intelligence",
  "cantrips_known": 2, "spells_prepared": 2,
  "spell_slots": { "1st": 2 }
}
```

### `items.json`
```json
{
  "id": "adventuring-gear:acid",
  "name": "Acid",
  "category": "Adventuring Gear",  // Adventuring Gear, Armor, Weapons, Mounts & Vehicles, Poisons, Tools, Magic Items
  "cost_cp": 2500,
  "description": "...",
  "source": "..."
}
```

### `spells.json` (~500KB)
```json
{
  "name": "Acid Splash", "level": 0, "school": "Evocation",
  "classes": ["Artificer", "Sorcerer", "Wizard"],
  "casting_time": "Action", "ritual": false, "range": "60 feet",
  "components": { "V": true, "S": true, "M": "..." },
  "concentration": false, "duration": "Instantaneous",
  "description": "...", "higher_levels": null, "cantrip_upgrade": "...",
  "source": "Player's Handbook"
}
```

### `feats.json` (~150KB)
```json
{
  "name": "Alert", "source": "Player's Handbook", "category": "origin",
  "prerequisites": null,
  "benefits": [{ "name": "Initiative Proficiency", "description": "..." }],
  "ability_score_increase": null
}
```
`category` is one of `origin`, `general`, `fighting_style`, `epic_boon`, `dragonmark`, or `greater_dragonmark`

### `subclasses.json` (~300KB)
```json
{
  "name": "Alchemist", "slug": "alchemist", "class_slug": "artificer",
  "source": "", "description": "...",
  "feature_levels": [3, 5, 9, 15],
  "features": { "3": [{ "name": "Tool Proficiency.", "description": "..." }] }
}
```

### `class_progressions.json` (~200KB)
```json
{
  "name": "Artificer", "slug": "artificer", "caster_type": "half",
  "levels": [{
    "level": 1, "proficiency_bonus": 2,
    "features": ["Spellcasting", "Tinker's Magic"],
    "cantrips": 2, "prepared_spells": 2, "spell_slots": { "1st": 2 },
    "extra": {},
    "feature_details": [{ "name": "Spellcasting", "description": "..." }]
  }]
}
```

### `species.json`, `backgrounds.json`
Follow a `{"name": "...", "source": "...", "description": "...", "features": [{"name": "...", "description": "..."}]}` pattern.

## Legacy (2014 / “5e”) Content Policy (Species, Backgrounds, Subclasses)

This project is a **2024 rules (“5.5e”) character builder** that may optionally include **legacy 2014 (“5e”) options**. When adding legacy content, follow these rules so the app remains rules-consistent and future AIs don’t accidentally “stack” incompatible systems.

### 0) Scraped raw data: never include race/species ability score increases
**Critical:** In **all** legacy raw scrape files (e.g. `dnd2014_data.json` and any future `dnd2014_*.json`), **do not include** paragraphs that grant **Ability Score Increases from a race or species** (e.g. “Your Intelligence score increases by …”, subrace +1 Dex, etc.).

- **Why:** This app applies ASIs from **backgrounds only** (2024 model). If race ASI text exists in the scrape, parsers may turn it into a **trait** that players or future code treat as mechanical, or someone may “helpfully” wire it into the ability step—producing **double ASIs** with the background and making characters **wildly unbalanced**.
- **What to do instead:** Omit those paragraphs from the scrape entirely. Do not rely on “we’ll ignore it in code”; keep it **out of the data**.
- This rule applies to **every future** legacy species added to raw scrapes, not only Deep Gnome.

### 1) Top-level compatibility rule (2024 builder)
- **Ability Score Increases (ASIs)** at character creation come from the **background** (2024 model).
- **Species/race ASIs must not appear in legacy scrapes** (see §0). The 2024 rules also say that if you used older book text that included species ASIs, you would **ignore** those increases when using 2024 creation—we enforce “ignore” by **not importing** that text at all.
- Avoid duplicate “two versions of the same option”:
  - If an option exists in both legacy and updated form, the **updated form should be preferred**.
  - The legacy one should be labeled/sectioned as **Legacy** (and ideally not coexist as a separate “equivalent” unless intentionally supported).

### 2) Data files: keep legacy raw sources separate
- **Never edit** `data/*.json` directly. Add/adjust parsers in `parsers/` and regenerate via `python parsers/run_all_parsers.py`.
- **Never read** large raw files for implementation. Don’t open `dnd2024_data.json` fully.
- For legacy additions, prefer **separate raw scrape files** (examples):
  - `dnd2024_data.json` (existing)
  - `dnd2014_data.json` (legacy)
  - If needed later: `dnd2014_backgrounds.json`, `dnd2014_subclasses.json`, etc.
- **Parsers should merge outputs** into the existing runtime `data/*.json` files rather than introducing new runtime files unless there’s a strong reason.

### 3) Legacy species implementation checklist
- **Raw input**: add the species entry to a legacy raw file (e.g. `dnd2014_data.json`) with a `source` string that clearly identifies it (e.g. `"Player's Handbook (2014)"`). The `content` string must **not** contain race/species ASI paragraphs (see §0).
- **Parsing**: update `parsers/run_all_parsers.py` to load both raw datasets and **merge species** into `data/species.json`.
  - **Dedupe by name** and prefer the newest printing if duplicates ever occur.
- **UI grouping**: `gui/source_config.py` controls sectioning via `SOURCE_TO_CATEGORY["species"]` and `SECTION_ORDER["species"]`.
  - Map the 2014 source to a new **Legacy** category.
  - Put **Legacy last** in `SECTION_ORDER["species"]` so it appears below existing sections.
- **Rule-sensitive choices inside species text**:
  - If a legacy species grants spells and says “choose Intelligence/Wisdom/Charisma”, the app’s existing pattern is to store that choice in `Character.spell_grant_choices` and collect it in the **Spells step** (see `models/spell_grant_utils.py` and `gui/step_spells.py`).
  - Do **not** invent a new ad-hoc field on `Character` unless necessary; reuse the spell-grant system so save/load and validations stay consistent.

### 4) Legacy backgrounds implementation checklist
Backgrounds are tricky because 2014 and 2024 backgrounds differ structurally.

- **2024 builder expectation**:
  - Backgrounds drive ASIs and usually provide a feat in this app’s flow.
- If adding a legacy background:
  - Treat it as a **content option** with a `source` that maps to **Legacy** (via `SOURCE_TO_CATEGORY["backgrounds"]` / `SECTION_ORDER["backgrounds"]`).
  - Ensure the UI/validation remains 2024-consistent:
    - **ASIs remain background-driven** (2024 model). Do not reintroduce race/species ASIs.
    - If a legacy background lacks a feat in its original printing, the 2024 compatibility model is: grant an **Origin feat choice**. If you implement that, do it centrally (so it affects all legacy backgrounds consistently).
- Prefer to implement any “legacy background conversion” logic in one place (models), not scattered across UI screens.

### 5) Legacy subclasses implementation checklist
Subclasses in this repo come from parsed data and are selected/validated through the class/level-up flows.

- **Data**: legacy subclasses should be added through the parser pipeline and end up in `data/subclasses.json` (and any progression data they require).
- **Source grouping**: add mappings in `gui/source_config.py` under the `"subclasses"` context so legacy sources can be filtered and clearly labeled.
- **Version precedence**: if a subclass has both a legacy and updated printing, prefer updated, and keep legacy clearly tagged/sectioned.

### 6) Build/packaging rule for new runtime data
- If you introduce a **new runtime `data/*.json` file** (avoid if you can), you must register it in all build scripts:
  - `build.py`, `build_macos.py`, `build_ubuntu.py`

## Guidelines for AI
1. **Token Conservation**: Do not read files in `data/` or `dnd2024_data.json` unless you need a specific lookup. Use the schemas above.
2. **Logic Updates**: Most logic is in `models/` and `gui/`. Refer to those for behavior changes.
3. **Data Updates**: Edit parsers in `parsers/`, not the JSON files in `data/` directly — they are regenerated.
4. **Path Handling**: Always use `paths.py` to resolve file paths so they work in both IDE and packaged builds.
5. **README Maintenance**: When adding or removing user-facing features, update the **Features** section in `README.md` to reflect the change.
6. **Build Integrity**: Do not break the build process. The CI workflow (`.github/workflows/build-installers.yml`) produces installers for Windows, macOS, and Ubuntu on every push to `main`. It runs `build.py --onefile` + Inno Setup for Windows, `build_macos.py` for macOS, and `build_ubuntu.py` for Ubuntu. After making changes, ensure these build scripts and `installer.iss` still work and that the resulting installers run correctly.
7. **Data Bundling**: When adding new data files, ensure they are included in the PyInstaller build. Files accessible via `python main.py` are **not** automatically available in the packaged installer. Update the `DATA_FILES` list in **all three** build scripts (`build.py`, `build_macos.py`, `build_ubuntu.py`) and use `paths.py` to resolve paths.
8. **Dependencies**: `pyproject.toml` is the source of truth for dependencies. `requirements.txt` is auto-generated from it (via `uv export`). Edit `pyproject.toml`, not `requirements.txt`. Build-time deps like PyInstaller are in the `[build]` extra and are excluded from the packaged app.
9. **Dialog Z-Order Rule**: All dialogs (`tk.Toplevel`) must open in front of the current app window. Use `gui.widgets.configure_modal_dialog(dialog, parent)` instead of manually calling `transient/grab_set/focus` in each dialog.
