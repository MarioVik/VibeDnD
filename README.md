# VibeDnD - D&D 2024 Character Creator

A desktop character creation tool for Dungeons & Dragons 2024 rules.

## Download & Install

Pre-built installers are automatically generated for every release. To get the latest version:

1. Go to the [**Actions** tab](../../actions) of this repository on GitHub.
2. Click the most recent **Build Installers** run with a green checkmark.
3. Scroll down to **Artifacts** and download the one for your operating system:
   - **Windows** — `VibeDnD-Setup-Windows` (run the `.exe` installer wizard)
   - **macOS** — `VibeDnD-Installer-macOS` (open the `.dmg`, drag VibeDnD to Applications)
   - **Ubuntu/Linux** — `VibeDnD-Installer-Ubuntu` (double-click the `.deb` to install)

No Python or technical setup required.

## Features

- **Step-by-Step Character Creation**: Species, Class, Background, Ability Scores (Standard Array or Point Buy), Feats, Spells, and Equipment
- **Strict Level 1 Class Requirements**: Character creation now blocks completion until every class-granted level 1 choice has been explicitly resolved, including skills, spell picks, weapon masteries, orders, fighting styles, invocations, and class equipment
- **Skill Expertise Support**: Choose creation-time Expertise on the Skills step for Rogue and supported feats, with automatic modifier updates and Zhentarim long-rest reselection
- **Leveling & Multiclass**: Level up to 20 with multiclass support, subclass selection, HP rolling, ASI/Feat choices, and spell swapping
- **Tracked Spell Resources**: Spend and restore spell slots plus limited free casts from species, feats, and class features, while still surfacing At Will magic in the spellbook
- **Inventory Management**: Browse the full D&D 2024 item database, filter by category and cost, and track your wealth
- **Source Filtering**: Toggle content from Common (PHB), Eberron, Faerun, Exotic, and Unearthed Arcana sources
- **Cinematic Home & Archive**: Start from a dedicated landing screen, then browse, import, load, and delete characters from a separate archive view
- **Biography Tab**: Add backstory, personality, and description notes, plus an embedded portrait image
- **Export**: PDF character sheets and JSON (for backup/sharing)
- **BDD Character-Creation Spec**: Level 1 class behavior is documented in Markdown and backed by executable `pytest-bdd` feature tests

---

## For Developers

If you want to run VibeDnD from source or contribute:

### Prerequisites
- **Python 3.12+**
- **uv** (recommended) or **pip**
- **Tkinter** — included with Python on Windows and most Linux distros, but on macOS requires a separate install:
  ```bash
  brew install python-tk@3.14  # match your Python version
  ```

### Run from Source
```bash
git clone <repo-url>
cd VibeDnD

# Using uv (recommended)
uv run main.py

# Using pip
python -m venv .venv
# Windows: .venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
pip install .
python main.py
```

### Build Installers Locally
```bash
# Install build tools
uv sync --extra build  # or: pip install ".[build]"

# Build standalone executable
python build.py --onefile
```

Platform-specific build scripts (`build_macos.py`, `build_ubuntu.py`) are also available. On Linux/macOS, ensure `python3-tk` is installed via your package manager.

### AI Development
If using an AI agent (Cursor, Claude, etc.), see [AI_README.md](AI_README.md) for data schemas. Avoid having the AI read the large JSON files in `data/`.
