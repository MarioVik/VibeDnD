# AI Documentation: VibeDnD Repository

This document is intended for AI agents (Claude, Cursor, GPT, etc.) to understand the repository structure and skip reading large data files unnecessarily.

## Project Overview
VibeDnD is a D&D 2024 Character Creator application. It uses a Python back-end for data processing and a GUI (likely Tkinter or similar, based on `gui/` directory) for character creation.

## Repository Structure
- `data/`: Contains **highly structured JSON files** parsed from raw sources. **DO NOT READ THESE ENTIRELY.** Use the schemas below.
- `models/`: Python data models representing characters, ability scores, etc.
- `parsers/`: Scripts that convert raw JSON/scraped data into the structured files in `data/`.
- `gui/`: The user interface implementation.
- `main.py`: Entry point for the application.
- `dnd2024_data.json`: 1.25MB raw scraped data. **DO NOT READ.**

## Data Schemas (`data/*.json`)

### `spells.json` (~500KB)
Each object in the array represents a spell:
```json
{
  "name": "Acid Splash",
  "level": 0,
  "school": "Evocation",
  "classes": ["Artificer", "Sorcerer", "Wizard"],
  "casting_time": "Action",
  "ritual": false,
  "range": "60 feet",
  "components": { "V": true, "S": true, "M": "..." },
  "concentration": false,
  "duration": "Instantaneous",
  "description": "...",
  "higher_levels": null,
  "cantrip_upgrade": "...",
  "source": "Player's Handbook"
}
```

### `feats.json` (~150KB)
Each object represents a feat:
```json
{
  "name": "Alert",
  "source": "Player's Handbook",
  "category": "origin",
  "prerequisites": null, // or {"level": 4, "abilities": {"Dexterity": 13}}
  "benefits": [
    { "name": "Initiative Proficiency", "description": "..." }
  ],
  "ability_score_increase": null // or "Charisma", "Strength", etc.
}
```

### `subclasses.json` (~300KB)
Each object represents a subclass for a specific class:
```json
{
  "name": "Alchemist",
  "slug": "alchemist",
  "class_slug": "artificer",
  "source": "",
  "description": "...",
  "feature_levels": [3, 5, 9, 15],
  "features": {
    "3": [
      { "name": "Tool Proficiency.", "description": "..." }
    ]
  }
}
```

### `class_progressions.json` (~200KB)
Contains level-by-level data for classes:
```json
{
  "name": "Artificer",
  "slug": "artificer",
  "caster_type": "half",
  "levels": [
    {
      "level": 1,
      "proficiency_bonus": 2,
      "features": ["Spellcasting", "Tinker's Magic"],
      "cantrips": 2,
      "prepared_spells": 2,
      "spell_slots": { "1st": 2 },
      "extra": { "Rages": 2, "Rage Damage": 2 }, // Varies by class
      "feature_details": [
        { "name": "Spellcasting", "description": "..." }
      ]
    }
  ]
}
```

### `species.json`, `backgrounds.json`
These generally follow a `{"name": "...", "description": "...", "features": [...]}` pattern where `features` is a list of `{ "name": "...", "description": "..." }`.

## Guidelines for AI
1. **Token Conservation**: Avoid `view_file` on anything in `data/` or `dnd2024_data.json` unless absolutely necessary for a specific lookup.
2. **Logic Updates**: Most logic resides in `models/` or `gui/`. Refer to those for behavior changes.
3. **Data Updates**: If you need to fix data, look at the corresponding parser in `parsers/` rather than editing the JSON files manually, as they are regenerated.
4. **Path Handling**: Use `paths.py` to get absolute paths to data and character directories.
