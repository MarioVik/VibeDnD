"""Dialog for taking a Short or Long Rest, allowing feature/spell swaps and hit dice spending."""

from __future__ import annotations

import json
import os
import random
import tkinter as tk
from tkinter import ttk
from typing import Any

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
from models.spell_grant_utils import (
    get_spendable_free_cast_resources,
    restore_free_casts,
    get_selectable_class_cantrip_options,
    get_selectable_class_spell_options,
)
from models.rest_actions import get_available_rest_actions, RestAction
from paths import data_dir

# Load class choices data
_CHOICES_PATH = os.path.join(data_dir(), "class_choices.json")
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

_PREPARED_CASTER_CLASSES = set(_REST_SPELL_SWAP.keys())
CARD_CHECK_STYLE = "Card.TCheckbutton"

def can_short_rest(character) -> bool:
    """Return True - every character can spend hit dice on a Short Rest."""
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
            if cfg["spell_swap"] == "all": return "all"
            mode = cfg["spell_swap"]
    return mode

def can_long_rest(character) -> bool:
    """Return True - every character benefits from a Long Rest (HP restoration)."""
    return True

def _restorable_free_cast_resources(character, game_data, rest_type: str) -> list[dict]:
    resources = get_spendable_free_cast_resources(character, game_data)
    if rest_type == "short":
        return [r for r in resources if r.get("refresh_type") == "short_or_long"]
    if rest_type == "long":
        return [r for r in resources if r.get("refresh_type") in {"long", "short_or_long"}]
    return []

def _is_warlock_pact_caster(character) -> bool:
    """Return True if the character has levels in Warlock (Pact Magic)."""
    for cl in character.class_levels:
        if cl.class_slug == "warlock": return True
    return False

def _has_arcane_recovery(character) -> bool:
    """Return True if the character has Arcane/Natural Recovery (Wizard or Land Druid)."""
    for cl in character.class_levels:
        if cl.class_slug == "wizard": return True
        if cl.class_slug == "druid" and cl.subclass_slug == "circle-of-the-land": return True
    return False

# ======================================================================
# RestDialog
# ======================================================================

