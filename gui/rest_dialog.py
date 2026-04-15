"""Dialog for taking a Short or Long Rest, allowing feature/spell swaps and hit dice spending."""

from __future__ import annotations

import json
import os
import random
import tkinter as tk
from tkinter import ttk

from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import (
    CardFrame,
    GradientHeader,
    HPBar,
    SectionHeader,
    ScrollableFrame,
    AlertDialog,
    center_dialog_over_parent,
    configure_modal_dialog,
)
from gui.spell_swap_panel import SpellSwapPanel, MultiSpellSwapPanel
from models.item_effects import get_effective_modifier
from models.skill_utils import (
    ZHENTARIM_TACTICS,
    get_feat_expertise_skill,
    get_selectable_expertise_grants,
    set_feat_expertise_skill,
)
from models.feature_resource_utils import (
    get_restorable_feature_resources,
    restore_feature_resources,
)
from models.spell_grant_utils import get_spendable_free_cast_resources, restore_free_casts

# Load class choices data (same file as level_up_wizard)
_CHOICES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "class_choices.json")
try:
    with open(_CHOICES_PATH, encoding="utf-8") as _f:
        _CLASS_CHOICES: dict = json.load(_f)
except Exception:
    _CLASS_CHOICES = {}

# Per-class Long Rest spell swap rules
# cantrip_swaps: how many cantrips can be swapped (0 = none)
# spell_swap: "all" = full re-preparation, "one" = single swap only
_REST_SPELL_SWAP: dict[str, dict] = {
    "artificer": {"cantrip_swaps": 1, "spell_swap": "all"},
    "cleric":    {"cantrip_swaps": 1, "spell_swap": "all"},
    "druid":     {"cantrip_swaps": 0, "spell_swap": "all"},
    "paladin":   {"cantrip_swaps": 0, "spell_swap": "one"},
    "ranger":    {"cantrip_swaps": 0, "spell_swap": "one"},
    "wizard":    {"cantrip_swaps": 1, "spell_swap": "all"},
}

# Kept for backwards compat in helper functions
_PREPARED_CASTER_CLASSES = set(_REST_SPELL_SWAP.keys())
CARD_CHECK_STYLE = "Card.TCheckbutton"


def _get_all_known_choices(character, key: str) -> list[str]:
    """Aggregate all choices the character has selected for a given class/subclass key."""
    result: list[str] = []
    for cl in character.class_levels:
        if cl.class_slug == key or cl.subclass_slug == key:
            result.extend(cl.new_choices)
            if cl.replaced_choice and cl.replaced_choice in result:
                result.remove(cl.replaced_choice)
    return result


def _get_all_known_sub_selections(character, key: str) -> dict[str, str]:
    """Aggregate sub-selections for class choices (e.g. 'Weapon +1' -> 'Longsword')."""
    result: dict[str, str] = {}
    for cl in character.class_levels:
        if cl.class_slug == key or cl.subclass_slug == key:
            result.update(cl.choice_sub_selections)
    return result


def _has_swappable_features(character, rest_type: str) -> bool:
    """Return True if the character has any features swappable on this rest type."""
    all_keys = set()
    for cl in character.class_levels:
        all_keys.add(cl.class_slug)
        if cl.subclass_slug:
            all_keys.add(cl.subclass_slug)

    for key in all_keys:
        config = _CLASS_CHOICES.get(key)
        if not config or not config.get("can_swap_on_rest"):
            continue
        swap_type = config.get("swap_rest_type", "long")
        if rest_type == "short" and swap_type not in ("short", "short_or_long"):
            continue
        known = _get_all_known_choices(character, key)
        if known:
            return True
    return False


def _is_prepared_caster(character) -> bool:
    """Return True if the character has at least one prepared-spellcasting class."""
    for cl in character.class_levels:
        if cl.class_slug in _PREPARED_CASTER_CLASSES:
            return True
    return False


def can_short_rest(character) -> bool:
    """Return True — every character can spend hit dice on a Short Rest."""
    return True


def _can_swap_cantrips_on_rest(character) -> bool:
    """Return True if the character can swap cantrips on Long Rest."""
    for cl in character.class_levels:
        cfg = _REST_SPELL_SWAP.get(cl.class_slug)
        if cfg and cfg.get("cantrip_swaps", 0) > 0 and character.selected_cantrips:
            return True
    return False


def _spell_swap_mode(character) -> str | None:
    """Return 'all', 'one', or None based on character's classes."""
    mode = None
    for cl in character.class_levels:
        cfg = _REST_SPELL_SWAP.get(cl.class_slug)
        if cfg and cfg.get("spell_swap"):
            if cfg["spell_swap"] == "all":
                return "all"  # "all" wins over "one" in multiclass
            mode = cfg["spell_swap"]
    return mode


def can_long_rest(character) -> bool:
    """Return True — every character benefits from a Long Rest (HP restoration)."""
    return True


def _restorable_free_cast_resources(character, game_data, rest_type: str) -> list[dict]:
    resources = get_spendable_free_cast_resources(character, game_data)
    if rest_type == "short":
        return [
            resource
            for resource in resources
            if resource.get("refresh_type") == "short_or_long"
        ]
    if rest_type == "long":
        return [
            resource
            for resource in resources
            if resource.get("refresh_type") in {"long", "short_or_long"}
        ]
    return []


def _get_feature_keys(character, rest_type: str) -> list[tuple[str, dict, list[str]]]:
    """Return swappable feature keys for a given rest type."""
    all_keys: set[str] = set()
    for cl in character.class_levels:
        all_keys.add(cl.class_slug)
        if cl.subclass_slug:
            all_keys.add(cl.subclass_slug)

    feature_keys = []
    for key in sorted(all_keys):
        config = _CLASS_CHOICES.get(key)
        if not config or not config.get("can_swap_on_rest"):
            continue
        swap_type = config.get("swap_rest_type", "long")
        if rest_type == "short" and swap_type not in ("short", "short_or_long"):
            continue
        known = _get_all_known_choices(character, key)
        if known:
            feature_keys.append((key, config, known))
    return feature_keys


def _is_warlock_pact_caster(character) -> bool:
    """Return True if the character has levels in Warlock (Pact Magic)."""
    for cl in character.class_levels:
        if cl.class_slug == "warlock":
            return True
    return False


def _has_arcane_recovery(character) -> bool:
    """Return True if the character has Arcane/Natural Recovery (Wizard or Land Druid)."""
    for cl in character.class_levels:
        if cl.class_slug == "wizard":
            return True
        # Note: 2024 Land Druid has 'Natural Recovery'
        if cl.class_slug == "druid" and cl.subclass_slug == "circle-of-the-land":
            return True
    return False


# ══════════════════════════════════════════════════════════════════════
# RestDialog
# ══════════════════════════════════════════════════════════════════════

