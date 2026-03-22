# CLAUDE.md — VibeDnD AI Assistant Guide

VibeDnD is a D&D 2024 Character Creator desktop application built with Python and Tkinter. This document provides everything Claude Code needs to work effectively in this repository.

---

## Repository Structure

```
VibeDnD/
├── main.py                   # Entry point: validates data, launches app
├── paths.py                  # Cross-platform path resolution (ALWAYS use this)
├── pyproject.toml            # Project metadata and dependencies (source of truth)
├── requirements.txt          # Auto-generated from pyproject.toml via uv export
├── uv.lock                   # Reproducible dependency lock file
├── settings.json             # User preferences (source filters, created at runtime)
├── dnd2024_data.json         # 1.25MB raw scraped source — DO NOT READ
│
├── gui/                      # All Tkinter UI code (~14,000 lines)
├── models/                   # Domain models and business logic
├── export/                   # PDF and JSON export
├── parsers/                  # Scripts that regenerate data/*.json
├── data/                     # Auto-generated game data JSON — DO NOT READ DIRECTLY
│
├── build.py                  # Cross-platform PyInstaller build
├── build_macos.py            # macOS DMG builder
├── build_ubuntu.py           # Ubuntu .deb builder
├── installer.iss             # Inno Setup script for Windows installer
└── .github/workflows/        # CI/CD: builds installers on push to main
    └── build-installers.yml
```

---

## Development Setup

**Package manager:** `uv` (preferred) or `pip`

```bash
# Install dependencies with uv
uv sync

# Or with pip
pip install -r requirements.txt

# Run the app
python main.py
```

**Python version:** 3.12+ required (3.14 pinned in `.python-version`)

**Dependencies** (defined in `pyproject.toml`):
- `beautifulsoup4` — web scraping (parsers)
- `requests` — HTTP
- `fpdf2` — PDF generation
- `Pillow` — image handling
- `pyinstaller` — build-time only (in `[build]` optional extra, not bundled in app)

---

## Architecture Overview

### Screen Manager Pattern

`gui/app.py` is the root controller that switches between three screens:

1. **Home Screen** (`gui/home_screen.py`) — Character library: list, create, import, delete
2. **Wizard** — Sequential 8-step character creation; each step is a separate file:
   - `step_species.py` → `step_class.py` → `step_background.py` → `step_ability_scores.py` → `step_feat.py` → `step_spells.py` → `step_equipment.py` → `step_biography.py` → `step_summary.py`
   - Base class: `gui/base_step.py` (`WizardStep`)
   - Tabs are shown/hidden dynamically (e.g., spells tab hidden for non-casters)
3. **Character Viewer** (`gui/character_viewer.py`) — Full character sheet, level-up, export

### Key GUI Modules

| File | Purpose |
|------|---------|
| `gui/data_loader.py` | `GameData` class: loads all JSON, builds lookup indexes |
| `gui/level_up_wizard.py` | Multi-step level-up dialog (HP, ASI/feat, subclass, spells) |
| `gui/spell_swap_panel.py` | Manage known/prepared spells |
| `gui/add_inventory_dialog.py` | Item browser with filtering |
| `gui/sheet_builder.py` | Renders character sheet display |
| `gui/rest_dialog.py` | Short/long rest mechanics and spell slot recovery |
| `gui/theme.py` | `COLORS` and `FONTS` constants (dark parchment TTK theme) |
| `gui/widgets.py` | `ScrollableFrame`, `WrappingLabel`, `AlertDialog`, `configure_modal_dialog()` |
| `gui/source_config.py` | UI for toggling game content sources |
| `gui/equipment_utils.py` | Equipment stat formatting helpers |

### Models

| File | Purpose |
|------|---------|
| `models/character.py` | `Character` dataclass — single source of truth for all character state |
| `models/ability_scores.py` | `AbilityScores` dataclass with modifiers and validation |
| `models/class_level.py` | `ClassLevel` — tracks per-level advancement (HP, feats, spells, subclass) |
| `models/enums.py` | `Ability`, `Skill` enums and `ALL_SKILLS` constant |
| `models/character_store.py` | `save_character()` / `load_character()` — JSON file serialization |
| `models/inventory_service.py` | Add/remove items, wealth tracking, transaction history |
| `models/standard_actions.py` | D&D standard action definitions |

---

## Critical Rules

### 1. Path Handling — Always Use `paths.py`

Never hardcode file paths. The app runs in two contexts:
- **Development:** paths relative to project root
- **Frozen (PyInstaller):** read-only assets in `sys._MEIPASS`, user data in platform-specific dirs

```python
from paths import data_dir, characters_dir, settings_path

# Correct
json_path = os.path.join(data_dir(), "classes.json")

# Wrong — breaks in packaged build
json_path = "data/classes.json"
```

