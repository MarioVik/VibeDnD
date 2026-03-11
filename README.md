# VibeDnD - D&D 2024 Character Creator

A desktop character creation tool for Dungeons & Dragons 2024 rules, built with Python and Tkinter.

## Features

- Step-by-step character creation wizard (species, class, background, ability scores, feats, spells, equipment)
- Live character summary panel that updates as you make selections
- DM-configurable source filtering (Common, Eberron, Faerun, Exotic) with persistent settings
- Export to PDF, JSON, or plain text
- Dark parchment-themed UI

## AI Development Guidelines

If you are using an AI agent (like Cursor, Claude, or Copilot) to work on this repository:
- Please refer to [AI_README.md](AI_README.md) for data schemas and token optimization guidelines.
- Use the `.cursorrules` file for automated AI behavior settings.
- **Do not** have the AI read the large JSON files in the `data/` directory or the root `dnd2024_data.json` file, as this will consume a significant amount of tokens. Use the provided schemas instead.

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
pip install .
# or:
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
pip install ".[build]"
# or with uv:
uv sync --extra build
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

### Platform-Specific Build Instructions

#### Windows

1. Open a terminal in the project directory.
2. Make sure your venv is activated:
   ```powershell
   .venv\Scripts\activate
   ```
3. Install build dependencies:
   ```powershell
   pip install ".[build]"
   ```
4. Build:
   ```powershell
   python build.py --clean --onefile
   ```
5. The executable is at `dist\VibeDnD.exe`. Copy it anywhere and run it — no Python needed.

> Windows Defender or SmartScreen may flag the unsigned executable the first time it runs. This is normal for unsigned apps — click "More info" then "Run anyway".

#### Ubuntu / Debian

1. Install Python 3.14+, Tkinter, and pip. On Ubuntu 24.04+:
   ```bash
   sudo apt update
   sudo apt install python3 python3-venv python3-pip python3-tk
   ```
   If your distro does not ship Python 3.14, install it from the [deadsnakes PPA](https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa):
   ```bash
   sudo add-apt-repository ppa:deadsnakes/ppa
   sudo apt update
   sudo apt install python3.14 python3.14-venv python3.14-tk
   ```
2. Clone the repository and create a virtual environment:
   ```bash
   git clone <repo-url>
   cd VibeDnD
   python3.14 -m venv .venv
   source .venv/bin/activate
   ```
3. Install runtime and build dependencies:
   ```bash
   pip install ".[build]"
   ```
4. Build:
   ```bash
   python build.py --clean --onefile
   ```
5. The executable is at `dist/VibeDnD`. Copy it to the target machine and run:
   ```bash
   chmod +x dist/VibeDnD
   ./dist/VibeDnD
   ```

> No Python installation is needed on the target machine to **run** the executable, but you need Python to **build** it.

#### macOS

1. Install Python 3.14+ with Tkinter. Using [Homebrew](https://brew.sh/):
   ```bash
   brew install python@3.14 python-tk@3.14
   ```
2. Clone the repository and create a virtual environment:
   ```bash
   git clone <repo-url>
   cd VibeDnD
   python3.14 -m venv .venv
   source .venv/bin/activate
   ```
3. Install runtime and build dependencies:
   ```bash
   pip install ".[build]"
   ```
4. Build:
   ```bash
   python build.py --clean --onefile
   ```
5. The executable is at `dist/VibeDnD`. Copy it anywhere and run:
   ```bash
   chmod +x dist/VibeDnD
   ./dist/VibeDnD
   ```

> macOS may require you to allow the app in **System Settings > Privacy & Security** on first launch since it is unsigned.

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