class RestDialog(tk.Toplevel):
    """Modal dialog for taking a rest and optionally swapping features/spells."""

    def __init__(self, parent, character, game_data, rest_type: str, on_changed=None):
        super().__init__(parent)
        self.withdraw()  # Hide while building to prevent flicker
        self.character = character
        self.data = game_data
        self.rest_type = rest_type
        self.on_changed = on_changed
        self.character_changed = False

        title = "Short Rest" if rest_type == "short" else "Long Rest"
        self.title(title)
        self.resizable(True, True)
        self.configure(bg=COLORS["bg"])

        configure_modal_dialog(self, parent)

        # UI State
        self._cantrip_panel: SpellSwapPanel | None = None
        self._spell_panel: SpellSwapPanel | None = None
        self._multi_spell_panel: MultiSpellSwapPanel | None = None
        self._spell_swap_mode: str | None = None
        self._available_actions: list[RestAction] = []
        self._action_vars: dict[str, Any] = {}

        self._current_step = 1
        self._total_steps = 1
        self._step_frames: list[ttk.Frame] = []
        self._step_ids: list[str] = []
        
        # Hit dice state
        self._hd_spend_vars: dict[str, tk.IntVar] = {}
        self._hd_roll_mode: tk.StringVar = tk.StringVar(value="auto")
        self._hd_manual_var: tk.StringVar = tk.StringVar(value="")
        self._has_hit_dice = False

        # Recovery state
        self._recovery_vars: dict[str, tk.IntVar] = {}
        self._recovery_max_points = 0
        self._recovery_current_points = tk.IntVar(value=0)

        # Build UI
        self._available_actions = get_available_rest_actions(character, game_data, rest_type)
        if rest_type == "short":
            self._build_short_rest_ui(title)
        else:
            self._build_long_rest_ui(title)

        # Size and center
        # We set a temporary large geometry while hidden so children can measure themselves correctly
        self.geometry("1000x800")
        self.update_idletasks()
        
        max_w, max_h = 0, 0
        for frame in self._step_frames:
            # We must map the frame briefly (behind the scenes) to get its requested size
            frame.grid(row=1, column=0, sticky="nsew")
            frame.update_idletasks()
            max_w = max(max_w, frame.winfo_reqwidth())
            max_h = max(max_h, frame.winfo_reqheight())
            frame.grid_forget()

        self._show_rest_step(1)
        width = max(640, max_w + 40)
        height = max(480, max_h + 120)
        
        # Center and show using explicit width/height to avoid hidden-window measurement errors
        center_dialog_over_parent(self, parent, width=width, height=height)
        self.deiconify()
        self.focus_force()

    def _append_rest_step(self, step_id: str, frame: ttk.Frame):
        self._step_ids.append(step_id)
        self._step_frames.append(frame)

    def _current_step_id(self) -> str:
        idx = self._current_step - 1
        return self._step_ids[idx] if 0 <= idx < len(self._step_ids) else ""

    # -- Building UI ----------------------------------------------------

    def _get_spell_dict(self, name: str) -> dict | None:
        """Helper to turn a spell name into a full dictionary from GameData."""
        if not hasattr(self, "_spell_cache"):
            self._spell_cache = {s["name"]: s for s in self.data.spells}
        return self._spell_cache.get(name)

    def _get_all_class_spells(self) -> list[dict]:
        """Get all spells available to the character's classes up to their max slot level."""
        cls = self.character.character_class or {}
        class_name = cls.get("name", "")
        if not class_name:
            return []
            
        slots = self.character.current_spell_slots(self.data)
        max_lvl = max((int(k) for k in slots.keys() if k.isdigit()), default=0)
        
        if max_lvl == 0:
            _, pact_lvl = self.character.current_pact_magic(self.data)
            max_lvl = pact_lvl or 0
        
        return self.data.spells_for_class(class_name, max_level=max_lvl)

    def _build_long_rest_ui(self, title: str):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Header
        header = GradientHeader(self, min_height=56)
        header.grid(row=0, column=0, sticky="ew")
        tk.Label(header.inner, text=title, font=FONTS["heading_serif_lg"], fg=COLORS["fg"], bg=COLORS["bg_hero"]).pack(side=tk.LEFT, padx=SPACING["lg"])

        has_cantrip_swap = _can_swap_cantrips_on_rest(self.character)
        self._spell_swap_mode = _spell_swap_mode(self.character)
        
        # Check if character actually HAS prepared spells to swap
        has_spells = (
            self._spell_swap_mode is not None 
            and (self.character.selected_spells or self.character.selected_cantrips)
        )
        has_decisions = bool(self._available_actions)

        # Step 1: Info
        info_f = ttk.Frame(self)
        self._build_long_rest_info_step(info_f, has_cantrip_swap=has_cantrip_swap, has_spells=has_spells, has_decisions=has_decisions)
        self._append_rest_step("info", info_f)

        # Step 2: Decisions
        if has_decisions:
            dec_f = ttk.Frame(self)
            self._build_decisions_step(dec_f)
            self._append_rest_step("decisions", dec_f)

        # Step 3: Swaps
        if has_cantrip_swap:
            c_f = ttk.Frame(self)
            self._build_cantrip_section(c_f)
            self._append_rest_step("cantrips", c_f)
        if has_spells:
            s_f = ttk.Frame(self)
            self._build_spell_section(s_f)
            self._append_rest_step("spells", s_f)

        self._total_steps = len(self._step_frames)
        self._build_footer()

    def _build_long_rest_info_step(self, parent, *, has_cantrip_swap, has_spells, has_decisions):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        scroll = ScrollableFrame(parent)
        scroll.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["lg"])
        
        SectionHeader(scroll.inner, text="Long Rest Effects").pack(fill=tk.X)
        effects = ["Hit points and all spent hit dice are fully restored."]
        if self.character.temp_hit_points > 0:
            effects.append(f"Temporary HP ({self.character.temp_hit_points}) will be lost.")
        for action in self._available_actions:
            effects.append(f"Decision: {action.name}")
        if has_cantrip_swap: effects.append("You may swap one cantrip.")
        if has_spells:
            mode = "any number of" if self._spell_swap_mode == "all" else "one"
            effects.append(f"You may change {mode} prepared spells.")
        effects.append("All spell slots and pact slots are fully restored.")

        card = CardFrame(scroll.inner, pad=SPACING["lg"])
        card.pack(fill=tk.X, expand=True)
        for text in effects:
            tk.Label(card.inner, text=f"- {text}", font=FONTS["body"], fg=COLORS["fg"], bg=COLORS["bg_surface"], wraplength=520, justify=tk.LEFT).pack(anchor="w", pady=2)

    def _build_short_rest_ui(self, title: str):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        header = GradientHeader(self, min_height=56)
        header.grid(row=0, column=0, sticky="ew")
        tk.Label(header.inner, text=title, font=FONTS["heading_serif_lg"], fg=COLORS["fg"], bg=COLORS["bg_hero"]).pack(side=tk.LEFT, padx=SPACING["lg"])

        has_decisions = bool(self._available_actions)
        self._has_hit_dice = self.character.total_hit_dice_remaining > 0

        info_f = ttk.Frame(self)
        self._build_short_rest_info_step(info_f, has_decisions=has_decisions)
        self._append_rest_step("info", info_f)

        if self._has_hit_dice:
            hd_f = ttk.Frame(self)
            self._build_hit_dice_step(hd_f)
            self._append_rest_step("hit_dice", hd_f)

        if has_decisions:
            dec_f = ttk.Frame(self)
            self._build_decisions_step(dec_f)
            self._append_rest_step("decisions", dec_f)

        if _has_arcane_recovery(self.character) and not self.character.arcane_recovery_used:
            rec_f = ttk.Frame(self)
            self._build_recovery_step(rec_f)
            self._append_rest_step("recovery", rec_f)

        self._total_steps = len(self._step_frames)
        self._build_footer()

    def _build_short_rest_info_step(self, parent, *, has_decisions):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        scroll = ScrollableFrame(parent)
        scroll.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["lg"])
        
        SectionHeader(scroll.inner, text="Short Rest Effects").pack(fill=tk.X)
        effects = [f"Hit Dice remaining: {self.character.total_hit_dice_remaining}"]
        for action in self._available_actions:
            effects.append(f"Decision: {action.name}")
        if _is_warlock_pact_caster(self.character):
            effects.append("All pact slots are fully restored.")
        if _has_arcane_recovery(self.character) and not self.character.arcane_recovery_used:
            effects.append("You may use Arcane Recovery to restore spell slots.")

        card = CardFrame(scroll.inner, pad=SPACING["lg"])
        card.pack(fill=tk.X, expand=True)
        for text in effects:
            tk.Label(card.inner, text=f"- {text}", font=FONTS["body"], fg=COLORS["fg"], bg=COLORS["bg_surface"], wraplength=520, justify=tk.LEFT).pack(anchor="w", pady=2)

    def _build_decisions_step(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        scroll = ScrollableFrame(parent)
        scroll.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["lg"])
        for action in self._available_actions:
            self._build_action_card(scroll.inner, action)

    def _build_action_card(self, parent, action: RestAction):
        card = CardFrame(parent, pad=SPACING["md"])
        card.pack(fill=tk.X, pady=(0, SPACING["md"]))
        inner = card.inner

        tk.Label(inner, text=action.name, font=FONTS["label_upper_bold"], fg=COLORS["fg"], bg=COLORS["bg_surface"]).pack(anchor="w")
        tk.Label(inner, text=action.description, font=FONTS["body_small"], fg=COLORS["fg_dim"], bg=COLORS["bg_surface"], wraplength=500, justify=tk.LEFT).pack(anchor="w", pady=(0, SPACING["sm"]))

        if action.kind == "choice":
            var = tk.StringVar(value=action.current_value or "")
            self._action_vars[action.id] = var
            if len(action.options) < 5:
                for opt in action.options:
                    ttk.Radiobutton(inner, text=opt, variable=var, value=opt, style="Card.TRadiobutton").pack(anchor="w")
            else:
                ttk.Combobox(inner, textvariable=var, values=action.options, state="readonly", width=40).pack(anchor="w", pady=2)
        elif action.kind == "checklist":
            var = tk.BooleanVar(value=False)
            self._action_vars[action.id] = var
            ttk.Checkbutton(inner, text="Done / Acknowledge", variable=var, style=CARD_CHECK_STYLE).pack(anchor="w")
        elif action.kind == "button":
            ttk.Button(inner, text=action.name, style="Accent.TButton", command=lambda a=action: self._execute_rest_button_action(a)).pack(side=tk.LEFT, pady=SPACING["sm"])

    def _execute_rest_button_action(self, action: RestAction):
        if action.apply(self.character, self.data, None):
            AlertDialog(self, "Success", f"Action performed: {action.name}")
            self.character_changed = True

    # -- Components -----------------------------------------------------

    def _build_cantrip_section(self, parent):
        body = ttk.Frame(parent)
        body.pack(fill=tk.BOTH, expand=True)
        SectionHeader(body, text="Cantrip Swap").pack(fill=tk.X, padx=SPACING["lg"])

        # Current cantrips
        forget_names = getattr(self.character, "selected_cantrips", []) or []
        forget_dicts = [d for n in forget_names if (d := self._get_spell_dict(n))]
        
        # Available cantrips
        learn_names = get_selectable_class_cantrip_options(self.character, self.data)
        learn_dicts = [d for n in learn_names if (d := self._get_spell_dict(n))]

        self._cantrip_panel = SpellSwapPanel(
            body,
            forget_spells=[],
            learn_spells=[],
            forget_cantrips=forget_dicts,
            learn_cantrips=learn_dicts,
            allow_cantrips=True
        )

    def _build_spell_section(self, parent):
        body = ttk.Frame(parent)
        body.pack(fill=tk.BOTH, expand=True)
        SectionHeader(body, text="Prepared Spells").pack(fill=tk.X, padx=SPACING["lg"])

        forget_names = getattr(self.character, "selected_spells", []) or []
        forget_dicts = [d for n in forget_names if (d := self._get_spell_dict(n))]
        
        all_class_spells = self._get_all_class_spells()
        learn_dicts = [s for s in all_class_spells if s["name"] not in forget_names and s.get("level", 0) > 0]

        if self._spell_swap_mode == "all":
            self._multi_spell_panel = MultiSpellSwapPanel(
                body,
                forget_spells=forget_dicts,
                learn_spells=learn_dicts
            )
        else:
            self._spell_panel = SpellSwapPanel(
                body,
                forget_spells=forget_dicts,
                learn_spells=learn_dicts,
                allow_cantrips=False
            )

    def _build_hit_dice_step(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        scroll = ScrollableFrame(parent)
        scroll.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["lg"])
        inner = scroll.inner
        
        SectionHeader(inner, text="Spend Hit Dice").pack(fill=tk.X)
        hp_card = CardFrame(inner, pad=SPACING["md"])
        hp_card.pack(fill=tk.X, pady=SPACING["md"])
        
        cur = self.character.effective_current_hp
        mx = self.character.hit_points
        self._hp_update_label = tk.Label(hp_card.inner, text=f"HP: {cur} / {mx}", font=FONTS["heading"], fg=COLORS["fg"], bg=COLORS["bg_surface"])
        self._hp_update_label.pack(anchor="w")

        pool = self.character.hit_dice_pool
        for slug in sorted(pool, key=lambda s: pool[s][2], reverse=True):
            rem, tot, die = pool[slug]
            if tot == 0: continue
            row = tk.Frame(inner, bg=COLORS["bg"])
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=f"{slug.title()} (d{die}): {rem} left", font=FONTS["body"], fg=COLORS["fg"], bg=COLORS["bg"]).pack(side=tk.LEFT)
            var = tk.IntVar(value=0)
            self._hd_spend_vars[slug] = var
            ttk.Spinbox(row, from_=0, to=rem, textvariable=var, width=5).pack(side=tk.RIGHT)

        mode_f = tk.Frame(inner, bg=COLORS["bg"])
        mode_f.pack(fill=tk.X, pady=SPACING["md"])
        ttk.Radiobutton(mode_f, text="Auto Roll", variable=self._hd_roll_mode, value="auto").pack(side=tk.LEFT)
        ttk.Radiobutton(mode_f, text="Manual", variable=self._hd_roll_mode, value="manual").pack(side=tk.LEFT, padx=10)
        ttk.Entry(mode_f, textvariable=self._hd_manual_var, width=8).pack(side=tk.LEFT)

    def _build_recovery_step(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        scroll = ScrollableFrame(parent)
        scroll.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["lg"])
        inner = scroll.inner
        SectionHeader(inner, text="Arcane Recovery").pack(fill=tk.X)
        max_pts = (self.character.level + 1) // 2
        tk.Label(inner, text=f"Recover up to {max_pts} levels of slots.", font=FONTS["body"], fg=COLORS["fg"], bg=COLORS["bg"]).pack(anchor="w", pady=SPACING["sm"])
        
        for lvl in range(1, 6):
            spent = self.character.used_spell_slots.get(str(lvl), 0)
            if spent <= 0: continue
            row = tk.Frame(inner, bg=COLORS["bg"])
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=f"Level {lvl} slots ({spent} spent)", font=FONTS["body"], fg=COLORS["fg"], bg=COLORS["bg"]).pack(side=tk.LEFT)
            var = tk.IntVar(value=0)
            self._recovery_vars[str(lvl)] = var
            ttk.Spinbox(row, from_=0, to=spent, textvariable=var, width=5).pack(side=tk.RIGHT)

    # -- Nav ------------------------------------------------------------

    def _build_footer(self):
        footer = tk.Frame(self, bg=COLORS["bg_surface"], height=60)
        footer.grid(row=99, column=0, sticky="ew")
        footer.grid_propagate(False)
        inner = tk.Frame(footer, bg=COLORS["bg_surface"])
        inner.pack(fill=tk.BOTH, expand=True, padx=SPACING["lg"])

        self._back_btn = ttk.Button(inner, text="Back", command=self._go_back)
        self._back_btn.pack(side=tk.LEFT, pady=10)
        
        self._finish_btn = ttk.Button(inner, text="Finish Rest", style="Accent.TButton", command=self._on_confirm)
        self._next_btn = ttk.Button(inner, text="Next", style="Accent.TButton", command=self._go_next)
        self._next_btn.pack(side=tk.RIGHT, pady=10)
        
        # Center section: Step counter + progress bar
        center_frame = tk.Frame(inner, bg=COLORS["bg_surface"])
        center_frame.pack(side=tk.TOP, pady=5)
        
        self._step_label = tk.Label(center_frame, text="", font=FONTS["body_small"], fg=COLORS["fg_dim"], bg=COLORS["bg_surface"])
        self._step_label.pack(side=tk.LEFT, padx=(0, SPACING["md"]))
        
        self._progress_bar = HPBar(center_frame, width=160, height=6)
        self._progress_bar.pack(side=tk.LEFT)

    def _show_rest_step(self, num: int):
        for f in self._step_frames: f.grid_forget()
        self._current_step = num
        self._step_frames[num-1].grid(row=1, column=0, sticky="nsew")
        self._back_btn.configure(state="normal" if num > 1 else "disabled")
        if num == self._total_steps:
            self._next_btn.pack_forget()
            self._finish_btn.pack(side=tk.RIGHT, pady=10)
        else:
            self._finish_btn.pack_forget()
            self._next_btn.pack(side=tk.RIGHT, pady=10)
        self._step_label.config(text=f"Step {num} of {self._total_steps}")
        self._progress_bar.set_hp(num, self._total_steps)

    def _go_next(self):
        if self._validate_current_step(): self._show_rest_step(self._current_step + 1)
    def _go_back(self):
        self._show_rest_step(self._current_step - 1)

    def _validate_current_step(self) -> bool:
        if self._current_step_id() == "decisions":
            for action in self._available_actions:
                if action.id == "feat:zhentarim_tactics":
                    var = self._action_vars.get(action.id)
                    if var and not var.get():
                        AlertDialog(self, "Required Selection", f"Please select a skill for {action.name}.")
                        return False
        if self._current_step_id() == "cantrips" and self._cantrip_panel:
            if self._cantrip_panel.has_incomplete_swap():
                AlertDialog(
                    self,
                    "Incomplete Swap",
                    "You chose a cantrip to replace but did not pick a new cantrip. "
                    "Select one on the right, or clear the forget selection on the left.",
                )
                return False
        if self._current_step_id() == "spells" and self._spell_panel:
            if self._spell_panel.has_incomplete_swap():
                AlertDialog(
                    self,
                    "Incomplete Swap",
                    "You chose a spell to replace but did not pick a new spell. "
                    "Select one on the right, or clear the forget selection on the left.",
                )
                return False
        return True

    def _on_confirm(self):
        if self._cantrip_panel and self._cantrip_panel.has_incomplete_swap():
            AlertDialog(
                self,
                "Incomplete Swap",
                "You chose a cantrip to replace but did not pick a new cantrip. "
                "Select one on the right, or clear the forget selection on the left.",
            )
            return
        if self._spell_panel and self._spell_panel.has_incomplete_swap():
            AlertDialog(
                self,
                "Incomplete Swap",
                "You chose a spell to replace but did not pick a new spell. "
                "Select one on the right, or clear the forget selection on the left.",
            )
            return
        if not self._validate_current_step():
            return
        changed = self.character_changed
        
        if self.rest_type == "long":
            self.character.current_hit_points = None
            self.character.temp_hit_points = 0
            self.character.spent_hit_dice.clear()
            self.character.reset_spell_slots()
            restore_free_casts(self.character, self.data, "long")
            restore_feature_resources(self.character, self.data, "long")
            self.character.arcane_recovery_used = False
            changed = True
        else:
            # Short Rest: hit dice spending
            pool = self.character.hit_dice_pool
            con_mod = get_effective_modifier(self.character, "Constitution")
            
            dice_to_spend = {}
            for slug, var in self._hd_spend_vars.items():
                count = var.get()
                if count > 0:
                    dice_to_spend[slug] = min(count, pool.get(slug, [0])[0])
            
            total_dice = sum(dice_to_spend.values())
            if total_dice > 0:
                healed = 0
                if self._hd_roll_mode.get() == "manual":
                    try:
                        rolled = int(self._hd_manual_var.get())
                        healed = max(0, rolled + (total_dice * con_mod))
                    except: healed = 0
                else:
                    for slug, count in dice_to_spend.items():
                        die = pool[slug][2]
                        healed += sum(random.randint(1, die) for _ in range(count))
                    healed = max(0, healed + (total_dice * con_mod))
                
                for slug, count in dice_to_spend.items():
                    self.character.spent_hit_dice[slug] = self.character.spent_hit_dice.get(slug, 0) + count
                
                cur = self.character.effective_current_hp
                self.character.current_hit_points = min(self.character.hit_points, cur + healed)
                changed = True

            # Short Rest: features/pact
            if _is_warlock_pact_caster(self.character):
                self.character.used_pact_slots = 0
                changed = True
            restore_free_casts(self.character, self.data, "short")
            restore_feature_resources(self.character, self.data, "short")
            
            # Arcane Recovery
            recovered_any = False
            for lvl_str, var in self._recovery_vars.items():
                count = var.get()
                if count > 0:
                    self.character.recover_spell_slots(lvl_str, count)
                    recovered_any = True
            if recovered_any:
                self.character.arcane_recovery_used = True
                changed = True

        for aid, var in self._action_vars.items():
            val = var.get()
            if val:
                action = next((a for a in self._available_actions if a.id == aid), None)
                if action and action.apply(self.character, self.data, val): changed = True

        if self._cantrip_panel:
            f, l = self._cantrip_panel.forget_var.get(), self._cantrip_panel.learn_var.get()
            if f and l:
                if f in self.character.selected_cantrips: self.character.selected_cantrips.remove(f)
                self.character.selected_cantrips.append(l)
                changed = True
        
        if self._multi_spell_panel:
            f_names, l_names = self._multi_spell_panel.forget_names, self._multi_spell_panel.learn_names
            if len(f_names) == len(l_names) > 0:
                for n in f_names:
                    if n in self.character.selected_spells: self.character.selected_spells.remove(n)
                self.character.selected_spells.extend(l_names)
                changed = True
        elif self._spell_panel:
            f, l = self._spell_panel.forget_var.get(), self._spell_panel.learn_var.get()
            if f and l:
                if f in self.character.selected_spells: self.character.selected_spells.remove(f)
                self.character.selected_spells.append(l)
                changed = True

        if changed and self.on_changed: self.on_changed()
        self.destroy()

# -- Helpers --------------------------------------------------------

def _apply_choice_swap(character, key, remove_name, replace_name, sub=""):
    for cl in character.class_levels:
        if (cl.class_slug == key or cl.subclass_slug == key) and remove_name in cl.new_choices:
            cl.new_choices.remove(remove_name)
            cl.new_choices.append(replace_name)
            cl.replaced_choice = remove_name
            cl.choice_sub_selections.pop(remove_name, None)
            if sub: cl.choice_sub_selections[replace_name] = sub
            return True
    return False