**User data locations (frozen builds):**
- Windows: `%APPDATA%\VibeDnD\`
- macOS: `~/Library/Application Support/VibeDnD/`
- Linux: `$XDG_DATA_HOME/VibeDnD/` (default: `~/.local/share/VibeDnD/`)

### 2. Dialog Z-Order — Use `configure_modal_dialog()`

All `tk.Toplevel` dialogs must use the helper from `gui/widgets.py` to appear in front:

```python
from gui.widgets import configure_modal_dialog

dialog = tk.Toplevel(parent)
configure_modal_dialog(dialog, parent)  # handles transient/grab_set/focus correctly
```

Never call `transient()`, `grab_set()`, or `focus()` manually on dialogs.

### 3. Dependencies — Edit `pyproject.toml`, Not `requirements.txt`

`requirements.txt` is auto-generated:
```bash
uv export --no-hashes > requirements.txt
```

Build-time deps (PyInstaller) go in `[project.optional-dependencies] build` — they are **not** included in the packaged app.

### 4. New Data Files Must Be Registered in All Three Build Scripts

When adding a new `data/*.json` file, update the `DATA_FILES` list in:
- `build.py`
- `build_macos.py`
- `build_ubuntu.py`

Otherwise the file will be missing in packaged installers.

### 5. Do Not Edit JSON Files in `data/` Directly

These are auto-generated by parsers. Edit the relevant file in `parsers/` instead, then regenerate:

```bash
python parsers/run_all_parsers.py
```

### 6. Build Integrity — Don't Break CI

CI runs on every push to `main` and produces three installers. Before merging, ensure:
- `build.py --onefile` succeeds
- `build_macos.py` succeeds
- `build_ubuntu.py` succeeds
- `installer.iss` is consistent with the Windows build output

### 7. Token Conservation — Never Read Large Data Files

Do not read these files unless absolutely necessary for a specific lookup:
- `data/spells.json` (~500KB)
- `data/subclasses.json` (~300KB)
- `data/class_progressions.json` (~200KB)
- `data/feats.json` (~150KB)
- `dnd2024_data.json` (1.25MB raw source — never read)

Use the schemas below instead.

---

## Data Schemas

### `data/classes.json`
```json
{
  "name": "Artificer",
  "slug": "artificer",
  "source": "Eberron - Rising from the Last War",
  "description": "...",
  "primary_ability": ["Intelligence"],
  "hit_die": 8,
  "saving_throws": ["Constitution", "Intelligence"],
  "skill_choices": { "count": 2, "options": ["Arcana", "History"] },
  "weapon_proficiencies": ["Simple weapons"],
  "armor_proficiencies": ["Light", "Medium armor", "Shields"],
  "starting_equipment": [{ "option": "A", "items": "..." }, { "option": "B", "items": "150 GP" }],
  "caster_type": "half",
  "spellcasting_ability": "Intelligence",
  "cantrips_known": 2,
  "spells_prepared": 2,
  "spell_slots": { "1st": 2 }
}
```
`caster_type`: `"full"`, `"half"`, `"third"`, or `null`

### `data/spells.json`
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

### `data/feats.json`
```json
{
  "name": "Alert",
  "source": "Player's Handbook",
  "category": "origin",
  "prerequisites": null,
  "benefits": [{ "name": "Initiative Proficiency", "description": "..." }],
  "ability_score_increase": null
}
```

### `data/subclasses.json`
```json
{
  "name": "Alchemist",
  "slug": "alchemist",
  "class_slug": "artificer",
  "source": "...",
  "description": "...",
  "feature_levels": [3, 5, 9, 15],
  "features": { "3": [{ "name": "Tool Proficiency", "description": "..." }] }
}
```

### `data/class_progressions.json`
```json
{
  "name": "Artificer",
  "slug": "artificer",
  "caster_type": "half",
  "levels": [{
    "level": 1,
    "proficiency_bonus": 2,
    "features": ["Spellcasting", "Tinker's Magic"],
    "cantrips": 2,
    "prepared_spells": 2,
    "spell_slots": { "1st": 2 },
    "extra": {},
    "feature_details": [{ "name": "Spellcasting", "description": "..." }]
  }]
}
```

### `data/items.json`
```json
{
  "id": "adventuring-gear:acid",
  "name": "Acid",
  "category": "Adventuring Gear",
  "cost_cp": 2500,
  "description": "...",
  "source": "..."
}
```
Categories: `Adventuring Gear`, `Armor`, `Weapons`, `Mounts & Vehicles`, `Poisons`, `Tools`, `Magic Items`

### `data/species.json`, `data/backgrounds.json`
```json
{
  "name": "...",
  "source": "...",
  "description": "...",
  "features": [{ "name": "...", "description": "..." }]
}
```

---

## Key Patterns

### Character Model as Single Source of Truth

All character state lives in the `Character` dataclass (`models/character.py`). Saves use name references (not full dicts) for resilience to data changes. Computed properties (`level`, `is_caster`, AC, etc.) are derived from the stored data.

### Multiclass Support

`Character.class_levels` is a list of `ClassLevel` objects, one per level gained. Each tracks: class slug, level in that class, subclass, HP roll, spell swaps, feat choices. Multiclass prerequisite validation is built into `Character`.

### Source Filtering

`GameData` (in `gui/data_loader.py`) filters all game data by the source categories enabled in `settings.json`. Sources: `Common`, `Eberron`, `Faerun`, `Exotic`, `Unearthed Arcana`.

### Theme

All styling comes from `gui/theme.py`:
- `COLORS` dict with 16 named color values (dark parchment palette)
- `FONTS` dict with `heading`, `body`, `mono`, `stat` families
- Platform-specific fonts: Segoe UI (Windows), Helvetica (macOS), DejaVu Sans (Linux)

Always reference `COLORS` and `FONTS` from `theme.py`; never hardcode colors or font names.

---

## CI/CD

**Trigger:** Push to `main` or `v*` tags, or manual dispatch.

**Three parallel jobs** in `.github/workflows/build-installers.yml`:

| Job | Runner | Script | Output |
|-----|--------|--------|--------|
| Windows | `windows-latest` | `build.py --onefile` + Inno Setup | `VibeDnD-Setup-Windows.exe` |
| macOS | `macos-latest` | `build_macos.py` | `VibeDnD-Installer-macOS.dmg` |
| Ubuntu | `ubuntu-latest` | `build_ubuntu.py` | `VibeDnD-Installer-Ubuntu.deb` |

All jobs use Python 3.12 and PyInstaller 6.19.0.

Ubuntu requires system packages: `dpkg-dev python3-tk libjpeg-dev zlib1g-dev libfreetype6-dev`.

---

## No Test Suite

There is no automated test framework. Testing is manual via running `python main.py`. When making changes, manually verify:
- App launches without errors
- Affected wizard step(s) behave correctly
- Character saves and loads successfully
- Export to PDF/JSON works if relevant

---

## PDF Preview Workflow

When making changes to the PDF character sheet (`export/pdf_export.py`), generate an inline preview so the user can visually verify changes without launching the GUI.

### How to generate a preview

```bash
# Ensure poppler-utils is installed (for PDF→PNG conversion)
which pdftoppm || apt-get install -y poppler-utils

uv run python preview_pdf.py /tmp/vibe_dnd_preview.pdf
```

The script generates the PDF and automatically converts it to PNG pages (`/tmp/vibe_dnd_preview-1.png`, `/tmp/vibe_dnd_preview-2.png`).

**IMPORTANT:** Use the **Read** tool on the `.png` files (NOT the `.pdf`) to display them inline. The chat interface renders PNG images visually but shows PDFs as just a file path. Always read the PNG files so the user can actually see the result.

### The preview script

`preview_pdf.py` builds a sample Level 3 Half-Elf Ranger (Hunter) named "Thorn Ironvale" with:
- Full ability scores, skills, proficiencies
- Background feat (Alert), species traits
- Spells (Cure Wounds, Hunter's Mark, Goodberry)
- Equipped weapons (Longbow, Shortsword) and armor (Studded Leather)
- Biography text and personality

This exercises both pages of the PDF (main sheet + spellcasting/personality page).

### When to update `preview_pdf.py`

If a PDF change requires data the sample character doesn't have (e.g., cantrips, multiclass, portrait image), update `build_sample_character()` in `preview_pdf.py` to include the relevant data so the preview covers the changed section.

### Workflow per change

1. Edit `export/pdf_export.py` (or related export code)
2. Run `uv run python preview_pdf.py /tmp/vibe_dnd_preview.pdf`
3. Read `/tmp/vibe_dnd_preview-1.png` (and `-2.png` if page 2 exists) with the Read tool to show the user
4. Iterate based on feedback

### Notes

- Georgia fonts are macOS-only; the preview will fall back to Helvetica on Linux — this is expected
- The script has no GUI dependencies (no Tkinter) and runs headlessly
- Output path can be overridden via CLI argument: `python preview_pdf.py /path/to/output.pdf`
- Requires `poppler-utils` for PNG conversion (`apt-get install -y poppler-utils`)

---

## Conventions

- **Style:** PEP 8, type hints with `|` union syntax (Python 3.10+), dataclasses for models
- **No linting/formatting tools** are configured (no ruff, black, mypy)
- **No test framework** (no pytest, unittest)
- **Logging:** Uses `print()` statements — no logging framework
- **User-facing changes:** Update `README.md` Features section
