"""Export character as a PDF character sheet inspired by D&D 2024 layout."""

from fpdf import FPDF
from models.character import Character
from models.enums import ALL_SKILLS


# Layout constants (all in mm, A4 = 210 x 297)
PAGE_W = 210
PAGE_H = 297
MARGIN = 8
COL_LEFT_W = 72  # left column for ability scores
COL_RIGHT_W = PAGE_W - MARGIN * 2 - COL_LEFT_W - 4  # right column

# Colors
C_BG = (43, 43, 43)
C_FG = (232, 220, 200)
C_ACCENT = (196, 149, 106)
C_BORDER = (100, 85, 70)
C_CARD = (55, 50, 45)
C_WHITE = (255, 255, 255)
C_BLACK = (0, 0, 0)
C_DARK = (30, 28, 25)
C_LIGHT_BG = (245, 240, 232)
C_LIGHT_FG = (40, 35, 30)
C_LIGHT_ACCENT = (140, 100, 65)
C_LIGHT_BORDER = (180, 165, 145)
C_LIGHT_CARD = (232, 225, 212)
C_LIGHT_HEADER = (80, 65, 50)

ABILITIES = ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"]

# Skill groupings by ability
SKILLS_BY_ABILITY = {
    "Strength": ["Athletics"],
    "Dexterity": ["Acrobatics", "Sleight of Hand", "Stealth"],
    "Constitution": [],
    "Intelligence": ["Arcana", "History", "Investigation", "Nature", "Religion"],
    "Wisdom": ["Animal Handling", "Insight", "Medicine", "Perception", "Survival"],
    "Charisma": ["Deception", "Intimidation", "Performance", "Persuasion"],
}


