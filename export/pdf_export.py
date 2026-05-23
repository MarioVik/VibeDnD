"""Export character as a PDF character sheet — D&D 2024, printer-friendly redesign."""

import base64
import os
import re
import tempfile

from fpdf import FPDF
from fpdf.enums import RenderStyle, Corner
from models.character import Character
from models.enums import ALL_SKILLS
from models.language_utils import all_languages, compute_language_sources
from models.level1_class_rules import (
    augment_level1_feature_description,
    get_level1_creation_choice_lines,
)
from models.spell_grant_utils import (
    format_spellbook_entry_label,
    get_spellbook_entries,
)
from models.item_effects import get_effective_ability_score, get_effective_modifier as _eff_mod
from models.standard_actions import build_standard_actions
from models.inventory_service import cp_to_coins, current_wealth_cp


# ── Layout ──
PAGE_W = 210
PAGE_H = 297
MARGIN = 11
CONTENT_W = PAGE_W - MARGIN * 2   # 188 mm

# ── Color palette (printer-friendly) ──
C_INK       = (54, 52, 49)
C_INK_2     = (94, 90, 86)
C_INK_3     = (140, 135, 128)
C_RULE      = (190, 184, 174)
C_RULE_2    = (212, 207, 199)
C_PAPER     = (255, 255, 255)

C_ACCENT     = (122, 42, 50)
C_ACCENT_INK = (58, 34, 24)
C_ACCENT_2   = (158, 90, 95)

C_CHIP_ACTION   = (138, 65, 38)
C_CHIP_BONUS    = (50, 92, 158)
C_CHIP_REACTION = (110, 60, 138)
C_CHIP_PASSIVE  = (110, 105, 100)
C_CHIP_REST     = (158, 122, 50)

# ── Border weights (mm) ──
LW_PANEL   = 0.21   # ≈0.6pt
LW_DIVIDER = 0.14   # ≈0.4pt
LW_ROW     = 0.18   # ≈0.5pt
LW_RULE    = 0.14

R_SM = 1.5
R_MD = 2.0

# ── Font paths ──
from paths import fonts_dir as _fonts_dir
_FONTS_DIR = _fonts_dir()
FONT_CINZEL        = os.path.join(_FONTS_DIR, "Cinzel-Regular.ttf")
FONT_EBGARAMOND    = os.path.join(_FONTS_DIR, "EBGaramond-Regular.ttf")
FONT_EBGARAMOND_B  = os.path.join(_FONTS_DIR, "EBGaramond-Bold.ttf")
FONT_EBGARAMOND_I  = os.path.join(_FONTS_DIR, "EBGaramond-Italic.ttf")
FONT_EBGARAMOND_BI = os.path.join(_FONTS_DIR, "EBGaramond-BoldItalic.ttf")
# macOS fallback
FONT_GEORGIA        = "/System/Library/Fonts/Supplemental/Georgia.ttf"
FONT_GEORGIA_BOLD   = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
FONT_GEORGIA_ITALIC = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
FONT_GEORGIA_BI     = "/System/Library/Fonts/Supplemental/Georgia Bold Italic.ttf"

ABILITIES = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]
ABILITY_ABBR = {
    "Strength": "STR", "Dexterity": "DEX", "Constitution": "CON",
    "Intelligence": "INT", "Wisdom": "WIS", "Charisma": "CHA",
}
SKILLS_BY_ABILITY = {
    "Strength":     ["Athletics"],
    "Dexterity":    ["Acrobatics", "Sleight of Hand", "Stealth"],
    "Constitution": [],
    "Intelligence": ["Arcana", "History", "Investigation", "Nature", "Religion"],
    "Wisdom":       ["Animal Handling", "Insight", "Medicine", "Perception", "Survival"],
    "Charisma":     ["Deception", "Intimidation", "Performance", "Persuasion"],
}

CONDITIONS = [
    "Blinded", "Charmed", "Deafened", "Frightened", "Grappled",
    "Incapacitated", "Invisible", "Paralyzed", "Petrified", "Poisoned",
    "Prone", "Restrained", "Stunned", "Unconscious",
]

ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]

FEATURE_ACTION_TYPES: dict[str, str] = {
    "Cunning Action": "bonus",
    "Steady Aim": "bonus",
    "Uncanny Dodge": "reaction",
    "Sneak Attack": "passive",
    "Expertise": "passive",
    "Thieves' Cant": "passive",
    "Weapon Mastery": "passive",
    "Cunning Strike": "passive",
    "Fast Hands": "bonus",
    "Second-Story Work": "passive",
    "Alert": "passive",
    "Darkvision": "passive",
    "Gnomish Magic Resistance": "passive",
    "Svirfneblin Camouflage": "passive",
    "Gift of the Svirfneblin": "passive",
    "Spellcasting": "passive",
    "Prepared Spells": "passive",
    "Hunter's Prey": "passive",
    "Favored Enemy": "passive",
    "Natural Explorer": "passive",
    "Fighting Style": "passive",
    "Action Surge": "action",
    "Second Wind": "bonus",
    "Extra Attack": "passive",
    "Rage": "bonus",
    "Reckless Attack": "action",
    "Primal Knowledge": "passive",
    "Bardic Inspiration": "bonus",
    "Song of Rest": "passive",
    "Countercharm": "action",
    "Cutting Words": "reaction",
    "Channel Divinity": "action",
    "Turn Undead": "action",
    "Divine Intervention": "action",
    "Lay on Hands": "action",
    "Divine Smite": "passive",
    "Aura of Protection": "passive",
    "Aura of Courage": "passive",
    "Ki": "bonus",
    "Patient Defense": "bonus",
    "Step of the Wind": "bonus",
    "Deflect Missiles": "reaction",
    "Slow Fall": "reaction",
    "Stunning Strike": "passive",
    "Wild Shape": "bonus",
    "Evasion": "passive",
    "Slippery Mind": "passive",
    "Elusive": "passive",
    "Stroke of Luck": "passive",
    "Reliable Talent": "passive",
    "Arcane Recovery": "passive",
    "Eldritch Invocations": "passive",
    "Pact of the Blade": "passive",
    "Pact of the Chain": "passive",
    "Pact of the Tome": "passive",
    "Frenzy": "bonus",
    "Intimidating Presence": "action",
    "Retaliation": "reaction",
    "Giant Killer": "reaction",
    "Stand Against the Tide": "reaction",
    "Escape the Horde": "reaction",
    "Multiattack Defense": "reaction",
    "Volley": "action",
    "Whirlwind Attack": "action",
    "Colossus Slayer": "passive",
    "Horde Breaker": "passive",
    "Blindsense": "passive",
    "Fey Ancestry": "passive",
    "Lucky": "passive",
    "Halfling Nimbleness": "passive",
    "Draconic Ancestry": "passive",
    "Breath Weapon": "action",
    "Stone's Endurance": "action",
    "Powerful Build": "passive",
    "Mountain Born": "passive",
    "Dwarven Resilience": "passive",
    "Stonecunning": "passive",
    "Dwarven Toughness": "passive",
    "Keen Senses": "passive",
    "Trance": "passive",
    "Gnome Cunning": "passive",
    "Natural Illusionist": "passive",
    "Speak with Small Beasts": "passive",
    "Drow Magic": "passive",
    "Sunlight Sensitivity": "passive",
    "Superior Darkvision": "passive",
    "Infernal Legacy": "passive",
    "Hellish Resistance": "passive",
}


