# VibeDnD - D&D 2024 Character Creator

A desktop character creation tool for Dungeons & Dragons 2024 rules, built with Python and Tkinter.

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.14+**
- **uv** (recommended) or **pip**

### 2. Setup & Run
```bash
# Clone and enter the repo
git clone <repo-url>
cd VibeDnD

# Install & Run (using uv)
uv run main.py

# OR (using pip)
python -m venv .venv
# Windows: .venv\Scripts\activate | macOS/Linux: source .venv/bin/activate
pip install .
python main.py
```

---

## 🛠️ Development & Building

### AI Development
If you are using an AI agent (like Cursor or Claude):
- Refer to [AI_README.md](AI_README.md) for data schemas and token optimization.
- **Do not** have the AI read the large JSON files in `data/`.

### Building an Executable
To package VibeDnD into a standalone `.exe` or app:

1. **Install build tools:**
   ```bash
   uv sync --extra build  # or: pip install ".[build]"
   ```

2. **Run the build script:**
   ```bash
   python build.py --onefile
   ```
   The result will be in the `dist/` folder.

<details>
<summary><b>Detailed Platform Instructions</b></summary>

- **Windows**: Use `build.py` with `.venv` activated.
- **Linux/macOS**: Ensure `python3-tk` or `python-tk` is installed via your package manager (brew/apt) before building.
</details>

---

## ✨ Features
- **Wizard Flow**: Species → Class → Background → Abilities → Feats → Spells → Equipment.
- **Live Summary**: View your character build in real-time.
- **Source Filtering**: Configurable source categories (Common, Eberron, Faerun, Exotic).
- **Export**: PDF, JSON, and plain text formats.
- **Themed UI**: Dark parchment aesthetic.

---

## 📂 Project Structure
<details>
<summary>View internal directory map</summary>

```
VibeDnD/
  main.py           # Entry point
  build.py          # Build script
  data/             # Game data (JSON)
  gui/              # Tkinter interface
  models/           # Character logic
  parsers/          # Data processing
  export/           # PDF/JSON/Text export logic
```
</details>