class CharacterSheetPDF(FPDF):
    """Custom PDF with helper drawing methods for the character sheet."""

    def __init__(self, character: Character):
        super().__init__("P", "mm", "A4")
        self.c = character
        self.set_auto_page_break(auto=False)
        self.add_page()
        self._draw_page_1()

        if character.is_caster or character.selected_cantrips or character.selected_spells:
            self.add_page()
            self._draw_page_2()

    # ── Text sanitizer (built-in Helvetica only supports latin-1) ──

    @staticmethod
    def _sanitize(text: str) -> str:
        """Replace Unicode characters that Helvetica can't render."""
        if not text:
            return ""
        replacements = {
            "\u2019": "'", "\u2018": "'",  # smart quotes
            "\u201c": '"', "\u201d": '"',
            "\u2013": "-", "\u2014": "--",  # dashes
            "\u2026": "...",  # ellipsis
            "\u2022": "*",   # bullet
            "\u00d7": "x",   # multiplication sign
            "\u2666": "*", "\u25cb": "o",  # diamond/circle
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        # Strip any remaining non-latin-1
        return text.encode("latin-1", errors="replace").decode("latin-1")

    # Override cell/multi_cell to auto-sanitize
    def cell(self, w=None, h=None, text="", *args, **kwargs):
        return super().cell(w, h, self._sanitize(str(text)), *args, **kwargs)

    def multi_cell(self, w, h=None, text="", *args, **kwargs):
        return super().multi_cell(w, h, self._sanitize(str(text)), *args, **kwargs)

    # ── Drawing helpers ──────────────────────────────────────

    def _box(self, x, y, w, h, title=None, fill_card=False):
        """Draw a bordered box, optionally with a title banner."""
        if fill_card:
            self.set_fill_color(*C_LIGHT_CARD)
            self.rect(x, y, w, h, "F")
        self.set_draw_color(*C_LIGHT_BORDER)
        self.set_line_width(0.4)
        self.rect(x, y, w, h)

        if title:
            self.set_fill_color(*C_LIGHT_HEADER)
            self.rect(x, y, w, 6, "F")
            self.set_draw_color(*C_LIGHT_BORDER)
            self.rect(x, y, w, 6)
            self.set_font("Helvetica", "B", 7)
            self.set_text_color(*C_LIGHT_BG)
            self.set_xy(x, y)
            self.cell(w, 6, f"  {title.upper()}", align="L")
            return y + 6
        return y

    def _stat_box(self, x, y, label, mod_val, score, w=32, h=28):
        """Draw an ability score box with modifier and score."""
        self.set_draw_color(*C_LIGHT_BORDER)
        self.set_line_width(0.4)
        self.rect(x, y, w, h)

        # Label at top
        self.set_font("Helvetica", "B", 6.5)
        self.set_text_color(*C_LIGHT_HEADER)
        self.set_xy(x, y + 1)
        self.cell(w, 4, label.upper(), align="C")

        # Big modifier
        mod_str = f"+{mod_val}" if mod_val >= 0 else str(mod_val)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*C_LIGHT_FG)
        self.set_xy(x, y + 5)
        self.cell(w, 11, mod_str, align="C")

        # Score in a small box at bottom-right
        self.set_font("Helvetica", "", 8)
        sw = 10
        sx = x + w - sw - 2
        sy = y + h - 9
        self.set_fill_color(*C_LIGHT_BG)
        self.rect(sx, sy, sw, 7, "DF")
        self.set_xy(sx, sy)
        self.cell(sw, 7, str(score), align="C")

    def _modifier_str(self, val):
        return f"+{val}" if val >= 0 else str(val)

    # ── Page 1: Main Character Sheet ─────────────────────────

    def _draw_page_1(self):
        c = self.c
        x0 = MARGIN
        y = MARGIN

        # ─── Header banner ───
        banner_h = 22
        inner_y = self._box(x0, y, PAGE_W - MARGIN * 2, banner_h, fill_card=True)

        # Character name (large)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*C_LIGHT_FG)
        self.set_xy(x0 + 3, y + 2)
        self.cell(90, 7, c.name)

        # Class
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*C_LIGHT_ACCENT)
        self.set_xy(x0 + 3, y + 9)
        self.cell(30, 5, "CLASS", align="L")
        self.set_text_color(*C_LIGHT_FG)
        self.set_xy(x0 + 3, y + 13.5)
        self.set_font("Helvetica", "B", 9)
        self.cell(50, 5, c.class_name)

        # Background
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*C_LIGHT_ACCENT)
        self.set_xy(x0 + 55, y + 9)
        self.cell(30, 5, "BACKGROUND")
        self.set_text_color(*C_LIGHT_FG)
        self.set_xy(x0 + 55, y + 13.5)
        self.set_font("Helvetica", "B", 9)
        self.cell(50, 5, c.background_name)

        # Species
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*C_LIGHT_ACCENT)
        self.set_xy(x0 + 115, y + 9)
        self.cell(30, 5, "SPECIES")
        self.set_text_color(*C_LIGHT_FG)
        self.set_xy(x0 + 115, y + 13.5)
        self.set_font("Helvetica", "B", 9)
        species_text = c.species_name
        if c.species_sub_choice:
            species_text += f" ({c.species_sub_choice})"
        self.cell(60, 5, species_text)

        # Level box on the right
        lx = x0 + PAGE_W - MARGIN * 2 - 22
        self.set_draw_color(*C_LIGHT_BORDER)
        self.rect(lx, y + 2, 18, 18)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*C_LIGHT_FG)
        self.set_xy(lx, y + 3)
        self.cell(18, 10, str(c.level), align="C")
        self.set_font("Helvetica", "", 6)
        self.set_text_color(*C_LIGHT_ACCENT)
        self.set_xy(lx, y + 13)
        self.cell(18, 4, "LEVEL", align="C")

        y += banner_h + 3

        # ─── Quick stats row ───
        stats_row = [
            ("PROF. BONUS", f"+{c.proficiency_bonus}"),
            ("INITIATIVE", self._modifier_str(c.initiative)),
            ("SPEED", f"{c.speed} ft"),
            ("SIZE", c.size_choice or "Medium"),
            ("ARMOR CLASS", str(c.armor_class)),
            ("HIT POINTS", str(c.hit_points)),
            ("HIT DICE", f"1d{c.character_class.get('hit_die', 8)}" if c.character_class else "—"),
        ]

        stat_w = (PAGE_W - MARGIN * 2) / len(stats_row)
        for i, (label, val) in enumerate(stats_row):
            sx = x0 + i * stat_w
            self.set_draw_color(*C_LIGHT_BORDER)
            self.rect(sx, y, stat_w, 14)
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(*C_LIGHT_FG)
            self.set_xy(sx, y + 0.5)
            self.cell(stat_w, 7, val, align="C")
            self.set_font("Helvetica", "", 5.5)
            self.set_text_color(*C_LIGHT_ACCENT)
            self.set_xy(sx, y + 8)
            self.cell(stat_w, 4, label, align="C")

        y += 17

        # ─── Left column: Ability Scores + Saves + Skills ───
        left_x = x0
        left_w = COL_LEFT_W
        right_x = x0 + left_w + 4
        right_w = COL_RIGHT_W

        col_y = y
        profs = c.all_skill_proficiencies

        for ability in ABILITIES:
            total = c.ability_scores.total(ability)
            mod = c.ability_scores.modifier(ability)
            self._stat_box(left_x, col_y, ability, mod, total, w=32, h=28)

            # Saving throw next to stat box
            save_x = left_x + 34
            save_prof = c.is_proficient_save(ability)
            save_mod = c.saving_throw_modifier(ability)
            marker = "*" if save_prof else "o"

            self.set_font("Helvetica", "", 7)
            self.set_text_color(*C_LIGHT_FG)
            self.set_xy(save_x, col_y + 1)
            self.cell(5, 4, marker, align="C")
            self.cell(8, 4, self._modifier_str(save_mod), align="C")
            self.set_font("Helvetica", "", 6.5)
            self.set_text_color(*C_LIGHT_ACCENT)
            self.cell(25, 4, "Saving Throw")

            # Skills for this ability
            skills = SKILLS_BY_ABILITY.get(ability, [])
            for si, skill_name in enumerate(skills):
                sk_y = col_y + 6 + si * 4.5
                is_prof = skill_name in profs
                sk_mod = c.skill_modifier(skill_name)
                marker = "*" if is_prof else "o"

                self.set_font("Helvetica", "", 7)
                self.set_text_color(*C_LIGHT_FG)
                self.set_xy(save_x, sk_y)
                self.cell(5, 4, marker, align="C")
                self.cell(8, 4, self._modifier_str(sk_mod), align="C")
                self.set_font("Helvetica", "", 6.5)
                self.set_text_color(*C_LIGHT_ACCENT)
                self.cell(25, 4, skill_name)

            # Height for this block: stat box + max skill rows
            block_h = max(28, 6 + len(skills) * 4.5 + 2)
            col_y += block_h + 2

        # ─── Right column ───
        ry = y

        # Weapons & Cantrips
        ry = self._draw_weapons_section(right_x, ry, right_w)
        ry += 3

        # Class Features
        ry = self._draw_class_features(right_x, ry, right_w)
        ry += 3

        # Species Traits + Feats side by side
        half_w = (right_w - 2) / 2
        traits_y = ry
        feats_y = ry
        traits_y = self._draw_species_traits(right_x, ry, half_w)
        feats_y = self._draw_feats(right_x + half_w + 2, ry, half_w)

        bottom_y = max(traits_y, feats_y) + 3

        # Equipment Training & Proficiencies (full width at bottom)
        self._draw_proficiencies(x0, max(bottom_y, col_y + 2), PAGE_W - MARGIN * 2)

    def _draw_weapons_section(self, x, y, w):
        """Draw weapons & cantrips table."""
        c = self.c
        inner = self._box(x, y, w, 6, "WEAPONS & DAMAGE / CANTRIPS")
        ty = inner + 1

        # Table header
        col_widths = [w * 0.35, w * 0.18, w * 0.25, w * 0.22]
        headers = ["Name", "Atk / DC", "Damage & Type", "Notes"]
        self.set_font("Helvetica", "B", 6)
        self.set_text_color(*C_LIGHT_ACCENT)
        cx = x + 1
        for i, hdr in enumerate(headers):
            self.set_xy(cx, ty)
            self.cell(col_widths[i], 4, hdr)
            cx += col_widths[i]
        ty += 5

        self.set_draw_color(*C_LIGHT_BORDER)
        self.set_line_width(0.2)
        self.line(x + 1, ty - 1, x + w - 1, ty - 1)

        # Empty weapon rows (user fills in)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*C_LIGHT_FG)
        for _ in range(4):
            self.set_draw_color(200, 195, 185)
            self.line(x + 1, ty + 4, x + w - 1, ty + 4)
            ty += 5

        # Bottom border
        total_h = ty - y + 1
        self.set_draw_color(*C_LIGHT_BORDER)
        self.set_line_width(0.4)
        self.rect(x, y, w, total_h)
        return y + total_h

    def _draw_class_features(self, x, y, w):
        """Draw class features section."""
        c = self.c
        if not c.character_class:
            return y

        features = c.character_class.get("level_1_features", [])
        if not features:
            return y

        # Estimate height
        text_lines = []
        for feat in features:
            text_lines.append(("B", feat["name"]))
            desc = feat.get("description", "")[:250]
            if desc:
                text_lines.append(("N", desc))

        inner = self._box(x, y, w, 6, f"{c.class_name.upper()} FEATURES")
        ty = inner + 2

        self.set_text_color(*C_LIGHT_FG)
        for style, text in text_lines:
            if style == "B":
                self.set_font("Helvetica", "B", 7)
            else:
                self.set_font("Helvetica", "", 6.5)

            self.set_xy(x + 2, ty)
            # Multi-cell for wrapping
            self.multi_cell(w - 4, 3.5, text)
            ty = self.get_y()

        total_h = ty - y + 2
        # Redraw outer box at correct height
        self.set_draw_color(*C_LIGHT_BORDER)
        self.set_line_width(0.4)
        self.rect(x, y, w, total_h)
        # Redraw title
        self.set_fill_color(*C_LIGHT_HEADER)
        self.rect(x, y, w, 6, "F")
        self.set_draw_color(*C_LIGHT_BORDER)
        self.rect(x, y, w, 6)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*C_LIGHT_BG)
        self.set_xy(x, y)
        self.cell(w, 6, f"  {c.class_name.upper()} FEATURES", align="L")

        return y + total_h

    def _draw_species_traits(self, x, y, w):
        """Draw species traits box."""
        c = self.c
        inner = self._box(x, y, w, 6, "SPECIES TRAITS")
        ty = inner + 2

        if c.species:
            ct = c.species.get("creature_type", "Humanoid")
            self.set_font("Helvetica", "B", 6.5)
            self.set_text_color(*C_LIGHT_FG)
            self.set_xy(x + 2, ty)
            self.cell(w - 4, 3.5, f"Creature Type: {ct}")
            ty += 4

            for trait in c.species.get("traits", []):
                self.set_font("Helvetica", "B", 6.5)
                self.set_text_color(*C_LIGHT_FG)
                self.set_xy(x + 2, ty)
                self.multi_cell(w - 4, 3.5, f"{trait['name']}:")
                ty = self.get_y()

                desc = trait.get("description", "")[:200]
                if desc:
                    self.set_font("Helvetica", "", 6)
                    self.set_text_color(*C_LIGHT_ACCENT)
                    self.set_xy(x + 2, ty)
                    self.multi_cell(w - 4, 3, desc)
                    ty = self.get_y() + 1

        total_h = max(ty - y + 2, 20)
        self.set_draw_color(*C_LIGHT_BORDER)
        self.set_line_width(0.4)
        self.rect(x, y, w, total_h)
        # Redraw title
        self.set_fill_color(*C_LIGHT_HEADER)
        self.rect(x, y, w, 6, "F")
        self.set_draw_color(*C_LIGHT_BORDER)
        self.rect(x, y, w, 6)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*C_LIGHT_BG)
        self.set_xy(x, y)
        self.cell(w, 6, "  SPECIES TRAITS", align="L")
        return y + total_h

    def _draw_feats(self, x, y, w):
        """Draw feats box."""
        c = self.c
        inner = self._box(x, y, w, 6, "FEATS")
        ty = inner + 2

        feats_to_show = []
        if c.feat:
            feat_name = c.background.get("feat", c.feat.get("name", "")) if c.background else c.feat.get("name", "")
            feats_to_show.append((feat_name, c.feat, "Background"))
        if c.species_origin_feat:
            feats_to_show.append((c.species_origin_feat["name"], c.species_origin_feat, c.species_name))

        for feat_name, feat, source in feats_to_show:
            self.set_font("Helvetica", "B", 7)
            self.set_text_color(*C_LIGHT_FG)
            self.set_xy(x + 2, ty)
            self.cell(w - 4, 3.5, f"{feat_name}")
            ty += 3.5

            self.set_font("Helvetica", "I", 5.5)
            self.set_text_color(*C_LIGHT_ACCENT)
            self.set_xy(x + 2, ty)
            self.cell(w - 4, 3, f"from {source}")
            ty += 4

            for benefit in feat.get("benefits", [])[:3]:
                desc = benefit.get("description", "")[:150]
                if desc:
                    self.set_font("Helvetica", "", 6)
                    self.set_text_color(*C_LIGHT_FG)
                    self.set_xy(x + 2, ty)
                    self.multi_cell(w - 4, 3, f"{benefit.get('name', '')}: {desc}")
                    ty = self.get_y() + 1

            ty += 1

        total_h = max(ty - y + 2, 20)
        self.set_draw_color(*C_LIGHT_BORDER)
        self.set_line_width(0.4)
        self.rect(x, y, w, total_h)
        # Redraw title
        self.set_fill_color(*C_LIGHT_HEADER)
        self.rect(x, y, w, 6, "F")
        self.set_draw_color(*C_LIGHT_BORDER)
        self.rect(x, y, w, 6)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*C_LIGHT_BG)
        self.set_xy(x, y)
        self.cell(w, 6, "  FEATS", align="L")
        return y + total_h

    def _draw_proficiencies(self, x, y, w):
        """Draw equipment training & proficiencies at the bottom."""
        c = self.c
        if y + 30 > PAGE_H - MARGIN:
            return  # no space

        inner = self._box(x, y, w, 6, "EQUIPMENT TRAINING & PROFICIENCIES")
        ty = inner + 2

        # Armor training
        armor_types = []
        if c.character_class:
            for at in c.character_class.get("armor_proficiencies", []):
                armor_types.append(at)
        armor_text = ", ".join(armor_types) if armor_types else "None"

        # Weapons
        weapon_profs = []
        if c.character_class:
            for wp in c.character_class.get("weapon_proficiencies", []):
                weapon_profs.append(wp)
        weapon_text = ", ".join(weapon_profs) if weapon_profs else "None"

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

        entries = [
            ("ARMOR TRAINING", armor_text),
            ("WEAPONS", weapon_text),
            ("TOOLS", tool_text),
        ]

        self.set_text_color(*C_LIGHT_FG)
        for label, val in entries:
            self.set_font("Helvetica", "B", 6.5)
            self.set_xy(x + 2, ty)
            self.cell(30, 3.5, label)
            self.set_font("Helvetica", "", 7)
            self.set_xy(x + 32, ty)
            self.cell(w - 34, 3.5, val)
            ty += 5

        # Equipment list
        equip_items = []
        if c.character_class:
            for opt in c.character_class.get("starting_equipment", []):
                if opt["option"] == c.equipment_choice_class:
                    equip_items.append(opt["items"][:150])
        if c.background:
            for opt in c.background.get("equipment", []):
                if opt["option"] == c.equipment_choice_background:
                    equip_items.append(opt["items"][:150])

        if equip_items:
            self.set_font("Helvetica", "B", 6.5)
            self.set_xy(x + 2, ty)
            self.cell(30, 3.5, "EQUIPMENT")
            ty += 4
            self.set_font("Helvetica", "", 6.5)
            for item in equip_items:
                self.set_xy(x + 4, ty)
                self.multi_cell(w - 8, 3, item)
                ty = self.get_y() + 1

        total_h = ty - y + 2
        self.set_draw_color(*C_LIGHT_BORDER)
        self.set_line_width(0.4)
        self.rect(x, y, w, total_h)
        # Redraw title
        self.set_fill_color(*C_LIGHT_HEADER)
        self.rect(x, y, w, 6, "F")
        self.set_draw_color(*C_LIGHT_BORDER)
        self.rect(x, y, w, 6)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*C_LIGHT_BG)
        self.set_xy(x, y)
        self.cell(w, 6, "  EQUIPMENT TRAINING & PROFICIENCIES", align="L")

    # ── Page 2: Spellcasting ─────────────────────────────────

    def _draw_page_2(self):
        c = self.c
        x0 = MARGIN
        y = MARGIN

        if not c.character_class:
            return

        # Spellcasting ability
        cast_ability = c.character_class.get("spellcasting_ability", "Intelligence")
        cast_mod = c.ability_scores.modifier(cast_ability)
        save_dc = 8 + c.proficiency_bonus + cast_mod
        atk_bonus = c.proficiency_bonus + cast_mod

        # ─── Spellcasting info header ───
        info_w = 60
        inner = self._box(x0, y, info_w, 6, "SPELLCASTING")
        ty = inner + 2

        rows = [
            ("SPELLCASTING ABILITY", cast_ability, 9),
            ("SPELLCASTING MODIFIER", self._modifier_str(cast_mod), 12),
            ("SPELL SAVE DC", str(save_dc), 12),
            ("SPELL ATTACK BONUS", self._modifier_str(atk_bonus), 12),
        ]

        for label, val, font_size in rows:
            self.set_font("Helvetica", "B", font_size)
            self.set_text_color(*C_LIGHT_FG)
            self.set_xy(x0 + 2, ty)
            self.cell(20, 6, val, align="C")
            self.set_font("Helvetica", "", 6.5)
            self.set_text_color(*C_LIGHT_ACCENT)
            self.set_xy(x0 + 23, ty + 1)
            self.cell(35, 4, label)
            ty += 7

        info_h = ty - y + 2
        self.set_draw_color(*C_LIGHT_BORDER)
        self.rect(x0, y, info_w, info_h)
        # Redraw title
        self.set_fill_color(*C_LIGHT_HEADER)
        self.rect(x0, y, info_w, 6, "F")
        self.set_draw_color(*C_LIGHT_BORDER)
        self.rect(x0, y, info_w, 6)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*C_LIGHT_BG)
        self.set_xy(x0, y)
        self.cell(info_w, 6, "  SPELLCASTING", align="L")

        # ─── Spell Slots ───
        slots_x = x0 + info_w + 4
        slots_w = PAGE_W - MARGIN * 2 - info_w - 4
        inner = self._box(slots_x, y, slots_w, 6, "SPELL SLOTS")
        sy = inner + 2

        spell_slots = c.character_class.get("spell_slots", {})
        # Keys might be "1st", "2nd", "3rd", "4th"... or "1", "2"...
        slot_key_map = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th",
                        6: "6th", 7: "7th", 8: "8th", 9: "9th"}
        self.set_font("Helvetica", "", 7)
        slot_col_w = slots_w / 3
        for i, level in enumerate(range(1, 10)):
            col = i % 3
            row = i // 3
            sx = slots_x + col * slot_col_w + 2
            ssy = sy + row * 6
            total = (spell_slots.get(slot_key_map[level])
                     or spell_slots.get(str(level))
                     or 0)

            self.set_text_color(*C_LIGHT_ACCENT)
            self.set_font("Helvetica", "", 6)
            self.set_xy(sx, ssy)
            self.cell(18, 4, f"Level {level}")
            self.set_text_color(*C_LIGHT_FG)
            self.set_font("Helvetica", "B", 8)
            self.set_xy(sx + 18, ssy)
            self.cell(10, 4, str(total) if total else "--", align="C")

        slots_h = info_h  # match height
        self.set_draw_color(*C_LIGHT_BORDER)
        self.rect(slots_x, y, slots_w, slots_h)
        self.set_fill_color(*C_LIGHT_HEADER)
        self.rect(slots_x, y, slots_w, 6, "F")
        self.set_draw_color(*C_LIGHT_BORDER)
        self.rect(slots_x, y, slots_w, 6)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*C_LIGHT_BG)
        self.set_xy(slots_x, y)
        self.cell(slots_w, 6, "  SPELL SLOTS", align="L")

        y += max(info_h, slots_h) + 3

        # ─── Cantrips & Prepared Spells table ───
        table_w = PAGE_W - MARGIN * 2
        inner = self._box(x0, y, table_w, 6, "CANTRIPS & PREPARED SPELLS")
        ty = inner + 1

        col_widths = [12, table_w * 0.28, table_w * 0.17, 18, table_w * 0.2, table_w - 12 - table_w * 0.28 - table_w * 0.17 - 18 - table_w * 0.2]
        headers = ["Level", "Name", "Casting Time", "Range", "C / R / M", "Notes"]

        self.set_font("Helvetica", "B", 6)
        self.set_text_color(*C_LIGHT_ACCENT)
        cx = x0 + 1
        for i, hdr in enumerate(headers):
            self.set_xy(cx, ty)
            self.cell(col_widths[i], 4, hdr)
            cx += col_widths[i]
        ty += 5

        self.set_draw_color(*C_LIGHT_BORDER)
        self.set_line_width(0.2)
        self.line(x0 + 1, ty - 0.5, x0 + table_w - 1, ty - 0.5)

        # Fill in known spells
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(*C_LIGHT_FG)

        # We need spell data — load it
        all_spells = self._get_spell_data()

        for spell_name in c.selected_cantrips:
            spell = all_spells.get(spell_name, {})
            self._draw_spell_row(x0, ty, col_widths, 0, spell_name, spell)
            ty += 5

        for spell_name in c.selected_spells:
            spell = all_spells.get(spell_name, {})
            level = spell.get("level", 1)
            self._draw_spell_row(x0, ty, col_widths, level, spell_name, spell)
            ty += 5

        # Empty rows for user to fill
        remaining = max(0, 20 - len(c.selected_cantrips) - len(c.selected_spells))
        for _ in range(remaining):
            self.set_draw_color(200, 195, 185)
            self.line(x0 + 1, ty + 4, x0 + table_w - 1, ty + 4)
            ty += 5

        total_h = ty - y + 2
        self.set_draw_color(*C_LIGHT_BORDER)
        self.set_line_width(0.4)
        self.rect(x0, y, table_w, total_h)
        # Redraw title
        self.set_fill_color(*C_LIGHT_HEADER)
        self.rect(x0, y, table_w, 6, "F")
        self.set_draw_color(*C_LIGHT_BORDER)
        self.rect(x0, y, table_w, 6)
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*C_LIGHT_BG)
        self.set_xy(x0, y)
        self.cell(table_w, 6, "  CANTRIPS & PREPARED SPELLS", align="L")

    def _draw_spell_row(self, x, y, col_widths, level, name, spell):
        """Draw one row in the spell table."""
        cx = x + 1
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(*C_LIGHT_FG)

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
            self.cell(col_widths[i], 5, val[:30])
            cx += col_widths[i]

    def _spell_flags(self, spell):
        """Get C/R/M flags for a spell."""
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
        """Get component abbreviation (V, S, M)."""
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
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
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
