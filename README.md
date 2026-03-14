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

### Building a Single-File macOS Installer (.dmg)
To share with non-technical Mac users (no Python needed), build a DMG on a Mac:

1. **On macOS, install build deps:**
   ```bash
   pip install pyinstaller
   ```

2. **Put your icon source in the repo root** as `icon-source.png` (optional but recommended).

3. **Run the mac packager script:**
   ```bash
   python3 build_macos.py
   ```

4. **Send this one file to your friend:**
   ```
   dist/installer-mac/VibeDnD-Installer-macOS.dmg
   ```

The DMG contains `VibeDnD.app` and an `Applications` shortcut for drag-and-drop install.

### Building a Single-File Ubuntu Installer (.deb)
To share with non-technical Ubuntu users (no Python needed), build a `.deb` on Ubuntu:

1. **On Ubuntu, install build deps:**
   ```bash
   sudo apt update
   sudo apt install -y dpkg-dev python3-pip python3-tk
   python3 -m pip install pyinstaller
   ```

2. **Put your icon source in the repo root** as `icon-source.png` (optional but recommended).

3. **Run the Ubuntu packager script:**
   ```bash
   python3 build_ubuntu.py
   ```

4. **Send this one file to your friend:**
   ```
   dist/installer-linux/VibeDnD-Installer-Ubuntu-amd64.deb
   ```

Your friend can install by double-clicking the `.deb` in Ubuntu Software, or via:
```bash
sudo apt install ./VibeDnD-Installer-Ubuntu-amd64.deb
```

### Zero-Setup Builds via GitHub Actions (Recommended)
If you do not want Python/PyInstaller installed on your own computer, use CI builds:

1. Push this repo to GitHub.
2. Open **Actions** → **Build Installers** → **Run workflow**.
3. Download artifacts from the finished run:
   - `VibeDnD-Setup-Windows`
   - `VibeDnD-Installer-macOS`
   - `VibeDnD-Installer-Ubuntu`

Workflow file: `.github/workflows/build-installers.yml`

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
