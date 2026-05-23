# Handoff: D&D Character Sheet PDF Redesign

## Overview

This package contains a redesigned 4-page character sheet for VibeDnD, the goal being to **replace the visual design** of `export/pdf_export.py` while keeping all data integration and code structure intact. The redesign is **printer-friendly** (white backgrounds, outlined chips/bars, no solid-fill panel headers) and reorganizes content for in-play usability.

It also fixes three real bugs found in the current output.

## About the design files

The HTML file in this bundle — `Character Sheet.html` — is a **design reference**, not production code. It is a hand-rendered mockup for *Enixif Gomblewomble* (Deep Gnome Rogue 5, Thief subclass, Criminal background, no class spells) at the level of detail needed to drive the FPDF port.

Your task is to recreate the design **inside `export/pdf_export.py`** using FPDF, **not** to render HTML to PDF. Re-use the existing helpers (`_section_box`, `_label_value_box`, `_rounded_rect`, `_small_circle`, `_draw_diamond`, etc.) where appropriate. The existing data-fetching paths (Character properties, `build_standard_actions`, `get_spellbook_entries`, etc.) should remain unchanged.

## Fidelity

**Hifi.** Use exact mm dimensions, font sizes, and grey/accent values listed in the **Design Tokens** section below. Where the HTML uses CSS values that don't map 1:1 (e.g. `oklch`), the hex/RGB equivalent is provided.

## Reference files in this bundle

| File | What it is |
|---|---|
| `Character Sheet.html` | The 4-page mockup. Open in a browser, use the in-page **Tweaks** panel to preview palette / type / chip toggles. |
| `tweaks-panel.jsx` | Tweaks panel runtime (only relevant for opening the HTML). |
| `screenshots/01-page.png` … `04-page.png` | Rendered images of each page at 1.0× — use these as the visual target. |
| `reference_old.pdf` | The current PDF output for Enixif. Read this side-by-side with the new design to see what's changing. |

---

## 🐛 Bugs to fix (do these first — they are independent of the redesign)

### Bug 1 — Content drawn twice on page 1

**Affected functions:** `_draw_proficiencies` (lines 1265–1379), `_draw_languages` (1382–), `_draw_equipment_list` (1422–), and `_draw_weapons_section` (808–).

These all follow a "draw content → measure height → redraw box → draw content again" pattern. The **first** content draw is supposed to be a dry-run for measurement, but it actually paints text onto the canvas. The redraw then paints the same text on top — looks fine if it lines up exactly, but if anything shifts even slightly the duplicate becomes visible (as seen in the reference PDF, where TRAINING & PROFICIENCIES, Languages, and Equipment all appear duplicated).

**Fix:** replace the "draw twice" pattern with either of:
- **Compute height up front** from data (preferred). For proficiencies: 3 fixed rows × known height. For equipment: `len(items)` × row height. For weapons: `max(4, len(rows))` × row height. The current code already estimates these; just use the estimate to draw the box first, then draw content once.
- **Use `local_context` save/restore** around the measure pass with `fill_opacity=0` and `text_color=transparent` to make it a true dry-run.

Recommendation: go with the first option. The text never overflows in practice — these are small fixed-content sections.

### Bug 2 — Empty spellcasting page on non-casters with innate spells

**Affected code:** `CharacterSheetPDF.__init__` (lines 100–108):
```python
if character.is_caster or self._spellbook_entries():
    self.add_page()
    self._draw_page_3_spells()
```

