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
    """Return True if this character has anything to do on a Long Rest."""
    if _has_swappable_features(character, "long"):
        return True
    if _is_prepared_caster(character) and character.selected_spells:
        return True
    if _can_swap_cantrips_on_rest(character):
        return True
    return False


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

        # Center over parent, same pattern as LevelUpWizard
        self.update_idletasks()
        width, height = 700, 650
        top = parent.winfo_toplevel()
        px = top.winfo_rootx()
        py = top.winfo_rooty()
        pw = top.winfo_width()
        ph = top.winfo_height()
        x = max(0, px + (pw - width) // 2)
        y = max(0, py + (ph - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(600, 450)

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
        self._cantrip_step_frame: ttk.Frame | None = None
        self._spell_step_frame: ttk.Frame | None = None
        self._next_btn: ttk.Button | None = None
        self._back_btn: ttk.Button | None = None
        self._finish_btn: ttk.Button | None = None

        self._build_ui(title)

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
        ttk.Label(
            header,
            text="Optionally swap features or prepared spells before completing this rest.",
            foreground=COLORS["fg_dim"],
        ).pack(anchor="w")

        any_section = False

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
        use_steps = has_cantrip_swap and has_spells  # multi-page only when both

        # Content area row (row=1) gets all the weight
        self.rowconfigure(1, weight=1)

        if use_steps:
            # ── Multi-step: cantrip page and spell page ────────────
            any_section = True

            # Step 1: features (if any) + cantrip swap
            self._cantrip_step_frame = ttk.Frame(self)
            step1 = self._cantrip_step_frame
            step1.columnconfigure(0, weight=1)
            s1_row = 0
            if has_features:
                scroll = ScrollableFrame(step1)
                scroll.grid(row=s1_row, column=0, sticky="nsew", padx=8, pady=2)
                for key, config, known in feature_keys:
                    self._build_feature_section(scroll.inner, key, config, known)
                s1_row += 1

            step1.rowconfigure(s1_row, weight=1)
            cantrip_frame = ttk.Frame(step1)
            cantrip_frame.grid(row=s1_row, column=0, sticky="nsew", padx=8, pady=2)
            self._build_cantrip_section(cantrip_frame)

            # Step 2: leveled spell swap
            self._spell_step_frame = ttk.Frame(self)
            step2 = self._spell_step_frame
            step2.columnconfigure(0, weight=1)
            step2.rowconfigure(0, weight=1)
            spell_frame = ttk.Frame(step2)
            spell_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=2)
            self._build_spell_section(spell_frame)

            self._total_steps = 2
        else:
            # ── Single page: all sections stacked ──────────────────
            next_row = 1
            if has_features:
                any_section = True
                scroll = ScrollableFrame(self)
                scroll.grid(row=next_row, column=0, sticky="nsew", padx=8, pady=2)
                for key, config, known in feature_keys:
                    self._build_feature_section(scroll.inner, key, config, known)
                next_row += 1

            if has_cantrip_swap:
                any_section = True
                cantrip_frame = ttk.Frame(self)
                cantrip_frame.grid(row=next_row, column=0, sticky="nsew", padx=8, pady=2)
                self._build_cantrip_section(cantrip_frame)
                next_row += 1

            if has_spells:
                any_section = True
                self.rowconfigure(next_row, weight=1)
                spell_frame = ttk.Frame(self)
                spell_frame.grid(row=next_row, column=0, sticky="nsew", padx=8, pady=2)
                self._build_spell_section(spell_frame)
                next_row += 1

            if not any_section:
                ttk.Label(
                    self,
                    text="Nothing to swap on this rest.",
                    foreground=COLORS["fg_dim"],
                ).grid(row=1, column=0, pady=20)

        # ── Footer ──────────────────────────────────────────────────
        footer = ttk.Frame(self)
        footer.grid(row=99, column=0, sticky="ew", padx=12, pady=(4, 8))

        self._back_btn = ttk.Button(footer, text="\u25C0 Back", command=self._go_back)
        self._next_btn = ttk.Button(
            footer, text="Next: Swap Spells \u25B6", command=self._go_next
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

        if use_steps:
            self._show_rest_step(1)
        else:
            self._finish_btn.pack(side=tk.RIGHT, padx=(4, 0))

    # ── Step navigation ──────────────────────────────────────────

    def _show_rest_step(self, step: int):
        """Show the given step (1 or 2) and update navigation buttons."""
        self._current_step = step

        # Hide both step frames
        if self._cantrip_step_frame:
            self._cantrip_step_frame.grid_forget()
        if self._spell_step_frame:
            self._spell_step_frame.grid_forget()

        # Hide nav buttons
        self._back_btn.pack_forget()
        self._next_btn.pack_forget()
        self._finish_btn.pack_forget()

        if step == 1:
            self._cantrip_step_frame.grid(row=1, column=0, sticky="nsew")
            self._next_btn.pack(side=tk.RIGHT, padx=(4, 0))
        elif step == 2:
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
