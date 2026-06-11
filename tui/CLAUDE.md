# CLAUDE.md — VibeDnD TUI (`tui/` package)

Textual-based terminal UI for VibeDnD. This file covers the `tui/`
package only. The host repo's own rules live in the root `AGENTS.md` /
`CLAUDE.md` — **read those too**; their critical rules (paths.py usage,
never read large data JSONs, pyproject.toml for deps) apply here.

## What this is

A TUI character tracker that reuses VibeDnD's `models/` package as its
backend. Scaffolded offline on 2026-06-10, wired to the real backend and
verified against live saves the same day (HANDOVER.md tasks 1–4 done).

```
tui/
├── app.py            # App shell; global `r` dice binding
├── adapter.py        # CharacterView snapshot + write-backs (set_hp, spend_slot…)
├── loader.py         # save discovery via paths.characters_dir() + shared GameData
├── widgets.py        # HPBar, SlotPips, AbilityRow, DiceRoller modal
├── vibednd.tcss      # theme stylesheet
├── screens/
│   ├── home.py       # roster + preview pane
│   └── sheet.py      # tabbed sheet (Overview/Skills/Spells/Inv/Features)
└── tests/            # plain pytest (no GUI) + headless pilot smoke drives
```

## Commands

```bash
uv run python -m tui               # run against real character saves
uv run python -m tui --demo       # built-in sample (no repo data needed)
PYTHONPATH=$PWD ./.venv/bin/pytest tui/tests -q   # TUI unit tests
uv run python -m tui.tests.smoke_demo   # headless pilot drive, demo data
uv run python -m tui.tests.smoke_real   # headless pilot drive, real saves (read-only)
```

The host repo's BDD suite (`tests/bdd`) does not cover the TUI; don't
break it either — `PYTHONPATH=$PWD ./.venv/bin/pytest tests/bdd -q` must
still pass if you touch anything outside `tui/`.

## Critical rules

1. **Model access only via `adapter.py`.** Screens and widgets must never
   call attributes on `models.Character` directly. `from_model()` builds
   the read snapshot; `set_hp` / `spend_slot` / `restore_slot` / `persist`
   are the only write paths. Both saves and loads go through
   `models.character_store`, so files stay GUI-compatible.
2. **Never modify `models/`, `gui/`, or `data/`** to make the TUI work.
   The TUI adapts to the backend, not the other way around. If a backend
   change seems genuinely needed, stop and ask the user first (it's their
   friend's codebase).
3. **Theme discipline.** All colors come from the palette documented at
   the top of `vibednd.tcss`. Violet (#9d7cd8) is reserved exclusively
   for magic; gold (#d4af37) for currency. No new hex values without
   adding them to the palette comment.
4. **Degrade, don't crash.** Unknown/missing data renders as "—" or an
   empty state with guidance. Every `from_model` section is individually
   guarded; a character file that fails to load is skipped, never fatal.
5. **Keyboard-first.** Every mouse interaction needs a key binding; vim
   motions everywhere. Footer map: `r` dice (global), `enter` open,
   `esc` back, `1-5` tabs, `h`/`H` HP -/+, `s`/`S` spend/restore spell
   slot (uses the highlighted spell's level when possible), `m` coin
   pouch/calculator (`tui/money.py` parser; pouch writes go through
   `adapter.adjust_wealth`, which mirrors the GUI's `wealth_adjust_cp`
   semantics incl. the no-negative-pouch rule). Hidden
   (show=False) vim layer: `j`/`k`/`g`/`G`/`ctrl+d`/`ctrl+u` motions via
   the `Vim*` widget subclasses in `widgets.py`, `[`/`]` tab cycling,
   `l` open on the roster, `h`/`l`+`j`/`k` die/count in the DiceRoller.
   `SheetScreen._focus_active_pane()` keeps focus on the visible tab's
   primary widget — preserve that when adding panes, or keys go nowhere.

## Confirmed integration points (2026-06-10)

- **Textual 8.2.7.** All scaffold widgets work as written. One quirk:
  shifted letter bindings must be declared as the uppercase character
  (`"H"`), not `"shift+h"`. `Static.renderable` no longer exists (use
  `render()` — only relevant in tests).
- `paths.characters_dir()` and
  `character_store.load_character(filepath, game_data)` /
  `save_character(character, characters_path, existing_filename=...)`
  are the real signatures. `game_data` is `gui.data_loader.GameData` —
  Tkinter-free, safe to import headless; `tui.loader.game_data()` holds
  the shared instance.
- Spell-slot table keys are ordinals (`"1st"`…`"9th"`), shared by
  `Character.current_spell_slots(game_data)` and
  `Character.used_spell_slots`. Pact magic is separate
  (`current_pact_magic`, `used_pact_slots`) and surfaces in the view
  under the `PACT_KEY` slot key.
- Spells are stored as **name strings**; the full spellbook (class picks
  + feat/species grants) comes from
  `models.spell_grant_utils.get_spellbook_entries(character, game_data)`,
  which hydrates each entry's `spell` dict — no manual spells.json reads.
- Inventory pools come from `models.standard_actions`
  (`get_selected_weapon_counts/armor_counts/non_weapon_items`) plus
  `custom_inventory` minus `removed_items`; wealth from
  `models.inventory_service.current_wealth_cp` + `format_coins`.
  Item details hydrate from `GameData.items_by_name` with tolerant
  matching (curly quotes, `"Clothes, Traveler's"` inversion).
- Species data uses a `"traits"` key (not `"features"` as the root
  AGENTS.md schema suggests); use
  `gui.species_trait_utils.get_species_trait_cards` (also Tkinter-free).
- `current_hit_points=None` in a save means "full HP"; read via
  `Character.effective_current_hp`, write the explicit int back.

## Backlog (from HANDOVER.md)

- Heroic inspiration on the Overview tab — **blocked on backend**: the
  model has no field for it (the PDF's diamond is a blank pen-and-paper
  checkbox). MarioVik will be asked to add it upstream; once
  `Character` grows e.g. `heroic_inspiration` + save/load support,
  surface it as a toggle here.

- Skill-check rolls: `enter` on a Skills row → DiceRoller pre-loaded
  with that modifier.
- Rest dialog (short/long) mirroring `gui/rest_dialog.py` semantics.
- Feature use tracking (spend/restore on the Features tab).
- Level-up wizard (big; plan with the human first).
