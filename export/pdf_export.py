"""Export character as a PDF character sheet — D&D 2024 inspired with visual flair."""

from fpdf import FPDF
from fpdf.enums import RenderStyle, Corner
from models.character import Character
from models.enums import ALL_SKILLS
from models.standard_actions import build_standard_actions


# Layout constants (all in mm, A4 = 210 x 297)
PAGE_W = 210
PAGE_H = 297
MARGIN = 8
CONTENT_W = PAGE_W - MARGIN * 2

# ── Color Palette ──
# Dark charcoal accent
C_ACCENT = (40, 40, 40)
C_ACCENT_LIGHT = (90, 90, 90)
C_ACCENT_DARK = (25, 25, 25)
# Neutrals
C_BLACK = (30, 30, 30)
C_TRUE_BLACK = (0, 0, 0)
C_WHITE = (255, 255, 255)
C_DARK_GRAY = (55, 55, 55)
C_MED_GRAY = (110, 110, 110)
C_LIGHT_GRAY = (190, 190, 190)
C_FILL_GRAY = (245, 243, 240)  # warm off-white
C_HEADER_BG = C_ACCENT_DARK
C_SHADOW = (0, 0, 0)

# Rounded corner radius
R_SM = 1.5
R_MD = 2.5
R_LG = 3.5

# Font paths (macOS system fonts)
FONT_GEORGIA = "/System/Library/Fonts/Supplemental/Georgia.ttf"
FONT_GEORGIA_BOLD = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
FONT_GEORGIA_ITALIC = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
FONT_GEORGIA_BI = "/System/Library/Fonts/Supplemental/Georgia Bold Italic.ttf"

ABILITIES = [
    "Strength",
    "Dexterity",
    "Constitution",
    "Intelligence",
    "Wisdom",
    "Charisma",
]
ABILITY_ABBR = {
    "Strength": "STR",
    "Dexterity": "DEX",
    "Constitution": "CON",
    "Intelligence": "INT",
    "Wisdom": "WIS",
    "Charisma": "CHA",
}
SKILLS_BY_ABILITY = {
    "Strength": ["Athletics"],
    "Dexterity": ["Acrobatics", "Sleight of Hand", "Stealth"],
    "Constitution": [],
    "Intelligence": ["Arcana", "History", "Investigation", "Nature", "Religion"],
    "Wisdom": ["Animal Handling", "Insight", "Medicine", "Perception", "Survival"],
    "Charisma": ["Deception", "Intimidation", "Performance", "Persuasion"],
}