The `or self._spellbook_entries()` clause means anyone with species-granted innate spells (Deep Gnome's Gift of the Svirfneblin, Tiefling cantrips, etc.) triggers the full caster page — including a "Spellcasting Ability: None", "Spell Save DC 11", and a 9-row empty spell-slot grid. Visually broken and a waste of paper.

**Fix:** split the conditional into two cases:
```python
if character.is_caster:
    self.add_page()
    self._draw_page_3_spells()
elif self._spellbook_entries():
    # Render innate-spell cards inline on the new page 3 (Heritage page),
    # don't add a separate caster page.
    pass  # handled inside _draw_page_3_heritage in the redesign
```

The redesign incorporates innate spells as compact cards on page 3 (see "Page 3" section below).

### Bug 3 — Equipped weapons missing from the Weapons table

**Affected code:** `_draw_weapons_section` calls `build_standard_actions(...)`, which apparently only emits a subset of equipped weapons. In the reference PDF only Shortsword shows up; Enixif's 2 Daggers, Shortbow, and 20 Arrows are in Equipment but not in the Weapons table.

**Fix:** out of scope for the design port, but flag it for the team — likely `models/standard_actions.py` is filtering on a `is_equipped` flag the inventory step never sets. Either:
- Promote every inventory item with weapon properties into the Weapons table, OR
- Add a UI step that lets the player mark which weapons are "ready" (the redesign's table is labeled simply "Weapons & Attacks" so either interpretation works).

---

## Design tokens

These are the **exact** values to use in `pdf_export.py`. Replace the existing `C_*` constants with these.

```python
# ── Color palette (printer-friendly) ──
C_INK       = (54, 52, 49)    # primary text — was C_BLACK (30,30,30); slightly warmer
C_INK_2     = (94, 90, 86)    # secondary text
C_INK_3     = (140, 135, 128) # muted / "key" labels
C_RULE      = (190, 184, 174) # thin borders & dotted dividers
C_RULE_2    = (212, 207, 199) # very faint dotted lines (skill row separators)
C_PAPER     = (255, 255, 255) # pure white (no paper tint — saves ink)

# Accent — Rogue oxblood (current default; the user has confirmed this).
# A future version may pick a class-keyed accent; for now use a single accent.
C_ACCENT     = (122, 42, 50)  # #7a2a32
C_ACCENT_INK = (58, 34, 24)   # #3a2218 — darker accent for text
C_ACCENT_2   = (158, 90, 95)  # lighter accent for ornaments

# Action-type chip colors (used on page 2/3 features, all rendered as outlines)
C_CHIP_ACTION   = (138, 65, 38)   # warm orange-red
C_CHIP_BONUS    = (50, 92, 158)   # blue
C_CHIP_REACTION = (110, 60, 138)  # purple
C_CHIP_PASSIVE  = (110, 105, 100) # grey
C_CHIP_REST     = (158, 122, 50)  # gold
```

### Typography

The HTML uses Cinzel (display) + EB Garamond (serif) + Inter Tight (UI). For the PDF port, **keep Georgia** as the workhorse serif (it's already wired up, cross-platform, and stylistically fine). If you want the Cinzel look, register Cinzel as an additional font for **major display only** (character name, page-title H2s, ability modifiers). Do NOT replace Georgia entirely — Cinzel is too tall for body text.

| Token | Font / size | Used for |
|---|---|---|
| `display` | Cinzel 600 (or Georgia Bold) — 26pt | Character name on page 1 |
| `display` | Cinzel 600 — 22pt | "Hit Points 33" max HP value |
| `display` | Cinzel 600 — 19pt | Page 2/3/4 H2 titles |
| `display` | Cinzel 600 — 17pt | Ability modifiers (+0, +2, …) |
| `display` | Cinzel 600 — 13pt | Senses values (Initiative +2, Speed 30 ft) |
| `display` | Cinzel 600 — 11pt | Section-rule headings ("Class — Rogue") |
| `serif` | EB Garamond / Georgia — 10pt | Body text in feature cards |
| `serif italic` | EB Garamond Italic / Georgia Italic — 11pt | Subtitle under each page header ("Class features, subclass, …") |
| `serif italic` | 9pt | "from Background", page references in feat headers |
| `ui` | Helvetica — 7pt, uppercase, letter-spacing .14em | All-caps labels ("CURRENT", "TEMPORARY", "PROFICIENCY") |
| `ui` | Helvetica Bold — 7pt, uppercase, letter-spacing .18em | Panel title bars ("WEAPONS & ATTACKS") |
| `ui` | Helvetica Bold — 5.8pt, uppercase | Action-type chips ("ACTION", "BONUS") |

### Spacing & geometry

A4 portrait. Page margin **11mm all sides** (current code uses 8mm — give the new layout more breathing room; the redesign is calibrated against 11mm).

| Geometry | Value |
|---|---|
| Border radius (small) | 1.5mm |
| Border radius (medium) | 2mm |
| Border weight | 0.6pt for panel borders, 0.4pt dotted for dividers, 0.5pt dotted for skill rows |
| Page-foot rule | 0.4pt above footer at `PAGE_H - 9mm` |

---

## Page-by-page port guide

The page count goes from **2 pages (or 4 with spells)** → **3 pages (or 4 with spells)** for a non-caster like Enixif. For a class caster (Wizard, Cleric, …) the spellcasting page remains the existing `_draw_page_3_spells` flow until that gets its own redesign pass (next).

### Page 1 — Combat & Stats (replaces current page 1)

#### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  HEADER                                                          │
│  ┌─────────────────────────────────┐  ┌───────┐ ┌──────────┐    │
│  │ Enixif Gomblewomble              │  │ HEROIC│ │   +3     │    │
│  │ Deep Gnome · Rogue 5 · Thief …   │  │ INSP. │ │  PROF.   │    │
│  └─────────────────────────────────┘  └───────┘ └──────────┘    │
│  ════════════════════════════════════════════════════════════   │
│  COMBAT ROW                                                      │
│  ┌────────┐ ┌─────────────────────┐ ┌────────┐ ┌──────────┐    │
│  │ AC 12  │ │ HP 33  ___ ___      │ │ HD 5d8 │ │ DEATH    │    │
│  │ Leather│ │   max  curr tmp     │ │ □□□□□  │ │ ○○○ ●●●  │    │
│  └────────┘ └─────────────────────┘ └────────┘ └──────────┘    │
│  CONDITIONS STRIP — 14 boxes + Exhaustion 6-tick                │
│  ┌─ □ Blinded  □ Charmed  …  Exhaustion ○○○○○○ ─┐               │
│                                                                  │
│  TWO COLUMNS                                                     │
│  ┌─ ABILITIES (60mm) ─┐  ┌─ RIGHT (rest) ──────────────┐        │
│  │ STR  +0     11     │  │ Senses · Init Speed Size PP │        │
│  │  ○ +0 Save        │  │   + Darkvision 120 ft       │        │
│  │  ○ +3 Athletics   │  ├──────────────────────────────┤        │
│  ├────────────────────┤  │ Weapons & Attacks (table)   │        │
│  │ DEX  +2     14     │  ├──────────────────────────────┤        │
│  │  ● +5 Save        │  │ Training & Proficiencies     │        │
│  │  ● +5 Acrobatics  │  ├──────────────────────────────┤        │
│  │  ◆ +8 SoH    Exp  │  │ Languages (chips)            │        │
│  │  ◆ +8 Stealth Exp │  ├──────────────────────────────┤        │
│  └────────────────────┘  │ Equipment (2-col) + Coins   │        │
│                          └──────────────────────────────┘        │
│  FOOTER ───────────────────────────────────────────────  I / IV │
└─────────────────────────────────────────────────────────────────┘
```

#### Components on this page

**Header (top ~18mm)**

- **Character name**: Cinzel/Georgia Bold 26pt at top-left, `C_INK`. Underline removed — replaced by the full-width thin rule under the header block.
- **Meta line** (Deep Gnome · Rogue 5 · Thief · Criminal): Georgia Italic 11pt, `C_INK_2`. The bullets between are `C_ACCENT`.
- **Heroic Inspiration card** (top-right, ~22mm wide): outlined rect, contains a rotated-square frame (~9mm) with `0.6pt` accent border + nested smaller diamond inside.
- **Proficiency badge** (top-right, beside Inspiration): outlined rect, `C_ACCENT` border, "+3" in Cinzel 18pt `C_ACCENT_INK`, "PROFICIENCY" caps label below.
- A **0.6pt rule** in `C_INK` runs across the full content width at the bottom of the header.

→ **Drop the "DUNGEONS & DRAGONS" centered text** from the current header — it's unnecessary clutter (you know what game it is).

**Combat row (~22mm tall, 4 columns: 32mm | flex | 28mm | 38mm)**

- **AC**: outlined rect; "ARMOR CLASS" caps label, value `12` in Cinzel 28pt, subtitle "Leather Armor" in 7pt caps.
- **HP — the hero element** ⚠ This is where the **two new pen-and-paper fields** live: outlined rect with **0.8pt `C_INK` border** (heavier than other boxes). Layout:
  - Top row of small labels: left "HIT POINTS" / right "1d8 · Average +Con per Level" — both 6.5pt caps, `C_INK_3`.
  - Bottom row split into 3: **MAX** (large Cinzel 26pt, with a right vertical divider), then two equal-width blank write boxes (no value, just `9mm` of vertical writing space) labeled "CURRENT" / "TEMPORARY" beneath.
  - The two blank lines are `0.6pt solid C_INK_2` baselines — these are the empty fields the user explicitly asked for. Do **not** print a number into them.
- **Hit Dice**: "HIT DICE" caps, value "5" in Cinzel 16pt + "d8" beside, then a row of small `4mm × 4mm` empty squares (one per maximum hit-die: `c.level` squares) labeled "Used" — for the player to tick.
- **Death Saves**: caps label, two rows:
  - "Success" + 3 empty circles (`r=1.3mm`, `0.6pt C_INK_2` outline)
  - "Failure" + 3 empty circles (border color `C_CHIP_ACTION` — they're more attention-grabbing)
  - Replaces the cramped single-letter "S"/"F" in the current sheet.

**Conditions strip** (full width, ~7mm tall, outlined rect)

- Left side: "CONDITIONS" caps label with a vertical divider.
- Middle (flex-wrap): 14 D&D 2024 conditions, each as `2.3mm` checkbox + name in 7pt Helvetica, `C_INK_2`. Conditions: Blinded, Charmed, Deafened, Frightened, Grappled, Incapacitated, Invisible, Paralyzed, Petrified, Poisoned, Prone, Restrained, Stunned, Unconscious.
- Right: vertical divider + "EXHAUSTION" + 6 empty circles (`r=1.2mm`).

**Body left column — Ability scores (60mm wide)**

Six stacked panels, one per ability. Each panel:
- Outlined rect, `padding: 1.5mm 2.5mm`.
- **Single-line header** (do NOT stack name/modifier on separate lines — that's how the current sheet wastes ~36mm): name on the left (Cinzel 9pt caps, `C_ACCENT_INK`), modifier in middle (Cinzel 17pt `C_INK`, e.g. `+2`), "SCORE 14" on the right (Helvetica 7.5pt caps, `C_INK_3`). Bottom border 0.4pt dotted under header.
- **Skill rows** below: 3-column grid `[pip 3.5mm | mod 6mm | name flex]`.
  - **Pip glyph**: `r=1.2mm` circle.
    - Not proficient → outline only, `C_RULE`
    - Proficient → filled with `C_ACCENT`
    - Expert → filled with `C_ACCENT` + inset white ring + outer accent ring (donut effect)
  - **Modifier**: tabular-nums, right-aligned, Georgia Bold 8pt `C_INK`.
  - **Skill name**: Georgia 8pt, `C_INK_2` normal / `C_INK` when expert. Expert rows also get a small `EXP` tag (Helvetica 5.8pt caps `C_ACCENT`) after the name.
- The **first row is always the Saving Throw**, formatted like a skill row but with `font-variant: small-caps` and a bottom 0.4pt dotted separator below it.

Map current data: keep using `c.is_proficient_save(ability)`, `c.saving_throw_modifier(ability)`, `c.skill_modifier(skill_name)`, `c.all_skill_proficiencies`. For expertise detection, you'll need to check `c.expertise_skills` or similar — verify the property name in `models/character.py`; it's currently not used by `pdf_export.py`, so this is new.

**Body right column — multiple panels (stacked, full remaining width)**

Each panel uses the **outline title bar** style:
- 1.5mm top padding, 1.2mm bottom padding.
- "WEAPONS & ATTACKS" etc. in Helvetica Bold 7pt, uppercase, `C_ACCENT_INK`, letter-spacing 0.18em.
- A small `1.6mm` diamond ornament to the left of the title, filled `C_ACCENT`.
- Bottom of the title bar: 0.6pt `C_ACCENT` rule (NOT a solid filled bar — this is the big ink saving).
- Panel body: 2mm top padding, 3mm side padding.

In order, the right column contains:

1. **Senses** — 4-column grid of equal-width cells with vertical separators (0.5pt `C_RULE`):
   - Initiative (`+modifier_str(c.initiative)`)
   - Speed (`30` large + "ft" superscript-style small)
   - Size (`Small`)
   - Passive Perception (`15`)
   - Each cell: caps label 6pt `C_INK_3` on top, value Cinzel 13pt `C_INK` below.
   - **Below the grid**: a thin separator + a one-line italic strip listing extra senses: "Darkvision 120 ft · Svirfneblin Camouflage". Label "SENSES" 6.5pt caps on the left, content right-aligned. This is where Darkvision lives (it's currently buried in species traits).

2. **Weapons & Attacks** — table with 4 columns:
   - `Name` (32mm), `Atk` (12mm), `Damage` (26mm), `Properties` (flex).
   - Header row: 6.5pt caps `C_INK_3`, bottom 0.5pt rule.
   - Each row: weapon name in Georgia 10pt small-caps; atk bonus tabular-nums bold; damage `1d6+2 piercing` (piercing in `C_INK_3`); properties with `Light, Finesse · ` muted + the mastery property (`Vex`, `Nick`) in `C_INK`.
   - Row dividers: 0.4pt dotted `C_RULE_2`.
   - Always render **at least 4 rows** even if fewer weapons — extra rows are dotted blanks for handwriting.

3. **Training & Proficiencies** — 2-column grid `[key 16mm | value flex]`:
   - `ARMOR` → "Light"
   - `WEAPONS` → "Simple weapons, Martial weapons with the Finesse or Light property"
   - `TOOLS` → "Thieves' Tools"
   - Keys: Helvetica 6.5pt caps `C_INK_3`. Values: Georgia 9pt `C_INK`.
   - **Drop the row of `○ Light  ○ Medium  ○ Heavy  ○ Shields` checkboxes** from the current sheet — listing only what the character actually has is cleaner than showing all 4 with most unfilled.

4. **Languages** — flex-wrap of pill chips:
   - Each chip: `0.5pt C_RULE` outline, fully rounded (border-radius = height/2), Georgia 9pt small-caps `C_INK_2`, padding `0.6mm 2.2mm`.
   - **Native languages** (Common, Thieves' Cant): `0.8pt C_ACCENT` outline, text `C_ACCENT_INK`, font weight 600. The distinction is "languages from the species/background's native set" vs. "extras". Check `c.languages` against `c.species.get('languages')` / background languages to decide.

5. **Equipment** — 2-column grid with bullet + name:
   - Each item: `1.4mm × 1.4mm` filled square in `C_ACCENT` + name in Georgia 9.2pt.
   - Quantity (if > 1) precedes the name in bold tabular-nums.
   - **Pad out to ~14 rows** with `0.4pt C_RULE_2` baseline blanks so the player can write more items.
   - **Coins row** at the bottom, separated by a 0.5pt top rule:
     - 5 equal columns: CP, SP, EP, GP, PP. Cinzel 11pt amount above, 6.5pt caps label below.
     - **Zeros fade to `C_RULE`** — both value and label. The non-zero values stay `C_INK`. This makes "157 GP" stand out instead of being lost in a row of mostly-zeros.

**Footer**

- 0.4pt rule, then a row:
  - Left: "Enixif Gomblewomble · Deep Gnome Rogue 5" — Helvetica 7pt small-caps `C_INK_3`.
  - Right: Roman numeral "I / IV" — Cinzel 9pt `C_INK_2`.

---

### Page 2 — Class Features

#### Layout

- **Page header** (top ~12mm):
  - "Features & Heritage" H2 (Cinzel 19pt) on the left, italic subtitle below ("Class features, subclass, and species traits.").
  - **Chip legend** on the right: 5 small outlined chips showing the meaning of each action-type color (Action / Bonus / Reaction / Passive / 1/Rest). This is the key the rest of the page references.
  - 0.6pt `C_INK` rule under header.
- **Section rule**: "CLASS — ROGUE" in Cinzel 11pt caps, `C_ACCENT_INK`, with a 2.4mm diamond ornament to the left and a thin 0.5pt rule extending to the right edge.
- **Feature list** below:

#### Feature card

Each feature is a card with a 1pt `C_ACCENT` left rule (no surrounding border). 4mm padding-left from the rule.

- **Head row**: flex with wrap, baseline-aligned, gap 2.5mm.
  - `h3` (Cinzel 11.5pt `C_INK`) — feature name.
  - **Action-type chip(s)** — see chip spec below.
  - **Source line** wraps to its own line below the heading (`flex-basis: 100%`), Georgia Italic 8.5pt `C_INK_3`. Contains the level + selections (e.g. "Rogue 1 · Selected: Sleight of Hand, Stealth") or computed values ("Rogue 5 · DC 13", "+3d6 at level 5").
- **Body paragraphs**: Georgia 9.5pt `C_INK`, line-height 1.42, `text-wrap: pretty` (use FPDF's `dedent`+`multi_cell` with manual paragraph spacing).
- **Bulleted lists** (used in Cunning Strike, Subclass body): same Georgia 9.5pt.

#### Action-type chips

Each chip: outlined rect, `0.6pt border`, `0.4mm × 1.6mm` padding, border-radius 1mm, Helvetica Bold 5.8pt caps letter-spacing 0.14em.

| Chip | Border + Text color | Constant |
|---|---|---|
| Action | warm orange-red | `C_CHIP_ACTION` |
| Bonus | blue | `C_CHIP_BONUS` |
| Reaction | purple | `C_CHIP_REACTION` |
| Passive | grey | `C_CHIP_PASSIVE` |
| 1/Rest | gold | `C_CHIP_REST` |
| Subclass | accent (`C_ACCENT_INK` text, `C_ACCENT` border) | special |

**How to derive the chip from data**: the current code at `_draw_class_features` just dumps `feature.description`. To get action-type chips you need to look at the feature's action_type field if it exists, OR maintain a small lookup table in the export module:

```python
FEATURE_ACTION_TYPES = {
    "Cunning Action": "bonus",
    "Steady Aim": "bonus",
    "Uncanny Dodge": "reaction",
    "Sneak Attack": "passive",
    "Expertise": "passive",
    "Thieves' Cant": "passive",
    "Weapon Mastery": "passive",
    "Cunning Strike": "passive",  # rider, not its own action
    "Fast Hands": "bonus",
    "Second-Story Work": "passive",
    "Alert": "passive",
    "Darkvision": "passive",
    "Gnomish Magic Resistance": "passive",
    "Svirfneblin Camouflage": "passive",
    "Gift of the Svirfneblin": "passive",
    # ... add more as you encounter them
}
```

A long-term fix is to add `"action_type"` to the JSON feature data and read it from there.

#### Subclass card

- Same card format but with a `Subclass` chip instead of an action-type chip.
- Body contains 2 paragraphs (one per subclass feature), each starting with the feature name in `Georgia Bold` and the body inline.

#### Footer
- "Enixif Gomblewomble · Features & Heritage" + "II / IV"

---

### Page 3 — Heritage, Feats & Magic

This page consolidates Species traits, Feats, and (only for non-casters with innate spells) Innate Spells into a single page.

For class-caster characters, this page becomes the existing Spellcasting page (no changes for this iteration).

#### Layout

- Page header: "Heritage, Feats & Magic" with subtitle "Species traits, feats, and the spells Enixif carries in his blood." + chip legend on the right (same as page 2).
- Section rule: "SPECIES — DEEP GNOME"
  - Feature list: Darkvision, Gnomish Magic Resistance, Svirfneblin Camouflage, Gift of the Svirfneblin
  - Same card format as page 2.
  - **Svirfneblin Camouflage** source field shows usage tracker: "Uses · ○○○ /3 per Long Rest" — render the circles as actual glyphs (3 outlined circles `r=0.8mm`).
- Section rule: "FEATS"
  - Feat list (currently Enixif only has Alert from his background).
- Section rule: "INNATE SPELLS — GIFT OF THE SVIRFNEBLIN" (only if `_spellbook_entries()` non-empty)
  - Container with the same outlined title-bar style.
  - One **spell card** per innate spell:
    - **Top row**: spell name (Cinzel 11pt) + level/school italic ("1st-level · Illusion") + right-aligned usage tracker: "Uses ○ per Long Rest" (single empty circle for 1/rest spells).
    - **Meta row**: 4-column grid (Casting / Range / Duration / Components) with caps label 7pt `C_INK_3` on top and value Georgia 9pt `C_INK` below.
    - **Description**: full body text in Georgia 10pt, line-height 1.55.

#### Footer
- "Enixif Gomblewomble · Heritage & Magic" + "III / IV"

---

### Page 4 — Persona & Story

Pure pen-and-paper — almost everything here is empty fields for the player to write into.

#### Layout

- Page header: "Persona & Story" + subtitle "Who Enixif is when the dice aren't rolling." (no chip legend on this page).
- **Persona quadrants** (2×2 grid, equal cells, gap 3mm):
  - Cells: Personality Trait, Ideal, Bond, Flaw
  - Each cell: outlined rect, min-height 44mm. Inside:
    - "PERSONALITY TRAIT" caps label 6.5pt `C_ACCENT_INK` letter-spacing 0.18em
    - Below the label: ruled-line writing area filling the rest of the cell. Lines every 5.5mm, `0.3pt C_RULE_2`. Implement as repeated horizontal lines.
- **Backstory card** (full width, below quadrants):
  - "BACKSTORY" caps label, then body text in Georgia 10pt line-height 1.55 (the existing backstory paragraphs flow into here), then **a 44mm ruled writing area** below for adding more.
- **Portrait** (full width, below backstory):
  - Outlined rect, min-height 60mm, background white (no diagonal stripes from the current portrait).
  - Center placeholder: 0.4pt dashed `C_INK_3` border with text "PORTRAIT OR SYMBOL" inside (Helvetica 7pt caps letter-spacing 0.18em `C_INK_3`).
  - If `biography_image_data` is set, render the image instead, fit-to-frame with `min` scaling (current code already does this — keep it).

#### Footer
- "Enixif Gomblewomble · Persona & Story" + "IV / IV"

---

## Function-by-function porting map

| Current function | Action | Notes |
|---|---|---|
| `__init__` | Tweak page-add logic | Split caster vs. innate-spells case (Bug 2) |
| `_register_fonts` | Keep | Optionally add Cinzel for display sizes |
| `_serif`, `_sans` | Keep | Add a `_display(style, size)` for Cinzel |
| `_rounded_rect` | Keep | |
| `_shadow_rect` | **Remove all calls** | Shadows print as grey blobs — not ink-friendly |
| `_section_box` | **Refactor** | Drop the solid title bar; replace with outline title bar (new function `_panel_title_outline`) |
| `_draw_section_title` | **Replace** | New version draws caps-text + diamond + bottom rule, no fill |
| `_draw_diamond` | Keep | Used for ornaments + chip dividers |
| `_draw_ornamental_line` | **Delete** | Replaced by simple thin rule under page header |
| `_label_value_box` | Refactor | Remove fill, change to outline-only |
| `_small_circle` | Keep | Used for prof pips, death saves, exhaustion, usage trackers |
| `_draw_corner_ornament` | **Delete** | Not used in redesign |
| `_draw_page_1` | Rewrite | New layout per spec above |
| `_draw_header` | Rewrite | New name+meta+inspiration+prof layout |
| `_draw_header_stat_box` | **Delete** | New combat row has 4 different box types, not 5 identical ones |
| `_header_info_pair` | Inline into `_draw_header` | The meta is now a single italic line with bullets, not 4 label/value boxes |
| `_draw_stats_row` | **Replace with `_draw_combat_row`** | New AC / HP / HitDice / DeathSaves layout. HP gets the new pen-and-paper fields. |
| — (new) | `_draw_conditions_strip` | 14 conditions + exhaustion track |
| `_draw_ability_scores` | Rewrite | Single-line header (name + mod + score), prof pips on every row, expertise as donut |
| — (new) | `_draw_senses_panel` | Init / Speed / Size / Pass Perc grid + dvision strip |
| `_draw_weapons_section` | Rewrite | New 4-column table, dotted dividers, padding to 4 rows minimum |
| `_draw_class_features` | Rewrite | New card format with chip + source-line + body |
| `_draw_species_traits` | Move to page 3 | Same card format as `_draw_class_features` |
| `_draw_feats` | Move to page 3 | Same card format |
| `_draw_heroic_inspiration` | Move to page 1 header | Now it's just a small rect in the header, not a separate footer card |
| `_draw_proficiencies` | Rewrite | 2-column key/value grid; drop the armor checkbox row |
| `_draw_languages` | Rewrite | Pill chips, native vs. extra distinction |
| `_draw_equipment_list` | Rewrite | 2-column grid + accent bullet + qty + blank rows + coin row with faded zeros |
| — (new) | `_draw_page_3_heritage` | Renders species + feats + innate spells (when non-caster) |
| — (new) | `_draw_innate_spell_card` | The compact spell card used on page 3 for innate spells (and as building block for the future caster page) |
| `_draw_page_3_spells` | Keep for now | Will be redesigned in a future iteration (the user said "we'll do the spellsheet tomorrow") |
| `_draw_personality` | Move to page 4 | Wrap in 2×2 quadrants instead of one box |
| — (new) | `_draw_persona_quadrants` | 2×2 grid with ruled writing areas |
| — (new) | `_draw_backstory_card` | Backstory text + 44mm ruled writing area |
| `_draw_portrait_placeholder` | Move to page 4 | Same impl; remove diagonal stripe background |
| `_draw_coins` | Move to bottom of equipment panel on page 1 | Add zero-fade styling |
| `_draw_page_footer` | Rewrite | Simple rule + left name + right roman numeral |
| `_draw_spell_descriptions_pages` | Keep | Don't touch for this iteration |

---

## Data sources to keep using

Don't introduce new property reads — these are already in the model:

| What | Where | Notes |
|---|---|---|
| Character name | `c.name` | |
| Species name | `c.species_name`, `c.species_sub_choice` | "Deep Gnome" |
| Class | `c.class_name`, `c.character_class` | |
| Subclass | `c.current_subclass` | Use `.replace('-', ' ').title()` for display |
| Background | `c.background_name` | |
| Level | `c.level` | |
| AC | `c.armor_class` | |
| HP max | `c.hit_points` | The number that goes in the "MAX" cell; current/temp are blank fields |
| Hit die | `c.character_class.get('hit_die', 8)` | for `1d8` label; level = number of hit dice |
| Proficiency bonus | `c.proficiency_bonus` | |
| Initiative | `c.initiative` | |
| Speed | `c.speed` | |
| Size | `c.size_choice or 'Medium'` | |
| Passive Perception | `10 + c.skill_modifier("Perception")` | |
| Ability score | `get_effective_ability_score(c, name)` | |
| Ability modifier | `_eff_mod(c, name)` (alias for `get_effective_modifier`) | |
| Save proficiency | `c.is_proficient_save(name)` | |
| Save modifier | `c.saving_throw_modifier(name)` | |
| Skill modifier | `c.skill_modifier(name)` | |
| Skill proficiencies | `c.all_skill_proficiencies` | |
| Skill expertise | **TODO — verify in `character.py`** | Likely `c.expertise_skills` or similar; falls back to `set()` if missing |
| Languages | `c.languages` | Native vs. extra: compare to species/background language sets |
| Weapon proficiencies | `c.effective_weapon_proficiencies` | |
| Armor proficiencies | `c.effective_armor_proficiencies` | |
| Tool proficiencies | `c.background.get('tool_proficiency')` + class tool proficiencies | |
| Inventory | `c.inventory` | for equipment list |
| Coins | `cp_to_coins(current_wealth_cp(c))` | already imported |
| Spellbook (incl. innate) | `self._spellbook_entries()` | |
| Is class caster | `c.is_caster` | |
| Standard actions (weapons + cantrips) | `build_standard_actions(...)` | already wired |
| Biography | `c.biography_backstory`, `c.biography_personality`, `c.biography_description`, `c.biography_image_data` | |

---

## Suggested implementation order

1. **Bug fixes first** — fix the double-draw in proficiencies/languages/equipment/weapons (Bug 1) and the caster/innate split (Bug 2). Verify the existing layout still renders correctly. This gives you a clean baseline before changing visuals.
2. **Update the color/font constants** — replace `C_*` constants with the new printer-friendly palette; introduce `_panel_title_outline` and replace calls to `_section_box`'s title bar with it. Don't change any layout yet. Verify the result is still readable but lighter on ink.
3. **Page 1 combat row** — rewrite `_draw_stats_row` → `_draw_combat_row`. Test that the HP "Current"/"Temporary" blank fields render correctly with empty space for handwriting.
4. **Page 1 abilities** — rewrite to single-line header + prof pips on every row.
5. **Page 1 right column** — Senses, then Weapons, then Profs, then Langs, then Equipment in this order.
6. **Conditions strip** — slot in between combat row and body.
7. **Page 2 features** — rewrite `_draw_class_features` with the new card format. Add the `FEATURE_ACTION_TYPES` lookup.
8. **Page 3 heritage** — new function `_draw_page_3_heritage` that runs only when `not c.is_caster and self._spellbook_entries()` (or always when species traits + feats exist — there is always at least one feat from the background per 2024 rules). Includes the innate spell cards.
9. **Page 4 persona** — new function `_draw_page_4_persona` with quadrants + backstory + portrait.
10. **Footers** — replace `_draw_page_footer` with the new minimal style.

After each step, regenerate the PDF with `python preview_pdf.py` (or however your dev loop works) and compare against `screenshots/0N-page.png`.

---

## What's intentionally NOT in scope here

- **The Spellcasting page redesign** — the user has said "we'll have a look at how to make a spellsheet tomorrow." Keep the existing `_draw_page_3_spells` for class casters; it's ugly but it's still there.
- **Class-keyed accent color** — the HTML has a Tweaks panel that swaps Rogue oxblood for Fighter steel / Wizard indigo / etc. Don't implement palette switching in the PDF for now; ship with `C_ACCENT = (122, 42, 50)` and we'll wire it to `c.class_name` later.
- **Cinzel font** — optional. If `Cinzel.ttf` is not bundled, fall back to Georgia Bold at the same size. Don't break Linux builds for the sake of the display font.

---

## Quick visual checks

After porting each page, eyeball these against the screenshots:

- ✅ Page 1: AC and HP boxes are visibly **larger** than Hit Dice and Death Saves (≈1.6× height-wise visually). HP has TWO empty rectangles below the max value.
- ✅ Page 1: every saving throw and skill has a circle/dot/donut in front of it.
- ✅ Page 1: panel headers are **outline + accent text**, not filled bars.
- ✅ Page 1: coins row has 4 grey zeros and one bold value.
- ✅ Page 2: every feature has a colored chip after its title.
- ✅ Page 2: features have a left accent rule (not a full border).
- ✅ Page 3: no 9-row empty spell-slot grid; innate spells appear as compact cards with description.
- ✅ Page 4: 2×2 quadrants with ruled lines for writing.
- ✅ All pages: white background, no warm paper tint, no drop shadows.
