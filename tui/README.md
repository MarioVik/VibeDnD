# VibeDnD TUI — "arcane ledger"

A flashy Textual-based terminal UI for [VibeDnD](https://github.com/MarioVik/VibeDnD)
character sheets: roster, tabbed character sheet, live HP tracking, spell
slot pips, and an animated dice roller.

## Install & run

Drop the `tui/` folder into the root of the VibeDnD repo (next to
`models/` and `paths.py`), then:

```bash
cd VibeDnD
uv add textual          # or: pip install textual
uv run python -m tui    # loads characters from VibeDnD's save dir
```

Standalone, without the repo (sample character):

```bash
pip install textual
python -m tui --demo
```

## Keys

| Key | Where | Action |
|---|---|---|
| `j` / `k` | everywhere | move down / up (roster rows, table cursor, scroll panes) |
| `g` / `G` | everywhere | jump to top / bottom |
| `ctrl+d` / `ctrl+u` | everywhere | page down / up |
| `r` | anywhere | dice roller (`j`/`k` count, `h`/`l` die size, `1-9` count, `r` reroll) |
| `enter` / `l` | roster | open character sheet |
| `1`–`5` | sheet | jump tabs (Overview / Skills / Spells / Inventory / Features) |
| `[` / `]` | sheet | previous / next tab |
| `h` / `H` | sheet | -1 / +1 HP (saved to the character file) |
| `s` / `S` | sheet | spend / restore a spell slot (uses the highlighted spell's level; saved) |
| `m` | sheet | coin pouch & money calculator |
| `esc` | sheet | back to roster |

The money modal doubles as a D&D calculator: `+2gp 5sp` / `-1gp` adjust
the pouch on enter (persisted, leading sign covers the whole amount),
while a plain expression like `(3gp + 12sp) / 4` just shows the result
in every denomination (pp/gp/ep/sp/cp).

Focus follows the active tab, so motion keys always act on the visible
pane — no mouse needed.

## Architecture

```
tui/
├── app.py            # App shell, global dice binding
├── adapter.py        # CharacterView: model → render-ready snapshot
├── loader.py         # VibeDnD save discovery + demo character
├── widgets.py        # HPBar, SlotPips, AbilityRow, DiceRoller
├── vibednd.tcss      # theme (umber/parchment/ember/arcane palette)
├── screens/
│   ├── home.py       # roster + preview pane
│   └── sheet.py      # tabbed character sheet
└── tests/            # pytest unit tests + headless smoke drives
```

The TUI never reads or writes `models.Character` directly — only via
`adapter.py` (`from_model()` for the render snapshot; `set_hp` /
`spend_slot` / `restore_slot` for write-backs). Saves go through
`models.character_store.save_character`, so the Tkinter GUI can always
read them back, and vice versa. Verified against Textual 8.2.7.

## Tests

```bash
PYTHONPATH=$PWD ./.venv/bin/pytest tui/tests -q     # unit tests
uv run python -m tui.tests.smoke_demo               # headless app drive (demo)
uv run python -m tui.tests.smoke_real               # headless app drive (real saves, read-only)
```

## Roadmap ideas

- Rest dialog (mirror `gui/rest_dialog.py` logic)
- Level-up wizard
- Skill-check rolls: press `enter` on a skill row → pre-modified d20 roll