class CharacterSheetPDF(FPDF):
    """Custom PDF with decorative drawing methods for the character sheet."""

    def __init__(self, character: Character):
        super().__init__("P", "mm", "A4")
        self.c = character
        self.set_auto_page_break(auto=False)

        # Register Georgia font family
        self._register_fonts()

        self.add_page()
        self._draw_page_1()

        if (
            character.is_caster
            or character.selected_cantrips
            or character.selected_spells
        ):
            self.add_page()
            self._draw_page_2()

    def _register_fonts(self):
        """Register Georgia font family for serif typography."""
        import os

        if os.path.exists(FONT_GEORGIA):
            self.add_font("Georgia", "", FONT_GEORGIA)
            self.add_font("Georgia", "B", FONT_GEORGIA_BOLD)
            self.add_font("Georgia", "I", FONT_GEORGIA_ITALIC)
            if os.path.exists(FONT_GEORGIA_BI):
                self.add_font("Georgia", "BI", FONT_GEORGIA_BI)
            self._has_georgia = True
        else:
            self._has_georgia = False

    def _serif(self, style: str = "", size: float = 10):
        """Set font to Georgia (serif) if available, fallback to Helvetica."""
        if self._has_georgia:
            self.set_font("Georgia", style, size)
        else:
            self.set_font("Helvetica", style, size)

    def _sans(self, style: str = "", size: float = 10):
        """Set font to Helvetica (sans-serif)."""
        self.set_font("Helvetica", style, size)

    # ── Text sanitizer ──

    @staticmethod
    def _sanitize(text: str) -> str:
        if not text:
            return ""
        replacements = {
            "\u2019": "'",
            "\u2018": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2013": "-",
            "\u2014": "--",
            "\u2026": "...",
            "\u2022": "*",
            "\u00d7": "x",
            "\u2666": "*",
            "\u25cb": "o",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text.encode("latin-1", errors="replace").decode("latin-1")

    def cell(self, w=None, h=None, text="", *args, **kwargs):
        return super().cell(w, h, self._sanitize(str(text)), *args, **kwargs)

    def multi_cell(self, w, h=None, text="", *args, **kwargs):
        return super().multi_cell(w, h, self._sanitize(str(text)), *args, **kwargs)

    # ── Core Drawing Helpers ──────────────────────────────────

    def _modifier_str(self, val):
        return f"+{val}" if val >= 0 else str(val)

    def _rounded_rect(self, x, y, w, h, r=R_MD, style="D", corners=True):
        """Draw a rounded rectangle. style: 'D'=draw, 'F'=fill, 'DF'=both."""
        style_map = {
            "D": RenderStyle.D,
            "F": RenderStyle.F,
            "DF": RenderStyle.DF,
            "FD": RenderStyle.DF,
        }
        rs = style_map.get(style, RenderStyle.D)
        if corners is True:
            self._draw_rounded_rect(x, y, w, h, rs, True, r)
        else:
            self._draw_rounded_rect(x, y, w, h, rs, corners, r)

    def _shadow_rect(self, x, y, w, h, r=R_MD, offset=0.6):
        """Draw a subtle drop shadow behind a rounded rect."""
        with self.local_context(fill_opacity=0.12):
            self.set_fill_color(*C_SHADOW)
            self._rounded_rect(x + offset, y + offset, w, h, r, "F")

    def _section_box(self, x, y, w, h, title=None, fill=False):
        """Draw a section box with rounded corners and accent title bar."""
        # Shadow
        self._shadow_rect(x, y, w, h, R_MD)

        # Fill
        if fill:
            self.set_fill_color(*C_FILL_GRAY)
            self._rounded_rect(x, y, w, h, R_MD, "F")

        # Border
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.3)
        self._rounded_rect(x, y, w, h, R_MD, "D")

        if title:
            return self._draw_section_title(x, y, w, title)
        return y

    def _draw_section_title(self, x, y, w, title):
        """Draw an accent-colored title bar with rounded top corners."""
        title_h = 6
        # Title background — rounded top, flat bottom
        self.set_fill_color(*C_ACCENT)
        self._draw_rounded_rect(
            x, y, w, title_h, RenderStyle.F, (Corner.TOP_LEFT, Corner.TOP_RIGHT), R_MD
        )
        # Crisp bottom edge
        self.set_fill_color(*C_ACCENT)
        self.rect(x, y + title_h - 1, w, 1, "F")

        # Title text
        self._sans("B", 6.5)
        self.set_text_color(*C_WHITE)
        self.set_xy(x + 3, y + 0.3)
        self.cell(w - 6, title_h, title.upper(), align="L")

        # Decorative diamond after title
        tw = self.get_string_width(title.upper())
        diamond_x = x + 3 + tw + 3
        diamond_y = y + title_h / 2
        if diamond_x < x + w - 6:
            self._draw_diamond(diamond_x, diamond_y, 1.2, C_WHITE)

        return y + title_h

    def _draw_diamond(self, cx, cy, size, color):
        """Draw a small diamond shape as decorative element."""
        self.set_fill_color(*color)
        self.set_draw_color(*color)
        # Draw as rotated square using polygon
        points = [
            (cx, cy - size),
            (cx + size, cy),
            (cx, cy + size),
            (cx - size, cy),
        ]
        # Use line segments to form diamond
        self.set_line_width(0.15)
        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]
        self.polygon(points, style="DF")

    def _draw_ornamental_line(self, x, y, w, thickness=0.4):
        """Draw a decorative line with diamond accents."""
        mid = x + w / 2
        # Lines on each side
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(thickness)
        self.line(x, y, mid - 8, y)
        self.line(mid + 8, y, x + w, y)
        # Center diamond
        self._draw_diamond(mid, y, 1.8, C_ACCENT)
        # Smaller flanking diamonds
        self._draw_diamond(mid - 5, y, 1.0, C_ACCENT_LIGHT)
        self._draw_diamond(mid + 5, y, 1.0, C_ACCENT_LIGHT)

    def _label_value_box(
        self,
        x,
        y,
        w,
        h,
        label,
        value,
        label_size: float = 5,
        value_size: float = 11,
        accent_border: bool = False,
    ):
        """Draw a stat box with large value and small label."""
        # Shadow
        self._shadow_rect(x, y, w, h, R_SM, 0.4)

        # Fill
        self.set_fill_color(*C_FILL_GRAY)
        self._rounded_rect(x, y, w, h, R_SM, "F")

        # Border
        if accent_border:
            self.set_draw_color(*C_ACCENT)
            self.set_line_width(0.5)
        else:
            self.set_draw_color(*C_LIGHT_GRAY)
            self.set_line_width(0.3)
        self._rounded_rect(x, y, w, h, R_SM, "D")

        # Value (large, centered)
        self._sans("B", value_size)
        self.set_text_color(*C_BLACK)
        self.set_xy(x, y + 1)
        self.cell(w, h * 0.52, str(value), align="C")

        # Label (small, centered at bottom)
        self._sans("", label_size)
        self.set_text_color(*C_MED_GRAY)
        self.set_xy(x, y + h * 0.58)
        self.cell(w, h * 0.35, label, align="C")

    def _small_circle(self, cx, cy, r=1.5, filled=False):
        """Draw a proficiency marker circle."""
        if filled:
            self.set_fill_color(*C_ACCENT)
            self.set_draw_color(*C_ACCENT)
            self.ellipse(cx - r, cy - r, r * 2, r * 2, "DF")
        else:
            self.set_draw_color(*C_LIGHT_GRAY)
            self.set_line_width(0.3)
            self.ellipse(cx - r, cy - r, r * 2, r * 2, "D")

    def _redraw_title(self, x, y, w, title):
        """Redraw a section title bar (needed after box resize)."""
        self._draw_section_title(x, y, w, title)

    def _draw_corner_ornament(self, x, y, size=4, corner="tl"):
        """Draw decorative corner brackets."""
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(0.5)
        if corner == "tl":
            self.line(x, y + size, x, y)
            self.line(x, y, x + size, y)
        elif corner == "tr":
            self.line(x - size, y, x, y)
            self.line(x, y, x, y + size)
        elif corner == "bl":
            self.line(x, y - size, x, y)
            self.line(x, y, x + size, y)
        elif corner == "br":
            self.line(x - size, y, x, y)
            self.line(x, y, x, y - size)

    # ── Page 1: Main Character Sheet ─────────────────────────

    def _draw_page_1(self):
        c = self.c
        x0 = MARGIN
        y = MARGIN

        # ─── Top Header Section ───
        y = self._draw_header(x0, y)
        y += 2

        # ─── Ornamental Divider ───
        self._draw_ornamental_line(x0, y, CONTENT_W)

        # "DUNGEONS & DRAGONS" text centered over divider
        self._serif("B", 7)
        self.set_text_color(*C_ACCENT)
        dnd_text = "DUNGEONS & DRAGONS"
        tw = self.get_string_width(dnd_text)
        dnd_x = x0 + (CONTENT_W - tw) / 2
        self.set_fill_color(*C_WHITE)
        self.rect(dnd_x - 4, y - 3, tw + 8, 6, "F")
        self.set_xy(dnd_x, y - 2.2)
        self.cell(tw, 4.5, dnd_text, align="C")

        y += 4

        # ─── Stats Row ───
        y = self._draw_stats_row(x0, y)
        y += 3

        # ─── Main two-column layout ───
        left_w = 55
        right_x = x0 + left_w + 3
        right_w = CONTENT_W - left_w - 3

        # Left column: Ability scores
        left_bottom = self._draw_ability_scores(x0, y, left_w)

        # Right column
        right_y = y
        right_y = self._draw_weapons_section(right_x, right_y, right_w)
        right_y += 2
        right_y = self._draw_class_features(right_x, right_y, right_w)
        right_y += 2

        # Species Traits + Feats side by side
        half_w = (right_w - 2) / 2
        traits_bottom = self._draw_species_traits(right_x, right_y, half_w)
        feats_bottom = self._draw_feats(right_x + half_w + 2, right_y, half_w)
        right_y = max(traits_bottom, feats_bottom)

        # ─── Heroic Inspiration ───
        heroic_y = left_bottom + 2
        heroic_bottom = self._draw_heroic_inspiration(x0, heroic_y, left_w)

        # ─── Bottom full-width sections ───
        bottom_y = max(heroic_bottom, right_y) + 3

        # Thin accent line separator
        self.set_draw_color(*C_ACCENT_LIGHT)
        self.set_line_width(0.2)
        self.line(x0 + 10, bottom_y - 1.5, x0 + CONTENT_W - 10, bottom_y - 1.5)

        half_bottom_w = CONTENT_W * 0.5 - 1
        prof_bottom = self._draw_proficiencies(x0, bottom_y, half_bottom_w)

        rb_x = x0 + CONTENT_W * 0.5 + 1
        rb_w = CONTENT_W * 0.5 - 1
        lang_bottom = self._draw_languages(rb_x, bottom_y, rb_w)
        equip_y = lang_bottom + 2
        equip_bottom = self._draw_equipment_list(rb_x, equip_y, rb_w)

        # Page footer ornament
        footer_y = PAGE_H - MARGIN - 1
        self._draw_ornamental_line(x0 + 30, footer_y, CONTENT_W - 60, 0.2)

    def _draw_header(self, x0, y):
        """Draw top header with character name, info, and stat boxes."""
        c = self.c

        # Right-side stat boxes
        box_w = 19
        box_h = 19
        gap = 2
        num_boxes = 5
        total_boxes_w = num_boxes * box_w + (num_boxes - 1) * gap
        boxes_x = x0 + CONTENT_W - total_boxes_w

        # Corner ornaments around header area
        self._draw_corner_ornament(x0, y, 5, "tl")
        self._draw_corner_ornament(x0 + CONTENT_W, y, 5, "tr")

        # Level
        bx = boxes_x
        self._draw_header_stat_box(bx, y, box_w, box_h, str(c.level), "LEVEL")

        # Armor Class
        bx += box_w + gap
        self._draw_header_stat_box(
            bx, y, box_w, box_h, str(c.armor_class), "ARMOR\nCLASS"
        )

        # Hit Points
        bx += box_w + gap
        self._draw_header_stat_box(
            bx, y, box_w, box_h, str(c.hit_points), "HIT\nPOINTS"
        )

        # Hit Dice
        bx += box_w + gap
        hit_die = (
            f"1d{c.character_class.get('hit_die', 8)}" if c.character_class else "--"
        )
        self._draw_header_stat_box(
            bx, y, box_w, box_h, hit_die, "HIT\nDICE", value_size=12
        )

        # Death Saves
        bx += box_w + gap
        self._shadow_rect(bx, y, box_w, box_h, R_MD, 0.5)
        self.set_fill_color(*C_FILL_GRAY)
        self._rounded_rect(bx, y, box_w, box_h, R_MD, "F")
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(0.4)
        self._rounded_rect(bx, y, box_w, box_h, R_MD, "D")

        self._sans("", 5)
        self.set_text_color(*C_MED_GRAY)
        self.set_xy(bx, y + 1.5)
        self.cell(box_w, 4, "DEATH", align="C")
        self.set_xy(bx, y + 5)
        self.cell(box_w, 4, "SAVES", align="C")
        for i in range(3):
            cx = bx + 5 + i * 3.5
            self._small_circle(cx, y + 13.5, r=1.4)

        # Left side: Character name
        left_w = boxes_x - x0 - 4

        self._serif("B", 18)
        self.set_text_color(*C_BLACK)
        self.set_xy(x0 + 1, y + 1)
        self.cell(left_w, 8, c.name)

        # Accent underline beneath name
        name_w = min(self.get_string_width(c.name) + 2, left_w)
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(0.6)
        self.line(x0 + 1, y + 10, x0 + 1 + name_w, y + 10)

        # Info rows
        info_y = y + 12
        col_w = left_w / 3

        self._header_info_pair(x0 + 1, info_y, "BACKGROUND", c.background_name)
        self._header_info_pair(x0 + 1 + col_w, info_y, "CLASS", c.class_name)
        subclass = ""
        if c.current_subclass:
            subclass = c.current_subclass.replace("-", " ").title()
        self._header_info_pair(x0 + 1 + col_w * 2, info_y, "SUBCLASS", subclass)

        info_y += 9
        species_text = c.species_name
        if c.species_sub_choice:
            species_text += f" ({c.species_sub_choice})"
        self._header_info_pair(x0 + 1, info_y, "SPECIES", species_text)

        return y + box_h + 3

    def _draw_header_stat_box(self, x, y, w, h, value, label, value_size=16):
        """Draw a single header stat box with accent styling."""
        # Shadow
        self._shadow_rect(x, y, w, h, R_MD, 0.5)
        # Fill
        self.set_fill_color(*C_FILL_GRAY)
        self._rounded_rect(x, y, w, h, R_MD, "F")
        # Accent border
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(0.4)
        self._rounded_rect(x, y, w, h, R_MD, "D")

        # Accent top bar (thin)
        self.set_fill_color(*C_ACCENT)
        self._draw_rounded_rect(
            x, y, w, 2.5, RenderStyle.F, (Corner.TOP_LEFT, Corner.TOP_RIGHT), R_MD
        )

        # Value
        self._sans("B", value_size)
        self.set_text_color(*C_BLACK)
        self.set_xy(x, y + 3)
        self.cell(w, h * 0.45, value, align="C")

        # Label
        self._sans("", 4.5)
        self.set_text_color(*C_MED_GRAY)
        lines = label.split("\n")
        label_y = y + h * 0.58
        for line in lines:
            self.set_xy(x, label_y)
            self.cell(w, 3.5, line, align="C")
            label_y += 3.5

    def _header_info_pair(self, x, y, label, value):
        """Draw a label/value pair in the header."""
        self._sans("", 5)
        self.set_text_color(*C_ACCENT)
        self.set_xy(x, y)
        self.cell(30, 3, label)

        self._serif("B", 8)
        self.set_text_color(*C_BLACK)
        self.set_xy(x, y + 3.5)
        self.cell(30, 4, value)

    def _draw_stats_row(self, x0, y):
        """Draw stats row spanning full width."""
        c = self.c

        primary_ability = "Intelligence"
        if c.character_class:
            pa = c.character_class.get("primary_ability", [])
            if pa:
                primary_ability = pa[0]

        primary_score = c.ability_scores.total(primary_ability)
        primary_mod = c.ability_scores.modifier(primary_ability)
        passive_perception = 10 + c.skill_modifier("Perception")

        row_h = 18

        pa_w = 34
        remaining = CONTENT_W - pa_w - 4
        reg_w = remaining / 5

        box_x = x0

        # Proficiency Bonus
        self._label_value_box(
            box_x,
            y,
            reg_w,
            row_h,
            "PROFICIENCY BONUS",
            f"+{c.proficiency_bonus}",
            value_size=14,
            accent_border=True,
        )
        box_x += reg_w + 1

        # Primary Ability (custom layout)
        self._shadow_rect(box_x, y, pa_w, row_h, R_SM, 0.4)
        self.set_fill_color(*C_FILL_GRAY)
        self._rounded_rect(box_x, y, pa_w, row_h, R_SM, "F")
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(0.4)
        self._rounded_rect(box_x, y, pa_w, row_h, R_SM, "D")

        self._serif("B", 7)
        self.set_text_color(*C_ACCENT)
        self.set_xy(box_x, y + 1)
        self.cell(pa_w, 4, primary_ability, align="C")

        half = pa_w / 2
        self._sans("", 4.5)
        self.set_text_color(*C_MED_GRAY)
        self.set_xy(box_x, y + 5)
        self.cell(half, 3, "MODIFIER", align="C")
        self.set_xy(box_x + half, y + 5)
        self.cell(half, 3, "SCORE", align="C")

        # Divider line in primary ability box
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.15)
        self.line(box_x + half, y + 5, box_x + half, y + row_h - 2)

        self._sans("B", 14)
        self.set_text_color(*C_BLACK)
        self.set_xy(box_x, y + 9)
        self.cell(half, 7, self._modifier_str(primary_mod), align="C")
        self.set_xy(box_x + half, y + 9)
        self.cell(half, 7, str(primary_score), align="C")

        box_x += pa_w + 1

        # Initiative
        self._label_value_box(
            box_x,
            y,
            reg_w,
            row_h,
            "INITIATIVE",
            self._modifier_str(c.initiative),
            value_size=14,
        )
        box_x += reg_w + 1

        # Speed
        self._label_value_box(
            box_x,
            y,
            reg_w,
            row_h,
            "SPEED",
            f"{c.speed} ft",
            value_size=11,
        )
        box_x += reg_w + 1

        # Size
        size_text = c.size_choice or "Medium"
        size_font = 10 if len(size_text) <= 6 else 8
        self._label_value_box(
            box_x,
            y,
            reg_w,
            row_h,
            "SIZE",
            size_text,
            value_size=size_font,
        )
        box_x += reg_w

        # Passive Perception
        pp_w = x0 + CONTENT_W - box_x
        self._label_value_box(
            box_x,
            y,
            pp_w,
            row_h,
            "PASSIVE PERCEP.",
            str(passive_perception),
            value_size=14,
            label_size=4.5,
        )

        return y + row_h

    def _draw_ability_scores(self, x, y, w):
        """Draw ability score blocks vertically with saves & skills."""
        c = self.c
        col_y = y
        profs = c.all_skill_proficiencies

        ab_w = 19
        ab_h = 23
        skills_x = x + ab_w + 2

        for ability in ABILITIES:
            total = c.ability_scores.total(ability)
            mod = c.ability_scores.modifier(ability)
            skills = SKILLS_BY_ABILITY.get(ability, [])

            # Ability name label above box
            self._serif("B", 7)
            self.set_text_color(*C_ACCENT)
            self.set_xy(x, col_y)
            self.cell(ab_w, 4, ability, align="C")
            col_y += 4

            # Shadow + outer box
            self._shadow_rect(x, col_y, ab_w, ab_h, R_SM, 0.4)
            self.set_fill_color(*C_FILL_GRAY)
            self._rounded_rect(x, col_y, ab_w, ab_h, R_SM, "F")
            self.set_draw_color(*C_ACCENT)
            self.set_line_width(0.4)
            self._rounded_rect(x, col_y, ab_w, ab_h, R_SM, "D")

            # Large modifier
            mod_str = self._modifier_str(mod)
            self._sans("B", 17)
            self.set_text_color(*C_BLACK)
            self.set_xy(x, col_y + 1)
            self.cell(ab_w, 9, mod_str, align="C")

            # "MODIFIER" label
            self._sans("", 4)
            self.set_text_color(*C_MED_GRAY)
            self.set_xy(x, col_y + 10)
            self.cell(ab_w, 3, "MODIFIER", align="C")

            # Score in small inner box
            score_w = 12
            score_h = 6.5
            score_x = x + (ab_w - score_w) / 2
            score_y = col_y + ab_h - score_h - 1.5
            self.set_fill_color(*C_WHITE)
            self._rounded_rect(score_x, score_y, score_w, score_h, 1.2, "F")
            self.set_draw_color(*C_ACCENT_LIGHT)
            self.set_line_width(0.3)
            self._rounded_rect(score_x, score_y, score_w, score_h, 1.2, "D")
            self._sans("B", 9)
            self.set_text_color(*C_BLACK)
            self.set_xy(score_x, score_y + 0.3)
            self.cell(score_w, score_h, str(total), align="C")

            # Saving throw
            save_prof = c.is_proficient_save(ability)
            save_mod = c.saving_throw_modifier(ability)

            sk_y = col_y + 1
            self._small_circle(skills_x + 1.5, sk_y + 1.8, r=1.3, filled=save_prof)
            self._sans("B" if save_prof else "", 7)
            self.set_text_color(*C_BLACK)
            self.set_xy(skills_x + 4, sk_y)
            self.cell(8, 3.5, self._modifier_str(save_mod), align="L")
            self._sans("", 5.5)
            self.set_text_color(*C_MED_GRAY)
            self.set_xy(skills_x + 12, sk_y + 0.3)
            self.cell(22, 3, "Saving Throw")
            sk_y += 4.5

            # Skills
            for skill_name in skills:
                is_prof = skill_name in profs
                sk_mod = c.skill_modifier(skill_name)

                self._small_circle(skills_x + 1.5, sk_y + 1.8, r=1.3, filled=is_prof)
                self._sans("B" if is_prof else "", 7)
                self.set_text_color(*C_BLACK if is_prof else C_DARK_GRAY)
                self.set_xy(skills_x + 4, sk_y)
                self.cell(8, 3.5, self._modifier_str(sk_mod), align="L")
                self._sans("I" if is_prof else "", 5.5)
                self.set_text_color(*C_DARK_GRAY)
                self.set_xy(skills_x + 12, sk_y + 0.3)
                self.cell(22, 3, skill_name)
                sk_y += 4.5

            col_y += ab_h + 3

        return col_y

    def _draw_weapons_section(self, x, y, w):
        """Draw weapons & damage / cantrips table."""
        rows = build_standard_actions(
            self.c,
            self._get_spell_data(),
            weapon_options=getattr(self.c, "standard_action_options", {}) or {},
        )
        row_count = max(4, len(rows))
        total_h_est = 12 + row_count * 5
        self._section_box(x, y, w, total_h_est, "WEAPONS & DAMAGE CANTRIPS")
        inner = y + 6
        ty = inner + 1

        col_widths = [w * 0.30, w * 0.22, w * 0.28, w * 0.20]
        headers = ["Name", "Atk Bonus", "Damage & Type", "Notes"]
        self._sans("B", 5.5)
        self.set_text_color(*C_MED_GRAY)
        cx = x + 2
        for i, hdr in enumerate(headers):
            self.set_xy(cx, ty)
            self.cell(col_widths[i], 3.5, hdr)
            cx += col_widths[i]
        ty += 4.5

        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.15)
        self.line(x + 2, ty - 0.5, x + w - 2, ty - 0.5)

        for _ in range(row_count):
            ty += 5
            self.set_draw_color(*C_LIGHT_GRAY)
            self.set_line_width(0.1)
            self.line(x + 2, ty, x + w - 2, ty)

        total_h = ty - y + 2
        # Redraw outer box at correct size
        self._shadow_rect(x, y, w, total_h, R_MD)
        self.set_fill_color(*C_WHITE)
        self._rounded_rect(x, y, w, total_h, R_MD, "F")
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.3)
        self._rounded_rect(x, y, w, total_h, R_MD, "D")
        self._redraw_title(x, y, w, "WEAPONS & DAMAGE CANTRIPS")

        # Re-draw table content over the fresh background
        ty2 = y + 6 + 1
        self._sans("B", 5.5)
        self.set_text_color(*C_MED_GRAY)
        cx = x + 2
        for i, hdr in enumerate(headers):
            self.set_xy(cx, ty2)
            self.cell(col_widths[i], 3.5, hdr)
            cx += col_widths[i]
        ty2 += 4.5
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.15)
        self.line(x + 2, ty2 - 0.5, x + w - 2, ty2 - 0.5)
        for i in range(row_count):
            if i < len(rows):
                r = rows[i]
                cy = ty2 + 0.2
                self._sans("", 5.7)
                self.set_text_color(*C_BLACK)
                cx = x + 2
                vals = [
                    r.get("name", ""),
                    r.get("attack", ""),
                    r.get("damage", ""),
                    r.get("notes", ""),
                ]
                limits = [22, 14, 22, 18]
                for col_idx, val in enumerate(vals):
                    self.set_xy(cx, cy)
                    self.cell(col_widths[col_idx], 4.2, str(val)[: limits[col_idx]])
                    cx += col_widths[col_idx]
            ty2 += 5
            self.set_draw_color(*C_LIGHT_GRAY)
            self.set_line_width(0.1)
            self.line(x + 2, ty2, x + w - 2, ty2)

        return y + total_h

    def _draw_class_features(self, x, y, w):
        """Draw class features section with two-column layout."""
        c = self.c
        if not c.character_class:
            return y

        features = c.character_class.get("level_1_features", [])
        title = "CLASS FEATURES"

        if not features:
            total_h = 15
            self._section_box(x, y, w, total_h, title)
            return y + total_h

        # First pass: measure content height
        inner_y = y + 6 + 1.5
        col_w = (w - 5) / 2
        left_ty = inner_y
        right_ty = inner_y
        use_right = False

        for i, feat in enumerate(features):
            curr_ty = left_ty if not use_right else right_ty
            curr_ty += 4  # title

            desc = feat.get("description", "")
            if desc:
                self._sans("", 5.5)
                # Approximate line count
                lines = len(desc) / (col_w * 0.55) + 1
                curr_ty += lines * 2.8 + 1

            if not use_right:
                left_ty = curr_ty
            else:
                right_ty = curr_ty

            if not use_right and i >= len(features) // 2:
                use_right = True

        content_h = max(left_ty, right_ty) - y + 3

        # Draw the box
        self._section_box(x, y, w, content_h, title)

        # Draw content
        ty = y + 6 + 1.5
        left_ty = ty
        right_ty = ty
        use_right = False

        self.set_text_color(*C_BLACK)
        for i, feat in enumerate(features):
            target_x = x + 2 if not use_right else x + 3 + col_w
            curr_ty = left_ty if not use_right else right_ty
            curr_w = col_w

            self._sans("B", 6.5)
            self.set_text_color(*C_ACCENT_DARK)
            self.set_xy(target_x, curr_ty)
            self.cell(curr_w, 3.5, feat["name"])
            curr_ty += 4

            desc = feat.get("description", "")
            if desc:
                self._sans("", 5.5)
                self.set_text_color(*C_DARK_GRAY)
                self.set_xy(target_x, curr_ty)
                self.multi_cell(curr_w, 2.8, desc)
                curr_ty = self.get_y() + 1

            if not use_right:
                left_ty = curr_ty
            else:
                right_ty = curr_ty

            if not use_right and i >= len(features) // 2:
                use_right = True

        total_h = max(left_ty, right_ty) - y + 2
        # Redraw final box
        self._shadow_rect(x, y, w, total_h, R_MD)
        self.set_fill_color(*C_WHITE)
        self._rounded_rect(x, y, w, total_h, R_MD, "F")
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.3)
        self._rounded_rect(x, y, w, total_h, R_MD, "D")
        self._redraw_title(x, y, w, title)

        # Re-draw content over fresh box
        ty = y + 6 + 1.5
        left_ty = ty
        right_ty = ty
        use_right = False

        for i, feat in enumerate(features):
            target_x = x + 2 if not use_right else x + 3 + col_w
            curr_ty = left_ty if not use_right else right_ty
            curr_w = col_w

            self._sans("B", 6.5)
            self.set_text_color(*C_ACCENT_DARK)
            self.set_xy(target_x, curr_ty)
            self.cell(curr_w, 3.5, feat["name"])
            curr_ty += 4

            desc = feat.get("description", "")
            if desc:
                self._sans("", 5.5)
                self.set_text_color(*C_DARK_GRAY)
                self.set_xy(target_x, curr_ty)
                self.multi_cell(curr_w, 2.8, desc)
                curr_ty = self.get_y() + 1

            if not use_right:
                left_ty = curr_ty
            else:
                right_ty = curr_ty

            if not use_right and i >= len(features) // 2:
                use_right = True

        return y + total_h

    def _draw_species_traits(self, x, y, w):
        """Draw species traits box."""
        c = self.c
        # Measure content first
        ty_measure = y + 6 + 1.5
        if c.species:
            ty_measure += 4
            for trait in c.species.get("traits", []):
                ty_measure += 3
                desc = trait.get("description", "")[:200]
                if desc:
                    lines = len(desc) / (w * 0.5) + 1
                    ty_measure += lines * 2.8 + 1

        total_h = max(ty_measure - y + 2, 20)
        self._section_box(x, y, w, total_h, "SPECIES TRAITS")
        ty = y + 6 + 1.5

        if c.species:
            ct = c.species.get("creature_type", "Humanoid")
            self._sans("B", 6)
            self.set_text_color(*C_BLACK)
            self.set_xy(x + 2, ty)
            self.cell(w - 4, 3, f"Creature Type: {ct}")
            ty += 4

            for trait in c.species.get("traits", []):
                self._sans("B", 6)
                self.set_text_color(*C_ACCENT_DARK)
                self.set_xy(x + 2, ty)
                self.multi_cell(w - 4, 3, f"{trait['name']}:")
                ty = self.get_y()

                desc = trait.get("description", "")[:200]
                if desc:
                    self._sans("", 5.5)
                    self.set_text_color(*C_DARK_GRAY)
                    self.set_xy(x + 2, ty)
                    self.multi_cell(w - 4, 2.8, desc)
                    ty = self.get_y() + 1

        actual_h = max(ty - y + 2, 20)
        # Redraw at correct size
        self._shadow_rect(x, y, w, actual_h, R_MD)
        self.set_fill_color(*C_WHITE)
        self._rounded_rect(x, y, w, actual_h, R_MD, "F")
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.3)
        self._rounded_rect(x, y, w, actual_h, R_MD, "D")
        self._redraw_title(x, y, w, "SPECIES TRAITS")

        # Re-draw content
        ty = y + 6 + 1.5
        if c.species:
            ct = c.species.get("creature_type", "Humanoid")
            self._sans("B", 6)
            self.set_text_color(*C_BLACK)
            self.set_xy(x + 2, ty)
            self.cell(w - 4, 3, f"Creature Type: {ct}")
            ty += 4
            for trait in c.species.get("traits", []):
                self._sans("B", 6)
                self.set_text_color(*C_ACCENT_DARK)
                self.set_xy(x + 2, ty)
                self.multi_cell(w - 4, 3, f"{trait['name']}:")
                ty = self.get_y()
                desc = trait.get("description", "")[:200]
                if desc:
                    self._sans("", 5.5)
                    self.set_text_color(*C_DARK_GRAY)
                    self.set_xy(x + 2, ty)
                    self.multi_cell(w - 4, 2.8, desc)
                    ty = self.get_y() + 1

        return y + actual_h

    def _draw_feats(self, x, y, w):
        """Draw feats box."""
        c = self.c

        feats_to_show = []
        if c.feat:
            feat_name = (
                c.background.get("feat", c.feat.get("name", ""))
                if c.background
                else c.feat.get("name", "")
            )
            feats_to_show.append((feat_name, c.feat, "Background"))
        if c.species_origin_feat:
            feats_to_show.append(
                (c.species_origin_feat["name"], c.species_origin_feat, c.species_name)
            )

        # Measure
        ty_m = y + 6 + 1.5
        for feat_name, feat, source in feats_to_show:
            ty_m += 3.5 + 3.5
            for benefit in feat.get("benefits", [])[:4]:
                desc = benefit.get("description", "")[:200]
                if desc:
                    lines = len(desc) / (w * 0.5) + 1
                    ty_m += lines * 2.8 + 0.5
            ty_m += 1

        total_h = max(ty_m - y + 2, 20)
        self._section_box(x, y, w, total_h, "FEATS")
        ty = y + 6 + 1.5

        for feat_name, feat, source in feats_to_show:
            self._serif("B", 6.5)
            self.set_text_color(*C_BLACK)
            self.set_xy(x + 2, ty)
            self.cell(w - 4, 3.5, feat_name)
            ty += 3.5

            self._serif("I", 5)
            self.set_text_color(*C_ACCENT_LIGHT)
            self.set_xy(x + 2, ty)
            self.cell(w - 4, 2.5, f"from {source}")
            ty += 3.5

            for benefit in feat.get("benefits", [])[:4]:
                desc = benefit.get("description", "")[:200]
                if desc:
                    self._sans("", 5.5)
                    self.set_text_color(*C_DARK_GRAY)
                    self.set_xy(x + 2, ty)
                    ben_name = benefit.get("name", "")
                    text = f"{ben_name}: {desc}" if ben_name else desc
                    self.multi_cell(w - 4, 2.8, text)
                    ty = self.get_y() + 0.5
            ty += 1

        actual_h = max(ty - y + 2, 20)
        # Redraw
        self._shadow_rect(x, y, w, actual_h, R_MD)
        self.set_fill_color(*C_WHITE)
        self._rounded_rect(x, y, w, actual_h, R_MD, "F")
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.3)
        self._rounded_rect(x, y, w, actual_h, R_MD, "D")
        self._redraw_title(x, y, w, "FEATS")

        # Re-draw content
        ty = y + 6 + 1.5
        for feat_name, feat, source in feats_to_show:
            self._serif("B", 6.5)
            self.set_text_color(*C_BLACK)
            self.set_xy(x + 2, ty)
            self.cell(w - 4, 3.5, feat_name)
            ty += 3.5
            self._serif("I", 5)
            self.set_text_color(*C_ACCENT_LIGHT)
            self.set_xy(x + 2, ty)
            self.cell(w - 4, 2.5, f"from {source}")
            ty += 3.5
            for benefit in feat.get("benefits", [])[:4]:
                desc = benefit.get("description", "")[:200]
                if desc:
                    self._sans("", 5.5)
                    self.set_text_color(*C_DARK_GRAY)
                    self.set_xy(x + 2, ty)
                    ben_name = benefit.get("name", "")
                    text = f"{ben_name}: {desc}" if ben_name else desc
                    self.multi_cell(w - 4, 2.8, text)
                    ty = self.get_y() + 0.5
            ty += 1

        return y + actual_h

    def _draw_heroic_inspiration(self, x, y, w):
        """Draw Heroic Inspiration box with accent circle."""
        h = 13
        self._section_box(x, y, w, h, "HEROIC INSPIRATION")
        # Large empty circle for tracking
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(0.5)
        self.ellipse(x + w / 2 - 3, y + 7, 6, 6, "D")

        # Redraw box
        self._shadow_rect(x, y, w, h, R_MD)
        self.set_fill_color(*C_WHITE)
        self._rounded_rect(x, y, w, h, R_MD, "F")
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.3)
        self._rounded_rect(x, y, w, h, R_MD, "D")
        self._redraw_title(x, y, w, "HEROIC INSPIRATION")
        # Redraw circle
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(0.5)
        self.ellipse(x + w / 2 - 3, y + 7.5, 6, 6, "D")
        return y + h

    def _draw_proficiencies(self, x, y, w):
        """Draw equipment training & proficiencies."""
        c = self.c
        if y + 20 > PAGE_H - MARGIN:
            return y

        # Measure content
        ty_m = y + 6 + 2 + 5 + 5 + 5  # approx rows
        total_h_est = ty_m - y + 4

        self._section_box(x, y, w, total_h_est, "EQUIPMENT TRAINING & PROFICIENCIES")
        ty = y + 6 + 2

        # Armor
        armor_types = []
        if c.character_class:
            for at in c.character_class.get("armor_proficiencies", []):
                armor_types.append(at)

        self._sans("B", 5.5)
        self.set_text_color(*C_ACCENT)
        self.set_xy(x + 2, ty)
        self.cell(14, 3, "ARMOR")

        armor_options = ["Light", "Medium", "Heavy", "Shields"]
        ax = x + 17
        for ao in armor_options:
            has = any(ao.lower() in a.lower() for a in armor_types)
            self._small_circle(ax + 1.5, ty + 1.5, r=1.2, filled=has)
            self._sans("", 5.5)
            self.set_text_color(*C_BLACK)
            self.set_xy(ax + 4, ty)
            self.cell(14, 3, ao)
            ax += 18
        ty += 5

        # Weapons
        weapon_profs = []
        if c.character_class:
            for wp in c.character_class.get("weapon_proficiencies", []):
                weapon_profs.append(wp)
        weapon_text = ", ".join(weapon_profs) if weapon_profs else "None"

        self._sans("B", 5.5)
        self.set_text_color(*C_ACCENT)
        self.set_xy(x + 2, ty)
        self.cell(14, 3, "WEAPONS")
        self._sans("", 6)
        self.set_text_color(*C_BLACK)
        self.set_xy(x + 17, ty)
        self.multi_cell(w - 19, 3, weapon_text)
        ty = self.get_y() + 1

        # Tools
        tool_profs = []
        if c.background:
            tp = c.background.get("tool_proficiency")
            if tp:
                tool_profs.append(tp)
        if c.character_class:
            for tp in c.character_class.get("tool_proficiencies", []):
                if tp not in tool_profs:
                    tool_profs.append(tp)
        tool_text = ", ".join(tool_profs) if tool_profs else "None"

        self._sans("B", 5.5)
        self.set_text_color(*C_ACCENT)
        self.set_xy(x + 2, ty)
        self.cell(14, 3, "TOOLS")
        self._sans("", 6)
        self.set_text_color(*C_BLACK)
        self.set_xy(x + 17, ty)
        self.multi_cell(w - 19, 3, tool_text)
        ty = self.get_y() + 1

        total_h = ty - y + 2
        # Redraw
        self._shadow_rect(x, y, w, total_h, R_MD)
        self.set_fill_color(*C_WHITE)
        self._rounded_rect(x, y, w, total_h, R_MD, "F")
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.3)
        self._rounded_rect(x, y, w, total_h, R_MD, "D")
        self._redraw_title(x, y, w, "EQUIPMENT TRAINING & PROFICIENCIES")

        # Re-draw content
        ty = y + 6 + 2
        self._sans("B", 5.5)
        self.set_text_color(*C_ACCENT)
        self.set_xy(x + 2, ty)
        self.cell(14, 3, "ARMOR")
        ax = x + 17
        for ao in armor_options:
            has = any(ao.lower() in a.lower() for a in armor_types)
            self._small_circle(ax + 1.5, ty + 1.5, r=1.2, filled=has)
            self._sans("", 5.5)
            self.set_text_color(*C_BLACK)
            self.set_xy(ax + 4, ty)
            self.cell(14, 3, ao)
            ax += 18
        ty += 5

        self._sans("B", 5.5)
        self.set_text_color(*C_ACCENT)
        self.set_xy(x + 2, ty)
        self.cell(14, 3, "WEAPONS")
        self._sans("", 6)
        self.set_text_color(*C_BLACK)
        self.set_xy(x + 17, ty)
        self.multi_cell(w - 19, 3, weapon_text)
        ty = self.get_y() + 1

        self._sans("B", 5.5)
        self.set_text_color(*C_ACCENT)
        self.set_xy(x + 2, ty)
        self.cell(14, 3, "TOOLS")
        self._sans("", 6)
        self.set_text_color(*C_BLACK)
        self.set_xy(x + 17, ty)
        self.multi_cell(w - 19, 3, tool_text)

        return y + total_h

    def _draw_languages(self, x, y, w):
        """Draw languages box."""
        c = self.c

        languages = ["Common"]
        if c.species:
            for trait in c.species.get("traits", []):
                name_lower = trait["name"].lower()
                if "language" in name_lower or "tongue" in name_lower:
                    desc = trait.get("description", "")
                    if desc:
                        languages.append(desc[:60])
        if len(languages) == 1:
            languages.append("Common Sign Language")
            languages.append("(Choose 1 more)")

        lang_text = ", ".join(languages)

        # Estimate height
        self._sans("B", 7)
        lines = len(lang_text) / (w * 0.55) + 1
        est_h = max(6 + 2 + lines * 4 + 3, 18)

        self._section_box(x, y, w, est_h, "LANGUAGES")
        ty = y + 6 + 2

        self._sans("B", 7)
        self.set_text_color(*C_BLACK)
        self.set_xy(x + 2, ty)
        self.multi_cell(w - 4, 4, lang_text)
        ty = self.get_y() + 1

        total_h = max(ty - y + 2, 18)
        # Redraw
        self._shadow_rect(x, y, w, total_h, R_MD)
        self.set_fill_color(*C_WHITE)
        self._rounded_rect(x, y, w, total_h, R_MD, "F")
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.3)
        self._rounded_rect(x, y, w, total_h, R_MD, "D")
        self._redraw_title(x, y, w, "LANGUAGES")

        # Re-draw content
        ty = y + 6 + 2
        self._sans("B", 7)
        self.set_text_color(*C_BLACK)
        self.set_xy(x + 2, ty)
        self.multi_cell(w - 4, 4, lang_text)

        return y + total_h

    def _draw_equipment_list(self, x, y, w):
        """Draw equipment list box."""
        c = self.c
        remaining = PAGE_H - MARGIN - y
        if remaining < 15:
            return y

        equip_items = []
        if c.character_class:
            for opt in c.character_class.get("starting_equipment", []):
                if opt["option"] == c.equipment_choice_class:
                    equip_items.append(opt["items"])
        if c.background:
            for opt in c.background.get("equipment", []):
                if opt["option"] == c.equipment_choice_background:
                    equip_items.append(opt["items"])

        # Measure
        ty_m = y + 6 + 2
        if equip_items:
            for item in equip_items:
                parts = [p.strip() for p in item.split(",")]
                for part in parts:
                    if part:
                        ty_m += 3.5
        else:
            ty_m += 4

        total_h = max(ty_m - y + 3, 20)
        total_h = min(total_h, remaining)

        self._section_box(x, y, w, total_h, "EQUIPMENT")
        ty = y + 6 + 2

        self._sans("", 6)
        self.set_text_color(*C_BLACK)

        if equip_items:
            for item in equip_items:
                parts = [p.strip() for p in item.split(",")]
                for part in parts:
                    if part and ty < PAGE_H - MARGIN - 4:
                        self.set_xy(x + 2, ty)
                        self.multi_cell(w - 4, 3, part)
                        ty = self.get_y() + 0.5
        else:
            self.set_xy(x + 2, ty)
            self.cell(w - 4, 3, "(No equipment selected)")
            ty += 4

        actual_h = max(ty - y + 3, 20)
        actual_h = min(actual_h, remaining)
        # Redraw
        self._shadow_rect(x, y, w, actual_h, R_MD)
        self.set_fill_color(*C_WHITE)
        self._rounded_rect(x, y, w, actual_h, R_MD, "F")
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.3)
        self._rounded_rect(x, y, w, actual_h, R_MD, "D")
        self._redraw_title(x, y, w, "EQUIPMENT")

        # Re-draw content
        ty = y + 6 + 2
        self._sans("", 6)
        self.set_text_color(*C_BLACK)
        if equip_items:
            for item in equip_items:
                parts = [p.strip() for p in item.split(",")]
                for part in parts:
                    if part and ty < PAGE_H - MARGIN - 4:
                        self.set_xy(x + 2, ty)
                        self.multi_cell(w - 4, 3, part)
                        ty = self.get_y() + 0.5
        else:
            self.set_xy(x + 2, ty)
            self.cell(w - 4, 3, "(No equipment selected)")

        return y + actual_h

    # ── Page 2: Spellcasting ─────────────────────────────────

    def _draw_page_2(self):
        c = self.c
        x0 = MARGIN
        y = MARGIN

        if not c.character_class:
            return

        cast_ability = c.character_class.get("spellcasting_ability", "Intelligence")
        cast_mod = c.ability_scores.modifier(cast_ability)
        save_dc = 8 + c.proficiency_bonus + cast_mod
        atk_bonus = c.proficiency_bonus + cast_mod

        # Corner ornaments
        self._draw_corner_ornament(x0, y, 5, "tl")
        self._draw_corner_ornament(x0 + CONTENT_W, y, 5, "tr")

        # ─── Spellcasting info (left) ───
        info_w = 55
        rows = [
            ("SPELLCASTING ABILITY", cast_ability, 8),
            ("SPELLCASTING MODIFIER", self._modifier_str(cast_mod), 12),
            ("SPELL SAVE DC", str(save_dc), 12),
            ("SPELL ATTACK BONUS", self._modifier_str(atk_bonus), 12),
        ]
        info_h = 6 + 2 + len(rows) * 6.5 + 2

        self._section_box(x0, y, info_w, info_h, "SPELLCASTING")

        # Redraw at correct size
        self._shadow_rect(x0, y, info_w, info_h, R_MD)
        self.set_fill_color(*C_WHITE)
        self._rounded_rect(x0, y, info_w, info_h, R_MD, "F")
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.3)
        self._rounded_rect(x0, y, info_w, info_h, R_MD, "D")
        self._redraw_title(x0, y, info_w, "SPELLCASTING")

        ty = y + 6 + 2
        for label, val, font_size in rows:
            self._sans("B", font_size)
            self.set_text_color(*C_ACCENT if font_size > 8 else C_BLACK)
            self.set_xy(x0 + 2, ty)
            self.cell(18, 5.5, val, align="C")
            self._sans("", 5.5)
            self.set_text_color(*C_MED_GRAY)
            self.set_xy(x0 + 21, ty + 1)
            self.cell(32, 3.5, label)
            ty += 6.5

        # ─── Spell Slots (right) ───
        slots_x = x0 + info_w + 3
        slots_w = CONTENT_W - info_w - 3
        slots_h = info_h

        self._section_box(slots_x, y, slots_w, slots_h, "SPELL SLOTS")

        # Redraw
        self._shadow_rect(slots_x, y, slots_w, slots_h, R_MD)
        self.set_fill_color(*C_WHITE)
        self._rounded_rect(slots_x, y, slots_w, slots_h, R_MD, "F")
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.3)
        self._rounded_rect(slots_x, y, slots_w, slots_h, R_MD, "D")
        self._redraw_title(slots_x, y, slots_w, "SPELL SLOTS")

        sy = y + 6 + 2
        spell_slots = c.character_class.get("spell_slots", {})
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

            total = (
                spell_slots.get(slot_key_map[level]) or spell_slots.get(str(level)) or 0
            )

            self.set_text_color(*C_MED_GRAY)
            self._sans("", 5.5)
            self.set_xy(sx, ssy)
            self.cell(16, 3.5, f"Level {level}")
            self.set_text_color(*C_BLACK)
            self._sans("B", 8)
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

        # ─── Cantrips & Prepared Spells table (left) ───
        table_w = CONTENT_W * 0.55
        table_y = y

        # First draw content to measure, then redraw
        col_widths = [
            10,
            table_w * 0.25,
            table_w * 0.18,
            16,
            table_w * 0.14,
            table_w - 10 - table_w * 0.25 - table_w * 0.18 - 16 - table_w * 0.14,
        ]
        headers = ["Level", "Name", "Casting Time", "Range", "C / R / M", "Notes"]

        all_spells = self._get_spell_data()
        num_spells = len(c.selected_cantrips) + len(c.selected_spells)
        blank_rows = max(0, 12 - num_spells)
        table_content_h = 6 + 1 + 4.5 + (num_spells + blank_rows) * 4.5 + 2
        table_content_h = min(table_content_h, PAGE_H - MARGIN - table_y)

        self._section_box(
            x0, table_y, table_w, table_content_h, "CANTRIPS & PREPARED SPELLS"
        )

        # Redraw box
        self._shadow_rect(x0, table_y, table_w, table_content_h, R_MD)
        self.set_fill_color(*C_WHITE)
        self._rounded_rect(x0, table_y, table_w, table_content_h, R_MD, "F")
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.3)
        self._rounded_rect(x0, table_y, table_w, table_content_h, R_MD, "D")
        self._redraw_title(x0, table_y, table_w, "CANTRIPS & PREPARED SPELLS")

        ty = table_y + 6 + 1
        self._sans("B", 5.5)
        self.set_text_color(*C_ACCENT)
        cx = x0 + 1
        for i, hdr in enumerate(headers):
            self.set_xy(cx, ty)
            self.cell(col_widths[i], 3.5, hdr)
            cx += col_widths[i]
        ty += 4.5

        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.15)
        self.line(x0 + 1, ty - 0.5, x0 + table_w - 1, ty - 0.5)

        for spell_name in c.selected_cantrips:
            if ty > PAGE_H - MARGIN - 5:
                break
            spell = all_spells.get(spell_name, {})
            self._draw_spell_row(x0, ty, col_widths, 0, spell_name, spell)
            ty += 4.5

        for spell_name in c.selected_spells:
            if ty > PAGE_H - MARGIN - 5:
                break
            spell = all_spells.get(spell_name, {})
            level = spell.get("level", 1)
            self._draw_spell_row(x0, ty, col_widths, level, spell_name, spell)
            ty += 4.5

        for _ in range(blank_rows):
            if ty > PAGE_H - MARGIN - 5:
                break
            self.set_draw_color(*C_LIGHT_GRAY)
            self.set_line_width(0.08)
            self.line(x0 + 1, ty + 4, x0 + table_w - 1, ty + 4)
            ty += 4.5

        # Footer ornament
        footer_y = PAGE_H - MARGIN - 1
        self._draw_ornamental_line(x0 + 30, footer_y, CONTENT_W - 60, 0.2)

    def _draw_personality(self, x, y, w):
        """Draw personality box."""
        h = 30
        self._section_box(x, y, w, h, "PERSONALITY")

        # Redraw
        self._shadow_rect(x, y, w, h, R_MD)
        self.set_fill_color(*C_WHITE)
        self._rounded_rect(x, y, w, h, R_MD, "F")
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.3)
        self._rounded_rect(x, y, w, h, R_MD, "D")
        self._redraw_title(x, y, w, "PERSONALITY")

        # Ruled lines
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.08)
        for ly in range(int(y + 11), int(y + h - 2), 5):
            self.line(x + 3, ly, x + w - 3, ly)
        return y + h

    def _draw_portrait_placeholder(self, x, y, w):
        """Draw character portrait placeholder."""
        h = 42
        self._section_box(x, y, w, h, "CHARACTER PORTRAIT / SYMBOL")

        # Redraw
        self._shadow_rect(x, y, w, h, R_MD)
        self.set_fill_color(*C_WHITE)
        self._rounded_rect(x, y, w, h, R_MD, "F")
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.3)
        self._rounded_rect(x, y, w, h, R_MD, "D")
        self._redraw_title(x, y, w, "CHARACTER PORTRAIT / SYMBOL")

        # Inner frame
        pm = 8
        px = x + pm
        pw = w - pm * 2
        py = y + 10
        ph = h - 14
        self.set_draw_color(*C_ACCENT_LIGHT)
        self.set_line_width(0.2)
        self._rounded_rect(px, py, pw, ph, R_SM, "D")

        return y + h

    def _draw_coins(self, x, y, w):
        """Draw coins tracking section."""
        h = 26
        self._section_box(x, y, w, h, "COINS")

        # Redraw
        self._shadow_rect(x, y, w, h, R_MD)
        self.set_fill_color(*C_WHITE)
        self._rounded_rect(x, y, w, h, R_MD, "F")
        self.set_draw_color(*C_LIGHT_GRAY)
        self.set_line_width(0.3)
        self._rounded_rect(x, y, w, h, R_MD, "D")
        self._redraw_title(x, y, w, "COINS")

        ty = y + 9
        coin_types = ["CP", "SP", "EP", "GP", "PP"]
        coin_w = (w - 6) / len(coin_types)
        for i, coin in enumerate(coin_types):
            cx = x + 3 + i * coin_w
            # Coin box
            self.set_fill_color(*C_FILL_GRAY)
            self._rounded_rect(cx, ty, coin_w - 2, 8, 1.0, "F")
            self.set_draw_color(*C_LIGHT_GRAY)
            self.set_line_width(0.2)
            self._rounded_rect(cx, ty, coin_w - 2, 8, 1.0, "D")
            # Label
            self._sans("B", 5.5)
            self.set_text_color(*C_ACCENT)
            self.set_xy(cx, ty + 8.5)
            self.cell(coin_w - 2, 3.5, coin, align="C")

        return y + h

    def _draw_spell_row(self, x, y, col_widths, level, name, spell):
        """Draw one row in the spell table."""
        cx = x + 1
        self._sans("", 6)
        self.set_text_color(*C_BLACK)

        values = [
            str(level),
            name,
            spell.get("casting_time", ""),
            spell.get("range", ""),
            self._spell_flags(spell),
            self._spell_components_short(spell),
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

    def _get_spell_data(self) -> dict[str, dict]:
        """Load spell data for the spell table."""
        import json
        import os

        data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
        )
        spells_path = os.path.join(data_dir, "spells.json")
        if os.path.exists(spells_path):
            with open(spells_path, "r", encoding="utf-8") as f:
                spells = json.load(f)
            return {s["name"]: s for s in spells}
        return {}


def export_pdf(character: Character, path: str):
    """Generate and save a PDF character sheet."""
    pdf = CharacterSheetPDF(character)
    pdf.output(path)
