"""Dialog for taking a Short or Long Rest, allowing feature/spell swaps and hit dice spending."""

from __future__ import annotations

import json
import os
import random
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

        if rest_type == "short":
            self._build_short_rest_ui(title)
        else:
            self._build_long_rest_ui(title)

        # Center over parent — done after build so we can size based on step count
        self.update_idletasks()
        if self._total_steps == 1:
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

    # ══════════════════════════════════════════════════════════════════
    # Long Rest UI (unchanged logic, refactored slightly)
    # ══════════════════════════════════════════════════════════════════

    def _build_long_rest_ui(self, title: str):
        self.columnconfigure(0, weight=1)

        # Header
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 2))
        ttk.Label(
            header, text=title, font=FONTS["heading"], foreground=COLORS["accent"],
        ).pack(anchor="w")

        feature_keys = _get_feature_keys(self.character, "long")

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
        )
        self._step_frames.append(info_frame)

        # Build swap steps
        if has_any_swap:
            if use_three_steps:
                # Step 2: features + cantrip swap
                cantrip_step = ttk.Frame(self)
                cantrip_step.columnconfigure(0, weight=1)
                s_row = 0
                if has_features:
                    scroll = ScrollableFrame(cantrip_step)
                    scroll.grid(row=s_row, column=0, sticky="nsew", padx=8, pady=2)
                    for key, config, known in feature_keys:
                        self._build_feature_section(scroll.inner, key, config, known)
                    s_row += 1
                cantrip_step.rowconfigure(s_row, weight=1)
                cf = ttk.Frame(cantrip_step)
                cf.grid(row=s_row, column=0, sticky="nsew", padx=8, pady=2)
                self._build_cantrip_section(cf)
                self._step_frames.append(cantrip_step)

                # Step 3: spell swap
                spell_step = ttk.Frame(self)
                spell_step.columnconfigure(0, weight=1)
                spell_step.rowconfigure(0, weight=1)
                sf = ttk.Frame(spell_step)
                sf.grid(row=0, column=0, sticky="nsew", padx=8, pady=2)
                self._build_spell_section(sf)
                self._step_frames.append(spell_step)
            else:
                # Step 2: all swap sections on one page
                swap_frame = ttk.Frame(self)
                swap_frame.columnconfigure(0, weight=1)
                sf_row = 0
                if has_features:
                    scroll = ScrollableFrame(swap_frame)
                    scroll.grid(row=sf_row, column=0, sticky="nsew", padx=8, pady=2)
                    for key, config, known in feature_keys:
                        self._build_feature_section(scroll.inner, key, config, known)
                    sf_row += 1
                if has_cantrip_swap:
                    cf = ttk.Frame(swap_frame)
                    cf.grid(row=sf_row, column=0, sticky="nsew", padx=8, pady=2)
                    self._build_cantrip_section(cf)
                    sf_row += 1
                if has_spells:
                    swap_frame.rowconfigure(sf_row, weight=1)
                    sf = ttk.Frame(swap_frame)
                    sf.grid(row=sf_row, column=0, sticky="nsew", padx=8, pady=2)
                    self._build_spell_section(sf)
                    sf_row += 1
                self._step_frames.append(swap_frame)

        self._total_steps = len(self._step_frames)
        self._build_footer()
        self._show_rest_step(1)

    def _build_long_rest_info_step(self, parent, *, feature_keys, has_cantrip_swap, has_spells):
        """Build the long rest info summary."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        inner = ttk.Frame(parent)
        inner.grid(row=0, column=0, sticky="nsew", padx=24, pady=12)
        inner.columnconfigure(0, weight=1)

        ttk.Label(
            inner, text="When you complete this rest:",
            font=FONTS["heading"], foreground=COLORS["fg"],
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

        for i, text in enumerate(effects):
            ttk.Label(
                inner, text=f"\u2022  {text}",
                foreground=COLORS["fg"], wraplength=500,
            ).grid(row=i + 1, column=0, sticky="w", padx=(12, 0), pady=2)

    # ══════════════════════════════════════════════════════════════════
    # Short Rest UI
    # ══════════════════════════════════════════════════════════════════

    def _build_short_rest_ui(self, title: str):
        self.columnconfigure(0, weight=1)

        # Header
        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 2))
        ttk.Label(
            header, text=title, font=FONTS["heading"], foreground=COLORS["accent"],
        ).pack(anchor="w")

        feature_keys = _get_feature_keys(self.character, "short")
        has_features = bool(feature_keys)
        pool = self.character.hit_dice_pool
        self._has_hit_dice = self.character.total_hit_dice_remaining > 0

        self.rowconfigure(1, weight=1)

        # Step 1: Info summary
        info_frame = ttk.Frame(self)
        self._build_short_rest_info_step(info_frame, feature_keys=feature_keys)
        self._step_frames.append(info_frame)

        # Step 2: Hit dice spending (if any remaining)
        if self._has_hit_dice:
            hd_frame = ttk.Frame(self)
            self._build_hit_dice_step(hd_frame)
            self._step_frames.append(hd_frame)

        # Step 3 (or 2): Feature swaps (if any)
        if has_features:
            swap_frame = ttk.Frame(self)
            swap_frame.columnconfigure(0, weight=1)
            scroll = ScrollableFrame(swap_frame)
            scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=2)
            swap_frame.rowconfigure(0, weight=1)
            for key, config, known in feature_keys:
                self._build_feature_section(scroll.inner, key, config, known)
            self._step_frames.append(swap_frame)

        self._total_steps = len(self._step_frames)
        self._build_footer()
        self._show_rest_step(1)

    def _build_short_rest_info_step(self, parent, *, feature_keys):
        """Build the short rest info summary."""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        inner = ttk.Frame(parent)
        inner.grid(row=0, column=0, sticky="nsew", padx=24, pady=12)
        inner.columnconfigure(0, weight=1)

        ttk.Label(
            inner, text="When you complete this rest:",
            font=FONTS["heading"], foreground=COLORS["fg"],
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        effects: list[str] = []

        # Hit dice available
        pool = self.character.hit_dice_pool
        for slug in sorted(pool, key=lambda s: pool[s][2], reverse=True):
            rem, total, die = pool[slug]
            class_name = slug.replace("-", " ").title()
            effects.append(f"You have {rem}/{total} d{die} hit dice remaining ({class_name})")

        if self.character.total_hit_dice_remaining > 0:
            con_mod = self.character.ability_scores.modifier("Constitution")
            sign = "+" if con_mod >= 0 else ""
            effects.append(f"You may spend hit dice to recover HP (each die {sign}{con_mod} CON)")
        else:
            effects.append("You have no hit dice left to spend")

        # Feature swaps
        for _key, config, _known in feature_keys:
            label = config.get("choice_label", "feature")
            effects.append(f"You may swap one {label}")

        if not feature_keys and self.character.total_hit_dice_remaining == 0:
            effects.append("There is nothing else to do on this rest")

        for i, text in enumerate(effects):
            ttk.Label(
                inner, text=f"\u2022  {text}",
                foreground=COLORS["fg"], wraplength=500,
            ).grid(row=i + 1, column=0, sticky="w", padx=(12, 0), pady=2)

    def _build_hit_dice_step(self, parent):
        """Build the hit dice spending step for short rest."""
        parent.columnconfigure(0, weight=1)

        ttk.Label(
            parent, text="Spend Hit Dice",
            font=FONTS["heading"], foreground=COLORS["accent"],
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 2))

        con_mod = self.character.ability_scores.modifier("Constitution")
        sign = "+" if con_mod >= 0 else ""
        ttk.Label(
            parent,
            text=f"Choose how many hit dice to spend. Each die heals: roll {sign}{con_mod} CON (minimum 0 HP per die).",
            foreground=COLORS["fg_dim"],
        ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))

        # Per-class die selectors
        pool = self.character.hit_dice_pool
        selector_frame = ttk.Frame(parent)
        selector_frame.grid(row=2, column=0, sticky="ew", padx=12)

        row_i = 0
        for slug in sorted(pool, key=lambda s: pool[s][2], reverse=True):
            rem, total, die = pool[slug]
            if rem == 0:
                continue

            class_name = slug.replace("-", " ").title()
            var = tk.IntVar(value=0)
            self._hd_spend_vars[slug] = var

            die_row = ttk.Frame(selector_frame)
            die_row.grid(row=row_i, column=0, sticky="ew", pady=4)

            ttk.Label(
                die_row, text=f"d{die} ({class_name}):",
                font=FONTS["body"], foreground=COLORS["fg"],
            ).pack(side=tk.LEFT, padx=(0, 8))

            # Spinbox for count selection
            spin = ttk.Spinbox(
                die_row, from_=0, to=rem, textvariable=var,
                width=4, command=self._update_hd_summary,
            )
            spin.pack(side=tk.LEFT, padx=(0, 8))
            # Also update on keyboard input
            var.trace_add("write", lambda *_: self._update_hd_summary())

            ttk.Label(
                die_row, text=f"(max {rem})",
                foreground=COLORS["fg_dim"],
            ).pack(side=tk.LEFT)

            row_i += 1

        # Summary label
        self._hd_summary_label = ttk.Label(
            parent, text="No dice selected", foreground=COLORS["fg_dim"],
        )
        self._hd_summary_label.grid(row=3, column=0, sticky="w", padx=12, pady=(8, 4))

        # Roll mode selection
        mode_frame = ttk.LabelFrame(parent, text="How to roll")
        mode_frame.grid(row=4, column=0, sticky="ew", padx=12, pady=(4, 4))

        ttk.Radiobutton(
            mode_frame, text="Roll for me (app rolls the dice)",
            variable=self._hd_roll_mode, value="auto",
            command=self._update_manual_entry_state,
        ).pack(anchor="w", padx=8, pady=2)

        manual_row = ttk.Frame(mode_frame)
        manual_row.pack(anchor="w", padx=8, pady=2)

        ttk.Radiobutton(
            manual_row, text="I rolled myself, total rolled:",
            variable=self._hd_roll_mode, value="manual",
            command=self._update_manual_entry_state,
        ).pack(side=tk.LEFT)

        self._hd_manual_entry = ttk.Entry(
            manual_row, textvariable=self._hd_manual_var, width=6, state="disabled",
        )
        self._hd_manual_entry.pack(side=tk.LEFT, padx=(4, 4))

        self._hd_manual_hint = ttk.Label(
            manual_row, text="", foreground=COLORS["fg_dim"],
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
                    foreground=COLORS["fg"],
                )
            else:
                self._hd_summary_label.config(
                    text="No dice selected",
                    foreground=COLORS["fg_dim"],
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

        con_mod = self.character.ability_scores.modifier("Constitution")
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
        footer = ttk.Frame(self)
        footer.grid(row=99, column=0, sticky="ew", padx=12, pady=(4, 8))

        self._back_btn = ttk.Button(footer, text="\u25C0 Back", command=self._go_back)
        self._next_btn = ttk.Button(
            footer, text="Next \u25B6", command=self._go_next,
        )
        self._finish_btn = ttk.Button(
            footer, text="Finish Rest", style="Accent.TButton",
            command=self._on_confirm,
        )
        ttk.Button(
            footer, text="Cancel", command=self.destroy,
        ).pack(side=tk.LEFT)

    def _show_rest_step(self, step: int):
        """Show the given step and update navigation buttons."""
        self._current_step = step

        # Hide all step frames
        for frame in self._step_frames:
            frame.grid_forget()

        # Hide nav buttons
        self._back_btn.pack_forget()
        self._next_btn.pack_forget()
        self._finish_btn.pack_forget()

        # Show current step
        idx = step - 1
        if 0 <= idx < len(self._step_frames):
            self._step_frames[idx].grid(row=1, column=0, sticky="nsew")

        if step > 1:
            self._back_btn.pack(side=tk.LEFT)
        if step < self._total_steps:
            self._next_btn.pack(side=tk.RIGHT, padx=(4, 0))
        else:
            self._finish_btn.pack(side=tk.RIGHT, padx=(4, 0))

    def _go_next(self):
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
            remove_lf, text="Don\u2019t replace", variable=remove_var, value="",
        ).pack(anchor="w", padx=8, pady=2)

        for name in sorted(known):
            ttk.Radiobutton(
                remove_lf, text=name, variable=remove_var, value=name,
            ).pack(anchor="w", padx=(16, 8), pady=1)

        # Right: Replace with
        add_lf = ttk.LabelFrame(cols, text="Replace with")
        add_lf.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        ttk.Radiobutton(
            add_lf, text="\u2014", variable=replace_var, value="",
        ).pack(anchor="w", padx=8, pady=2)

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
            ).pack(anchor="w", padx=(16, 8), pady=1)

        if not available:
            ttk.Label(
                add_lf, text="No other options available.", foreground=COLORS["fg_dim"],
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

    def _build_cantrip_section(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)

        ttk.Label(
            parent, text="Swap Cantrip",
            font=FONTS["heading"], foreground=COLORS["accent"],
        ).grid(row=0, column=0, sticky="w", padx=4, pady=(2, 0))
        ttk.Label(
            parent,
            text="You may replace one cantrip with another from your class spell list.",
            foreground=COLORS["fg_dim"],
        ).grid(row=1, column=0, sticky="w", padx=4, pady=(0, 4))

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
            parent, text=heading,
            font=FONTS["heading"], foreground=COLORS["accent"],
        ).grid(row=0, column=0, sticky="w", padx=4, pady=(2, 0))
        ttk.Label(
            parent, text=desc, foreground=COLORS["fg_dim"],
        ).grid(row=1, column=0, sticky="w", padx=4, pady=(0, 4))

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
        changed = False

        # ── Long Rest: HP restoration + hit dice restoration ──────
        if self.rest_type == "long":
            self.character.current_hit_points = None  # reset to full
            self.character.temp_hit_points = 0
            self.character.spent_hit_dice.clear()
            changed = True

        # ── Short Rest: hit dice spending ─────────────────────────
        if self.rest_type == "short" and self._hd_spend_vars:
            pool = self.character.hit_dice_pool
            con_mod = self.character.ability_scores.modifier("Constitution")

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

    frame = ttk.Frame(dlg)
    frame.pack(padx=20, pady=16)

    ttk.Label(
        frame, text="Hit Dice Roll Results",
        font=FONTS["heading"], foreground=COLORS["accent"],
    ).pack(anchor="w", pady=(0, 8))

    # Per-class rolls
    for slug in sorted(rolls_by_class, key=lambda s: pool[s][2], reverse=True):
        rolls = rolls_by_class[slug]
        _, _, die = pool[slug]
        class_name = slug.replace("-", " ").title()
        roll_str = ", ".join(str(r) for r in rolls)
        ttk.Label(
            frame,
            text=f"{class_name} (d{die}): {roll_str}",
            foreground=COLORS["fg"],
        ).pack(anchor="w", padx=(8, 0), pady=1)

    raw_total = sum(r for rolls in rolls_by_class.values() for r in rolls)

    # CON bonus line
    con_total = total_dice * con_mod
    if con_mod >= 0:
        con_text = f"+ {con_total} CON ({total_dice} \u00d7 +{con_mod})"
    else:
        con_text = f"\u2212 {abs(con_total)} CON ({total_dice} \u00d7 {con_mod})"
    ttk.Label(
        frame, text=con_text, foreground=COLORS["fg_dim"],
    ).pack(anchor="w", padx=(8, 0), pady=(4, 4))

    # Total
    ttk.Label(
        frame,
        text=f"{healed} HP restored ({old_hp}/{max_hp} \u2192 {new_hp}/{max_hp})",
        font=FONTS["heading"], foreground=COLORS["fg"],
    ).pack(anchor="w", pady=(4, 8))

    ttk.Button(
        frame, text="OK", style="Accent.TButton",
        command=dlg.destroy,
    ).pack(pady=(4, 0))

    # Center over parent
    dlg.update_idletasks()
    w, h = dlg.winfo_reqwidth() + 40, dlg.winfo_reqheight() + 20
    top = parent.winfo_toplevel()
    px, py = top.winfo_rootx(), top.winfo_rooty()
    pw, ph = top.winfo_width(), top.winfo_height()
    dlg.geometry(f"+{max(0, px + (pw - w) // 2)}+{max(0, py + (ph - h) // 2)}")


def _show_short_rest_result_manual(parent, *, healed, old_hp, new_hp, max_hp):
    """Show manual-roll results for short rest hit dice spending."""
    dlg = tk.Toplevel(parent)
    dlg.title("Short Rest — Results")
    dlg.configure(bg=COLORS["bg"])
    dlg.resizable(False, False)

    configure_modal_dialog(dlg, parent)

    frame = ttk.Frame(dlg)
    frame.pack(padx=20, pady=16)

    ttk.Label(
        frame, text="Short Rest Results",
        font=FONTS["heading"], foreground=COLORS["accent"],
    ).pack(anchor="w", pady=(0, 8))

    ttk.Label(
        frame,
        text=f"{healed} HP restored ({old_hp}/{max_hp} \u2192 {new_hp}/{max_hp})",
        font=FONTS["heading"], foreground=COLORS["fg"],
    ).pack(anchor="w", pady=(4, 8))

    ttk.Button(
        frame, text="OK", style="Accent.TButton",
        command=dlg.destroy,
    ).pack(pady=(4, 0))

    dlg.update_idletasks()
    w, h = dlg.winfo_reqwidth() + 40, dlg.winfo_reqheight() + 20
    top = parent.winfo_toplevel()
    px, py = top.winfo_rootx(), top.winfo_rooty()
    pw, ph = top.winfo_width(), top.winfo_height()
    dlg.geometry(f"+{max(0, px + (pw - w) // 2)}+{max(0, py + (ph - h) // 2)}")


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════


def _apply_choice_swap(character, key: str, remove_name: str, replace_name: str):
    """Update the character's class_levels to swap one choice for another."""
    for cl in character.class_levels:
        if (cl.class_slug == key or cl.subclass_slug == key) and remove_name in cl.new_choices:
            cl.new_choices.remove(remove_name)
            cl.new_choices.append(replace_name)
            cl.replaced_choice = remove_name
            return