class RestDialog(tk.Toplevel):
    """Modal dialog for taking a rest and optionally swapping features/spells."""

    def __init__(self, parent, character, game_data, rest_type: str, on_changed=None):
        """
        rest_type: "short" or "long"
        on_changed: callback called if any changes were saved
        """
        super().__init__(parent)
        self.character = character
        self.data = game_data
        self.rest_type = rest_type
        self.on_changed = on_changed

        title = "Short Rest" if rest_type == "short" else "Long Rest"
        self.title(title)
        self.resizable(True, True)
        self.configure(bg=COLORS["bg"])

        configure_modal_dialog(self, parent)

        # State: maps choice_key -> {new_choice: str, old_choice: str}
        self._swaps: dict[str, dict] = {}
        # State: spell swap panels (set during build)
        self._cantrip_panel: SpellSwapPanel | None = None
        self._spell_panel: SpellSwapPanel | None = None
        self._multi_spell_panel: MultiSpellSwapPanel | None = None
        self._spell_swap_mode: str | None = None  # "all" or "one"

        # Multi-step navigation state
        self._current_step = 1
        self._total_steps = 1
        self._step_frames: list[ttk.Frame] = []  # ordered list of step frames
        self._step_ids: list[str] = []
        self._next_btn: ttk.Button | None = None
        self._back_btn: ttk.Button | None = None
        self._finish_btn: ttk.Button | None = None

        # Hit dice spending state (short rest)
        self._hd_spend_vars: dict[str, tk.IntVar] = {}  # class_slug -> IntVar count
        self._hd_roll_mode: tk.StringVar = tk.StringVar(value="auto")  # "auto" or "manual"
        self._hd_manual_var: tk.StringVar = tk.StringVar(value="")
        self._hd_manual_hint: ttk.Label | None = None
        self._hd_summary_label: ttk.Label | None = None
        self._has_hit_dice: bool = False
        self._zhentarim_expertise_vars: dict[str, tk.BooleanVar] = {}
        self._zhentarim_expertise_options: list[str] = []

        # Recovery state (short rest)
        self._recovery_vars: dict[str, tk.IntVar] = {}  # slot_level -> IntVar
        self._recovery_max_points = 0
        self._recovery_current_points = tk.IntVar(value=0)

        if rest_type == "short":
            self._build_short_rest_ui(title)
        else:
            self._build_long_rest_ui(title)

        # Size the dialog to fit the largest step without cutting off content.
        # Temporarily show every step so Tk can compute its natural size,
        # then pick the maximum required width and height across all steps.
        self.update_idletasks()

        max_w, max_h = 0, 0
        for frame in self._step_frames:
            frame.grid(row=1, column=0, sticky="nsew")
            frame.update_idletasks()
            max_w = max(max_w, frame.winfo_reqwidth())
            max_h = max(max_h, frame.winfo_reqheight())
            frame.grid_forget()

        # Re-show step 1 after measurement
        self._show_rest_step(1)

        # Account for header (row 0) and footer nav bar (row 99)
        header_h = 0
        for child in self.grid_slaves(row=0):
            child.update_idletasks()
            header_h = max(header_h, child.winfo_reqheight())
        footer_h = 0
        for child in self.grid_slaves(row=99):
            child.update_idletasks()
            footer_h = max(footer_h, child.winfo_reqheight())

        # Add padding for chrome
        width = max_w + SPACING["lg"] * 2
        height = max_h + header_h + footer_h + SPACING["lg"] * 2

        # Clamp to screen bounds (leave some margin); minimum 600 wide so
        # the bottom bar with buttons and progress indicator isn't squeezed.
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = max(600, min(width, int(screen_w * 0.85)))
        height = max(350, min(height, int(screen_h * 0.85)))

        self.geometry(f"{width}x{height}")
        self.minsize(600, 350)
        center_dialog_over_parent(self, parent)
        self.after_idle(lambda: center_dialog_over_parent(self, parent))

    # ══════════════════════════════════════════════════════════════════
    # Long Rest UI (unchanged logic, refactored slightly)
    # ══════════════════════════════════════════════════════════════════

    def _append_rest_step(self, step_id: str, frame: ttk.Frame):
        self._step_ids.append(step_id)
        self._step_frames.append(frame)

    def _current_step_id(self) -> str:
        idx = self._current_step - 1
        if 0 <= idx < len(self._step_ids):
            return self._step_ids[idx]
        return ""

    def _get_zhentarim_rest_grant(self) -> dict | None:
        for grant in get_selectable_expertise_grants(self.character):
            if grant.get("kind") == "feat" and grant.get("feat_name") == ZHENTARIM_TACTICS:
                return grant
        return None

    def _build_long_rest_ui(self, title: str):
        self.columnconfigure(0, weight=1)

        # Hero header with gradient styling
        header = GradientHeader(self, min_height=56)
        header.grid(row=0, column=0, sticky="ew")

        hero_row = tk.Frame(header.inner, bg=COLORS["bg_hero"])
        hero_row.pack(fill=tk.X, padx=SPACING["card_pad"], pady=(SPACING["lg"], SPACING["lg"]))

        tk.Label(
            hero_row,
            text=title,
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        feature_keys = _get_feature_keys(self.character, "long")
        zhentarim_grant = self._get_zhentarim_rest_grant()

        # Determine sections
        has_cantrip_swap = _can_swap_cantrips_on_rest(self.character)
        self._spell_swap_mode = _spell_swap_mode(self.character)
        has_spells = self._spell_swap_mode is not None and self.character.selected_spells
        has_features = bool(feature_keys)
        has_any_swap = has_features or has_cantrip_swap or has_spells
        use_three_steps = has_cantrip_swap and has_spells

        self.rowconfigure(1, weight=1)

        # Step 1: Info summary (always)
        info_frame = ttk.Frame(self)
        self._build_long_rest_info_step(
            info_frame,
            feature_keys=feature_keys,
            has_cantrip_swap=has_cantrip_swap,
            has_spells=has_spells,
            has_zhentarim_refresh=zhentarim_grant is not None,
        )
        self._append_rest_step("info", info_frame)

        # Build swap steps
        if has_any_swap:
            if use_three_steps:
                # Step 2: features + cantrip swap
                cantrip_step = ttk.Frame(self)
                cantrip_step.columnconfigure(0, weight=1)
                s_row = 0
                if has_features:
                    scroll = ScrollableFrame(cantrip_step, auto_hide_scrollbar=True)
                    scroll.grid(row=s_row, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["xs"])
                    for key, config, known in feature_keys:
                        self._build_feature_section(scroll.inner, key, config, known)
                    s_row += 1
                cantrip_step.rowconfigure(s_row, weight=1)
                cf = ttk.Frame(cantrip_step)
                cf.grid(row=s_row, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["xs"])
                self._build_cantrip_section(cf)
                self._append_rest_step("swap_cantrips", cantrip_step)

                # Step 3: spell swap
                spell_step = ttk.Frame(self)
                spell_step.columnconfigure(0, weight=1)
                spell_step.rowconfigure(0, weight=1)
                sf = ttk.Frame(spell_step)
                sf.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["xs"])
                self._build_spell_section(sf)
                self._append_rest_step("swap_spells", spell_step)
            else:
                # Step 2: all swap sections on one page
                swap_frame = ttk.Frame(self)
                swap_frame.columnconfigure(0, weight=1)
                sf_row = 0
                if has_features:
                    scroll = ScrollableFrame(swap_frame, auto_hide_scrollbar=True)
                    scroll.grid(row=sf_row, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["xs"])
                    for key, config, known in feature_keys:
                        self._build_feature_section(scroll.inner, key, config, known)
                    sf_row += 1
                if has_cantrip_swap:
                    cf = ttk.Frame(swap_frame)
                    cf.grid(row=sf_row, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["xs"])
                    self._build_cantrip_section(cf)
                    sf_row += 1
                if has_spells:
                    swap_frame.rowconfigure(sf_row, weight=1)
                    sf = ttk.Frame(swap_frame)
                    sf.grid(row=sf_row, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["xs"])
                    self._build_spell_section(sf)
                    sf_row += 1
                self._append_rest_step("swap_all", swap_frame)

        if zhentarim_grant:
            zhentarim_frame = ttk.Frame(self)
            self._build_zhentarim_expertise_step(zhentarim_frame, zhentarim_grant)
            self._append_rest_step("zhentarim_expertise", zhentarim_frame)

        self._total_steps = len(self._step_frames)
        self._build_footer()
        self._show_rest_step(1)

    def _build_long_rest_info_step(
        self,
        parent,
        *,
        feature_keys,
        has_cantrip_swap,
        has_spells,
        has_zhentarim_refresh,
    ):
        """Build the long rest info summary with card-based theming."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        scroll = ScrollableFrame(parent, auto_hide_scrollbar=True)
        scroll.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["lg"])
        inner = scroll.inner

        SectionHeader(inner, text="Rest Effects").pack(
            fill=tk.X, padx=0, pady=(0, SPACING["md"])
        )

        effects: list[str] = []

        # HP restoration
        cur = self.character.effective_current_hp
        max_hp = self.character.hit_points
        if cur < max_hp:
            effects.append(f"Hit points restored to full ({cur} \u2192 {max_hp})")
        else:
            effects.append(f"Hit points are already full ({max_hp}/{max_hp})")

        # Temp HP
        if self.character.temp_hit_points > 0:
            effects.append(
                f"Temporary hit points ({self.character.temp_hit_points}) will be lost"
            )

        # Hit dice restoration
        if self.character.spent_hit_dice:
            pool = self.character.hit_dice_pool
            parts = []
            for slug in sorted(pool, key=lambda s: pool[s][2], reverse=True):
                rem, total, die = pool[slug]
                spent = total - rem
                if spent > 0:
                    parts.append(f"{spent}d{die}")
            if parts:
                effects.append(f"All spent hit dice restored ({', '.join(parts)})")

        # Feature swaps
        for _key, config, _known in feature_keys:
            label = config.get("choice_label", "feature")
            effects.append(f"You may swap one {label}")

        # Cantrip swap
        if has_cantrip_swap:
            effects.append("You may swap one cantrip")

        # Spell swap
        if has_spells:
            mode = self._spell_swap_mode or "one"
            if mode == "all":
                effects.append("You may change any number of your prepared spells")
            else:
                effects.append("You may swap one prepared spell")

        # Spell slot restoration
        if self.character.is_caster or _is_warlock_pact_caster(self.character):
            effects.append("All spell slots and pact slots are fully restored")
        if _restorable_free_cast_resources(self.character, self.data, "long"):
            effects.append("All limited free spell uses are fully restored")
        if get_restorable_feature_resources(self.character, self.data, "long"):
            effects.append("All tracked feature uses and pools are fully restored")

        if has_zhentarim_refresh:
            effects.append("You must choose your Zhentarim Tactics Expertise again")

        card = CardFrame(inner, pad=SPACING["lg"])
        card.pack(fill=tk.X, expand=True)
        card_inner = card.inner

        for i, text in enumerate(effects):
            tk.Label(
                card_inner,
                text=f"\u2022  {text}",
                font=FONTS["body"],
                fg=COLORS["fg"],
                bg=COLORS["bg_surface"],
                wraplength=520,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=SPACING["xs"])

    def _build_zhentarim_expertise_step(self, parent, grant: dict):
        """Build the Zhentarim Tactics Expertise reselection step with card theming."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        scroll = ScrollableFrame(parent, auto_hide_scrollbar=True)
        scroll.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["lg"])
        inner = scroll.inner

        SectionHeader(inner, text="Zhentarim Expertise").pack(
            fill=tk.X, padx=0, pady=(0, SPACING["md"])
        )

        card = CardFrame(inner, pad=SPACING["lg"])
        card.pack(fill=tk.X, expand=True)
        card_inner = card.inner

        tk.Label(
            card_inner,
            text=(
                "Zhentarim Tactics lets you choose one proficient skill to gain "
                "Expertise in until your next Long Rest."
            ),
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, SPACING["sm"]))

        previous = get_feat_expertise_skill(self.character, ZHENTARIM_TACTICS)
        if previous:
            tk.Label(
                card_inner,
                text=f"Previous selection: {previous}",
                font=FONTS["body_small"],
                fg=COLORS["accent"],
                bg=COLORS["bg_surface"],
            ).pack(anchor=tk.W, pady=(0, SPACING["sm"]))

        slot = grant["slots"][0] if grant.get("slots") else {"options": [], "current": ""}
        self._zhentarim_expertise_options = list(slot["options"])
        self._zhentarim_expertise_vars = {}

        if not self._zhentarim_expertise_options:
            tk.Label(
                card_inner,
                text="No eligible proficient skills are currently available.",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
                wraplength=520,
            ).pack(anchor=tk.W, pady=SPACING["sm"])
        else:
            tk.Label(
                card_inner,
                text="Select New Expertise Skill",
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg"],
                bg=COLORS["bg_surface"],
            ).pack(anchor=tk.W, pady=(SPACING["sm"], SPACING["xs"]))

            options_frame = tk.Frame(card_inner, bg=COLORS["bg_surface"])
            options_frame.pack(fill=tk.X, pady=SPACING["xs"])

            for idx, skill_name in enumerate(self._zhentarim_expertise_options):
                var = tk.BooleanVar(value=False)
                self._zhentarim_expertise_vars[skill_name] = var
                cb = ttk.Checkbutton(
                    options_frame,
                    text=skill_name,
                    variable=var,
                    style=CARD_CHECK_STYLE,
                    command=lambda s=skill_name, v=var: self._on_zhentarim_expertise_toggle(
                        s, v
                    ),
                )
                col = idx % 3
                row = idx // 3
                cb.grid(row=row, column=col, sticky="w", padx=8, pady=1)

            tk.Label(
                card_inner,
                text="Choose one skill to continue. You may keep the same one or pick a new one.",
                font=FONTS["body_small"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
                wraplength=520,
            ).pack(anchor=tk.W, pady=(SPACING["sm"], 0))

    def _selected_zhentarim_expertise(self) -> str:
        for skill_name, var in self._zhentarim_expertise_vars.items():
            if var.get():
                return skill_name
        return ""

    def _on_zhentarim_expertise_toggle(self, skill_name: str, var: tk.BooleanVar):
        if not var.get():
            return

        for other_skill, other_var in self._zhentarim_expertise_vars.items():
            if other_skill != skill_name and other_var.get():
                other_var.set(False)

    # ══════════════════════════════════════════════════════════════════
    # Short Rest UI
    # ══════════════════════════════════════════════════════════════════

    def _build_short_rest_ui(self, title: str):
        self.columnconfigure(0, weight=1)

        # Hero header with gradient styling
        header = GradientHeader(self, min_height=56)
        header.grid(row=0, column=0, sticky="ew")

        hero_row = tk.Frame(header.inner, bg=COLORS["bg_hero"])
        hero_row.pack(fill=tk.X, padx=SPACING["card_pad"], pady=(SPACING["lg"], SPACING["lg"]))

        tk.Label(
            hero_row,
            text=title,
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        feature_keys = _get_feature_keys(self.character, "short")
        has_features = bool(feature_keys)
        pool = self.character.hit_dice_pool
        self._has_hit_dice = self.character.total_hit_dice_remaining > 0

        self.rowconfigure(1, weight=1)

        # Step 1: Info summary
        info_frame = ttk.Frame(self)
        self._build_short_rest_info_step(info_frame, feature_keys=feature_keys)
        self._append_rest_step("info", info_frame)

        # Step 2: Hit dice spending (if any remaining)
        if self._has_hit_dice:
            hd_frame = ttk.Frame(self)
            self._build_hit_dice_step(hd_frame)
            self._append_rest_step("hit_dice", hd_frame)

        # Step 3 (or 2): Feature swaps (if any)
        if has_features:
            swap_frame = ttk.Frame(self)
            swap_frame.columnconfigure(0, weight=1)
            scroll = ScrollableFrame(swap_frame, auto_hide_scrollbar=True)
            scroll.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["xs"])
            swap_frame.rowconfigure(0, weight=1)
            for key, config, known in feature_keys:
                self._build_feature_section(scroll.inner, key, config, known)
            self._append_rest_step("swap_features", swap_frame)

        # Step 4 (or 3): Arcane/Natural Recovery
        if _has_arcane_recovery(self.character) and not self.character.arcane_recovery_used:
            recovery_frame = ttk.Frame(self)
            self._build_recovery_step(recovery_frame)
            self._append_rest_step("recovery", recovery_frame)

        self._total_steps = len(self._step_frames)
        self._build_footer()
        self._show_rest_step(1)

    def _build_short_rest_info_step(self, parent, *, feature_keys):
        """Build the short rest info summary with card-based theming."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        scroll = ScrollableFrame(parent, auto_hide_scrollbar=True)
        scroll.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["lg"])
        inner = scroll.inner

        SectionHeader(inner, text="Rest Effects").pack(
            fill=tk.X, padx=0, pady=(0, SPACING["md"])
        )

        effects: list[str] = []

        # Hit dice available
        pool = self.character.hit_dice_pool
        for slug in sorted(pool, key=lambda s: pool[s][2], reverse=True):
            rem, total, die = pool[slug]
            class_name = slug.replace("-", " ").title()
            effects.append(f"You have {rem}/{total} d{die} hit dice remaining ({class_name})")

        if self.character.total_hit_dice_remaining > 0:
            con_mod = get_effective_modifier(self.character, "Constitution")
            sign = "+" if con_mod >= 0 else ""
            effects.append(f"You may spend hit dice to recover HP (each die {sign}{con_mod} CON)")
        else:
            effects.append("You have no hit dice left to spend")

        # Feature swaps
        for _key, config, _known in feature_keys:
            label = config.get("choice_label", "feature")
            effects.append(f"You may swap one {label}")

        short_rest_free_casts = _restorable_free_cast_resources(self.character, self.data, "short")
        short_rest_features = get_restorable_feature_resources(self.character, self.data, "short")
        if not feature_keys and self.character.total_hit_dice_remaining == 0:
            if (
                not _is_warlock_pact_caster(self.character)
                and not _has_arcane_recovery(self.character)
                and not short_rest_free_casts
                and not short_rest_features
            ):
                effects.append("There is nothing else to do on this rest")

        # Spell slots (Warlock)
        if _is_warlock_pact_caster(self.character):
            effects.append("All pact slots are fully restored")
        if short_rest_free_casts:
            effects.append("Limited free spell uses that refresh on a Short Rest are restored")
        if short_rest_features:
            if any(
                resource.get("refresh_type") == "partial_short_full_long"
                for resource in short_rest_features
            ):
                effects.append("Tracked feature uses refresh, including partial Short Rest recoveries")
            else:
                effects.append("Tracked feature uses and pools that refresh on a Short Rest are restored")

        # Arcane Recovery
        if _has_arcane_recovery(self.character):
            if self.character.arcane_recovery_used:
                effects.append("Arcane/Natural Recovery has already been used today")
            else:
                effects.append("You may use Arcane/Natural Recovery to restore spell slots")

        card = CardFrame(inner, pad=SPACING["lg"])
        card.pack(fill=tk.X, expand=True)
        card_inner = card.inner

        for i, text in enumerate(effects):
            tk.Label(
                card_inner,
                text=f"\u2022  {text}",
                font=FONTS["body"],
                fg=COLORS["fg"],
                bg=COLORS["bg_surface"],
                wraplength=520,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=SPACING["xs"])

    def _build_hit_dice_step(self, parent):
        """Build the hit dice spending step for short rest with card theming."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        scroll = ScrollableFrame(parent, auto_hide_scrollbar=True)
        scroll.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["lg"])
        inner = scroll.inner

        SectionHeader(inner, text="Spend Hit Dice").pack(
            fill=tk.X, padx=0, pady=(0, SPACING["md"])
        )

        con_mod = get_effective_modifier(self.character, "Constitution")
        sign = "+" if con_mod >= 0 else ""

        # Per-class die selectors card
        pool = self.character.hit_dice_pool
        dice_card = CardFrame(inner, pad=SPACING["lg"])
        dice_card.pack(fill=tk.X, pady=(0, SPACING["md"]))
        dice_inner = dice_card.inner

        tk.Label(
            dice_inner,
            text=f"Choose how many hit dice to spend. Each die heals: roll {sign}{con_mod} CON (minimum 0 HP per die).",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, SPACING["sm"]))

        for slug in sorted(pool, key=lambda s: pool[s][2], reverse=True):
            rem, total, die = pool[slug]
            if rem == 0:
                continue

            class_name = slug.replace("-", " ").title()
            var = tk.IntVar(value=0)
            self._hd_spend_vars[slug] = var

            die_row = tk.Frame(dice_inner, bg=COLORS["bg_surface"])
            die_row.pack(fill=tk.X, pady=SPACING["xs"])

            tk.Label(
                die_row, text=f"d{die} ({class_name}):",
                font=FONTS["body"], fg=COLORS["fg"],
                bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT, padx=(0, SPACING["sm"]))

            # Spinbox for count selection
            spin = ttk.Spinbox(
                die_row, from_=0, to=rem, textvariable=var,
                width=4, command=self._update_hd_summary,
            )
            spin.pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
            # Also update on keyboard input
            var.trace_add("write", lambda *_: self._update_hd_summary())

            tk.Label(
                die_row, text=f"(max {rem})",
                font=FONTS["body_small"], fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT)

        # Summary label
        self._hd_summary_label = tk.Label(
            dice_inner,
            text="No dice selected",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        )
        self._hd_summary_label.pack(anchor=tk.W, pady=(SPACING["sm"], 0))

        # Roll mode selection card
        mode_card = CardFrame(inner, pad=SPACING["lg"])
        mode_card.pack(fill=tk.X)
        mode_inner = mode_card.inner

        tk.Label(
            mode_inner,
            text="How to roll",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(anchor=tk.W, pady=(0, SPACING["sm"]))

        ttk.Radiobutton(
            mode_inner,
            text="Roll for me (app rolls the dice)",
            variable=self._hd_roll_mode, value="auto",
            command=self._update_manual_entry_state,
            style="Card.TRadiobutton",
        ).pack(anchor=tk.W, pady=SPACING["xs"])

        manual_row = tk.Frame(mode_inner, bg=COLORS["bg_surface"])
        manual_row.pack(fill=tk.X, pady=SPACING["xs"])

        ttk.Radiobutton(
            manual_row,
            text="I rolled myself, total rolled:",
            variable=self._hd_roll_mode, value="manual",
            command=self._update_manual_entry_state,
            style="Card.TRadiobutton",
        ).pack(side=tk.LEFT)

        self._hd_manual_entry = ttk.Entry(
            manual_row, textvariable=self._hd_manual_var, width=6, state="disabled",
        )
        self._hd_manual_entry.pack(side=tk.LEFT, padx=(SPACING["xs"], SPACING["xs"]))

        self._hd_manual_hint = tk.Label(
            manual_row,
            text="",
            font=FONTS["body_small"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        )
        self._hd_manual_hint.pack(side=tk.LEFT)
        self._hd_manual_var.trace_add("write", lambda *_: self._update_manual_hint())

    def _update_hd_summary(self):
        """Update the hit dice summary text."""
        parts = []
        pool = self.character.hit_dice_pool
        total_count = 0
        for slug, var in self._hd_spend_vars.items():
            try:
                count = var.get()
            except tk.TclError:
                count = 0
            if count > 0:
                _, _, die = pool[slug]
                parts.append(f"{count}d{die}")
                total_count += count

        if self._hd_summary_label:
            if parts:
                self._hd_summary_label.config(
                    text=f"Spending: {' + '.join(parts)} ({total_count} dice total)",
                    fg=COLORS["fg"],
                )
            else:
                self._hd_summary_label.config(
                    text="No dice selected",
                    fg=COLORS["fg_dim"],
                )

        self._update_manual_hint()

    def _update_manual_entry_state(self):
        """Enable/disable manual entry based on roll mode."""
        if self._hd_roll_mode.get() == "manual":
            self._hd_manual_entry.config(state="normal")
        else:
            self._hd_manual_entry.config(state="disabled")
        self._update_manual_hint()

    def _update_manual_hint(self):
        """Update the manual entry hint with CON bonus calculation."""
        if not self._hd_manual_hint:
            return
        if self._hd_roll_mode.get() != "manual":
            self._hd_manual_hint.config(text="")
            return

        con_mod = get_effective_modifier(self.character, "Constitution")
        total_dice = sum(
            v.get() for v in self._hd_spend_vars.values()
            if isinstance(v.get(), int)
        )
        con_total = total_dice * con_mod

        val = self._hd_manual_var.get().strip()
        try:
            rolled = int(val)
            healed = max(0, rolled + con_total)
            sign = "+" if con_total >= 0 else ""
            self._hd_manual_hint.config(
                text=f" {sign}{con_total} CON = {healed} HP"
            )
        except ValueError:
            if con_total != 0:
                sign = "+" if con_total >= 0 else ""
                self._hd_manual_hint.config(text=f" {sign}{con_total} CON = ? HP")
            else:
                self._hd_manual_hint.config(text="")

    # ══════════════════════════════════════════════════════════════════
    # Footer & Step Navigation (shared)
    # ══════════════════════════════════════════════════════════════════

    def _build_footer(self):
        nav_bar = tk.Frame(
            self,
            bg=COLORS["bg_surface"],
            highlightbackground=COLORS["border_subtle"],
            highlightcolor=COLORS["border_subtle"],
            highlightthickness=1,
        )
        nav_bar.grid(row=99, column=0, sticky="ew")

        nav_inner = tk.Frame(nav_bar, bg=COLORS["bg_surface"])
        nav_inner.pack(fill=tk.X, padx=SPACING["lg"], pady=10)

        # Left section: Cancel / Back
        left_frame = tk.Frame(nav_inner, bg=COLORS["bg_surface"])
        left_frame.pack(side=tk.LEFT)

        self._cancel_btn = ttk.Button(
            left_frame, text="Cancel", command=self.destroy,
        )
        self._back_btn = ttk.Button(
            left_frame, text="\u25C0  Back", command=self._go_back,
        )
        self._cancel_btn.pack(side=tk.LEFT)

        # Center section: Step counter + progress bar
        center_frame = tk.Frame(nav_inner, bg=COLORS["bg_surface"])
        center_frame.pack(side=tk.LEFT, expand=True)

        center_inner = tk.Frame(center_frame, bg=COLORS["bg_surface"])
        center_inner.pack()

        self._step_label = tk.Label(
            center_inner,
            text=f"Step 1 of {self._total_steps}",
            font=FONTS["step_counter"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        )
        self._step_label.pack(side=tk.LEFT, padx=(0, SPACING["md"]))

        self._progress_bar = HPBar(center_inner, width=160, height=6)
        self._progress_bar.pack(side=tk.LEFT)

        # Right section: Next / Finish
        right_frame = tk.Frame(nav_inner, bg=COLORS["bg_surface"])
        right_frame.pack(side=tk.RIGHT)

        self._next_btn = ttk.Button(
            right_frame, text="Next  \u25B6", command=self._go_next,
        )
        self._finish_btn = ttk.Button(
            right_frame, text="Finish Rest", style="Accent.TButton",
            command=self._on_confirm,
        )

    def _build_recovery_step(self, parent):
        """Build the manual spell slot recovery step (Arcane/Natural Recovery) with card theming."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        scroll = ScrollableFrame(parent, auto_hide_scrollbar=True)
        scroll.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["lg"])
        inner = scroll.inner

        SectionHeader(inner, text="Arcane / Natural Recovery").pack(
            fill=tk.X, padx=0, pady=(0, SPACING["md"])
        )

        # Calculate max points (half level rounded up)
        wizard_lvl = self.character.class_level_in("wizard")
        druid_lvl = self.character.class_level_in("druid") if self.character.current_subclass == "circle-of-the-land" else 0
        # In 2024, it's half your level in that class
        self._recovery_max_points = (max(wizard_lvl, druid_lvl) + 1) // 2

        card = CardFrame(inner, pad=SPACING["lg"])
        card.pack(fill=tk.X, expand=True)
        card_inner = card.inner

        tk.Label(
            card_inner,
            text=f"You can recover spell slots with a combined level up to {self._recovery_max_points}. "
                 "None of the slots can be level 6 or higher.",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, SPACING["md"]))

        # List spent slots that can be recovered
        slots_frame = tk.Frame(card_inner, bg=COLORS["bg_surface"])
        slots_frame.pack(fill=tk.X)

        row_i = 0
        for lvl_str, spent in sorted(self.character.used_spell_slots.items(), key=lambda x: int(x[0])):
            lvl = int(lvl_str)
            if lvl >= 6 or spent <= 0:
                continue

            var = tk.IntVar(value=0)
            self._recovery_vars[lvl_str] = var

            s_row = tk.Frame(slots_frame, bg=COLORS["bg_surface"])
            s_row.pack(fill=tk.X, pady=SPACING["xs"])

            tk.Label(
                s_row,
                text=f"Level {lvl} Slot:",
                font=FONTS["body"],
                fg=COLORS["fg"],
                bg=COLORS["bg_surface"],
                width=15,
            ).pack(side=tk.LEFT)

            spin = ttk.Spinbox(s_row, from_=0, to=spent, textvariable=var, width=5, command=self._update_recovery_summary)
            spin.pack(side=tk.LEFT, padx=SPACING["sm"])

            tk.Label(
                s_row,
                text=f"(Spent: {spent})",
                font=FONTS["body_small"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(side=tk.LEFT)

            var.trace_add("write", lambda *_: self._update_recovery_summary())
            row_i += 1

        if row_i == 0:
            tk.Label(
                card_inner,
                text="No eligible spent spell slots to recover.",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(anchor=tk.W, pady=SPACING["sm"])

        self._recovery_summary_label = tk.Label(
            card_inner,
            text="Points Used: 0 / " + str(self._recovery_max_points),
            font=FONTS["body"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        )
        self._recovery_summary_label.pack(anchor=tk.W, pady=(SPACING["sm"], 0))

    def _update_recovery_summary(self):
        total = 0
        for lvl_str, var in self._recovery_vars.items():
            try:
                total += int(lvl_str) * var.get()
            except: pass
        self._recovery_current_points.set(total)
        color = COLORS["fg"] if total <= self._recovery_max_points else COLORS["negative"]
        self._recovery_summary_label.config(text=f"Points Used: {total} / {self._recovery_max_points}", fg=color)

    def _show_rest_step(self, step: int):
        """Show the given step and update navigation buttons."""
        self._current_step = step

        # Hide all step frames
        for frame in self._step_frames:
            frame.grid_forget()

        # Hide nav buttons
        self._cancel_btn.pack_forget()
        self._back_btn.pack_forget()
        self._next_btn.pack_forget()
        self._finish_btn.pack_forget()

        # Show current step
        idx = step - 1
        if 0 <= idx < len(self._step_frames):
            self._step_frames[idx].grid(row=1, column=0, sticky="nsew")

        # Left: Cancel on step 1, Back on later steps
        if step > 1:
            self._back_btn.pack(side=tk.LEFT)
        else:
            self._cancel_btn.pack(side=tk.LEFT)

        # Right: Next or Finish
        if step < self._total_steps:
            self._next_btn.pack(side=tk.RIGHT)
        else:
            self._finish_btn.pack(side=tk.RIGHT)

        # Center: Step counter and progress bar
        self._step_label.configure(text=f"Step {step} of {self._total_steps}")
        self._progress_bar.set_hp(step, self._total_steps)

    def _validate_current_step(self) -> bool:
        step_id = self._current_step_id()
        if step_id == "recovery":
            points = self._recovery_current_points.get()
            if points > self._recovery_max_points:
                AlertDialog(self, "Too Many Slots", f"You can only recover up to {self._recovery_max_points} points worth of slots.")
                return False
            return True

        if step_id != "zhentarim_expertise":
            return True

        if not self._zhentarim_expertise_options:
            AlertDialog(
                self,
                "No Eligible Skill",
                "Zhentarim Tactics needs a proficient skill without existing Expertise, "
                "but none are currently available.",
            )
            return False

        selected = self._selected_zhentarim_expertise().strip()
        if selected not in set(self._zhentarim_expertise_options):
            AlertDialog(
                self,
                "Expertise Selection Required",
                "Choose a skill for Zhentarim Tactics before continuing.",
            )
            return False

        return True

    def _go_next(self):
        if not self._validate_current_step():
            return
        if self._current_step < self._total_steps:
            self._show_rest_step(self._current_step + 1)

    def _go_back(self):
        if self._current_step > 1:
            self._show_rest_step(self._current_step - 1)

    # ══════════════════════════════════════════════════════════════════
    # Feature / Cantrip / Spell sections (unchanged)
    # ══════════════════════════════════════════════════════════════════

    def _build_feature_section(self, parent, key: str, config: dict, known: list[str]):
        choice_plural = config.get("choice_plural", "Choices")
        choice_label = config.get("choice_label", "Choice")
        options = config.get("options", [])

        card = CardFrame(parent, pad=SPACING["md"])
        card.pack(fill=tk.X, pady=(0, SPACING["md"]))
        frame = card.inner

        tk.Label(
            frame,
            text=f"Swap {choice_plural}",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", pady=(0, SPACING["sm"]))

        tk.Label(
            frame,
            text=f"You may replace one {choice_label} with a different one.",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", pady=(0, SPACING["sm"]))

        cols = tk.Frame(frame, bg=COLORS["bg_surface"])
        cols.pack(fill=tk.X)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        remove_var = tk.StringVar(value="")
        replace_var = tk.StringVar(value="")
        self._swaps[key] = {"remove_var": remove_var, "replace_var": replace_var, "config": config}
        sub_sels = _get_all_known_sub_selections(self.character, key)

        # Left: Remove
        remove_lf = tk.Frame(cols, bg=COLORS["bg_surface"])
        remove_lf.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["xs"]))

        tk.Label(
            remove_lf,
            text="Remove",
            font=FONTS["label_upper"],
            fg=COLORS["accent"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", pady=(0, SPACING["xs"]))

        ttk.Radiobutton(
            remove_lf, text="Don\u2019t replace", variable=remove_var, value="",
            style="Card.TRadiobutton",
        ).pack(anchor="w", pady=SPACING["xs"])

        for name in sorted(known):
            sub = sub_sels.get(name, "")
            if sub and "|" in sub:
                parts = sub.split("|", 1)
                display = f"{name} ({parts[0]} \u2014 {parts[1]})"
            elif sub:
                display = f"{name} ({sub})"
            else:
                display = name
            ttk.Radiobutton(
                remove_lf, text=display, variable=remove_var, value=name,
                style="Card.TRadiobutton",
            ).pack(anchor="w", padx=(SPACING["sm"], 0), pady=SPACING["xs"])

        # Right: Replace with
        add_lf = tk.Frame(cols, bg=COLORS["bg_surface"])
        add_lf.grid(row=0, column=1, sticky="nsew", padx=(SPACING["xs"], 0))

        tk.Label(
            add_lf,
            text="Replace with",
            font=FONTS["label_upper"],
            fg=COLORS["accent"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", pady=(0, SPACING["xs"]))

        ttk.Radiobutton(
            add_lf, text="\u2014", variable=replace_var, value="",
            style="Card.TRadiobutton",
        ).pack(anchor="w", pady=SPACING["xs"])

        available = [o for o in options if o["name"] not in known]

        pools_cfg = config.get("pools", {})
        if pools_cfg:
            unlocked_pools: set[str] = set()
            for cl in self.character.class_levels:
                if cl.class_slug == key or cl.subclass_slug == key:
                    lvl_str = str(cl.class_level)
                    pool = pools_cfg.get(lvl_str)
                    if pool:
                        unlocked_pools.add(pool)
            available = [o for o in options if o.get("pool") in unlocked_pools and o["name"] not in known]

        for opt in sorted(available, key=lambda o: o["name"]):
            ttk.Radiobutton(
                add_lf, text=opt["name"], variable=replace_var, value=opt["name"],
                style="Card.TRadiobutton",
            ).pack(anchor="w", padx=(SPACING["sm"], 0), pady=SPACING["xs"])

        if not available:
            tk.Label(
                add_lf,
                text="No other options available.",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w", pady=SPACING["xs"])

    def _max_spell_level(self) -> int:
        """Compute the highest spell slot level available to this character."""
        _SLOT_ORDER = {
            "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5,
            "6th": 6, "7th": 7, "8th": 8, "9th": 9,
        }
        max_lvl = 0
        for cl in self.character.class_levels:
            if cl.class_slug not in _PREPARED_CASTER_CLASSES:
                continue
            class_level = self.character.class_level_in(cl.class_slug)
            level_data = self.data.get_level_data(cl.class_slug, class_level)
            if level_data:
                slots = level_data.get("spell_slots") or {}
                for k in slots:
                    max_lvl = max(max_lvl, _SLOT_ORDER.get(k, 0))
        return max_lvl

    def _cantrip_swap_classes(self) -> set[str]:
        """Return class slugs that allow cantrip swapping on Long Rest."""
        return {
            cl.class_slug for cl in self.character.class_levels
            if _REST_SPELL_SWAP.get(cl.class_slug, {}).get("cantrip_swaps", 0) > 0
        }

    def _build_cantrip_section(self, parent):
        """Build the cantrip swap section with card theming."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        scroll = ScrollableFrame(parent, auto_hide_scrollbar=True)
        scroll.grid(row=0, column=0, sticky="nsew")
        inner = scroll.inner

        SectionHeader(inner, text="Swap Cantrip").pack(
            fill=tk.X, padx=0, pady=(0, SPACING["sm"])
        )

        card = CardFrame(inner, pad=SPACING["md"])
        card.pack(fill=tk.BOTH, expand=True)
        card_inner = card.inner

        tk.Label(
            card_inner,
            text="You may replace one cantrip with another from your class spell list.",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor=tk.W, pady=(0, SPACING["sm"]))

        swap_classes = self._cantrip_swap_classes()
        forget_cantrips = self._collect_cantrip_dicts(
            set(self.character.selected_cantrips), swap_classes
        )
        learn_cantrips = self._collect_available_cantrip_dicts(
            set(self.character.selected_cantrips), swap_classes
        )

        content = tk.Frame(card_inner, bg=COLORS["bg_surface"])
        content.pack(fill=tk.BOTH, expand=True)

        self._cantrip_panel = SpellSwapPanel(
            content,
            forget_spells=forget_cantrips,
            learn_spells=learn_cantrips,
            allow_cantrips=False,
            left_label="Forget",
            right_label="Learn",
            no_swap_label="Don\u2019t swap",
        )

    def _collect_cantrip_dicts(self, names: set[str], class_slugs: set[str]) -> list[dict]:
        result = []
        for spell in self.data.spells:
            if spell.get("level", -1) != 0:
                continue
            if spell.get("name") not in names:
                continue
            spell_classes = {c.lower() for c in spell.get("classes", [])}
            if spell_classes & class_slugs:
                result.append(spell)
        return result

    def _collect_available_cantrip_dicts(self, known_set: set[str], class_slugs: set[str]) -> list[dict]:
        result = []
        for spell in self.data.spells:
            if spell.get("level", -1) != 0:
                continue
            name = spell.get("name", "")
            if not name or name in known_set:
                continue
            spell_classes = {c.lower() for c in spell.get("classes", [])}
            if spell_classes & class_slugs:
                result.append(spell)
        return result

    def _build_spell_section(self, parent):
        """Build the spell swap section with card theming."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        scroll = ScrollableFrame(parent, auto_hide_scrollbar=True)
        scroll.grid(row=0, column=0, sticky="nsew")
        inner = scroll.inner

        mode = self._spell_swap_mode or "one"

        if mode == "all":
            heading = "Change Prepared Spells"
            desc = "You may change any number of your prepared spells. Select spells to unprepare on the left, then select the same number of replacements on the right."
        else:
            heading = "Swap Prepared Spell"
            desc = "You may replace one prepared spell with another from your class spell list."

        SectionHeader(inner, text=heading).pack(
            fill=tk.X, padx=0, pady=(0, SPACING["sm"])
        )

        card = CardFrame(inner, pad=SPACING["md"])
        card.pack(fill=tk.BOTH, expand=True)
        card_inner = card.inner

        tk.Label(
            card_inner,
            text=desc,
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor=tk.W, pady=(0, SPACING["sm"]))

        known_set = set(self.character.selected_spells)
        forget_spells = self._collect_spell_dicts(known_set)
        max_lvl = self._max_spell_level()
        learn_spells = self._collect_available_spell_dicts(known_set, max_lvl)

        content = tk.Frame(card_inner, bg=COLORS["bg_surface"])
        content.pack(fill=tk.BOTH, expand=True)

        if mode == "all":
            self._multi_spell_panel = MultiSpellSwapPanel(
                content,
                forget_spells=forget_spells,
                learn_spells=learn_spells,
                left_label="Unprepare",
                right_label="Prepare instead",
            )
        else:
            self._spell_panel = SpellSwapPanel(
                content,
                forget_spells=forget_spells,
                learn_spells=learn_spells,
                allow_cantrips=False,
                left_label="Unprepare",
                right_label="Prepare instead",
                no_swap_label="Don\u2019t change",
            )

    def _collect_spell_dicts(self, names: set[str]) -> list[dict]:
        result = []
        primary_slugs = {cl.class_slug for cl in self.character.class_levels
                         if cl.class_slug in _PREPARED_CASTER_CLASSES}
        for spell in self.data.spells:
            if spell.get("name") in names:
                spell_classes = {c.lower() for c in spell.get("classes", [])}
                if spell_classes & primary_slugs:
                    result.append(spell)
        return result

    def _collect_available_spell_dicts(self, known_set: set[str], max_spell_level: int) -> list[dict]:
        result = []
        primary_slugs = {cl.class_slug for cl in self.character.class_levels
                         if cl.class_slug in _PREPARED_CASTER_CLASSES}
        for spell in self.data.spells:
            name = spell.get("name", "")
            if not name or name in known_set:
                continue
            level = spell.get("level", 0)
            if level < 1 or level > max_spell_level:
                continue
            spell_classes = {c.lower() for c in spell.get("classes", [])}
            if spell_classes & primary_slugs:
                result.append(spell)
        return result

    # ══════════════════════════════════════════════════════════════════
    # Confirm
    # ══════════════════════════════════════════════════════════════════

    def _on_confirm(self):
        if not self._validate_current_step():
            return

        changed = False

        # ── Long Rest: HP restoration + hit dice restoration ──────
        if self.rest_type == "long":
            self.character.current_hit_points = None  # reset to full
            self.character.temp_hit_points = 0
            self.character.spent_hit_dice.clear()
            self.character.reset_spell_slots()
            if restore_free_casts(self.character, self.data, "long"):
                changed = True
            if restore_feature_resources(self.character, self.data, "long"):
                changed = True
            self.character.arcane_recovery_used = False
            changed = True

        # ── Short Rest: hit dice spending ─────────────────────────
        if self.rest_type == "short" and self._hd_spend_vars:
            pool = self.character.hit_dice_pool
            con_mod = get_effective_modifier(self.character, "Constitution")

            # Gather dice to spend per class
            dice_to_spend: dict[str, int] = {}
            for slug, var in self._hd_spend_vars.items():
                try:
                    count = var.get()
                except tk.TclError:
                    count = 0
                if count > 0:
                    # Clamp to remaining
                    rem = pool.get(slug, (0, 0, 0))[0]
                    dice_to_spend[slug] = min(count, rem)

            total_dice = sum(dice_to_spend.values())

            if total_dice > 0:
                if self._hd_roll_mode.get() == "manual":
                    # Manual entry
                    val = self._hd_manual_var.get().strip()
                    try:
                        rolled_total = int(val)
                    except ValueError:
                        AlertDialog(
                            self, "Invalid Roll",
                            "Please enter a valid number for your dice roll total.",
                        )
                        return
                    if rolled_total < 0:
                        AlertDialog(
                            self, "Invalid Roll",
                            "Roll total must be 0 or greater.",
                        )
                        return

                    con_total = total_dice * con_mod
                    healed = max(0, rolled_total + con_total)

                    # Apply spending
                    for slug, count in dice_to_spend.items():
                        self.character.spent_hit_dice[slug] = (
                            self.character.spent_hit_dice.get(slug, 0) + count
                        )

                    # Apply healing
                    cur = self.character.effective_current_hp
                    max_hp = self.character.hit_points
                    new_hp = min(max_hp, cur + healed)
                    self.character.current_hit_points = new_hp
                    changed = True

                    # Show result
                    _show_short_rest_result_manual(
                        self, healed=healed, old_hp=cur, new_hp=new_hp, max_hp=max_hp,
                    )
                else:
                    # Auto roll
                    rolls_by_class: dict[str, list[int]] = {}
                    for slug, count in dice_to_spend.items():
                        _, _, die = pool[slug]
                        rolls_by_class[slug] = [
                            random.randint(1, die) for _ in range(count)
                        ]

                    raw_total = sum(r for rolls in rolls_by_class.values() for r in rolls)
                    con_total = total_dice * con_mod
                    healed = max(0, raw_total + con_total)

                    # Apply spending
                    for slug, count in dice_to_spend.items():
                        self.character.spent_hit_dice[slug] = (
                            self.character.spent_hit_dice.get(slug, 0) + count
                        )

                    # Apply healing
                    cur = self.character.effective_current_hp
                    max_hp = self.character.hit_points
                    new_hp = min(max_hp, cur + healed)
                    self.character.current_hit_points = new_hp
                    changed = True

                    # Show result
                    _show_short_rest_result_auto(
                        self, rolls_by_class=rolls_by_class, pool=pool,
                        con_mod=con_mod, total_dice=total_dice,
                        healed=healed, old_hp=cur, new_hp=new_hp, max_hp=max_hp,
                    )

        # ── Short Rest: Spell/Pact Recovery ───────────────────────
        if self.rest_type == "short":
            # Warlock Pact Magic
            if _is_warlock_pact_caster(self.character):
                if self.character.used_pact_slots > 0:
                    self.character.used_pact_slots = 0
                    changed = True
            if restore_free_casts(self.character, self.data, "short"):
                changed = True
            if restore_feature_resources(self.character, self.data, "short"):
                changed = True
            
            # Arcane Recovery
            if self._recovery_vars:
                recovered_any = False
                for lvl_str, var in self._recovery_vars.items():
                    count = var.get()
                    if count > 0:
                        self.character.recover_spell_slots(lvl_str, count)
                        recovered_any = True
                if recovered_any:
                    self.character.arcane_recovery_used = True
                    changed = True

        # ── Feature swaps ─────────────────────────────────────────
        for key, swap_data in self._swaps.items():
            remove_var: tk.StringVar = swap_data["remove_var"]
            replace_var: tk.StringVar = swap_data["replace_var"]
            remove_name = remove_var.get()
            replace_name = replace_var.get()

            if not remove_name:
                continue
            if not replace_name:
                AlertDialog(
                    self,
                    "Incomplete Swap",
                    f"You selected a {swap_data['config'].get('choice_label', 'choice')} to remove "
                    f"but didn\u2019t pick a replacement. Either select a replacement or choose "
                    f"\u201cDon\u2019t replace\u201d.",
                )
                return

            _apply_choice_swap(self.character, key, remove_name, replace_name)
            changed = True

        # ── Cantrip swap ──────────────────────────────────────────
        if self._cantrip_panel:
            forget_c = self._cantrip_panel.forget_var.get()
            learn_c = self._cantrip_panel.learn_var.get()
            if forget_c:
                if not learn_c:
                    AlertDialog(
                        self,
                        "Incomplete Swap",
                        "You selected a cantrip to forget but didn\u2019t pick one to learn. "
                        "Either select a replacement or choose \u201cDon\u2019t swap\u201d.",
                    )
                    return
                if forget_c in self.character.selected_cantrips:
                    self.character.selected_cantrips.remove(forget_c)
                self.character.selected_cantrips.append(learn_c)
                changed = True

        # ── Leveled spell swap — multi mode ───────────────────────
        if self._multi_spell_panel:
            forget_names = self._multi_spell_panel.forget_names
            learn_names = self._multi_spell_panel.learn_names
            if forget_names or learn_names:
                if len(forget_names) != len(learn_names):
                    AlertDialog(
                        self,
                        "Unequal Swap",
                        f"You selected {len(forget_names)} spell{'s' if len(forget_names) != 1 else ''} to unprepare "
                        f"but {len(learn_names)} to prepare. The counts must match.",
                    )
                    return
                for name in forget_names:
                    if name in self.character.selected_spells:
                        self.character.selected_spells.remove(name)
                self.character.selected_spells.extend(learn_names)
                changed = True

        # ── Leveled spell swap — single mode ──────────────────────
        elif self._spell_panel:
            remove_spell = self._spell_panel.forget_var.get()
            add_spell = self._spell_panel.learn_var.get()
            if remove_spell:
                if not add_spell:
                    AlertDialog(
                        self,
                        "Incomplete Swap",
                        "You selected a spell to unprepare but didn\u2019t pick a replacement. "
                        "Either select a replacement or choose \u201cDon\u2019t change\u201d.",
                    )
                    return
                if remove_spell in self.character.selected_spells:
                    self.character.selected_spells.remove(remove_spell)
                self.character.selected_spells.append(add_spell)
                changed = True

        if (
            self.rest_type == "long"
            and self._zhentarim_expertise_vars
            and self._zhentarim_expertise_options
        ):
            selected = self._selected_zhentarim_expertise().strip()
            if selected in set(self._zhentarim_expertise_options):
                current = get_feat_expertise_skill(self.character, ZHENTARIM_TACTICS)
                if current != selected:
                    set_feat_expertise_skill(
                        self.character, ZHENTARIM_TACTICS, selected
                    )
                    changed = True

        if changed and self.on_changed:
            self.on_changed()

        self.destroy()


# ══════════════════════════════════════════════════════════════════════
# Result dialogs
# ══════════════════════════════════════════════════════════════════════


def _show_short_rest_result_auto(
    parent, *, rolls_by_class, pool, con_mod, total_dice,
    healed, old_hp, new_hp, max_hp,
):
    """Show auto-roll results for short rest hit dice spending."""
    dlg = tk.Toplevel(parent)
    dlg.title("Short Rest — Hit Dice Results")
    dlg.configure(bg=COLORS["bg"])
    dlg.resizable(False, False)

    configure_modal_dialog(dlg, parent)

    # Hero header
    hero = GradientHeader(dlg, min_height=40)
    hero.pack(fill=tk.X)
    tk.Label(
        hero.inner,
        text="Hit Dice Roll Results",
        font=FONTS["heading_serif_lg"],
        fg=COLORS["fg"],
        bg=COLORS["bg_hero"],
    ).pack(padx=SPACING["card_pad"], pady=(SPACING["md"], SPACING["md"]))

    # Card body
    card = CardFrame(dlg, pad=SPACING["lg"])
    card.pack(fill=tk.X, padx=SPACING["lg"], pady=SPACING["lg"])
    frame = card.inner

    # Per-class rolls
    for slug in sorted(rolls_by_class, key=lambda s: pool[s][2], reverse=True):
        rolls = rolls_by_class[slug]
        _, _, die = pool[slug]
        class_name = slug.replace("-", " ").title()
        roll_str = ", ".join(str(r) for r in rolls)
        tk.Label(
            frame,
            text=f"{class_name} (d{die}): {roll_str}",
            font=FONTS["body"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", pady=SPACING["xs"])

    raw_total = sum(r for rolls in rolls_by_class.values() for r in rolls)

    # CON bonus line
    con_total = total_dice * con_mod
    if con_mod >= 0:
        con_text = f"+ {con_total} CON ({total_dice} \u00d7 +{con_mod})"
    else:
        con_text = f"\u2212 {abs(con_total)} CON ({total_dice} \u00d7 {con_mod})"
    tk.Label(
        frame,
        text=con_text,
        font=FONTS["body_small"],
        fg=COLORS["fg_dim"],
        bg=COLORS["bg_surface"],
    ).pack(anchor="w", pady=(SPACING["sm"], SPACING["sm"]))

    # Total
    tk.Label(
        frame,
        text=f"{healed} HP restored ({old_hp}/{max_hp} \u2192 {new_hp}/{max_hp})",
        font=FONTS["heading"],
        fg=COLORS["fg"],
        bg=COLORS["bg_surface"],
    ).pack(anchor="w", pady=(0, SPACING["sm"]))

    ttk.Button(
        dlg, text="OK", style="Accent.TButton",
        command=dlg.destroy,
    ).pack(pady=(0, SPACING["lg"]))

    center_dialog_over_parent(dlg, parent)
    dlg.after_idle(lambda: center_dialog_over_parent(dlg, parent))


def _show_short_rest_result_manual(parent, *, healed, old_hp, new_hp, max_hp):
    """Show manual-roll results for short rest hit dice spending."""
    dlg = tk.Toplevel(parent)
    dlg.title("Short Rest — Results")
    dlg.configure(bg=COLORS["bg"])
    dlg.resizable(False, False)

    configure_modal_dialog(dlg, parent)

    # Hero header
    hero = GradientHeader(dlg, min_height=40)
    hero.pack(fill=tk.X)
    tk.Label(
        hero.inner,
        text="Short Rest Results",
        font=FONTS["heading_serif_lg"],
        fg=COLORS["fg"],
        bg=COLORS["bg_hero"],
    ).pack(padx=SPACING["card_pad"], pady=(SPACING["md"], SPACING["md"]))

    # Card body
    card = CardFrame(dlg, pad=SPACING["lg"])
    card.pack(fill=tk.X, padx=SPACING["lg"], pady=SPACING["lg"])

    tk.Label(
        card.inner,
        text=f"{healed} HP restored ({old_hp}/{max_hp} \u2192 {new_hp}/{max_hp})",
        font=FONTS["heading"],
        fg=COLORS["fg"],
        bg=COLORS["bg_surface"],
    ).pack(anchor="w")

    ttk.Button(
        dlg, text="OK", style="Accent.TButton",
        command=dlg.destroy,
    ).pack(pady=(0, SPACING["lg"]))

    center_dialog_over_parent(dlg, parent)
    dlg.after_idle(lambda: center_dialog_over_parent(dlg, parent))


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════


def _apply_choice_swap(character, key: str, remove_name: str, replace_name: str,
                       replace_sub_selection: str = ""):
    """Update the character's class_levels to swap one choice for another."""
    for cl in character.class_levels:
        if (cl.class_slug == key or cl.subclass_slug == key) and remove_name in cl.new_choices:
            cl.new_choices.remove(remove_name)
            cl.new_choices.append(replace_name)
            cl.replaced_choice = remove_name
            # Remove old sub-selection and add new one if provided
            cl.choice_sub_selections.pop(remove_name, None)
            if replace_sub_selection:
                cl.choice_sub_selections[replace_name] = replace_sub_selection
            return
