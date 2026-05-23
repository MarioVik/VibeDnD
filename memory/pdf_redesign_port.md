---
name: pdf-redesign-port
description: The PDF character sheet was fully redesigned in May 2026 per design_handoff_pdf_redesing/README.md — printer-friendly, 4-page layout with oxblood accent
metadata:
  type: project
---

Ported the complete PDF redesign from `design_handoff_pdf_redesing/README.md` into `export/pdf_export.py`.

**Why:** User requested visual redesign for printer-friendliness and in-play usability.

**How to apply:** The spellcasting page (`_draw_page_3_spells`) was deliberately kept as-is (old style) per the design doc — "we'll do the spellsheet tomorrow." Don't redesign that page without explicit instruction.

Key changes:
- New color palette: C_INK/C_INK_2/C_INK_3/C_RULE/C_RULE_2/C_PAPER + oxblood C_ACCENT
- MARGIN changed from 8mm → 11mm
- Page structure: P1 Combat, P2 Class Features, P3 Heritage (non-casters) or Spells (casters), P4 Persona
- Panel headers are now outline-only (no solid fill), printer-friendly
- Bug fixes: double-draw pattern eliminated; caster vs innate-spells conditional split (Bug 2 from handoff)
- Non-casters get heritage page (species traits + feats + innate spell cards)
- 2×2 persona quadrants on page 4 with ruled writing areas
