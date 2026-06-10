# HANDOVER.md — first Claude Code session brief

> **STATUS (2026-06-10): tasks 1–4 below are DONE.** The TUI runs against
> real saves, persists HP and spell slots GUI-compatibly, and has a
> pytest suite (`tui/tests/`). See `tui/CLAUDE.md` for the confirmed
> integration points. Remaining work: the Backlog section.

**Project:** VibeDnD TUI ("arcane ledger") — Textual terminal UI using
[MarioVik/VibeDnD](https://github.com/MarioVik/VibeDnD)'s `models/`
package as backend.

**State:** Complete scaffold, compiles clean, adapter math unit-checked
offline. **Never executed with Textual installed, never run inside the
real repo.** The author of the scaffold could not access the network, so
all `models/` and `paths.py` integration is written from the repo's
AGENTS.md documentation, defensively, with fallbacks.

**Setup (human has likely already done this; verify):**

```bash
cd VibeDnD                      # repo root
cp -r /path/to/vibednd-tui/tui ./tui
uv add textual
```

Read `tui/CLAUDE.md` and the repo root `AGENTS.md` before editing.

---

## Tasks, in order

### 1. Make it launch (demo mode)

```bash
uv run python -m tui --demo
```

Fix any Textual API mismatches (check installed version first:
`uv run python -c "import textual; print(textual.__version__)"`).
Likely suspects: TCSS selectors for `Tabs`/`DataTable` component classes,
`OptionList` event names, `TabbedContent` pane padding selector.

**Done when:** demo launches; roster → enter → sheet → all 5 tabs render;
`r` opens dice roller, numbers spin and settle; `h`/`H` move the HP bar;
`esc` navigates back; no tracebacks in `textual console`.

### 2. Wire the real backend

Open `models/character.py`, `models/character_store.py`, `paths.py` and:

- Correct `loader._character_files()` and `loader._load_one()` to the
  real `characters_dir()` / `load_character()` signatures. Remove the
  try/except signature-guessing once confirmed.
- Audit `FALLBACK_ATTRS` in `tui/adapter.py` against the real
  `Character` dataclass. Replace guesses with confirmed names. Pay
  attention to: how spells are stored (objects vs name strings — if
  names, hydrate details from `data/spells.json` via a small lookup,
  respecting the repo rule against bulk-reading large JSONs), how
  inventory quantity/wealth are modeled, and how spell slot usage is
  tracked.
- Confirm `is_caster`, AC, and proficiency bonus are computed properties
  on the model and use them.

**Done when:** `uv run python -m tui` lists the human's real saved
characters and every field on every tab shows real data (no spurious
"—"). Create a throwaway character in the Tkinter GUI first if no saves
exist.

### 3. Persist HP and spell slots

- `h`/`H` (consider `shift+h`→`H` handling) write through to the model
  and call `save_character()`.
- On the Spells tab: `s` spends a slot, `S` restores one, updating
  `SlotPips`. Persist.
- Never write a save the Tkinter GUI can't read back — round-trip test:
  edit in TUI, open in GUI, verify, edit in GUI, reopen in TUI.

**Done when:** the round-trip test passes both directions.

### 4. Quality pass

- Add `tui/tests/` (plain pytest, no GUI) covering `adapter.py` and
  `loader.py` with a fixture character JSON.
- Run the repo BDD suite to prove nothing outside `tui/` broke.
- Update `tui/CLAUDE.md`: remove resolved "known-unverified" items,
  record the confirmed Textual version and any API corrections made.

## Backlog (after the above, in rough priority)

- Skill-check rolls: `enter` on a Skills row → DiceRoller pre-loaded
  with that modifier.
- Rest dialog (short/long) mirroring `gui/rest_dialog.py` semantics.
- Feature use tracking (spend/restore on the Features tab).
- Level-up wizard (big; plan with the human first).

## Ground rules recap

Adapter-only model access · never modify `models/`/`gui/`/`data/` ·
palette discipline (violet = magic only) · degrade to "—", never crash ·
every action has a visible key binding.
