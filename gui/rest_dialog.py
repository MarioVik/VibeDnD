"""Dialog for taking a Short or Long Rest, allowing feature and spell swaps."""

from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import ttk

from gui.theme import COLORS, FONTS
from gui.widgets import ScrollableFrame, AlertDialog, configure_modal_dialog
from gui.spell_swap_panel import SpellSwapPanel, MultiSpellSwapPanel

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


def _get_all_known_choices(character, key: str) -> list[str]:
    """Aggregate all choices the character has selected for a given class/subclass key."""
    result: list[str] = []
    for cl in character.class_levels:
        if cl.class_slug == key or cl.subclass_slug == key:
            result.extend(cl.new_choices)
            if cl.replaced_choice and cl.replaced_choice in result:
                result.remove(cl.replaced_choice)
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
    """Return True if this character has anything to do on a Short Rest."""
    return _has_swappable_features(character, "short")


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
        self._info_step_frame: ttk.Frame | None = None
        self._cantrip_step_frame: ttk.Frame | None = None
        self._spell_step_frame: ttk.Frame | None = None
        self._single_swap_frame: ttk.Frame | None = None
        self._next_btn: ttk.Button | None = None
        self._back_btn: ttk.Button | None = None
        self._finish_btn: ttk.Button | None = None

        self._build_ui(title)

        # Center over parent — done after build so we can size based on step count
        self.update_idletasks()
        if self.rest_type == "long" and self._total_steps == 1:
            # Info-only long rest (no swaps) — smaller dialog
            width, height = 600, 400
            min_w, min_h = 500, 350
        else:
            width, height = 1400, 1000
            min_w, min_h = 1000, 750
        top = parent.winfo_toplevel()
        px = top.winfo_rootx()
        py = top.winfo_rooty()
        pw = top.winfo_width()
        ph = top.winfo_height()
        x = max(0, px + (pw - width) // 2)
        y = max(0, py + (ph - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(min_w, min_h)

    def _build_ui(self, title: str):
        self.columnconfigure(0, weight=1)

        # ── Header ─────────────────────────────────────────────────
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 2))

        ttk.Label(
            header,
            text=title,
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w")
        if self.rest_type == "short":
            ttk.Label(
                header,
                text="Optionally swap features before completing this rest.",
                foreground=COLORS["fg_dim"],
            ).pack(anchor="w")

        # ── Check for feature swap sections ────────────────────────
        all_keys: set[str] = set()
        for cl in self.character.class_levels:
            all_keys.add(cl.class_slug)
            if cl.subclass_slug:
                all_keys.add(cl.subclass_slug)

        feature_keys = []
        for key in sorted(all_keys):
            config = _CLASS_CHOICES.get(key)
            if not config or not config.get("can_swap_on_rest"):
                continue
            swap_type = config.get("swap_rest_type", "long")
            if self.rest_type == "short" and swap_type not in ("short", "short_or_long"):
                continue
            known = _get_all_known_choices(self.character, key)
            if known:
                feature_keys.append((key, config, known))

        # ── Determine sections ─────────────────────────────────────
        has_cantrip_swap = (
            self.rest_type == "long"
            and _can_swap_cantrips_on_rest(self.character)
        )
        self._spell_swap_mode = _spell_swap_mode(self.character) if self.rest_type == "long" else None
        has_spells = (
            self._spell_swap_mode is not None
            and self.character.selected_spells
        )
        has_features = bool(feature_keys)
        has_any_swap = has_features or has_cantrip_swap or has_spells
        use_three_steps = has_cantrip_swap and has_spells  # cantrip + spell on separate pages

        # Content area row (row=1) gets all the weight
        self.rowconfigure(1, weight=1)

        # ── Step 1 (long rest): Info summary ─────────────────────────
        if self.rest_type == "long":
            self._info_step_frame = ttk.Frame(self)
            self._build_info_step(
                self._info_step_frame,
                feature_keys=feature_keys,
                has_cantrip_swap=has_cantrip_swap,
                has_spells=has_spells,
            )

        # ── Build swap step frames (only for long rest with swaps) ─
        if has_any_swap and self.rest_type == "long":
            if use_three_steps:
                # Step 2: features (if any) + cantrip swap
                self._cantrip_step_frame = ttk.Frame(self)
                step_c = self._cantrip_step_frame
                step_c.columnconfigure(0, weight=1)
                s_row = 0
                if has_features:
                    scroll = ScrollableFrame(step_c)
                    scroll.grid(row=s_row, column=0, sticky="nsew", padx=8, pady=2)
                    for key, config, known in feature_keys:
                        self._build_feature_section(scroll.inner, key, config, known)
                    s_row += 1
                step_c.rowconfigure(s_row, weight=1)
                cantrip_frame = ttk.Frame(step_c)
                cantrip_frame.grid(row=s_row, column=0, sticky="nsew", padx=8, pady=2)
                self._build_cantrip_section(cantrip_frame)

                # Step 3: leveled spell swap
                self._spell_step_frame = ttk.Frame(self)
                step_s = self._spell_step_frame
                step_s.columnconfigure(0, weight=1)
                step_s.rowconfigure(0, weight=1)
                spell_frame = ttk.Frame(step_s)
                spell_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=2)
                self._build_spell_section(spell_frame)

                self._total_steps = 3
            else:
                # Step 2: all swap sections stacked on one page
                self._single_swap_frame = ttk.Frame(self)
                sf = self._single_swap_frame
                sf.columnconfigure(0, weight=1)
                sf_row = 0
                if has_features:
                    scroll = ScrollableFrame(sf)
                    scroll.grid(row=sf_row, column=0, sticky="nsew", padx=8, pady=2)
                    for key, config, known in feature_keys:
                        self._build_feature_section(scroll.inner, key, config, known)
                    sf_row += 1
                if has_cantrip_swap:
                    cantrip_frame = ttk.Frame(sf)
                    cantrip_frame.grid(row=sf_row, column=0, sticky="nsew", padx=8, pady=2)
                    self._build_cantrip_section(cantrip_frame)
                    sf_row += 1
                if has_spells:
                    sf.rowconfigure(sf_row, weight=1)
                    spell_frame = ttk.Frame(sf)
                    spell_frame.grid(row=sf_row, column=0, sticky="nsew", padx=8, pady=2)
                    self._build_spell_section(spell_frame)
                    sf_row += 1

                self._total_steps = 2
        elif has_any_swap and self.rest_type == "short":
            # Short rest: single swap page (no info step for short rests)
            self._single_swap_frame = ttk.Frame(self)
            sf = self._single_swap_frame
            sf.columnconfigure(0, weight=1)
            sf_row = 0
            if has_features:
                scroll = ScrollableFrame(sf)
                scroll.grid(row=sf_row, column=0, sticky="nsew", padx=8, pady=2)
                for key, config, known in feature_keys:
                    self._build_feature_section(scroll.inner, key, config, known)
                sf_row += 1
            # Short rest has no cantrip or spell swaps — only features
            self._single_swap_frame.grid(row=1, column=0, sticky="nsew")
            self._total_steps = 1

        # ── Footer ──────────────────────────────────────────────────
        footer = ttk.Frame(self)
        footer.grid(row=99, column=0, sticky="ew", padx=12, pady=(4, 8))

        self._back_btn = ttk.Button(footer, text="\u25C0 Back", command=self._go_back)
        self._next_btn = ttk.Button(
            footer, text="Next \u25B6", command=self._go_next
        )
        self._finish_btn = ttk.Button(
            footer,
            text="Finish Rest",
            style="Accent.TButton",
            command=self._on_confirm,
        )
        ttk.Button(
            footer,
            text="Cancel",
            command=self.destroy,
        ).pack(side=tk.LEFT)

        if self.rest_type == "short":
            # Short rest — no info step, just finish button
            self._finish_btn.pack(side=tk.RIGHT, padx=(4, 0))
        else:
            # Long rest — always starts with info step
            self._show_rest_step(1)

    # ── Info summary step ────────────────────────────────────────

    def _build_info_step(self, parent, *, feature_keys, has_cantrip_swap, has_spells):
        """Build the long rest info summary as step 1."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        inner = ttk.Frame(parent)
        inner.grid(row=0, column=0, sticky="nsew", padx=24, pady=12)
        inner.columnconfigure(0, weight=1)

        ttk.Label(
            inner,
            text="When you complete this rest:",
            font=FONTS["heading"],
            foreground=COLORS["fg"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

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

        for i, text in enumerate(effects):
            ttk.Label(
                inner,
                text=f"\u2022  {text}",
                foreground=COLORS["fg"],
                wraplength=500,
            ).grid(row=i + 1, column=0, sticky="w", padx=(12, 0), pady=2)

    # ── Step navigation ──────────────────────────────────────────

    def _show_rest_step(self, step: int):
        """Show the given step and update navigation buttons."""
        self._current_step = step

        # Hide all step frames
        for frame in (
            self._info_step_frame,
            self._cantrip_step_frame,
            self._spell_step_frame,
            self._single_swap_frame,
        ):
            if frame:
                frame.grid_forget()

        # Hide nav buttons
        self._back_btn.pack_forget()
        self._next_btn.pack_forget()
        self._finish_btn.pack_forget()

        if step == 1:
            # Info step (always first for long rests)
            if self._info_step_frame:
                self._info_step_frame.grid(row=1, column=0, sticky="nsew")
            if self._total_steps == 1:
                self._finish_btn.pack(side=tk.RIGHT, padx=(4, 0))
            else:
                self._next_btn.pack(side=tk.RIGHT, padx=(4, 0))
        elif step == 2:
            self._back_btn.pack(side=tk.LEFT)
            if self._total_steps == 2:
                # Single swap page
                if self._single_swap_frame:
                    self._single_swap_frame.grid(row=1, column=0, sticky="nsew")
                self._finish_btn.pack(side=tk.RIGHT, padx=(4, 0))
            elif self._total_steps == 3:
                # Cantrip step (3-step flow)
                if self._cantrip_step_frame:
                    self._cantrip_step_frame.grid(row=1, column=0, sticky="nsew")
                self._next_btn.pack(side=tk.RIGHT, padx=(4, 0))
        elif step == 3:
            # Spell step (3-step flow)
            if self._spell_step_frame:
                self._spell_step_frame.grid(row=1, column=0, sticky="nsew")
            self._back_btn.pack(side=tk.LEFT)
            self._finish_btn.pack(side=tk.RIGHT, padx=(4, 0))

    def _go_next(self):
        if self._current_step < self._total_steps:
            self._show_rest_step(self._current_step + 1)

    def _go_back(self):
        if self._current_step > 1:
            self._show_rest_step(self._current_step - 1)

    def _build_feature_section(self, parent, key: str, config: dict, known: list[str]):
        choice_plural = config.get("choice_plural", "Choices")
        choice_label = config.get("choice_label", "Choice")
        options = config.get("options", [])

        frame = ttk.LabelFrame(parent, text=f"Swap {choice_plural}")
        frame.pack(fill=tk.X, pady=(8, 0), padx=4)

        ttk.Label(
            frame,
            text=f"You may replace one {choice_label} with a different one.",
            foreground=COLORS["fg_dim"],
        ).pack(anchor="w", padx=8, pady=(4, 8))

        cols = ttk.Frame(frame)
        cols.pack(fill=tk.X, padx=8, pady=(0, 8))
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)

        remove_var = tk.StringVar(value="")
        replace_var = tk.StringVar(value="")
        self._swaps[key] = {"remove_var": remove_var, "replace_var": replace_var, "config": config}

        # Left: Remove
        remove_lf = ttk.LabelFrame(cols, text="Remove")
        remove_lf.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        ttk.Radiobutton(
            remove_lf,
            text="Don\u2019t replace",
            variable=remove_var,
            value="",
        ).pack(anchor="w", padx=8, pady=2)

        for name in sorted(known):
            ttk.Radiobutton(
                remove_lf,
                text=name,
                variable=remove_var,
                value=name,
            ).pack(anchor="w", padx=(16, 8), pady=1)

        # Right: Replace with
        add_lf = ttk.LabelFrame(cols, text="Replace with")
        add_lf.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        ttk.Radiobutton(
            add_lf,
            text="\u2014",
            variable=replace_var,
            value="",
        ).pack(anchor="w", padx=8, pady=2)

        # All options minus currently known
        available = [o for o in options if o["name"] not in known]

        # Pool-aware filtering: if pools exist, show all valid options (reshuffling freely)
        # No pool restriction on rest swaps — they can pick from any pool they've unlocked
        pools_cfg = config.get("pools", {})
        if pools_cfg:
            # Determine which pools the character has unlocked
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
                add_lf,
                text=opt["name"],
                variable=replace_var,
                value=opt["name"],
            ).pack(anchor="w", padx=(16, 8), pady=1)

        if not available:
            ttk.Label(
                add_lf,
                text="No other options available.",
                foreground=COLORS["fg_dim"],
            ).pack(anchor="w", padx=8, pady=4)

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

    # ── Cantrip swap section ──────────────────────────────────────

    def _build_cantrip_section(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)

        ttk.Label(
            parent,
            text="Swap Cantrip",
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).grid(row=0, column=0, sticky="w", padx=4, pady=(2, 0))
        ttk.Label(
            parent,
            text="You may replace one cantrip with another from your class spell list.",
            foreground=COLORS["fg_dim"],
        ).grid(row=1, column=0, sticky="w", padx=4, pady=(0, 4))

        # Gather cantrip dicts
        swap_classes = self._cantrip_swap_classes()
        forget_cantrips = self._collect_cantrip_dicts(
            set(self.character.selected_cantrips), swap_classes
        )
        learn_cantrips = self._collect_available_cantrip_dicts(
            set(self.character.selected_cantrips), swap_classes
        )

        content = ttk.Frame(parent)
        content.grid(row=2, column=0, sticky="nsew")

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
        """Look up full spell dicts for known cantrips from given classes."""
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
        """Return available cantrip dicts not already known."""
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

    # ── Leveled spell swap section ────────────────────────────────

    def _build_spell_section(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)

        mode = self._spell_swap_mode or "one"

        if mode == "all":
            heading = "Change Prepared Spells"
            desc = "You may change any number of your prepared spells. Select spells to unprepare on the left, then select the same number of replacements on the right."
        else:
            heading = "Swap Prepared Spell"
            desc = "You may replace one prepared spell with another from your class spell list."

        ttk.Label(
            parent,
            text=heading,
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).grid(row=0, column=0, sticky="w", padx=4, pady=(2, 0))
        ttk.Label(
            parent,
            text=desc,
            foreground=COLORS["fg_dim"],
        ).grid(row=1, column=0, sticky="w", padx=4, pady=(0, 4))

        # Gather spell dicts
        known_set = set(self.character.selected_spells)
        forget_spells = self._collect_spell_dicts(known_set)
        max_lvl = self._max_spell_level()
        learn_spells = self._collect_available_spell_dicts(known_set, max_lvl)

        content = ttk.Frame(parent)
        content.grid(row=2, column=0, sticky="nsew")

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
        """Look up full spell dicts for a set of spell names."""
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
        """Return full spell dicts from class spell lists not already prepared."""
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

    def _on_confirm(self):
        changed = False

        # Apply HP restoration (Long Rest)
        if self.rest_type == "long":
            self.character.current_hit_points = None  # reset to full
            self.character.temp_hit_points = 0
            changed = True

        # Apply feature swaps
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

        # Apply cantrip swap (single, radio-based)
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

        # Apply leveled spell swap — multi mode
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

        # Apply leveled spell swap — single mode
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

        if changed and self.on_changed:
            self.on_changed()

        self.destroy()


def _apply_choice_swap(character, key: str, remove_name: str, replace_name: str):
    """Update the character's class_levels to swap one choice for another."""
    # Find the ClassLevel that owns remove_name for this key
    for cl in character.class_levels:
        if (cl.class_slug == key or cl.subclass_slug == key) and remove_name in cl.new_choices:
            cl.new_choices.remove(remove_name)
            cl.new_choices.append(replace_name)
            # Track the replacement (use replaced_choice field for most recent swap)
            cl.replaced_choice = remove_name
            return
    # Fallback: not found in any specific ClassLevel — do nothing (shouldn't happen)