class CharacterSheetPDF(FPDF):
    """Redesigned D&D 2024 character sheet — printer-friendly, 4-page layout."""

    def __init__(self, character: Character, game_data=None):
        super().__init__("P", "mm", "A4")
        self.c = character
        self._game_data = game_data
        self.set_auto_page_break(auto=False)
        self._register_fonts()

        # Pre-count feature overflow pages so Roman numeral totals are accurate
        extra = self._precount_feature_pages()
        self._total_main = 4 + extra
        self._p3_num = 3 + extra
        self._p4_num = 4 + extra

        self.add_page()
        self._draw_page_1()

        self.add_page()
        self._draw_page_2_features()

        if character.is_caster:
            self.add_page()
            self._draw_page_3_spells()
        else:
            self.add_page()
            self._draw_page_3_heritage()

        self.add_page()
        self._draw_page_4_persona()

        if self._spellbook_entries():
            self._draw_spell_descriptions_pages()

    # ── Feature page pre-count ───────────────────────────────────

    def _precount_feature_pages(self) -> int:
        """Estimate overflow pages for the feature section (runs before any page exists)."""
        bottom = PAGE_H - MARGIN - 12
        # Approximate y after page header + class section rule
        y = MARGIN + 19 + 8
        cont_start = MARGIN + 19 + 8
        extra = 0

        def _estimate_card_h(feat):
            desc = feat.get("description", "")
            source = feat.get("source", "")
            # Estimate lines: EB Garamond 9pt on CONTENT_W-9mm inner width
            # approx 2mm/char average → ~90 chars per line
            chars_per_line = max(1, int((CONTENT_W - 9) / 2.0))
            n_lines = (len(desc) + chars_per_line - 1) // chars_per_line if desc else 0
            desc_h = n_lines * 3.8 + 0.5 if n_lines else 0
            return 5.5 + (3.5 if source else 0) + desc_h + 2

        def step(h):
            nonlocal y, extra
            if y + h > bottom:
                extra += 1
                y = cont_start
            y += h + 2

        for feat in self._get_class_features():
            step(_estimate_card_h(feat))

        subclass = self._get_subclass_features()
        if subclass:
            step(10)  # section rule + gap
            for feat in subclass:
                fc = dict(feat); fc["chip"] = "subclass"
                step(_estimate_card_h(fc))

        return extra

    # ── Font registration ────────────────────────────────────────

    def _register_fonts(self):
        if os.path.exists(FONT_CINZEL) and os.path.exists(FONT_EBGARAMOND):
            self.add_font("Cinzel", "", FONT_CINZEL)
            self.add_font("EBGaramond", "", FONT_EBGARAMOND)
            self.add_font("EBGaramond", "B", FONT_EBGARAMOND_B)
            self.add_font("EBGaramond", "I", FONT_EBGARAMOND_I)
            if os.path.exists(FONT_EBGARAMOND_BI):
                self.add_font("EBGaramond", "BI", FONT_EBGARAMOND_BI)
            self._font_display = "Cinzel"
            self._font_serif = "EBGaramond"
        elif os.path.exists(FONT_GEORGIA):
            self.add_font("Georgia", "", FONT_GEORGIA)
            self.add_font("Georgia", "B", FONT_GEORGIA_BOLD)
            self.add_font("Georgia", "I", FONT_GEORGIA_ITALIC)
            if os.path.exists(FONT_GEORGIA_BI):
                self.add_font("Georgia", "BI", FONT_GEORGIA_BI)
            self._font_display = "Georgia"
            self._font_serif = "Georgia"
        else:
            self._font_display = None
            self._font_serif = None

    def _serif(self, style: str = "", size: float = 10):
        if self._font_serif:
            self.set_font(self._font_serif, style, size)
        else:
            self.set_font("Helvetica", style, size)

    def _sans(self, style: str = "", size: float = 10):
        self.set_font("Helvetica", style, size)

    def _display(self, size: float = 16):
        """Cinzel (display) — falls back to EB Garamond Bold, then Helvetica Bold."""
        if self._font_display == "Cinzel":
            self.set_font("Cinzel", "", size)
        elif self._font_serif:
            self.set_font(self._font_serif, "B", size)
        else:
            self.set_font("Helvetica", "B", size)

    # ── Text sanitizer ───────────────────────────────────────────

    @staticmethod
    def _sanitize(text: str) -> str:
        if not text:
            return ""
        replacements = {
            "’": "'", "‘": "'", "“": '"', "”": '"',
            "–": "-", "—": "--", "…": "...", "•": "*",
            "×": "x", "♦": "*", "○": "o", "·": ".",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text.encode("latin-1", errors="replace").decode("latin-1")

    def cell(self, w=None, h=None, text="", *args, **kwargs):
        return super().cell(w, h, self._sanitize(str(text)), *args, **kwargs)

    def multi_cell(self, w, h=None, text="", *args, **kwargs):
        return super().multi_cell(w, h, self._sanitize(str(text)), *args, **kwargs)

    # ── Core drawing helpers ─────────────────────────────────────

    def _modifier_str(self, val: int) -> str:
        return f"+{val}" if val >= 0 else str(val)

    def _rounded_rect(self, x, y, w, h, r=R_MD, style="D", corners=True):
        style_map = {"D": RenderStyle.D, "F": RenderStyle.F, "DF": RenderStyle.DF, "FD": RenderStyle.DF}
        rs = style_map.get(style, RenderStyle.D)
        if corners is True:
            self._draw_rounded_rect(x, y, w, h, rs, True, r)
        else:
            self._draw_rounded_rect(x, y, w, h, rs, corners, r)

    def _draw_diamond(self, cx, cy, size, color):
        self.set_fill_color(*color)
        self.set_draw_color(*color)
        points = [(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)]
        self.set_line_width(0.1)
        self.polygon(points, style="DF")

    def _small_circle(self, cx, cy, r=1.2, filled=False, expert=False):
        """Draw proficiency pip. expert=True draws a donut (accent fill + white ring)."""
        if expert:
            # Outer filled circle
            self.set_fill_color(*C_ACCENT)
            self.set_draw_color(*C_ACCENT)
            self.set_line_width(0.15)
            self.ellipse(cx - r, cy - r, r * 2, r * 2, "DF")
            # White inner ring
            ri = r * 0.45
            self.set_fill_color(*C_PAPER)
            self.set_draw_color(*C_PAPER)
            self.ellipse(cx - ri, cy - ri, ri * 2, ri * 2, "F")
        elif filled:
            self.set_fill_color(*C_ACCENT)
            self.set_draw_color(*C_ACCENT)
            self.set_line_width(0.15)
            self.ellipse(cx - r, cy - r, r * 2, r * 2, "DF")
        else:
            self.set_draw_color(*C_RULE)
            self.set_line_width(LW_DIVIDER)
            self.ellipse(cx - r, cy - r, r * 2, r * 2, "D")

    def _panel_title_outline(self, x, y, w, title, border_color=None) -> float:
        """Draw panel outline box header (title + C_ACCENT rule below). Returns content start y."""
        title_h = 6.5  # 1.5mm top + ~3.5mm text + 1.5mm bottom
        if border_color is None:
            border_color = C_RULE
        # Draw outline border for the whole panel — caller provides height
        # Here we just draw the title area separator
        diamond_x = x + 3.5
        diamond_y = y + title_h / 2
        self._draw_diamond(diamond_x, diamond_y, 1.6, C_ACCENT)
        self._sans("B", 7)
        self.set_text_color(*C_ACCENT_INK)
        self.set_xy(x + 3.5 + 3.5, y + 1.5)
        self.cell(w - 8, 3.5, title.upper())
        # Accent rule at bottom of title bar
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(LW_PANEL)
        self.line(x, y + title_h, x + w, y + title_h)
        return y + title_h

    def _draw_panel(self, x, y, w, h, title, border_color=None) -> float:
        """Draw a full outlined panel (border + title). Returns content-area start y."""
        if border_color is None:
            border_color = C_RULE
        self.set_draw_color(*border_color)
        self.set_line_width(LW_PANEL)
        self._rounded_rect(x, y, w, h, R_MD, "D")
        return self._panel_title_outline(x, y, w, title, border_color)

    def _section_rule(self, x, y, w, title) -> float:
        """Draw a section heading with diamond + title + rule extending right. Returns bottom y."""
        h = 6
        title_safe = self._sanitize(title.upper())
        diam_cx = x + 3
        self._draw_diamond(diam_cx, y + h / 2, 2.4, C_ACCENT)
        self._display(11)
        self.set_text_color(*C_ACCENT_INK)
        self.set_xy(x + 8, y + 0.5)
        tw = self.get_string_width(title_safe)
        self.cell(tw, h, title_safe)
        self.set_draw_color(*C_RULE)
        self.set_line_width(LW_ROW)
        rule_x = x + 8 + tw + 3
        self.line(rule_x, y + h / 2, x + w, y + h / 2)
        return y + h

    def _action_chip(self, x, y, chip_type: str) -> float:
        """Draw a colored action-type chip. Returns right edge x."""
        chip_colors = {
            "action":   C_CHIP_ACTION,
            "bonus":    C_CHIP_BONUS,
            "reaction": C_CHIP_REACTION,
            "passive":  C_CHIP_PASSIVE,
            "rest":     C_CHIP_REST,
            "subclass": C_ACCENT,
        }
        label_map = {
            "action": "ACTION", "bonus": "BONUS", "reaction": "REACTION",
            "passive": "PASSIVE", "rest": "1/REST", "subclass": "SUBCLASS",
        }
        color = chip_colors.get(chip_type, C_CHIP_PASSIVE)
        text_color = C_ACCENT_INK if chip_type == "subclass" else color
        label = label_map.get(chip_type, chip_type.upper())
        self._sans("B", 5.8)
        tw = self.get_string_width(label)
        chip_w = tw + 3.2   # 1.6mm padding each side
        chip_h = 3.8
        pad_x = 1.6
        pad_y = 0.4
        self.set_draw_color(*color)
        self.set_line_width(LW_PANEL)
        self._rounded_rect(x, y, chip_w, chip_h, 1.0, "D")
        self.set_text_color(*text_color)
        self.set_xy(x, y + pad_y)
        self.cell(chip_w, chip_h - pad_y * 2, label, align="C")
        return x + chip_w

    def _pill_chip(self, x, y, text, native=False) -> float:
        """Draw a language pill chip. Returns right edge x."""
        self._serif("", 9)
        tw = self.get_string_width(text)
        pad_h = 1.1
        pad_v = 0.5
        chip_w = tw + pad_h * 2
        chip_h = 4.5
        if native:
            self.set_draw_color(*C_ACCENT)
            self.set_line_width(LW_PANEL + 0.1)
            self.set_text_color(*C_ACCENT_INK)
        else:
            self.set_draw_color(*C_RULE)
            self.set_line_width(LW_ROW)
            self.set_text_color(*C_INK_2)
        self._rounded_rect(x, y, chip_w, chip_h, chip_h / 2, "D")
        self.set_xy(x, y + pad_v)
        self.cell(chip_w, chip_h - pad_v * 2, text, align="C")
        return x + chip_w

    def _ruled_lines(self, x, y, w, h, step=5.5):
        """Draw horizontal ruled lines in a writing area."""
        self.set_draw_color(*C_RULE_2)
        self.set_line_width(0.11)
        cy = y
        while cy <= y + h - 2:
            self.line(x, cy, x + w, cy)
            cy += step

    # ── Page footer ──────────────────────────────────────────────

    def _draw_page_footer(self, page_num: int, name_line: str, page_label: str):
        """Draw minimal footer: rule + name left + Roman numeral right."""
        fy = PAGE_H - MARGIN - 6
        self.set_draw_color(*C_INK_3)
        self.set_line_width(LW_DIVIDER)
        self.line(MARGIN, fy, MARGIN + CONTENT_W, fy)
        fy += 1.5
        self._sans("", 7)
        self.set_text_color(*C_INK_3)
        self.set_xy(MARGIN, fy)
        self.cell(CONTENT_W / 2, 4, name_line)
        self._display(9)
        self.set_text_color(*C_INK_2)
        rn = ROMAN[page_num - 1] if 0 < page_num <= len(ROMAN) else str(page_num)
        total_rn = ROMAN[self._total_main - 1] if 0 < self._total_main <= len(ROMAN) else str(self._total_main)
        label = f"{rn} / {total_rn}"
        self.set_xy(MARGIN + CONTENT_W / 2, fy)
        self.cell(CONTENT_W / 2, 4, label, align="R")

    def _footer_name(self) -> str:
        c = self.c
        class_display = c.class_name or ""
        if c.level:
            class_display = f"{class_display} {c.level}"
        species = c.species_name or ""
        return f"{c.name}  ·  {species} {class_display}".strip(" ·")

    # ════════════════════════════════════════════════════════════
    # PAGE 1 — Combat & Stats
    # ════════════════════════════════════════════════════════════

    def _draw_page_1(self):
        c = self.c
        x0 = MARGIN
        y = MARGIN

        y = self._draw_header(x0, y)
        y = self._draw_combat_row(x0, y)
        y += 2
        y = self._draw_conditions_strip(x0, y)
        y += 3

        left_w = 60
        right_x = x0 + left_w + 3
        right_w = CONTENT_W - left_w - 3

        left_bottom = self._draw_ability_scores(x0, y, left_w)

        right_y = y
        right_y = self._draw_senses_panel(right_x, right_y, right_w)
        right_y += 2
        right_y = self._draw_weapons_section(right_x, right_y, right_w)
        right_y += 2
        right_y = self._draw_proficiencies(right_x, right_y, right_w)
        right_y += 2
        right_y = self._draw_languages(right_x, right_y, right_w)
        right_y += 2
        right_y = self._draw_equipment_list(right_x, right_y, right_w)

        self._draw_page_footer(1, self._footer_name(), "Combat & Stats")

    # ── Header ──

    def _draw_header(self, x0, y) -> float:
        c = self.c
        # Right side: Proficiency badge + Inspiration card
        badge_w = 24
        insp_w = 22
        gap = 2
        boxes_right_x = x0 + CONTENT_W - badge_w - insp_w - gap

        header_h = 22

        # ── Heroic Inspiration card ──
        insp_x = boxes_right_x
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(LW_PANEL)
        self._rounded_rect(insp_x, y, insp_w, header_h, R_MD, "D")
        self._sans("B", 5.5)
        self.set_text_color(*C_INK_3)
        self.set_xy(insp_x, y + 1)
        self.cell(insp_w, 3.5, "HEROIC", align="C")
        self.set_xy(insp_x, y + 4)
        self.cell(insp_w, 3.5, "INSPIRATION", align="C")
        # Rotated square frame
        cx = insp_x + insp_w / 2
        cy = y + 14
        sq = 4.5
        pts = [(cx, cy - sq), (cx + sq, cy), (cx, cy + sq), (cx - sq, cy)]
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(LW_PANEL)
        self.polygon(pts, style="D")
        # Inner diamond
        sq2 = 2.2
        pts2 = [(cx, cy - sq2), (cx + sq2, cy), (cx, cy + sq2), (cx - sq2, cy)]
        self.set_draw_color(*C_ACCENT_2)
        self.set_line_width(LW_DIVIDER)
        self.polygon(pts2, style="D")

        # ── Proficiency badge ──
        prof_x = boxes_right_x + insp_w + gap
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(LW_PANEL)
        self._rounded_rect(prof_x, y, badge_w, header_h, R_MD, "D")
        self._display(18)
        self.set_text_color(*C_ACCENT_INK)
        self.set_xy(prof_x, y + 1)
        self.cell(badge_w, 10, f"+{c.proficiency_bonus}", align="C")
        self._sans("B", 5.5)
        self.set_text_color(*C_INK_3)
        self.set_xy(prof_x, y + 13)
        self.cell(badge_w, 3.5, "PROFICIENCY", align="C")
        self.set_xy(prof_x, y + 16.5)
        self.cell(badge_w, 3.5, "BONUS", align="C")

        # ── Character name + meta ──
        name_w = boxes_right_x - x0 - 4
        self._display(24)
        self.set_text_color(*C_INK)
        self.set_xy(x0, y + 0.5)
        self.cell(name_w, 12, c.name)

        # Meta line: Species · Class Level · Subclass · Background
        parts = []
        if c.species_name:
            species_display = c.species_name
            if c.species_sub_choice:
                species_display += f" ({c.species_sub_choice})"
            parts.append(species_display)
        if c.class_name:
            cls = c.class_name
            if c.level:
                cls += f" {c.level}"
            parts.append(cls)
        if c.current_subclass:
            parts.append(c.current_subclass.replace("-", " ").title())
        if c.background_name:
            parts.append(c.background_name)
        meta_text = "  .  ".join(parts)
        self._serif("I", 10)
        self.set_text_color(*C_INK_2)
        self.set_xy(x0, y + 13)
        self.cell(name_w, 6, meta_text)

        # Full-width rule below header
        rule_y = y + header_h + 1
        self.set_draw_color(*C_INK)
        self.set_line_width(LW_PANEL)
        self.line(x0, rule_y, x0 + CONTENT_W, rule_y)

        return rule_y + 3

    # ── Combat row ──

    def _draw_combat_row(self, x0, y) -> float:
        c = self.c
        row_h = 26
        gap = 2.5
        # Columns: AC (32mm) | HP (flex) | Hit Dice (30mm) | Death Saves (40mm)
        ac_w = 32
        hd_w = 30
        ds_w = 40
        hp_w = CONTENT_W - ac_w - hd_w - ds_w - gap * 3

        bx = x0

        # ── AC ──
        self.set_draw_color(*C_RULE)
        self.set_line_width(LW_PANEL)
        self._rounded_rect(bx, y, ac_w, row_h, R_MD, "D")
        self._sans("B", 5.5)
        self.set_text_color(*C_INK_3)
        self.set_xy(bx, y + 1.5)
        self.cell(ac_w, 3, "ARMOR CLASS", align="C")
        self._display(26)
        self.set_text_color(*C_INK)
        self.set_xy(bx, y + 5)
        self.cell(ac_w, 13, str(c.armor_class), align="C")
        # Armor type subtitle
        armor_name = ""
        if c.equipped_armor:
            armor_name = c.equipped_armor[0]
        self._sans("", 5.5)
        self.set_text_color(*C_INK_3)
        self.set_xy(bx, y + 19)
        self.cell(ac_w, 3.5, armor_name[:18], align="C")

        bx += ac_w + gap

        # ── HP (hero element) ──
        self.set_draw_color(*C_INK)
        self.set_line_width(LW_PANEL + 0.1)
        self._rounded_rect(bx, y, hp_w, row_h, R_MD, "D")

        # Top row labels
        self._sans("B", 5.5)
        self.set_text_color(*C_INK_3)
        self.set_xy(bx + 2, y + 1.5)
        self.cell(hp_w / 2, 3, "HIT POINTS")
        hit_die = c.character_class.get("hit_die", 8) if c.character_class else 8
        self._sans("", 5.5)
        self.set_text_color(*C_INK_3)
        self.set_xy(bx + hp_w / 2, y + 1.5)
        self.cell(hp_w / 2 - 2, 3, f"1d{hit_die} · avg +Con/level", align="R")

        # MAX value
        max_w = hp_w * 0.38
        curr_w = (hp_w - max_w) / 2
        self._display(22)
        self.set_text_color(*C_INK)
        self.set_xy(bx + 2, y + 5)
        self.cell(max_w - 3, 14, str(c.hit_points), align="C")

        # Vertical divider after MAX
        self.set_draw_color(*C_INK_2)
        self.set_line_width(LW_DIVIDER)
        self.line(bx + max_w, y + 5, bx + max_w, y + row_h - 2)

        # MAX label
        self._sans("B", 5.5)
        self.set_text_color(*C_INK_3)
        self.set_xy(bx + 2, y + row_h - 5.5)
        self.cell(max_w - 2, 3, "MAX", align="C")

        # CURRENT and TEMPORARY blank fields
        for i, lbl in enumerate(["CURRENT", "TEMPORARY"]):
            fx = bx + max_w + i * curr_w
            field_y = y + 7
            field_h = row_h - 12
            # Baseline sits 3mm above the bottom to leave room for the label below
            line_y = field_y + field_h - 3
            self.set_draw_color(*C_INK_2)
            self.set_line_width(LW_PANEL)
            self.line(fx + 2, line_y, fx + curr_w - 3, line_y)
            # Label below the baseline with clear gap
            self._sans("B", 5.5)
            self.set_text_color(*C_INK_3)
            self.set_xy(fx, line_y + 1.5)
            self.cell(curr_w, 3, lbl, align="C")

        bx += hp_w + gap

        # ── Hit Dice ──
        self.set_draw_color(*C_RULE)
        self.set_line_width(LW_PANEL)
        self._rounded_rect(bx, y, hd_w, row_h, R_MD, "D")
        self._sans("B", 5.5)
        self.set_text_color(*C_INK_3)
        self.set_xy(bx, y + 1.5)
        self.cell(hd_w, 3, "HIT DICE", align="C")
        # Value
        self._display(16)
        self.set_text_color(*C_INK)
        self.set_xy(bx, y + 5)
        self.cell(hd_w * 0.45, 9, str(c.level), align="C")
        self._display(11)
        self.set_text_color(*C_INK_2)
        self.set_xy(bx + hd_w * 0.45, y + 7)
        self.cell(hd_w * 0.55 - 2, 9, f"d{hit_die}")
        # Tick boxes
        self._sans("", 5)
        self.set_text_color(*C_INK_3)
        self.set_xy(bx + 2, y + 16.5)
        self.cell(hd_w - 4, 2.5, "Used:", align="L")
        sq = 3.0
        gap_sq = 1.5
        used_x = bx + 2
        used_y = y + row_h - 5
        for _ in range(min(c.level, 6)):
            self.set_draw_color(*C_RULE)
            self.set_line_width(LW_DIVIDER)
            self.rect(used_x, used_y, sq, sq, "D")
            used_x += sq + gap_sq
            if used_x + sq > bx + hd_w - 2:
                break

        bx += hd_w + gap

        # ── Death Saves ──
        self.set_draw_color(*C_RULE)
        self.set_line_width(LW_PANEL)
        self._rounded_rect(bx, y, ds_w, row_h, R_MD, "D")
        self._sans("B", 5.5)
        self.set_text_color(*C_INK_3)
        self.set_xy(bx, y + 1.5)
        self.cell(ds_w, 3, "DEATH SAVES", align="C")

        # Success row
        self._sans("", 6)
        self.set_text_color(*C_INK_2)
        self.set_xy(bx + 2, y + 7)
        self.cell(14, 3.5, "Success")
        sx = bx + 16
        for _ in range(3):
            self._small_circle(sx, y + 9, r=1.3)
            sx += 4

        # Failure row
        self.set_xy(bx + 2, y + 14)
        self.cell(14, 3.5, "Failure")
        sx = bx + 16
        for _ in range(3):
            self.set_draw_color(*C_CHIP_ACTION)
            self.set_line_width(LW_PANEL)
            self.ellipse(sx - 1.3, y + 15.7, 2.6, 2.6, "D")
            sx += 4

        return y + row_h

    # ── Conditions strip ──

    def _draw_conditions_strip(self, x0, y) -> float:
        strip_h = 8
        self.set_draw_color(*C_RULE)
        self.set_line_width(LW_PANEL)
        self._rounded_rect(x0, y, CONTENT_W, strip_h, R_SM, "D")

        # Label — measure actual width to place divider safely
        self._sans("B", 5.8)
        self.set_text_color(*C_INK_3)
        self.set_xy(x0 + 1.5, y + 1.5)
        self.cell(18, strip_h - 3, "CONDITIONS", align="L")
        # Vertical divider — placed after label with 2mm clearance
        divider_x = x0 + 20
        self.set_draw_color(*C_RULE)
        self.set_line_width(LW_DIVIDER)
        self.line(divider_x, y + 1.5, divider_x, y + strip_h - 1.5)

        # Condition checkboxes
        avail_w = CONTENT_W - 20 - 25  # reserve 25mm for exhaustion
        cond_x = x0 + 21.5
        cond_y = y + 1.5
        self._sans("", 5.5)
        row_h_c = (strip_h - 3) / 2
        for i, cond in enumerate(CONDITIONS):
            col = i % 7
            row = i // 7
            cx2 = cond_x + col * (avail_w / 7)
            cy2 = cond_y + row * row_h_c
            # checkbox
            self.set_draw_color(*C_RULE)
            self.set_line_width(LW_DIVIDER)
            self.rect(cx2, cy2 + 0.3, 2.3, 2.3, "D")
            self.set_text_color(*C_INK_2)
            self.set_xy(cx2 + 3, cy2)
            self.cell(avail_w / 7 - 3, row_h_c, cond[:12])

        # Exhaustion
        ex_x = x0 + CONTENT_W - 24
        self.set_draw_color(*C_RULE)
        self.set_line_width(LW_DIVIDER)
        self.line(ex_x, y + 1.5, ex_x, y + strip_h - 1.5)
        self._sans("B", 5.5)
        self.set_text_color(*C_INK_3)
        self.set_xy(ex_x + 1, y + 1)
        self.cell(23, 3.5, "EXHAUSTION")
        ex_cx = ex_x + 2
        for _ in range(6):
            self._small_circle(ex_cx, y + strip_h - 2.5, r=1.2)
            ex_cx += 3.8

        return y + strip_h

    # ── Ability scores ──

    def _draw_ability_scores(self, x, y, w) -> float:
        c = self.c
        profs = c.all_skill_proficiencies
        expertise: set[str] = set()
        try:
            expertise = c.all_skill_expertise
        except AttributeError:
            pass

        row_h = 4.2
        header_h = 7.0  # single-line header with larger modifier
        sep_v = 1.5     # vertical gap between panels

        for ability in ABILITIES:
            total = get_effective_ability_score(c, ability)
            mod = _eff_mod(c, ability)
            mod_str = self._modifier_str(mod)
            abbr = ABILITY_ABBR[ability]
            skills = SKILLS_BY_ABILITY.get(ability, [])
            save_prof = c.is_proficient_save(ability)
            save_mod = c.saving_throw_modifier(ability)

            num_rows = 1 + len(skills)  # save + skill rows
            panel_h = header_h + num_rows * row_h + 2.5

            # Panel outline
            self.set_draw_color(*C_RULE)
            self.set_line_width(LW_PANEL)
            self._rounded_rect(x, y, w, panel_h, R_SM, "D")

            # ── Single-line header: ABBR | modifier | SCORE N ──
            inner_x = x + 2.5
            inner_w = w - 5

            # ABBR (left)
            self._sans("B", 9)
            self.set_text_color(*C_ACCENT_INK)
            self.set_xy(inner_x, y + 1.2)
            self.cell(14, header_h - 1.5, abbr)

            # Modifier (center)
            self._display(17)
            self.set_text_color(*C_INK)
            self.set_xy(inner_x + 14, y + 0.5)
            self.cell(inner_w - 28, header_h - 0.5, mod_str, align="C")

            # Score (right)
            self._sans("B", 7)
            self.set_text_color(*C_INK_3)
            self.set_xy(inner_x + inner_w - 14, y + 2.5)
            self.cell(14, 4, f"SCORE {total}", align="R")

            # Dotted rule below header
            self.set_draw_color(*C_RULE_2)
            self.set_line_width(LW_DIVIDER)
            self.set_dash_pattern(dash=1, gap=1)
            self.line(x + 1.5, y + header_h, x + w - 1.5, y + header_h)
            self.set_dash_pattern()

            # ── Saving throw row (first) ──
            sk_y = y + header_h + 0.5
            pip_x = inner_x + 0.5
            mod_col_w = 8
            name_col_x = inner_x + 5 + mod_col_w

            is_expert_save = False
            self._small_circle(pip_x + 1.2, sk_y + row_h / 2, r=1.2, filled=save_prof, expert=is_expert_save)
            # Modifier
            self._serif("B" if save_prof else "", 7.5)
            self.set_text_color(*C_INK)
            self.set_xy(inner_x + 4, sk_y)
            self.cell(mod_col_w, row_h, self._modifier_str(save_mod), align="R")
            # Name
            self._serif("", 7.5)
            self.set_text_color(*C_INK_2)
            self.set_xy(name_col_x + 1, sk_y)
            self.cell(inner_w - 5 - mod_col_w - 1, row_h, "Save")

            # Dotted divider after save row
            sk_y += row_h
            self.set_draw_color(*C_RULE_2)
            self.set_line_width(LW_DIVIDER)
            self.set_dash_pattern(dash=1, gap=1)
            self.line(x + 1.5, sk_y, x + w - 1.5, sk_y)
            self.set_dash_pattern()

            # ── Skill rows ──
            for skill_name in skills:
                is_prof = skill_name in profs
                is_exp = skill_name in expertise
                sk_mod = c.skill_modifier(skill_name)

                self._small_circle(pip_x + 1.2, sk_y + row_h / 2, r=1.2,
                                   filled=(is_prof or is_exp), expert=is_exp)
                self._serif("B" if is_prof else "", 7.5)
                self.set_text_color(*C_INK)
                self.set_xy(inner_x + 4, sk_y)
                self.cell(mod_col_w, row_h, self._modifier_str(sk_mod), align="R")

                sn_short = skill_name
                self._serif("", 7.5)
                self.set_text_color(*C_INK if is_exp else C_INK_2)
                self.set_xy(name_col_x + 1, sk_y)
                name_w_avail = inner_w - 5 - mod_col_w - 1
                self.cell(name_w_avail, row_h, sn_short[:18])
                if is_exp:
                    exp_x = name_col_x + 1 + self.get_string_width(sn_short[:18]) + 1
                    self._sans("", 5.5)
                    self.set_text_color(*C_ACCENT)
                    self.set_xy(exp_x, sk_y + 0.5)
                    self.cell(6, row_h - 1, "EXP")

                sk_y += row_h
                if skill_name != skills[-1]:
                    self.set_draw_color(*C_RULE_2)
                    self.set_line_width(0.08)
                    self.set_dash_pattern(dash=1, gap=1.5)
                    self.line(x + 1.5, sk_y, x + w - 1.5, sk_y)
                    self.set_dash_pattern()

            y += panel_h + sep_v

        return y

    # ── Senses panel ──

    def _draw_senses_panel(self, x, y, w) -> float:
        panel_h = 23
        content_y = self._draw_panel(x, y, w, panel_h, "SENSES")

        # 4-column grid
        cols = ["Initiative", "Speed", "Size", "Passive Perc."]
        c = self.c
        passive_perc = 10 + c.skill_modifier("Perception")
        size_text = c.size_choice or "Medium"
        values = [
            self._modifier_str(c.initiative),
            f"{c.speed} ft",
            size_text,
            str(passive_perc),
        ]
        col_w = w / 4
        for i, (lbl, val) in enumerate(zip(cols, values)):
            cx = x + i * col_w
            # Vertical divider (except first)
            if i > 0:
                self.set_draw_color(*C_RULE)
                self.set_line_width(LW_ROW)
                self.line(cx, content_y + 1, cx, content_y + 10)
            # Label
            self._sans("B", 6)
            self.set_text_color(*C_INK_3)
            self.set_xy(cx + 1, content_y + 1.5)
            self.cell(col_w - 1, 3, lbl.upper(), align="C")
            # Value
            self._display(12)
            self.set_text_color(*C_INK)
            self.set_xy(cx, content_y + 4.5)
            self.cell(col_w, 6, val, align="C")

        # Extra senses strip
        senses_y = content_y + 12
        self.set_draw_color(*C_RULE_2)
        self.set_line_width(LW_DIVIDER)
        self.line(x + 1.5, senses_y, x + w - 1.5, senses_y)
        senses_y += 1

        extra_senses = self._get_extra_senses()
        self._sans("B", 6)
        self.set_text_color(*C_INK_3)
        self.set_xy(x + 2, senses_y)
        self.cell(16, 5, "SENSES")
        self._serif("I", 7.5)
        self.set_text_color(*C_INK_2)
        self.set_xy(x + 18, senses_y)
        senses_text = "  ·  ".join(extra_senses) if extra_senses else "None"
        self.cell(w - 20, 5, senses_text[:55])

        return y + panel_h

    def _get_extra_senses(self) -> list[str]:
        c = self.c
        if not c.species:
            return []
        traits = c.species.get("features", []) or c.species.get("traits", [])
        senses = []
        sense_keywords = {"Darkvision", "Blindsight", "Tremorsense", "Truesight",
                          "Superior Darkvision", "Keen Senses", "Camouflage"}
        for t in traits:
            name = t.get("name", "")
            if any(kw in name for kw in sense_keywords):
                # Try to extract range from description
                desc = t.get("description", "")
                m = re.search(r"(\d+)\s*feet", desc)
                if m and "Darkvision" in name:
                    senses.append(f"Darkvision {m.group(1)} ft")
                elif m and ("Blindsight" in name or "Tremorsense" in name):
                    senses.append(f"{name} {m.group(1)} ft")
                else:
                    senses.append(name)
        return senses

    # ── Weapons & Attacks ──

    def _draw_weapons_section(self, x, y, w) -> float:
        rows = build_standard_actions(
            self.c,
            self._get_spell_data(),
            game_data=self._game_data_context(),
            weapon_options=getattr(self.c, "standard_action_options", {}) or {},
        )
        row_count = max(4, len(rows))
        row_h = 5.5
        table_h = 6.5 + 5 + row_count * row_h + 3  # title + header + rows + pad

        content_y = self._draw_panel(x, y, w, table_h, "WEAPONS & ATTACKS")

        # Column widths: Name 32mm | Atk 14mm | Damage flex | Properties flex
        name_w = 32
        atk_w = 14
        dmg_w = 28
        prop_w = w - name_w - atk_w - dmg_w - 4

        headers = ["Name", "Atk", "Damage", "Properties"]
        col_widths = [name_w, atk_w, dmg_w, prop_w]
        hx = x + 2
        ty = content_y + 1.5

        self._sans("B", 6)
        self.set_text_color(*C_INK_3)
        for i, hdr in enumerate(headers):
            self.set_xy(hx, ty)
            self.cell(col_widths[i], 3.5, hdr)
            hx += col_widths[i]
        ty += 4
        self.set_draw_color(*C_RULE)
        self.set_line_width(LW_ROW)
        self.line(x + 2, ty, x + w - 2, ty)
        ty += 0.5

        for i in range(row_count):
            if i < len(rows):
                r = rows[i]
                self._sans("", 7)
                self.set_text_color(*C_INK)
                hx = x + 2
                name = r.get("name", "")
                atk = r.get("attack", "")
                dmg_str = r.get("damage", "")
                notes = r.get("notes", "")

                vals = [name[:20], atk[:8], dmg_str[:18], notes[:22]]
                for j, val in enumerate(vals):
                    self.set_xy(hx, ty + 0.3)
                    if j == 0:
                        self._serif("", 7.5)
                        self.set_text_color(*C_INK)
                    elif j == 1:
                        self._serif("B", 7.5)
                        self.set_text_color(*C_INK)
                    elif j == 2:
                        self._serif("", 7)
                        self.set_text_color(*C_INK)
                    else:
                        self._serif("", 6.5)
                        self.set_text_color(*C_INK_3)
                    self.cell(col_widths[j], row_h - 0.3, val)
                    hx += col_widths[j]
            else:
                # Blank row - dotted line
                pass

            ty += row_h
            if i < row_count - 1:
                self.set_draw_color(*C_RULE_2)
                self.set_line_width(LW_DIVIDER)
                self.set_dash_pattern(dash=1.5, gap=1.5)
                self.line(x + 2, ty, x + w - 2, ty)
                self.set_dash_pattern()

        return y + table_h

    # ── Training & Proficiencies ──

    def _draw_proficiencies(self, x, y, w) -> float:
        c = self.c
        armor_types = list(getattr(c, "effective_armor_proficiencies", []))
        weapon_profs = list(getattr(c, "effective_weapon_proficiencies", []))
        tool_profs = []
        if c.background:
            tp = c.background.get("tool_proficiency")
            if tp:
                tool_profs.append(tp)
        if c.character_class:
            for tp in c.character_class.get("tool_proficiencies", []):
                if tp not in tool_profs:
                    tool_profs.append(tp)

        # Compute height from data
        key_w = 18
        val_w = w - key_w - 5
        row_gap = 0.8

        armor_text = ", ".join(armor_types) if armor_types else "None"
        weapon_text = ", ".join(weapon_profs) if weapon_profs else "None"
        tool_text = ", ".join(tool_profs) if tool_profs else "None"

        def measure_text(txt):
            self._serif("", 8)
            lines = self.multi_cell(val_w, 3.5, txt, dry_run=True, output="LINES")
            return max(1, len(lines))

        rows_data = [
            ("ARMOR",   armor_text,  measure_text(armor_text)),
            ("WEAPONS", weapon_text, measure_text(weapon_text)),
            ("TOOLS",   tool_text,   measure_text(tool_text)),
        ]
        row_line_h = 3.5
        content_h = sum(n * row_line_h + row_gap for _, _, n in rows_data) + 2
        panel_h = 6.5 + content_h + 2

        content_y = self._draw_panel(x, y, w, panel_h, "TRAINING & PROFICIENCIES")
        ty = content_y + 1.5

        for key_lbl, val_text, _ in rows_data:
            self._sans("B", 6)
            self.set_text_color(*C_INK_3)
            self.set_xy(x + 2, ty)
            self.cell(key_w, row_line_h, key_lbl)

            self._serif("", 8)
            self.set_text_color(*C_INK)
            self.set_xy(x + 2 + key_w + 1, ty)
            self.multi_cell(val_w, row_line_h, val_text)
            ty = self.get_y() + row_gap

        return y + panel_h

    # ── Languages ──

    def _draw_languages(self, x, y, w) -> float:
        c = self.c
        lang_list = all_languages(c)
        native_set = set(compute_language_sources(c).get("auto", []))

        # Estimate height
        chip_h = 4.5
        gap_x = 2
        gap_y = 2
        cx = x + 3
        cy_est = 0
        row_max_h = chip_h
        for lang in lang_list:
            self._serif("", 9)
            tw = self.get_string_width(lang)
            chip_w = tw + 4.4
            if cx + chip_w > x + w - 3 and cx > x + 3:
                cy_est += row_max_h + gap_y
                cx = x + 3
            cx += chip_w + gap_x
        cy_est += chip_h + 2

        panel_h = 6.5 + cy_est + 3
        content_y = self._draw_panel(x, y, w, panel_h, "LANGUAGES")

        # Draw chips
        cx = x + 3
        cy = content_y + 2
        for lang in lang_list:
            self._serif("", 9)
            tw = self.get_string_width(lang)
            chip_w = tw + 4.4
            if cx + chip_w > x + w - 3 and cx > x + 3:
                cy += chip_h + gap_y
                cx = x + 3
            is_native = lang in native_set
            right = self._pill_chip(cx, cy, lang, native=is_native)
            cx = right + gap_x

        return y + panel_h

    # ── Equipment list + Coins ──

    def _draw_equipment_list(self, x, y, w) -> float:
        c = self.c
        remaining = PAGE_H - MARGIN - 9 - y  # leave footer space
        if remaining < 20:
            return y

        # Collect items
        items: list[tuple[str, int]] = []
        # Custom inventory first (actual purchased items)
        for ent in getattr(c, "custom_inventory", []) or []:
            name = ent.get("item_name") or ent.get("item") or ""
            qty = int(ent.get("qty", 1))
            if name:
                items.append((name, qty))
        # Starting equipment text (if no custom inventory)
        if not items:
            if c.character_class:
                for opt in c.character_class.get("starting_equipment", []):
                    if opt.get("option") == c.equipment_choice_class:
                        for part in opt.get("items", "").split(","):
                            part = part.strip()
                            if part:
                                items.append((part, 1))
            if c.background:
                for opt in c.background.get("equipment", []):
                    if opt.get("option") == c.equipment_choice_background:
                        for part in opt.get("items", "").split(","):
                            part = part.strip()
                            if part:
                                items.append((part, 1))

        # 2-column grid
        col_w = (w - 7) / 2
        row_h = 4.5
        blank_rows = max(0, 14 - len(items))
        total_items = len(items) + blank_rows

        # Coins row at bottom
        coins_h = 10
        grid_h = (total_items // 2 + (total_items % 2)) * row_h
        panel_h = min(6.5 + grid_h + 2 + coins_h + 2, remaining)

        content_y = self._draw_panel(x, y, w, panel_h, "EQUIPMENT")

        ty = content_y + 1.5
        col_items = [items[i::2] for i in range(2)] if items else [[], []]
        # Flatten to alternating layout
        all_items_padded = items + [("", 0)] * blank_rows
        left_items = all_items_padded[0::2]
        right_items = all_items_padded[1::2]
        max_rows = max(len(left_items), len(right_items))

        for row_i in range(max_rows):
            row_y = ty + row_i * row_h
            for col_i, col_list in enumerate([left_items, right_items]):
                cx = x + 3 + col_i * (col_w + 2)
                if row_i < len(col_list):
                    name, qty = col_list[row_i]
                    if name:
                        # Accent bullet square
                        sq = 1.4
                        self.set_fill_color(*C_ACCENT)
                        self.rect(cx, row_y + (row_h - sq) / 2, sq, sq, "F")
                        # Item name
                        self._serif("", 7.5)
                        self.set_text_color(*C_INK)
                        self.set_xy(cx + sq + 1.2, row_y)
                        label = f"{qty} " if qty > 1 else ""
                        self.cell(col_w - sq - 1.5, row_h, label + name[:18])
                    else:
                        # Blank row baseline
                        self.set_draw_color(*C_RULE_2)
                        self.set_line_width(LW_DIVIDER)
                        self.line(cx, row_y + row_h - 0.5, cx + col_w - 1, row_y + row_h - 0.5)

        # Coins row
        coins_y = ty + max_rows * row_h + 1.5
        self.set_draw_color(*C_RULE)
        self.set_line_width(LW_ROW)
        self.line(x + 2, coins_y - 1, x + w - 2, coins_y - 1)

        gp, sp, cp_val = cp_to_coins(current_wealth_cp(c))
        coin_rows = [("CP", cp_val), ("SP", sp), ("EP", 0), ("GP", gp), ("PP", 0)]
        coin_w = (w - 6) / 5
        for i, (coin, val) in enumerate(coin_rows):
            ccx = x + 3 + i * coin_w
            is_zero = (val == 0)
            text_color = C_RULE if is_zero else C_INK
            label_color = C_RULE if is_zero else C_INK_3
            self._display(10)
            self.set_text_color(*text_color)
            self.set_xy(ccx, coins_y)
            self.cell(coin_w, 4.5, str(val), align="C")
            self._sans("B", 6)
            self.set_text_color(*label_color)
            self.set_xy(ccx, coins_y + 4.5)
            self.cell(coin_w, 3.5, coin, align="C")

        return y + panel_h

    # ════════════════════════════════════════════════════════════
    # PAGE 2 — Class Features
    # ════════════════════════════════════════════════════════════

    def _draw_page_2_features(self):
        c = self.c
        x0 = MARGIN
        bottom_limit = PAGE_H - MARGIN - 12
        cur_page = 2

        y = MARGIN
        y = self._draw_page_header(x0, y, "Features & Heritage",
                                   "Class features, subclass, and species traits.",
                                   show_chip_legend=True)

        def page_break():
            nonlocal y, cur_page
            self._draw_page_footer(cur_page, self._footer_name(), "Class Features")
            self.add_page()
            cur_page += 1
            y = MARGIN
            y = self._draw_page_header(x0, y, "Features (cont.)", "", show_chip_legend=False)

        # Class features — full width, overflow to new pages
        class_label = f"CLASS  -  {c.class_name.upper()}" if c.class_name else "CLASS"
        y = self._section_rule(x0, y, CONTENT_W, class_label)
        y += 2
        for feat in self._get_class_features():
            card_h = self._measure_feature_card(feat, CONTENT_W)
            if y + card_h > bottom_limit:
                page_break()
            y = self._draw_feature_card(x0, y, CONTENT_W, feat)
            y += 2

        # Subclass features
        subclass_features = self._get_subclass_features()
        if subclass_features:
            sc_name = (c.current_subclass or "").replace("-", " ").title()
            sc_label = f"SUBCLASS  -  {sc_name.upper()}" if sc_name else "SUBCLASS"
            if y + 10 > bottom_limit:
                page_break()
            y += 1
            y = self._section_rule(x0, y, CONTENT_W, sc_label)
            y += 2
            for feat in subclass_features:
                feat_with_chip = dict(feat)
                feat_with_chip["chip"] = "subclass"
                card_h = self._measure_feature_card(feat_with_chip, CONTENT_W)
                if y + card_h > bottom_limit:
                    page_break()
                y = self._draw_feature_card(x0, y, CONTENT_W, feat_with_chip)
                y += 2

        self._draw_page_footer(cur_page, self._footer_name(), "Class Features")

    def _draw_page_header(self, x0, y, title, subtitle, show_chip_legend=False) -> float:
        header_h = 16
        # Title
        self._display(18)
        self.set_text_color(*C_INK)
        self.set_xy(x0, y)
        self.cell(CONTENT_W * 0.6, 10, title)
        # Subtitle
        self._serif("I", 10)
        self.set_text_color(*C_INK_2)
        self.set_xy(x0, y + 10)
        self.cell(CONTENT_W * 0.6, 5, subtitle)

        if show_chip_legend:
            legend_x = x0 + CONTENT_W * 0.6 + 2
            legend_y = y + 2
            chip_types = ["action", "bonus", "reaction", "passive", "rest"]
            cx = legend_x
            for ct in chip_types:
                cx = self._action_chip(cx, legend_y, ct) + 2
                if cx > x0 + CONTENT_W - 5:
                    legend_y += 5
                    cx = legend_x

        # Rule
        rule_y = y + header_h
        self.set_draw_color(*C_INK)
        self.set_line_width(LW_PANEL)
        self.line(x0, rule_y, x0 + CONTENT_W, rule_y)
        return rule_y + 3

    def _measure_feature_card(self, feat: dict, w: float) -> float:
        """Return the height a feature card will occupy."""
        desc = feat.get("description", "")
        source = feat.get("source", "")
        inner_w = w - 9
        head_h = 5.5
        desc_h = 0
        if desc:
            self._serif("", 9)
            lines = self.multi_cell(inner_w, 3.8, desc, dry_run=True, output="LINES")
            desc_h = len(lines) * 3.8 + 0.5
        source_h = 3.5 if source else 0
        return head_h + source_h + desc_h + 2

    def _draw_feature_card(self, x, y, w, feat: dict) -> float:
        """Draw a single feature card with left accent rule. Returns bottom y."""
        name = feat.get("name", "")
        desc = feat.get("description", "")
        source = feat.get("source", "")
        chip_type = feat.get("chip") or FEATURE_ACTION_TYPES.get(name)

        inner_w = w - 9  # left rule (1pt=0.35mm) + 4mm pad + right edge
        card_h = self._measure_feature_card(feat, w)

        # Left accent rule
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(0.35)
        self.line(x + 1, y, x + 1, y + card_h)

        inner_x = x + 5

        # ── Head row: name + chip ──
        head_y = y + 1
        self._display(11)
        self.set_text_color(*C_INK)
        self.set_xy(inner_x, head_y)
        name_w_used = min(self.get_string_width(name) + 1, inner_w - 20)
        self.cell(name_w_used, 5, name)

        if chip_type:
            chip_x = inner_x + name_w_used + 2
            self._action_chip(chip_x, head_y + 0.5, chip_type)

        ty = head_y + 5

        # ── Source line ──
        if source:
            self._serif("I", 8)
            self.set_text_color(*C_INK_3)
            self.set_xy(inner_x, ty)
            self.cell(inner_w, 3.5, source)
            ty += 3.5

        # ── Body text ──
        if desc:
            self._serif("", 9)
            self.set_text_color(*C_INK)
            self.set_xy(inner_x, ty)
            self.multi_cell(inner_w, 3.8, desc)
            ty = self.get_y() + 0.5

        return y + card_h

    def _get_class_features(self) -> list[dict]:
        import json
        c = self.c
        if not c.character_class:
            return []
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        prog_path = os.path.join(data_dir, "class_progressions.json")
        if not os.path.exists(prog_path):
            return []
        with open(prog_path, "r", encoding="utf-8") as f:
            progressions = json.load(f)
        prog_by_slug = {p["slug"]: p for p in progressions}
        features = []
        creation_choice_lines = get_level1_creation_choice_lines(c)
        if creation_choice_lines:
            features.append({
                "name": "Level 1 Creation Choices",
                "description": "\n".join(f"- {line}" for line in creation_choice_lines),
            })
        for cl in c.class_levels:
            prog = prog_by_slug.get(cl.class_slug)
            if not prog:
                continue
            for level_data in prog.get("levels", []):
                if level_data.get("level") != cl.class_level:
                    continue
                for f in level_data.get("feature_details", []):
                    if isinstance(f, dict) and f.get("name") not in ("-", "Ability Score Improvement"):
                        features.append({
                            "name": f.get("name", ""),
                            "description": augment_level1_feature_description(
                                f.get("name", ""), f.get("description", ""), c, None),
                            "source": f"Level {cl.class_level}",
                        })
                if not level_data.get("feature_details"):
                    for name in level_data.get("features", []):
                        if name not in ("-", "Ability Score Improvement"):
                            features.append({
                                "name": name,
                                "description": augment_level1_feature_description(name, "", c, None),
                                "source": f"Level {cl.class_level}",
                            })
                break
        return features

    def _get_subclass_features(self) -> list[dict]:
        import json
        c = self.c
        if not c.current_subclass:
            return []
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        sc_path = os.path.join(data_dir, "subclasses.json")
        if not os.path.exists(sc_path):
            return []
        with open(sc_path, "r", encoding="utf-8") as f:
            subclasses = json.load(f)
        sc = next((s for s in subclasses if s.get("slug") == c.current_subclass), None)
        if not sc:
            return []
        features = []
        for fl in sc.get("feature_levels", []):
            if fl <= c.level:
                for feat in sc.get("features", {}).get(str(fl), []):
                    if isinstance(feat, dict):
                        features.append({
                            "name": feat.get("name", ""),
                            "description": feat.get("description", ""),
                            "source": f"Subclass Level {fl}",
                        })
        return features

    # ════════════════════════════════════════════════════════════
    # PAGE 3A — Heritage, Feats & Magic (non-casters)
    # ════════════════════════════════════════════════════════════

    def _draw_page_3_heritage(self):
        c = self.c
        x0 = MARGIN
        y = MARGIN
        species_name = c.species_name or "Species"
        subtitle_text = f"Species traits, feats, and the spells {c.name} carries in their blood."
        y = self._draw_page_header(x0, y, "Heritage, Feats & Magic",
                                   subtitle_text, show_chip_legend=True)

        # Species traits
        if c.species:
            y = self._section_rule(x0, y, CONTENT_W, f"SPECIES  -  {species_name.upper()}")
            y += 2
            traits = c.species.get("features", []) or c.species.get("traits", [])
            for trait in traits:
                name = trait.get("name", "")
                desc = trait.get("description", "")
                chip_type = FEATURE_ACTION_TYPES.get(name, "passive")
                feat_dict = {"name": name, "description": desc, "chip": chip_type}
                y = self._draw_feature_card(x0, y, CONTENT_W, feat_dict)
                y += 2
                if y > PAGE_H - MARGIN - 20:
                    break

        # Feats
        feats_to_show: list[tuple[str, dict, str]] = []
        if c.feat:
            feat_name = c.background.get("feat", c.feat.get("name", "")) if c.background else c.feat.get("name", "")
            feats_to_show.append((feat_name, c.feat, "Background"))
        if c.species_origin_feat:
            feats_to_show.append((c.species_origin_feat["name"], c.species_origin_feat, c.species_name or "Species"))

        if feats_to_show:
            y += 1
            y = self._section_rule(x0, y, CONTENT_W, "FEATS")
            y += 2
            for feat_name, feat, source in feats_to_show:
                desc_parts = []
                for benefit in feat.get("benefits", []):
                    ben_desc = benefit.get("description", "")
                    ben_name = benefit.get("name", "")
                    if ben_name and ben_desc:
                        desc_parts.append(f"{ben_name}: {ben_desc}")
                    elif ben_desc:
                        desc_parts.append(ben_desc)
                desc = "\n".join(desc_parts)
                feat_dict = {
                    "name": feat_name,
                    "description": desc,
                    "source": f"from {source}",
                    "chip": "passive",
                }
                y = self._draw_feature_card(x0, y, CONTENT_W, feat_dict)
                y += 2
                if y > PAGE_H - MARGIN - 20:
                    break

        # Innate spells (non-casters with species-granted spells)
        spell_entries = self._spellbook_entries()
        if spell_entries:
            y += 1
            y = self._section_rule(x0, y, CONTENT_W, "INNATE SPELLS")
            y += 2
            all_spells = self._get_spell_data()
            for entry in spell_entries:
                spell = all_spells.get(entry["spell_name"], {})
                if not spell:
                    continue
                card_h = self._measure_innate_spell_card(spell, CONTENT_W, entry)
                if y + card_h > PAGE_H - MARGIN - 12:
                    break
                y = self._draw_innate_spell_card(x0, y, CONTENT_W, spell, entry)
                y += 2

        self._draw_page_footer(self._p3_num, self._footer_name(), "Heritage & Magic")

    def _measure_innate_spell_card(self, spell, w, entry=None) -> float:
        h = 6.5  # panel title
        h += 3.5  # level/school + usage
        h += 7    # meta grid (4 cols)
        h += 1    # sep
        desc = spell.get("description", "")
        if desc:
            self._serif("", 9)
            lines = self.multi_cell(w - 8, 3.8, desc, dry_run=True, output="LINES")
            h += len(lines) * 3.8 + 1
        h += 2
        return h

    def _draw_innate_spell_card(self, x, y, w, spell, entry=None) -> float:
        card_h = self._measure_innate_spell_card(spell, w, entry)
        content_y = self._draw_panel(x, y, w, card_h, spell.get("name", "Spell"))

        ty = content_y + 1

        # Level / school
        level = spell.get("level", 0)
        school = spell.get("school", "")
        if level == 0:
            level_text = f"Cantrip · {school}"
        else:
            ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(level, f"{level}th")
            level_text = f"{ordinal}-level · {school}"

        self._serif("I", 8.5)
        self.set_text_color(*C_INK_2)
        self.set_xy(x + 3, ty)
        self.cell(w * 0.6, 3.5, level_text)

        # Usage tracker
        if entry and entry.get("free_casts"):
            free = entry["free_casts"]
            rest_label = free[0] if free else "Long Rest"
            self._sans("", 6.5)
            self.set_text_color(*C_INK_3)
            self.set_xy(x + w * 0.6, ty)
            self.cell(20, 3.5, "Uses")
            cx = x + w * 0.6 + 20
            for _ in range(len(free)):
                self._small_circle(cx, ty + 1.75, r=0.9)
                cx += 3
            self._sans("", 6.5)
            self.set_text_color(*C_INK_3)
            self.set_xy(cx + 1, ty)
            self.cell(w * 0.4 - 21 - len(free) * 3, 3.5, f"per {rest_label}")

        ty += 3.5

        # Meta grid: Casting | Range | Duration | Components
        meta_cols = [
            ("CASTING TIME", spell.get("casting_time", "")),
            ("RANGE",        spell.get("range", "")),
            ("DURATION",     spell.get("duration", "")),
            ("COMPONENTS",   self._spell_components_short(spell)),
        ]
        meta_col_w = w / 4
        for i, (lbl, val) in enumerate(meta_cols):
            mcx = x + i * meta_col_w
            if i > 0:
                self.set_draw_color(*C_RULE_2)
                self.set_line_width(LW_DIVIDER)
                self.line(mcx, ty, mcx, ty + 7)
            self._sans("B", 5.8)
            self.set_text_color(*C_INK_3)
            self.set_xy(mcx + 1, ty)
            self.cell(meta_col_w - 1, 3, lbl)
            self._sans("", 7.5)
            self.set_text_color(*C_INK)
            self.set_xy(mcx + 1, ty + 3)
            self.cell(meta_col_w - 1, 3.5, val[:16])

        ty += 7

        self.set_draw_color(*C_RULE_2)
        self.set_line_width(LW_DIVIDER)
        self.line(x + 2, ty, x + w - 2, ty)
        ty += 1.5

        # Description
        desc = spell.get("description", "")
        if desc:
            self._serif("", 9)
            self.set_text_color(*C_INK)
            self.set_xy(x + 3, ty)
            self.multi_cell(w - 6, 3.8, desc)

        return y + card_h

    # ════════════════════════════════════════════════════════════
    # PAGE 3B — Spellcasting (casters — kept from original)
    # ════════════════════════════════════════════════════════════

    def _draw_page_3_spells(self):
        c = self.c
        x0 = MARGIN
        y = MARGIN

        if not c.character_class:
            return

        from models.item_effects import get_spell_attack_bonus, get_spell_save_dc_bonus, get_effective_modifier

        cast_ability = c.character_class.get("spellcasting_ability", "Intelligence")
        cast_mod = get_effective_modifier(c, cast_ability)
        item_spell_atk = get_spell_attack_bonus(c)
        item_spell_dc = get_spell_save_dc_bonus(c)
        save_dc = 8 + c.proficiency_bonus + cast_mod + item_spell_dc
        atk_bonus = c.proficiency_bonus + cast_mod + item_spell_atk

        y = self._draw_page_header(x0, y, "Spellcasting",
                                   f"Ability: {cast_ability}  ·  Save DC {save_dc}  ·  Attack +{atk_bonus}",
                                   show_chip_legend=False)

        # ─── Spellcasting info (left) ───
        info_w = 55
        rows_info = [
            ("SPELLCASTING ABILITY", cast_ability, 8),
            ("SPELLCASTING MODIFIER", self._modifier_str(cast_mod), 12),
            ("SPELL SAVE DC", str(save_dc), 12),
            ("SPELL ATTACK BONUS", self._modifier_str(atk_bonus), 12),
        ]
        info_h = 6.5 + 2 + len(rows_info) * 6.5 + 2
        content_y = self._draw_panel(x0, y, info_w, info_h, "SPELLCASTING")

        ty = content_y + 2
        for label, val, font_size in rows_info:
            self._display(font_size)
            self.set_text_color(*C_ACCENT_INK if font_size > 8 else C_INK)
            self.set_xy(x0 + 2, ty)
            self.cell(18, 5.5, val, align="C")
            self._sans("", 5.5)
            self.set_text_color(*C_INK_3)
            self.set_xy(x0 + 21, ty + 1)
            self.cell(32, 3.5, label)
            ty += 6.5

        # ─── Spell Slots (right) ───
        slots_x = x0 + info_w + 3
        slots_w = CONTENT_W - info_w - 3
        slots_h = info_h
        content_sy = self._draw_panel(slots_x, y, slots_w, slots_h, "SPELL SLOTS")

        sy = content_sy + 2
        game_data = self._game_data_context()
        spell_slots = c.current_spell_slots(game_data)
        pact_slots, pact_slot_level = c.current_pact_magic(game_data)
        slot_key_map = {
            i: f"{i}{'st' if i == 1 else 'nd' if i == 2 else 'rd' if i == 3 else 'th'}"
            for i in range(1, 10)
        }
        slot_col_w = slots_w / 3
        for i, level in enumerate(range(1, 10)):
            col = i % 3
            row = i // 3
            sx = slots_x + col * slot_col_w + 2
            ssy = sy + row * 6.5
            total = (spell_slots.get(slot_key_map[level]) or spell_slots.get(str(level)) or 0)
            if pact_slots > 0 and level == pact_slot_level:
                total = pact_slots
            self.set_text_color(*C_INK_3)
            self._sans("", 5.5)
            self.set_xy(sx, ssy)
            self.cell(16, 3.5, f"Level {level}")
            self.set_text_color(*C_INK)
            self._display(8)
            self.set_xy(sx + 16, ssy)
            self.cell(10, 3.5, str(total) if total else "--", align="C")

        y += info_h + 3

        # ─── Right side: Personality + Portrait + Coins ───
        right_col_x = x0 + CONTENT_W * 0.55 + 2
        right_col_w = CONTENT_W * 0.45 - 2
        right_y = y

        right_y = self._draw_personality(right_col_x, right_y, right_col_w)
        right_y += 2
        right_y = self._draw_portrait_placeholder(right_col_x, right_y, right_col_w)
        right_y += 2
        right_y = self._draw_coins(right_col_x, right_y, right_col_w)

        # ─── Spell table (left) ───
        table_w = CONTENT_W * 0.55
        table_y = y

        col_widths = [
            10, table_w * 0.25, table_w * 0.18, 16,
            table_w * 0.14,
            table_w - 10 - table_w * 0.25 - table_w * 0.18 - 16 - table_w * 0.14,
        ]
        headers_s = ["Level", "Name", "Casting Time", "Range", "C / R / M", "Notes"]
        spell_entries = self._spellbook_entries()
        all_spells = self._get_spell_data()
        num_spells = len(spell_entries)
        blank_rows = max(0, 12 - num_spells)
        table_content_h = 6.5 + 1 + 4.5 + (num_spells + blank_rows) * 4.5 + 2
        table_content_h = min(table_content_h, PAGE_H - MARGIN - table_y)

        content_ty = self._draw_panel(x0, table_y, table_w, table_content_h, "CANTRIPS & PREPARED SPELLS")
        ty = content_ty + 1
        self._sans("B", 5.5)
        self.set_text_color(*C_ACCENT_INK)
        cx = x0 + 1
        for i, hdr in enumerate(headers_s):
            self.set_xy(cx, ty)
            self.cell(col_widths[i], 3.5, hdr)
            cx += col_widths[i]
        ty += 4.5
        self.set_draw_color(*C_RULE)
        self.set_line_width(LW_ROW)
        self.line(x0 + 1, ty - 0.5, x0 + table_w - 1, ty - 0.5)

        for entry in spell_entries:
            if ty > PAGE_H - MARGIN - 5:
                break
            spell_name = entry["spell_name"]
            spell = all_spells.get(spell_name, {})
            level = int(entry.get("level", spell.get("level", 0)) or 0)
            self._draw_spell_row(x0, ty, col_widths, level,
                                 format_spellbook_entry_label(entry), spell, entry)
            ty += 4.5

        for _ in range(blank_rows):
            if ty > PAGE_H - MARGIN - 5:
                break
            self.set_draw_color(*C_RULE_2)
            self.set_line_width(0.08)
            self.line(x0 + 1, ty + 4, x0 + table_w - 1, ty + 4)
            ty += 4.5

        self._draw_page_footer(self._p3_num, self._footer_name(), "Spellcasting")

    # ════════════════════════════════════════════════════════════
    # PAGE 4 — Persona & Story
    # ════════════════════════════════════════════════════════════

    def _draw_page_4_persona(self):
        c = self.c
        x0 = MARGIN
        y = MARGIN
        y = self._draw_page_header(x0, y, "Persona & Story",
                                   f"Who {c.name} is when the dice aren't rolling.",
                                   show_chip_legend=False)

        # 2×2 persona quadrants
        y = self._draw_persona_quadrants(x0, y)
        y += 3

        # Backstory card
        y = self._draw_backstory_card(x0, y)
        y += 3

        # Portrait
        remaining = PAGE_H - MARGIN - 9 - y
        if remaining >= 30:
            self._draw_portrait_placeholder(x0, y, CONTENT_W)

        self._draw_page_footer(self._p4_num, self._footer_name(), "Persona & Story")

    def _draw_persona_quadrants(self, x0, y) -> float:
        """Draw 2×2 grid: Personality Trait | Ideal | Bond | Flaw."""
        c = self.c
        gap = 3
        quad_w = (CONTENT_W - gap) / 2
        quad_h = 44
        labels = ["PERSONALITY TRAIT", "IDEAL", "BOND", "FLAW"]
        values = [
            getattr(c, "biography_personality", "") or "",
            "",  # No ideal field yet
            getattr(c, "biography_description", "") or "",  # using description as Bond
            "",  # No flaw field yet
        ]

        for i, (lbl, val) in enumerate(zip(labels, values)):
            col = i % 2
            row = i // 2
            qx = x0 + col * (quad_w + gap)
            qy = y + row * (quad_h + gap)
            self.set_draw_color(*C_RULE)
            self.set_line_width(LW_PANEL)
            self._rounded_rect(qx, qy, quad_w, quad_h, R_MD, "D")

            # Label
            self._sans("B", 6)
            self.set_text_color(*C_ACCENT_INK)
            self.set_xy(qx + 3, qy + 2)
            self.cell(quad_w - 6, 3.5, lbl)

            # Text content if any
            content_y = qy + 6.5
            if val:
                self._serif("", 9)
                self.set_text_color(*C_INK)
                self.set_xy(qx + 3, content_y)
                self.multi_cell(quad_w - 6, 4, val)
                content_y = self.get_y() + 1

            # Ruled writing lines for remaining space
            self._ruled_lines(qx + 3, content_y, quad_w - 6, qy + quad_h - content_y - 2, step=5.5)

        return y + 2 * (quad_h + gap) - gap

    def _draw_backstory_card(self, x0, y) -> float:
        """Draw backstory card with text + writing area."""
        c = self.c
        backstory = getattr(c, "biography_backstory", "") or ""
        writing_h = 32

        # Measure text height
        text_h = 0
        if backstory:
            self._serif("", 9.5)
            lines = self.multi_cell(CONTENT_W - 8, 4.2, backstory, dry_run=True, output="LINES")
            text_h = len(lines) * 4.2 + 2

        panel_h = 6.5 + text_h + writing_h + 3
        content_y = self._draw_panel(x0, y, CONTENT_W, panel_h, "BACKSTORY")
        ty = content_y + 1.5

        if backstory:
            self._serif("", 9.5)
            self.set_text_color(*C_INK)
            self.set_xy(x0 + 3, ty)
            self.multi_cell(CONTENT_W - 6, 4.2, backstory)
            ty = self.get_y() + 2

        # Ruled writing area
        self._ruled_lines(x0 + 3, ty, CONTENT_W - 6, y + panel_h - ty - 2, step=5.5)

        return y + panel_h

    # ── Personality / Portrait / Coins (kept for caster page 3) ──

    def _draw_personality(self, x, y, w) -> float:
        fields = [
            ("Backstory", getattr(self.c, "biography_backstory", "") or ""),
            ("Personality", getattr(self.c, "biography_personality", "") or ""),
            ("Description", getattr(self.c, "biography_description", "") or ""),
        ]
        lines_list: list[str] = []
        for label, value in fields:
            cleaned = " ".join(str(value).split())
            if cleaned:
                lines_list.append(f"{label}: {cleaned}")
        if not lines_list:
            lines_list = ["No biography details provided."]

        self._sans("", 5.2)
        text_w = w - 6
        total_text_lines = 0
        for line in lines_list:
            line_w = self.get_string_width(self._sanitize(line))
            total_text_lines += max(1, -(-int(line_w) // int(text_w)) + 1)
        text_h = total_text_lines * 3.1
        h = max(text_h + 8.5 + 4, 30)

        content_y = self._draw_panel(x, y, w, h, "PERSONALITY")

        self.set_draw_color(*C_RULE_2)
        self.set_line_width(0.08)
        for ly in range(int(y + 11), int(y + h - 2), 5):
            self.line(x + 3, ly, x + w - 3, ly)

        self._sans("", 5.2)
        self.set_text_color(*C_INK)
        self.set_xy(x + 3, y + 8.5)
        for line in lines_list:
            self.set_x(x + 3)
            self.multi_cell(text_w, 3.1, line)

        return y + h

    def _draw_portrait_placeholder(self, x, y, w) -> float:
        h = 60
        remaining = PAGE_H - MARGIN - 9 - y
        h = min(h, remaining)
        if h < 20:
            return y

        content_y = self._draw_panel(x, y, w, h, "PORTRAIT")
        pm = 5
        px = x + pm
        pw = w - pm * 2
        py = content_y + 2
        ph = h - content_y + y - 4

        image_data = getattr(self.c, "biography_image_data", "") or ""
        image_format = (getattr(self.c, "biography_image_format", "") or "").lower()
        if image_data:
            ext = "jpg" if image_format in {"jpg", "jpeg"} else "png"
            tmp_path = None
            try:
                raw = base64.b64decode(image_data)
                with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
                    tmp.write(raw)
                    tmp_path = tmp.name
                from PIL import Image as PILImage
                with PILImage.open(tmp_path) as img:
                    img_w, img_h = img.size
                avail_w = pw - 0.8
                avail_h = ph - 0.8
                scale = min(avail_w / img_w, avail_h / img_h)
                draw_w = img_w * scale
                draw_h = img_h * scale
                draw_x = px + 0.4 + (avail_w - draw_w) / 2
                draw_y = py + 0.4 + (avail_h - draw_h) / 2
                self.image(tmp_path, x=draw_x, y=draw_y, w=draw_w, h=draw_h)
            except Exception:
                self._draw_portrait_placeholder_empty(px, py, pw, ph)
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass
        else:
            self._draw_portrait_placeholder_empty(px, py, pw, ph)

        return y + h

    def _draw_portrait_placeholder_empty(self, px, py, pw, ph):
        self.set_draw_color(*C_INK_3)
        self.set_line_width(LW_DIVIDER)
        self.set_dash_pattern(dash=2, gap=2)
        self._rounded_rect(px, py, pw, ph, R_SM, "D")
        self.set_dash_pattern()
        self._sans("", 7)
        self.set_text_color(*C_INK_3)
        self.set_xy(px, py + ph / 2 - 2)
        self.cell(pw, 4, "PORTRAIT OR SYMBOL", align="C")

    def _draw_coins(self, x, y, w) -> float:
        h = 18
        content_y = self._draw_panel(x, y, w, h, "COINS")
        ty = content_y + 2
        gp, sp, cp_val = cp_to_coins(current_wealth_cp(self.c))
        coin_rows = [("CP", cp_val), ("SP", sp), ("EP", 0), ("GP", gp), ("PP", 0)]
        coin_w = (w - 6) / len(coin_rows)
        for i, (coin, val) in enumerate(coin_rows):
            ccx = x + 3 + i * coin_w
            is_zero = (val == 0)
            text_c = C_RULE if is_zero else C_INK
            lbl_c = C_RULE if is_zero else C_INK_3
            self._display(10)
            self.set_text_color(*text_c)
            self.set_xy(ccx, ty)
            self.cell(coin_w, 4.5, str(val), align="C")
            self._sans("B", 5.5)
            self.set_text_color(*lbl_c)
            self.set_xy(ccx, ty + 4.5)
            self.cell(coin_w, 3, coin, align="C")
        return y + h

    # ════════════════════════════════════════════════════════════
    # Spell utilities (kept mostly unchanged)
    # ════════════════════════════════════════════════════════════

    def _draw_spell_row(self, x, y, col_widths, level, name, spell, entry=None):
        cx = x + 1
        self._sans("", 6)
        self.set_text_color(*C_INK)
        notes: list[str] = []
        if entry:
            if entry.get("free_casts"):
                notes.append(", ".join(entry["free_casts"]))
            if entry.get("ritual_only"):
                notes.append("Ritual only")
            if entry.get("dragonmark_eligible"):
                notes.append("Dragonmark")
        values = [
            "C" if int(level or 0) == 0 else str(level),
            name,
            spell.get("casting_time", ""),
            spell.get("range", ""),
            self._spell_flags(spell),
            "; ".join(notes)[:30],
        ]
        for i, val in enumerate(values):
            self.set_xy(cx, y)
            self.cell(col_widths[i], 4.5, val[:30])
            cx += col_widths[i]

    def _spell_flags(self, spell):
        flags = []
        if spell.get("concentration"):
            flags.append("C")
        if spell.get("ritual"):
            flags.append("R")
        comps = spell.get("components", {})
        if comps.get("M") or comps.get("material"):
            flags.append("M")
        return ", ".join(flags)

    def _spell_components_short(self, spell):
        comps = spell.get("components", {})
        parts = []
        if comps.get("V") or comps.get("verbal"):
            parts.append("V")
        if comps.get("S") or comps.get("somatic"):
            parts.append("S")
        if comps.get("M") or comps.get("material"):
            parts.append("M")
        return ", ".join(parts)

    # ── Spell Description Pages ────────────────────────────────

    def _draw_spell_descriptions_pages(self):
        spell_data = self._get_spell_data()
        spell_entries = self._spellbook_entries()
        spells_to_render: list[tuple[dict, dict]] = []
        for entry in spell_entries:
            spell = spell_data.get(entry["spell_name"])
            if spell:
                spells_to_render.append((entry, spell))

        if not spells_to_render:
            return

        self.add_page()
        x0 = MARGIN
        col_w = (CONTENT_W - 3) / 2
        col_x = [x0, x0 + col_w + 3]
        col_y = [MARGIN, MARGIN]
        current_col = 0
        max_y = PAGE_H - MARGIN - 12

        for entry, spell in spells_to_render:
            card_h = self._measure_spell_card(spell, col_w, entry)
            if col_y[current_col] + card_h > max_y:
                if current_col == 0:
                    current_col = 1
                    if col_y[1] + card_h > max_y:
                        self._draw_spell_desc_footer()
                        self.add_page()
                        col_y = [MARGIN, MARGIN]
                        current_col = 0
                else:
                    self._draw_spell_desc_footer()
                    self.add_page()
                    col_y = [MARGIN, MARGIN]
                    current_col = 0

            col_y[current_col] = self._draw_spell_card(
                col_x[current_col], col_y[current_col], col_w, spell, entry)
            col_y[current_col] += 2

            if current_col == 0 and col_y[0] > col_y[1] + 20:
                current_col = 1
            elif current_col == 1 and col_y[1] > col_y[0] + 20:
                current_col = 0

        self._draw_spell_desc_footer()

    def _draw_spell_desc_footer(self):
        fy = PAGE_H - MARGIN - 6
        self.set_draw_color(*C_INK_3)
        self.set_line_width(LW_DIVIDER)
        self.line(MARGIN, fy, MARGIN + CONTENT_W, fy)

    def _measure_spell_card(self, spell, w, entry=None):
        inner_w = w - 4
        h = 6.5 + 1.5 + 3.5
        if entry:
            extra_tags: list[str] = []
            if entry.get("free_casts"):
                extra_tags.append(f"Free Casting: {', '.join(entry['free_casts'])}")
            if entry.get("ritual_only"):
                extra_tags.append("Ritual only")
            for note in entry.get("detail_notes", []) or []:
                extra_tags.append(note)
            if extra_tags:
                self._sans("I", 5.2)
                lines = self.multi_cell(inner_w, 2.8, " • ".join(extra_tags), dry_run=True, output="LINES")
                h += len(lines) * 2.8 + 0.5
        h += 3 + 3 + 2
        desc = spell.get("description", "")
        if desc:
            self._sans("", 5.5)
            lines = self.multi_cell(inner_w, 2.8, desc, dry_run=True, output="LINES")
            h += len(lines) * 2.8 + 1
        higher = spell.get("higher_levels")
        if higher:
            h += 3.5
            self._sans("", 5.5)
            lines = self.multi_cell(inner_w, 2.8, higher, dry_run=True, output="LINES")
            h += len(lines) * 2.8 + 1
        cantrip_up = spell.get("cantrip_upgrade")
        if cantrip_up:
            h += 3.5
            self._sans("", 5.5)
            lines = self.multi_cell(inner_w, 2.8, cantrip_up, dry_run=True, output="LINES")
            h += len(lines) * 2.8 + 1
        h += 2
        return h

    def _draw_spell_card(self, x, y, w, spell, entry=None) -> float:
        inner_w = w - 4
        inner_x = x + 2
        card_h = self._measure_spell_card(spell, w, entry)
        content_y = self._draw_panel(x, y, w, card_h,
                                     format_spellbook_entry_label(entry) if entry else spell.get("name", "Spell"))
        ty = content_y + 1.5

        level = spell.get("level", 0)
        school = spell.get("school", "")
        if level == 0:
            level_text = f"Cantrip -- {school}"
        else:
            ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(level, f"{level}th")
            level_text = f"{ordinal}-level {school}"
        conc = spell.get("concentration", False)
        ritual = spell.get("ritual", False)
        tags = []
        if conc:
            tags.append("Concentration")
        if ritual:
            tags.append("Ritual")
        if tags:
            level_text += f"  ({', '.join(tags)})"

        self._sans("I", 5.5)
        self.set_text_color(*C_INK_3)
        self.set_xy(inner_x, ty)
        self.cell(inner_w, 3.5, level_text)
        ty += 3.5

        if entry:
            extra_tags: list[str] = []
            if entry.get("free_casts"):
                extra_tags.append(f"Free Casting: {', '.join(entry['free_casts'])}")
            if entry.get("ritual_only"):
                extra_tags.append("Ritual only")
            for note in entry.get("detail_notes", []) or []:
                extra_tags.append(note)
            if extra_tags:
                self._sans("I", 5.2)
                self.set_text_color(*C_INK_3)
                self.set_xy(inner_x, ty)
                self.multi_cell(inner_w, 2.8, " • ".join(extra_tags))
                ty = self.get_y() + 0.5

        self._sans("B", 5.5)
        self.set_text_color(*C_ACCENT_INK)
        self.set_xy(inner_x, ty)
        self.cell(14, 3, "Casting Time:")
        self._sans("", 5.5)
        self.set_text_color(*C_INK_2)
        self.cell(inner_w / 2 - 14, 3, f"  {spell.get('casting_time', '')}")
        self._sans("B", 5.5)
        self.set_text_color(*C_ACCENT_INK)
        self.cell(8, 3, "Range:")
        self._sans("", 5.5)
        self.set_text_color(*C_INK_2)
        self.cell(inner_w / 2 - 8, 3, f"  {spell.get('range', '')}")
        ty += 3

        self._sans("B", 5.5)
        self.set_text_color(*C_ACCENT_INK)
        self.set_xy(inner_x, ty)
        self.cell(10, 3, "Duration:")
        self._sans("", 5.5)
        self.set_text_color(*C_INK_2)
        self.cell(inner_w / 2 - 10, 3, f"  {spell.get('duration', '')}")
        self._sans("B", 5.5)
        self.set_text_color(*C_ACCENT_INK)
        self.cell(14, 3, "Components:")
        self._sans("", 5.5)
        self.set_text_color(*C_INK_2)
        self.cell(inner_w / 2 - 14, 3, f"  {self._spell_components_short(spell)}")
        ty += 3
        ty += 2

        desc = spell.get("description", "")
        if desc:
            self._sans("", 5.5)
            self.set_text_color(*C_INK)
            self.set_xy(inner_x, ty)
            self.multi_cell(inner_w, 2.8, desc)
            ty = self.get_y() + 1

        higher = spell.get("higher_levels")
        if higher:
            self._sans("B", 5.5)
            self.set_text_color(*C_ACCENT_INK)
            self.set_xy(inner_x, ty)
            self.cell(inner_w, 3, "At Higher Levels:")
            ty += 3.5
            self._sans("", 5.5)
            self.set_text_color(*C_INK_2)
            self.set_xy(inner_x, ty)
            self.multi_cell(inner_w, 2.8, higher)
            ty = self.get_y() + 1

        cantrip_up = spell.get("cantrip_upgrade")
        if cantrip_up:
            self._sans("B", 5.5)
            self.set_text_color(*C_ACCENT_INK)
            self.set_xy(inner_x, ty)
            self.cell(inner_w, 3, "Cantrip Upgrade:")
            ty += 3.5
            self._sans("", 5.5)
            self.set_text_color(*C_INK_2)
            self.set_xy(inner_x, ty)
            self.multi_cell(inner_w, 2.8, cantrip_up)

        return y + card_h

    def _format_components_full(self, spell):
        comps = spell.get("components", {})
        parts = []
        if comps.get("V") or comps.get("verbal"):
            parts.append("V")
        if comps.get("S") or comps.get("somatic"):
            parts.append("S")
        mat = comps.get("M") or comps.get("material")
        if mat:
            if isinstance(mat, str) and mat not in ("true", "True"):
                parts.append(f"M ({mat})")
            else:
                parts.append("M")
        return ", ".join(parts)

    # ── Data helpers ────────────────────────────────────────────

    def _game_data_context(self):
        if self._game_data is None:
            from gui.data_loader import GameData
            self._game_data = GameData()
        return self._game_data

    def _spellbook_entries(self) -> list[dict]:
        return get_spellbook_entries(self.c, self._game_data_context())

    def _get_spell_data(self) -> dict[str, dict]:
        import json
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        spells_path = os.path.join(data_dir, "spells.json")
        if os.path.exists(spells_path):
            with open(spells_path, "r", encoding="utf-8") as f:
                spells = json.load(f)
            return {s["name"]: s for s in spells}
        return {}


def export_pdf(character: Character, path: str, game_data=None):
    """Generate and save a PDF character sheet."""
    pdf = CharacterSheetPDF(character, game_data=game_data)
    pdf.output(path)
