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
