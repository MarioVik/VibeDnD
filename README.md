# VibeDnD - D&D 2024 Character Creator

A desktop character creation tool for Dungeons & Dragons 2024 rules, built with Python and Tkinter.

## Features

- Step-by-step character creation wizard (species, class, background, ability scores, feats, spells, equipment)
- Live character summary panel that updates as you make selections
- DM-configurable source filtering (Common, Eberron, Faerun, Exotic) with persistent settings
- Export to PDF, JSON, or plain text
- Dark parchment-themed UI

## Running from Source

### Prerequisites

- **Python 3.14+**
- **uv** (recommended) or **pip**

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd VibeDnD

# Create a virtual environment and install dependencies
uv sync
# or with pip:
python -m venv .venv
.venv/Scripts/activate      # Windows
source .venv/bin/activate    # macOS / Linux
pip install -r requirements.txt
```

### Running

```bash
python main.py
```

On first run, if the parsed data files are missing from `data/`, the app will automatically run the parsers to generate them from `dnd2024_data.json`.

## Building a Standalone Executable

You can package VibeDnD into a standalone executable that does not require Python to be installed on the target machine. Builds use [PyInstaller](https://pyinstaller.org/) and must be run **on each target platform** (PyInstaller does not cross-compile).

### Prerequisites

Install the build dependencies into your virtual environment:

```bash
pip install pyinstaller fpdf2
# or with uv:
uv pip install pyinstaller fpdf2
```

### Building

VibeDnD includes a `build.py` script that handles the PyInstaller invocation for you:

```bash
# Directory bundle (faster startup, recommended for local use)
python build.py

# Single-file executable (easier to share/distribute)
python build.py --onefile

# Clean previous build artifacts first
python build.py --clean
python build.py --clean --onefile
```

### Build Output

| Mode | Output Location | Description |
|------|----------------|-------------|
| `--onedir` (default) | `dist/VibeDnD/` | Folder containing `VibeDnD.exe` (or `VibeDnD` on macOS/Linux) plus supporting files |
| `--onefile` | `dist/VibeDnD.exe` | Single self-contained executable |

### Running the Built Executable

**Windows:**
```
dist\VibeDnD\VibeDnD.exe
```

**macOS / Linux:**
```bash
dist/VibeDnD/VibeDnD
```

No Python installation is needed on the target machine.

### Platform-Specific Notes

#### Windows
- Works out of the box. The build produces a `.exe` file.
- Windows Defender or SmartScreen may flag the unsigned executable the first time it runs. This is normal for unsigned apps.

#### macOS
- You must build on a Mac with Python 3.14+ and Tkinter installed.
- macOS may require you to allow the app in **System Preferences > Privacy & Security** on first launch.
- If using Homebrew Python, make sure `python3-tk` / `tkinter` is available: `brew install python-tk@3.14`

#### Linux (Ubuntu / Debian)
- Tkinter is not always bundled with Python on Linux. Install it first:
  ```bash
  sudo apt install python3-tk
  ```
- The built executable is a standard Linux binary. Mark it executable if needed:
  ```bash
  chmod +x dist/VibeDnD/VibeDnD
  ```

### Settings Persistence

When running as a built executable, user settings (`settings.json` for source category filters) are stored next to the executable so they persist between runs. This file is created automatically when you toggle source categories.

## Project Structure

```
VibeDnD/
  main.py                  # Application entry point
  paths.py                 # Path resolution (dev vs frozen)
  build.py                 # Cross-platform build script
  dnd2024_scraper.py       # Data scraper (not needed at runtime)
  dnd2024_data.json        # Raw scraped data
  pyproject.toml           # Project metadata and dependencies
  settings.json            # User source filter preferences

  data/                    # Parsed game data (JSON)
    spells.json
    classes.json
    species.json
    backgrounds.json
    feats.json

  gui/                     # Tkinter GUI
    app.py                 # Main window and summary panel
    theme.py               # Dark parchment color scheme
    data_loader.py         # Loads parsed JSON data
    source_config.py       # Source category mappings and settings
    base_step.py           # Base class for wizard steps
    widgets.py             # Custom widgets (SectionedListbox, etc.)
    step_species.py        # Species selection
    step_class.py          # Class selection
    step_background.py     # Background selection
    step_ability_scores.py # Ability score assignment
    step_feat.py           # Feat selection
    step_spells.py         # Spell/cantrip selection
    step_equipment.py      # Equipment choice
    step_summary.py        # Final summary and export

  models/                  # Data models
    character.py           # Character dataclass
    ability_scores.py      # Ability score calculations
    enums.py               # Skills, abilities

  parsers/                 # Data parsers (dev-only)
    run_all_parsers.py     # Runs all parsers
    base_parser.py         # Shared parsing utilities
    spell_parser.py        # Spell parser
    class_parser.py        # Class parser
    species_parser.py      # Species parser
    background_parser.py   # Background parser
    feat_parser.py         # Feat parser

  export/                  # Character export
    json_export.py         # Export to JSON
    text_export.py         # Export to plain text
    pdf_export.py          # Export to PDF (uses fpdf2)
```
