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
- **Leveling & Multiclass**: Level up to 20 with multiclass support, subclass selection, HP rolling, ASI/Feat choices, and spell swapping
- **Inventory Management**: Browse the full D&D 2024 item database, filter by category and cost, and track your wealth
- **Source Filtering**: Toggle content from Common (PHB), Eberron, Faerun, Exotic, and Unearthed Arcana sources
- **Character Management**: Save, view, edit/respec, import, and delete characters from the home screen
- **Biography Tab**: Add backstory, personality, and description notes, plus an embedded portrait image
- **Export**: PDF character sheets and JSON (for backup/sharing)

---

## For Developers

If you want to run VibeDnD from source or contribute:

### Prerequisites
- **Python 3.12+**
- **uv** (recommended) or **pip**

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
