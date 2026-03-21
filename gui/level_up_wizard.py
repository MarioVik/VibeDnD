"""Level-up wizard dialog for advancing a character by one level.

Two-step flow:
  Step 1 – class features, HP, ASI / feat, subclass
  Step 2 – spell selection (only shown when the level grants new spells)
"""

import json
import os
import re
import tkinter as tk
from tkinter import ttk, messagebox

from gui.theme import COLORS, FONTS
from gui.spell_swap_panel import SpellSwapPanel
from gui.widgets import (
    ScrollableFrame,
    WrappingLabel,
    ConfirmDialog,
    AlertDialog,
    configure_modal_dialog,
    _wheel_units,
)
from models.character import Character
from models.class_level import ClassLevel

# Load class choices data (maneuvers, invocations, plans, arcane shots)
_CHOICES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "class_choices.json")
try:
    with open(_CHOICES_PATH, encoding="utf-8") as _f:
        _CLASS_CHOICES: dict = json.load(_f)
except Exception:
    _CLASS_CHOICES = {}

_SLOT_ORDER = {
    "1st": 1,
    "2nd": 2,
    "3rd": 3,
    "4th": 4,
    "5th": 5,
    "6th": 6,
    "7th": 7,
    "8th": 8,
    "9th": 9,
}

# Classes that can swap one cantrip/spell when gaining a level
_SWAP_CLASSES = {"bard", "sorcerer", "warlock"}


class LevelUpWizard(tk.Toplevel):
    """Modal dialog that walks the player through gaining one level."""

    def __init__(self, parent, character: Character, game_data, on_complete=None):
        super().__init__(parent)
        self.character = character
        self.data = game_data
        self.on_complete = on_complete

        self.title(f"Level Up - {character.name}")
        # Center the window over the parent main window
        self.update_idletasks()
        width = 1400
        height = 1000

        # Use winfo_toplevel() to get coordinates relative to the main app window
        top = parent.winfo_toplevel()
        parent_x = top.winfo_rootx()
        parent_y = top.winfo_rooty()
        parent_width = top.winfo_width()
        parent_height = top.winfo_height()

        x = parent_x + (parent_width // 2) - (width // 2)
        y = parent_y + (parent_height // 2) - (height // 2)

        # Ensure it's not off-screen
        x = max(0, x)
        y = max(0, y)

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(1000, 750)
        self.configure(bg=COLORS["bg"])

        configure_modal_dialog(self, top)

        # Determine what the next level will be
        self.new_total_level = character.level + 1
        self.primary_class_slug = (
            character.character_class.get("slug", "")
            if character.character_class
            else ""
        )
        self.class_slug = self.primary_class_slug
        self.class_var = tk.StringVar(value=self.class_slug)

        self._update_level_data()

        # Choices to collect
        self.hp_choice = tk.IntVar(value=0)
        self.hp_mode = tk.StringVar(value="average")   # "average" | "max" | "manual"
        self.hp_manual_var = tk.StringVar(value="")
        self.subclass_var = tk.StringVar()
        self.feat_var = tk.StringVar()
        self.selected_new_cantrips: list[str] = []
        self.selected_new_spells: list[str] = []

        # Spell-step guard flags
        self._updating_cantrips = False
        self._updating_spells = False
        self.cantrip_vars: dict[str, dict] = {}
        self.spell_vars: dict[str, dict] = {}
        self.cantrip_checkbuttons: dict[str, ttk.Checkbutton] = {}
        self.spell_checkbuttons: dict[str, ttk.Checkbutton] = {}

        # Swap-step state
        self.swap_out_cantrip: str | None = None
        self.swap_in_cantrip: str | None = None
        self.swap_out_spell: str | None = None
        self.swap_in_spell: str | None = None

        # Class choices step state (maneuvers, invocations, plans, arcane shots)
        self.selected_new_choices: set[str] = set()
        self.replace_out_var = tk.StringVar(value="")
        self.replace_in_var = tk.StringVar(value="")
        self._updating_choices = False
        self.choice_vars: dict[str, tk.BooleanVar] = {}
        self.choice_checkbuttons: dict[str, ttk.Checkbutton] = {}

        # Subclass proficiency/expertise step state
        self.prof_grant_vars: list[tk.StringVar] = []  # dropdown vars for proficiency picks
        self.expertise_grant_vars: list[tk.StringVar] = []  # dropdown vars for expertise picks

        self._build_ui()

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def _update_level_data(self):
        """Update progression data for the currently selected class."""
        self.class_slug = self.class_var.get()
        self.new_class_level = self.character.class_level_in(self.class_slug) + 1
        self.progression = self.data.get_progression(self.class_slug)
        self.level_data = self.data.get_level_data(
            self.class_slug, self.new_class_level
        )

        self.selected_class_data = None
        for cls in self.data.classes:
            if cls.get("slug") == self.class_slug:
                self.selected_class_data = cls
                break

    def _spell_deltas(self):
        """Return (new_cantrip_count, new_prepared_count, max_spell_level)."""
        if not self.level_data:
            return 0, 0, 0
        prev = self.data.get_level_data(self.class_slug, self.new_class_level - 1)
        if not prev:
            return 0, 0, 0

        def to_int(v):
            if not v:
                return 0
            if isinstance(v, int):
                return v
            s = str(v).strip()
            if not s or s == "-":
                return 0
            try:
                return int(s.replace("+", ""))
            except:
                return 0

        curr_cantrips = to_int(self.level_data.get("cantrips"))
        prev_cantrips = to_int(prev.get("cantrips"))
        curr_prepared = to_int(self.level_data.get("prepared_spells"))
        prev_prepared = to_int(prev.get("prepared_spells"))

        curr_slots = self.level_data.get("spell_slots") or {}
        max_spell_level = max((_SLOT_ORDER.get(k, 0) for k in curr_slots), default=0)
        # Pact Magic casters (Warlock) use pact_slot_level instead of spell_slots
        pact_level = to_int(self.level_data.get("pact_slot_level"))
        if pact_level > max_spell_level:
            max_spell_level = pact_level

        return (
            max(curr_cantrips - prev_cantrips, 0),
            max(curr_prepared - prev_prepared, 0),
            max_spell_level,
        )

    def _has_new_spell_options(self) -> bool:
        new_cantrips, new_prepared, _ = self._spell_deltas()
        return new_cantrips > 0 or new_prepared > 0

    def _can_swap(self) -> tuple[bool, bool]:
        """Return (can_swap_cantrips, can_swap_spells)."""
        if self.class_slug not in _SWAP_CLASSES:
            return False, False
        has_cantrips = len(self.character.selected_cantrips) > 0
        has_spells = len(self.character.selected_spells) > 0
        return has_cantrips, has_spells

    def _has_swap_step(self) -> bool:
        can_c, can_s = self._can_swap()
        return can_c or can_s

    def _get_current_subclass(self) -> str | None:
        """Return the subclass slug active for self.class_slug (existing or being chosen now)."""
        if self.subclass_var.get():
            sub_name = self.subclass_var.get().replace(" (PHB)", "")
            for sc in self.data.get_subclasses_for_class(self.class_slug):
                if sc["name"] == sub_name:
                    return sc["slug"]
        for cl in self.character.class_levels:
            if cl.class_slug == self.class_slug and cl.subclass_slug:
                return cl.subclass_slug
        return None

    def _get_choices_config(self) -> dict | None:
        """Return choice config dict if this level-up grants class choices, else None."""
        level_str = str(self.new_class_level)
        # Check class-level choices (warlock, artificer)
        cfg = _CLASS_CHOICES.get(self.class_slug)
        if cfg and cfg.get("gains_by_level", {}).get(level_str):
            return cfg
        # Check subclass-level choices (battle-master, arcane-archer2)
        sub = self._get_current_subclass()
        if sub:
            cfg = _CLASS_CHOICES.get(sub)
            if cfg and cfg.get("gains_by_level", {}).get(level_str):
                return cfg
        return None

    def _has_class_choices(self) -> bool:
        return self._get_choices_config() is not None

    def _get_known_choices(self, key: str) -> list[str]:
        """Return the character's current choices for class/subclass key."""
        result: list[str] = []
        for cl in self.character.class_levels:
            if cl.class_slug == key or cl.subclass_slug == key:
                result.extend(cl.new_choices)
                if cl.replaced_choice and cl.replaced_choice in result:
                    result.remove(cl.replaced_choice)
        return result

    def _get_active_pool(self, config: dict) -> str | None:
        """Return the active pool name for the current level, or None if no pools."""
        return config.get("pools", {}).get(str(self.new_class_level))

    def _get_available_options(self, config: dict) -> list[dict]:
        """Return options from config that are available to pick right now."""
        options = config.get("options", [])
        # Pool filtering (Tattooed Warrior, Hunter — different option sets per level)
        active_pool = self._get_active_pool(config)
        if active_pool:
            options = [o for o in options if o.get("pool") == active_pool]
        # Determine which key (class or subclass) this config belongs to
        key = self.class_slug
        for k, v in _CLASS_CHOICES.items():
            if v is config:
                key = k
                break
        known = set(self._get_known_choices(key))
        result = []
        for opt in options:
            name = opt["name"]
            # Already known — exclude from new picks (still shows in replace)
            if name in known:
                continue
            # Warlock prerequisite level check
            prereq = opt.get("prerequisite_level")
            if prereq and self.new_class_level < prereq:
                continue
            # Artificer min_level check
            min_lvl = opt.get("min_level")
            if min_lvl and self.new_class_level < min_lvl:
                continue
            result.append(opt)
        return result

    # ------------------------------------------------------------------
    # Subclass proficiency/expertise grants
    # ------------------------------------------------------------------

    def _get_subclass_grants(self) -> list[dict]:
        """Return grant info for subclass features at the current level.

        Each dict has keys: feature_name, grants_proficiency, grants_expertise.
        """
        sub_slug = self._get_current_subclass()
        if not sub_slug:
            return []
        subclass = self.data.get_subclass(self.class_slug, sub_slug)
        if not subclass:
            return []
        feats = subclass.get("features", {}).get(str(self.new_class_level), [])
        grants = []
        for feat in feats:
            gp = feat.get("grants_proficiency")
            ge = feat.get("grants_expertise")
            if gp or ge:
                grants.append({
                    "feature_name": feat["name"],
                    "grants_proficiency": gp,
                    "grants_expertise": ge,
                })
        return grants

    def _has_proficiency_step(self) -> bool:
        """True if subclass grants require player choices."""
        for g in self._get_subclass_grants():
            gp = g.get("grants_proficiency")
            ge = g.get("grants_expertise")
            if gp and not gp.get("automatic"):
                return True
            if ge and not ge.get("automatic") and not ge.get("from_granted"):
                return True
        return False

    def _build_proficiency_step(self):
        """Build the proficiency/expertise selection UI."""
        for w in self.step_prof_frame.winfo_children():
            w.destroy()
        self.prof_grant_vars.clear()
        self.expertise_grant_vars.clear()

        grants = self._get_subclass_grants()
        if not grants:
            return

        existing_profs = self.character.all_skill_proficiencies

        ttk.Label(
            self.step_prof_frame,
            text="Subclass Proficiencies",
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(8, 4))

        for grant in grants:
            gp = grant.get("grants_proficiency")
            ge = grant.get("grants_expertise")

            if gp and gp.get("automatic") and ge and ge.get("automatic"):
                # Automatic grant — just show info text
                ttk.Label(
                    self.step_prof_frame,
                    text=f"{grant['feature_name']}: automatically gained",
                    foreground=COLORS["fg"],
                ).pack(anchor="w", padx=12, pady=4)
                continue

            ttk.Label(
                self.step_prof_frame,
                text=grant["feature_name"],
                font=FONTS["subheading"],
                foreground=COLORS["fg_bright"],
            ).pack(anchor="w", padx=4, pady=(8, 2))

            if gp and not gp.get("automatic"):
                count = gp.get("count", 1)
                available = [s for s in gp["skills"] if s not in existing_profs]

                ttk.Label(
                    self.step_prof_frame,
                    text=f"Choose {count} skill proficiency(s):",
                    foreground=COLORS["fg"],
                ).pack(anchor="w", padx=12, pady=(0, 2))

                for i in range(count):
                    var = tk.StringVar(value="")
                    self.prof_grant_vars.append(var)
                    combo = ttk.Combobox(
                        self.step_prof_frame,
                        textvariable=var,
                        values=available,
                        state="readonly",
                        width=30,
                    )
                    combo.pack(anchor="w", padx=24, pady=2)

                if ge and ge.get("from_granted"):
                    ttk.Label(
                        self.step_prof_frame,
                        text="(You also gain Expertise in the chosen skills.)",
                        foreground=COLORS["fg_dim"],
                        font=("Segoe UI", 9, "italic"),
                    ).pack(anchor="w", padx=12, pady=(2, 0))

            if ge and not ge.get("automatic") and not ge.get("from_granted"):
                count = ge.get("count", 1)
                available = ge.get("skills", [])

                ttk.Label(
                    self.step_prof_frame,
                    text=f"Choose {count} skill expertise(s):",
                    foreground=COLORS["fg"],
                ).pack(anchor="w", padx=12, pady=(4, 2))

                for i in range(count):
                    var = tk.StringVar(value="")
                    self.expertise_grant_vars.append(var)
                    combo = ttk.Combobox(
                        self.step_prof_frame,
                        textvariable=var,
                        values=available,
                        state="readonly",
                        width=30,
                    )
                    combo.pack(anchor="w", padx=24, pady=2)

    def _validate_proficiency_step(self) -> bool:
        """Ensure all required proficiency/expertise selections are made."""
        for var in self.prof_grant_vars:
            if not var.get():
                AlertDialog(
                    self,
                    "Missing Choice",
                    "Please select all skill proficiencies.",
                )
                return False
        for var in self.expertise_grant_vars:
            if not var.get():
                AlertDialog(
                    self,
                    "Missing Choice",
                    "Please select all skill expertise choices.",
                )
                return False
        # Check for duplicates among proficiency picks
        picks = [v.get() for v in self.prof_grant_vars if v.get()]
        if len(picks) != len(set(picks)):
            AlertDialog(
                self,
                "Duplicate Choice",
                "Please choose different skills for each proficiency.",
            )
            return False
        return True

    # ------------------------------------------------------------------
    # UI skeleton
    # ------------------------------------------------------------------

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────
        self.header_frame = ttk.Frame(self)
        self.header_frame.pack(fill=tk.X, padx=16, pady=(16, 8))

        self.header_label = ttk.Label(
            self.header_frame,
            text=self._header_text(),
            font=("Segoe UI", 16, "bold"),
            foreground=COLORS["accent"],
        )
        self.header_label.pack(side=tk.LEFT)

        ttk.Label(
            self.header_frame,
            text=f"(Total Level {self.new_total_level})",
            font=FONTS["body"],
            foreground=COLORS["fg_dim"],
        ).pack(side=tk.LEFT, padx=8)

        # ── Multiclass selector ───────────────────────────────────
        self.mc_frame = ttk.Frame(self)
        self.mc_frame.pack(fill=tk.X, padx=16, pady=(0, 4))

        ttk.Label(self.mc_frame, text="Class:", foreground=COLORS["fg"]).pack(
            side=tk.LEFT
        )
        class_options = [cls["slug"] for cls in self.data.classes]
        self.class_combo = ttk.Combobox(
            self.mc_frame,
            textvariable=self.class_var,
            values=class_options,
            state="readonly",
            width=20,
        )
        self.class_combo.pack(side=tk.LEFT, padx=8)

        self.prereq_label = ttk.Label(self.mc_frame, text="", foreground="#e74c3c")
        self.prereq_label.pack(side=tk.LEFT, padx=8)

        self.class_var.trace_add("write", self._on_class_change)

        # ── Content container (holds step frames) ─────────────────
        self.content_container = ttk.Frame(self)

        # Step 1 – features / HP / ASI / subclass
        self.step1_scroll = ScrollableFrame(self.content_container)
        self.step1_content = self.step1_scroll.inner

        # Step 1.5 – subclass proficiency/expertise selection (built lazily)
        self.step_prof_frame = ttk.Frame(self.content_container)

        # Step 2 – class choices (built lazily; maneuvers, invocations, plans, etc.)
        self.step2b_frame = ttk.Frame(self.content_container)

        # Step 3 – spell selection (built lazily)
        self.step2_frame = ttk.Frame(self.content_container)

        # Step 4 – spell swap (built lazily)
        self.step3_frame = ttk.Frame(self.content_container)

        # ── Bottom buttons (pack BEFORE content so they always get space) ──
        self.btn_frame = ttk.Frame(self)
        self.btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=(8, 16))

        # Now pack content container to fill remaining space
        self.content_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)

        self.cancel_btn = ttk.Button(
            self.btn_frame, text="Cancel", command=self.destroy
        )
        self.cancel_btn.pack(side=tk.LEFT)

        self.confirm_btn = ttk.Button(
            self.btn_frame,
            text="Confirm Level Up",
            style="Accent.TButton",
            command=self._confirm,
        )

        self.next_btn = ttk.Button(
            self.btn_frame,
            text="Next: Spells \u2192",
            style="Accent.TButton",
            command=lambda: self._try_go_next(2),
        )

        self.back_btn = ttk.Button(
            self.btn_frame,
            text="\u2190 Back",
            command=lambda: self._show_step(1),
        )

        # Build step 1 content and show it
        self._rebuild_content()
        self._show_step(1)

    def _try_go_next(self, target_step: int):
        # Build the ordered list of active steps
        step_order = [1]
        if self._has_proficiency_step():
            step_order.append(15)
        if self._has_class_choices():
            step_order.append(2)
        if self._has_new_spell_options():
            step_order.append(3)
        if self._has_swap_step():
            step_order.append(4)

        target_idx = step_order.index(target_step) if target_step in step_order else len(step_order)

        # Validate all steps before the target
        validators = {
            1: self._validate_step1,
            15: self._validate_proficiency_step,
            2: self._validate_choices_step,
            3: self._validate_step2,
        }
        for s in step_order:
            if step_order.index(s) >= target_idx:
                break
            validator = validators.get(s)
            if validator and not validator():
                return

        self._show_step(target_step)

    def _validate_step1(self) -> bool:
        if (
            self.class_slug != self.primary_class_slug
            and self.character.class_level_in(self.class_slug) == 0
        ):
            met, reason = self.character.multiclass_prereqs_met(self.class_slug)
            if not met:
                AlertDialog(
                    self,
                    "Prerequisites Not Met",
                    f"Cannot multiclass into {self.class_slug.title()}:\n{reason}",
                )
                return False
            pri_met, pri_reason = self.character.multiclass_prereqs_met(
                self.primary_class_slug
            )
            if not pri_met:
                AlertDialog(
                    self,
                    "Prerequisites Not Met",
                    f"Cannot multiclass out of {self.primary_class_slug.title()}:\n{pri_reason}",
                )
                return False

        if self.level_data:
            features = self.level_data.get("features", [])
            if any("Ability Score Improvement" in f for f in features):
                if not self.feat_var.get():
                    AlertDialog(
                        self,
                        "Missing Choice",
                        "Please select a feat for your Ability Score Improvement.",
                    )
                    return False
            if any("Subclass" in f and "Feature" not in f for f in features):
                if not self.subclass_var.get():
                    AlertDialog(self, "Missing Choice", "Please select a subclass.")
                    return False
        return True

    def _validate_step2(self) -> bool:
        if self._has_new_spell_options():
            new_cantrips_max, new_prepared_max, _ = self._spell_deltas()
            if (
                new_cantrips_max > 0
                and len(self.selected_new_cantrips) < new_cantrips_max
            ):
                AlertDialog(
                    self,
                    "Missing Choice",
                    f"Please select {new_cantrips_max} new cantrip(s) on the Spells step.",
                )
                return False
            if (
                new_prepared_max > 0
                and len(self.selected_new_spells) < new_prepared_max
            ):
                AlertDialog(
                    self,
                    "Missing Choice",
                    f"Please select {new_prepared_max} new spell(s) on the Spells step.",
                )
                return False
        return True

    def _validate_choices_step(self) -> bool:
        config = self._get_choices_config()
        if not config:
            return True
        required = config.get("gains_by_level", {}).get(str(self.new_class_level), 0)
        label = config.get("choice_plural", "choices")
        if len(self.selected_new_choices) < required:
            AlertDialog(
                self,
                "Missing Choice",
                f"Please select {required} new {label} on the Class Choices step.",
            )
            return False
        # If user picked something to remove but not what to add (or vice versa)
        out = self.replace_out_var.get()
        inp = self.replace_in_var.get()
        if out and not inp:
            AlertDialog(
                self,
                "Incomplete Swap",
                f"You chose to remove a {config.get('choice_label', 'choice')} but haven't selected a replacement.",
            )
            return False
        return True

    def _next_step_after(self, current: int) -> tuple[int, str] | None:
        """Return (step_number, button_label) for the next step after *current*, or None."""
        has_prof = self._has_proficiency_step()
        has_choices = self._has_class_choices()
        has_spells = self._has_new_spell_options()
        has_swap = self._has_swap_step()
        order: list[tuple[int, str]] = [(1, "")]
        if has_prof:
            order.append((15, "Next: Proficiencies \u2192"))
        if has_choices:
            order.append((2, "Next: Class Choices \u2192"))
        if has_spells:
            order.append((3, "Next: Spells \u2192"))
        if has_swap:
            order.append((4, "Next: Swap Spells \u2192"))
        # Find the entry right after current
        found = False
        for entry in order:
            if found:
                return entry
            if entry[0] == current:
                found = True
        return None

    def _prev_step_before(self, current: int) -> int:
        """Return the step number before *current*."""
        has_prof = self._has_proficiency_step()
        has_choices = self._has_class_choices()
        has_spells = self._has_new_spell_options()
        order = [1]
        if has_prof:
            order.append(15)
        if has_choices:
            order.append(2)
        if has_spells:
            order.append(3)
        order.append(4)
        idx = order.index(current) if current in order else 0
        return order[max(0, idx - 1)]

    def _show_step(self, step: int):
        """Show *step* and update bottom buttons.

        Step 1  = features / HP / ASI / subclass
        Step 15 = subclass proficiency/expertise (conditional)
        Step 2  = class choices (conditional)
        Step 3  = spell selection (conditional)
        Step 4  = spell swap (conditional)
        """
        self.step1_scroll.pack_forget()
        self.step_prof_frame.pack_forget()
        self.step2b_frame.pack_forget()
        self.step2_frame.pack_forget()
        self.step3_frame.pack_forget()
        self.confirm_btn.pack_forget()
        self.next_btn.pack_forget()
        self.back_btn.pack_forget()

        # Only show multiclass selector on step 1
        if step == 1:
            self.mc_frame.pack(fill=tk.X, padx=16, pady=(0, 4), after=self.header_frame)
        else:
            self.mc_frame.pack_forget()

        def _setup_next_or_confirm(current_step: int):
            nxt = self._next_step_after(current_step)
            if nxt:
                self.next_btn.configure(
                    text=nxt[1],
                    command=lambda s=nxt[0]: self._try_go_next(s),
                )
                self.next_btn.pack(side=tk.RIGHT)
            else:
                self.confirm_btn.pack(side=tk.RIGHT)

        if step == 1:
            self.step1_scroll.pack(
                in_=self.content_container, fill=tk.BOTH, expand=True
            )
            _setup_next_or_confirm(1)

        elif step == 15:
            # Subclass proficiency/expertise step
            self._build_proficiency_step()
            self.step_prof_frame.pack(in_=self.content_container, fill=tk.BOTH, expand=True)
            self.back_btn.configure(command=lambda: self._show_step(1))
            self.back_btn.pack(side=tk.LEFT, padx=(8, 0))
            _setup_next_or_confirm(15)

        elif step == 2:
            # Class choices step
            self._build_choices_step()
            self.step2b_frame.pack(in_=self.content_container, fill=tk.BOTH, expand=True)
            self.back_btn.configure(command=lambda p=self._prev_step_before(2): self._show_step(p))
            self.back_btn.pack(side=tk.LEFT, padx=(8, 0))
            _setup_next_or_confirm(2)

        elif step == 3:
            # Spell selection step
            self._build_spell_step()
            self.step2_frame.pack(in_=self.content_container, fill=tk.BOTH, expand=True)
            self.back_btn.configure(command=lambda p=self._prev_step_before(3): self._show_step(p))
            self.back_btn.pack(side=tk.LEFT, padx=(8, 0))
            _setup_next_or_confirm(3)

        elif step == 4:
            # Spell swap step
            self._build_swap_step()
            self.step3_frame.pack(in_=self.content_container, fill=tk.BOTH, expand=True)
            self.back_btn.configure(command=lambda p=self._prev_step_before(4): self._show_step(p))
            self.back_btn.pack(side=tk.LEFT, padx=(8, 0))
            self.confirm_btn.pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    # Header / class change
    # ------------------------------------------------------------------

    def _header_text(self) -> str:
        cls_name = self.class_slug.title()
        if self.selected_class_data:
            cls_name = self.selected_class_data.get("name", cls_name)
        return f"Level Up to {cls_name} {self.new_class_level}"

    def _on_class_change(self, *_):
        self._update_level_data()
        self.header_label.configure(text=self._header_text())
        self.subclass_var.set("")
        self.feat_var.set("")

        if (
            self.class_slug != self.primary_class_slug
            and self.character.class_level_in(self.class_slug) == 0
        ):
            met, reason = self.character.multiclass_prereqs_met(self.class_slug)
            pri_met, pri_reason = self.character.multiclass_prereqs_met(
                self.primary_class_slug
            )
            if not met:
                self.prereq_label.configure(text=f"\u26a0 {reason}")
            elif not pri_met:
                self.prereq_label.configure(text=f"\u26a0 Primary class: {pri_reason}")
            else:
                self.prereq_label.configure(text="")
        else:
            self.prereq_label.configure(text="")

        self._rebuild_content()
        self._show_step(1)

    # ------------------------------------------------------------------
    # Step 1 content (features, HP, ASI, subclass, spell summary)
    # ------------------------------------------------------------------

    def _rebuild_content(self):
        for w in self.step1_content.winfo_children():
            w.destroy()

        # Reset class choices state whenever content is rebuilt
        self.selected_new_choices.clear()
        self.replace_out_var.set("")
        self.replace_in_var.set("")
        self.choice_vars.clear()
        self.choice_checkbuttons.clear()

        self._build_features_section()
        self._build_hp_section()

        if self.level_data:
            features = self.level_data.get("features", [])
            if any("Ability Score Improvement" in f for f in features):
                self._build_asi_section()
            if any("Subclass" in f and "Feature" not in f for f in features):
                self._build_subclass_section()

        # Show spell summary info on step 1 if there are new spells
        if self._has_new_spell_options():
            self._build_spell_summary()

    # ── features ──────────────────────────────────────────────────

    def _build_features_section(self):
        if not self.level_data:
            ttk.Label(
                self.step1_content,
                text="No progression data available for this class/level.",
                foreground=COLORS["fg_dim"],
            ).pack(anchor="w", pady=4)
            return

        features = self.level_data.get("features", [])
        details = self.level_data.get("feature_details", [])

        if not features:
            return

        ttk.Label(
            self.step1_content,
            text="New Features",
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(8, 4))

        for feat_name in features:
            if feat_name in ("-", "Ability Score Improvement"):
                continue

            sub_slug = self.character.subclass_for_class(self.class_slug)
            if feat_name == "Subclass Feature" and sub_slug:
                self._show_subclass_features()
                continue

            frame = ttk.Frame(self.step1_content, style="Card.TFrame")
            frame.pack(fill=tk.X, pady=2, padx=4)

            ttk.Label(
                frame,
                text=feat_name,
                font=FONTS["subheading"],
                foreground=COLORS["fg_bright"],
                background=COLORS["bg_card"],
            ).pack(anchor="w", padx=8, pady=(4, 0))

            desc = ""
            feat_lower = feat_name.lower().replace("\u2019", "'")
            for d in details:
                d_lower = d["name"].lower().replace("\u2019", "'")
                if d_lower == feat_lower or feat_lower.startswith(d_lower + " ("):
                    desc = d["description"]
                    break

            # Fallback: search all levels for the base feature description
            if not desc:
                base_name = feat_name.split(" (")[0].lower().replace("\u2019", "'")
                prog = self.data.get_progression(self.class_slug)
                if prog:
                    for lvl_data in prog.get("levels", []):
                        for d in lvl_data.get("feature_details", []):
                            if d["name"].lower().replace("\u2019", "'") == base_name:
                                desc = d["description"]
                                break
                        if desc:
                            break
            if desc:
                WrappingLabel(
                    frame,
                    text=desc,
                    foreground=COLORS["fg_dim"],
                    background=COLORS["bg_card"],
                ).pack(fill=tk.X, anchor="w", padx=8, pady=(0, 4))

        extra = self.level_data.get("extra", {})
        if extra:
            for col_name, val in extra.items():
                if val is not None:
                    ttk.Label(
                        self.step1_content,
                        text=f"{col_name}: {val}",
                        foreground=COLORS["fg"],
                    ).pack(anchor="w", padx=12, pady=1)

    def _show_subclass_features(self):
        sub_slug = self.character.subclass_for_class(self.class_slug)
        subclass = self.data.get_subclass(self.class_slug, sub_slug)
        if not subclass:
            ttk.Label(
                self.step1_content,
                text=f"Subclass Feature (data not available for {sub_slug})",
                foreground=COLORS["fg_dim"],
            ).pack(anchor="w", padx=12, pady=2)
            return

        sub_features = subclass.get("features", {}).get(str(self.new_class_level), [])
        if not sub_features:
            sub_name = subclass.get("name", sub_slug)
            ttk.Label(
                self.step1_content,
                text=f"{sub_name} Feature (Level {self.new_class_level})",
                foreground=COLORS["fg"],
            ).pack(anchor="w", padx=12, pady=2)
            return

        for feat in sub_features:
            frame = ttk.Frame(self.step1_content, style="Card.TFrame")
            frame.pack(fill=tk.X, pady=2, padx=4)
            ttk.Label(
                frame,
                text=f"{feat['name']} (Subclass)",
                font=FONTS["subheading"],
                foreground=COLORS["fg_bright"],
                background=COLORS["bg_card"],
            ).pack(anchor="w", padx=8, pady=(4, 0))
            desc = feat.get("description", "")
            if desc:
                WrappingLabel(
                    frame,
                    text=desc,
                    foreground=COLORS["fg_dim"],
                    background=COLORS["bg_card"],
                ).pack(fill=tk.X, anchor="w", padx=8, pady=(0, 4))

    # ── HP ────────────────────────────────────────────────────────

    def _build_hp_section(self):
        ttk.Separator(self.step1_content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Label(
            self.step1_content,
            text="Hit Points",
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(4, 4))

        hit_die = (
            self.selected_class_data.get("hit_die", 8)
            if self.selected_class_data
            else 8
        )
        con_mod = self.character.ability_scores.modifier("Constitution")
        average = hit_die // 2 + 1

        self.hp_mode.set("average")
        self.hp_manual_var.set("")

        hp_frame = ttk.Frame(self.step1_content)
        hp_frame.pack(fill=tk.X, padx=12)

        ttk.Radiobutton(
            hp_frame,
            text=f"Take average ({average} + {con_mod} CON = {average + con_mod} HP)",
            variable=self.hp_mode,
            value="average",
        ).pack(anchor="w", pady=2)

        ttk.Radiobutton(
            hp_frame,
            text=f"Take max ({hit_die} + {con_mod} CON = {hit_die + con_mod} HP)",
            variable=self.hp_mode,
            value="max",
        ).pack(anchor="w", pady=2)

        # Manual entry row
        manual_row = ttk.Frame(hp_frame)
        manual_row.pack(anchor="w", pady=2, fill=tk.X)

        ttk.Radiobutton(
            manual_row,
            text="Enter manually:",
            variable=self.hp_mode,
            value="manual",
        ).pack(side=tk.LEFT)

        manual_entry = ttk.Entry(manual_row, textvariable=self.hp_manual_var, width=5)
        manual_entry.pack(side=tk.LEFT, padx=(4, 4))

        self._hp_manual_hint = ttk.Label(
            manual_row,
            text=f"+ {con_mod} CON = ? HP",
            foreground=COLORS["fg_dim"],
        )
        self._hp_manual_hint.pack(side=tk.LEFT)

        def _update_manual_state(*_):
            if self.hp_mode.get() == "manual":
                manual_entry.config(state="normal")
            else:
                manual_entry.config(state="disabled")
            _update_hint()

        def _update_hint(*_):
            if self.hp_mode.get() != "manual":
                return
            val = self.hp_manual_var.get().strip()
            try:
                roll = int(val)
                if roll >= 1:
                    self._hp_manual_hint.config(text=f"+ {con_mod} CON = {roll + con_mod} HP")
                else:
                    self._hp_manual_hint.config(text="(must be ≥ 1)")
            except ValueError:
                self._hp_manual_hint.config(text=f"+ {con_mod} CON = ? HP")

        self.hp_mode.trace_add("write", _update_manual_state)
        self.hp_manual_var.trace_add("write", _update_hint)
        manual_entry.config(state="disabled")

    # ── ASI ───────────────────────────────────────────────────────

    def _build_asi_section(self):
        ttk.Separator(self.step1_content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Label(
            self.step1_content,
            text="Ability Score Improvement",
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(4, 4))
        ttk.Label(
            self.step1_content,
            text="Choose a feat (the Ability Score Improvement feat lets you increase two scores):",
            foreground=COLORS["fg"],
        ).pack(anchor="w", padx=12)

        feat_options = []
        for feat in self.data.feats:
            cat = feat.get("category", "general")
            if cat == "general":
                feat_options.append(feat["name"])
            elif cat == "epic_boon" and self.new_total_level >= 19:
                feat_options.append(feat["name"])
        feat_options.sort()

        feat_frame = ttk.Frame(self.step1_content)
        feat_frame.pack(fill=tk.X, padx=12, pady=4)
        self.feat_var.set("")
        ttk.Combobox(
            feat_frame,
            textvariable=self.feat_var,
            values=feat_options,
            state="readonly",
            width=40,
        ).pack(anchor="w")

    # ── Subclass ──────────────────────────────────────────────────

    def _build_subclass_section(self):
        ttk.Separator(self.step1_content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Label(
            self.step1_content,
            text="Choose Subclass",
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(4, 4))

        subclasses = self.data.get_subclasses_for_class(self.class_slug)
        phb_names = set()
        if self.progression:
            for name in self.progression.get("subclass_names", []):
                phb_names.add(name)

        sub_frame = ttk.Frame(self.step1_content)
        sub_frame.pack(fill=tk.X, padx=12, pady=4)

        options = [sc["name"] for sc in subclasses]
        ua_lower = {n.lower() for n in options}
        for name in sorted(phb_names):
            if name.lower() not in ua_lower:
                options.append(f"{name} (PHB)")

        self.subclass_var.set("")
        ttk.Combobox(
            sub_frame,
            textvariable=self.subclass_var,
            values=sorted(options),
            state="readonly",
            width=40,
        ).pack(anchor="w")

        self.sub_detail_frame = ttk.Frame(self.step1_content)
        self.sub_detail_frame.pack(fill=tk.X, anchor="w", padx=12, pady=4)

        def on_sub_select(*_):
            for w in self.sub_detail_frame.winfo_children():
                w.destroy()

            name = self.subclass_var.get().replace(" (PHB)", "")
            sc = None
            for s in subclasses:
                if s["name"] == name:
                    sc = s
                    break

            if not sc:
                WrappingLabel(
                    self.sub_detail_frame,
                    text="(Core subclass - feature data not available)",
                    foreground=COLORS["fg_dim"],
                ).pack(fill=tk.X, anchor="w")
                self._show_step(1)
                return

            # Intro summary (text before first "Level N:" marker)
            desc = (sc.get("description") or "").strip()
            if desc:
                parts = re.split(r"\bLevel\s+\d+\s*:", desc, maxsplit=1)
                intro = parts[0].strip()
                if intro:
                    WrappingLabel(
                        self.sub_detail_frame,
                        text=intro,
                        foreground=COLORS["fg_dim"],
                    ).pack(fill=tk.X, anchor="w", pady=(0, 4))

            # Structured features by level
            features_by_level = sc.get("features", {})
            if features_by_level:
                def _lvl_key(level_str: str):
                    try:
                        return int(level_str)
                    except (TypeError, ValueError):
                        return 99

                for lvl in sorted(features_by_level.keys(), key=_lvl_key):
                    ttk.Label(
                        self.sub_detail_frame,
                        text=f"Level {lvl}",
                        style="Subheading.TLabel",
                    ).pack(anchor="w", pady=(8, 2))

                    for feat in features_by_level.get(lvl, []):
                        feat_name = feat.get("name", "Feature")
                        ttk.Label(
                            self.sub_detail_frame,
                            text=f"  \u2022 {feat_name}",
                            foreground=COLORS["accent"],
                            font=FONTS["body"],
                        ).pack(anchor="w")

                        feat_desc = feat.get("description", "")
                        if feat_desc:
                            WrappingLabel(
                                self.sub_detail_frame,
                                text=f"    {feat_desc}",
                                foreground=COLORS["fg_dim"],
                            ).pack(fill=tk.X, anchor="w", pady=(0, 4))
            elif desc:
                # No structured features — show full description as fallback
                WrappingLabel(
                    self.sub_detail_frame,
                    text=desc,
                    foreground=COLORS["fg_dim"],
                ).pack(fill=tk.X, anchor="w")
            # Refresh navigation buttons — the selected subclass may add
            # a Class Choices step (e.g. Hunter's Prey for Hunter).
            self._show_step(1)

        self.subclass_var.trace_add("write", on_sub_select)

    # ── Spell summary (shown on step 1) ──────────────────────────

    def _build_spell_summary(self):
        """Informational summary of spell changes, shown on step 1."""
        new_cantrips, new_prepared, _ = self._spell_deltas()
        prev = self.data.get_level_data(self.class_slug, self.new_class_level - 1) or {}
        curr_slots = self.level_data.get("spell_slots", {}) if self.level_data else {}
        prev_slots = prev.get("spell_slots", {})
        new_slot_levels = set(curr_slots.keys()) - set(prev_slots.keys())

        ttk.Separator(self.step1_content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Label(
            self.step1_content,
            text="Spellcasting Changes",
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(4, 4))

        parts = []
        if new_cantrips > 0:
            parts.append(f"Learn {new_cantrips} new cantrip(s)")
        if new_prepared > 0:
            parts.append(f"Prepare {new_prepared} additional spell(s)")
        if new_slot_levels:
            names = sorted(new_slot_levels, key=lambda x: _SLOT_ORDER.get(x, 99))
            parts.append(f"New spell slot level(s): {', '.join(names)}")
        if curr_slots:
            s = ", ".join(
                f"{k}: {v}"
                for k, v in sorted(
                    curr_slots.items(), key=lambda x: _SLOT_ORDER.get(x[0], 99)
                )
            )
            parts.append(f"Total spell slots: {s}")

        for p in parts:
            ttk.Label(
                self.step1_content,
                text=f"  {p}",
                foreground=COLORS["fg"],
            ).pack(anchor="w", padx=12, pady=1)

        ttk.Label(
            self.step1_content,
            text="(Choose your new spells on the next step)",
            foreground=COLORS["fg_dim"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=12, pady=(4, 0))

    # ------------------------------------------------------------------
    # Step 2 – class choices (maneuvers, invocations, plans, arcane shots)
    # ------------------------------------------------------------------

    def _build_choices_step(self):
        """Build (or rebuild) the class choices UI in step2b_frame."""
        for w in self.step2b_frame.winfo_children():
            w.destroy()
        self.selected_new_choices.clear()
        self.replace_out_var.set("")
        self.replace_in_var.set("")
        self.choice_vars.clear()
        self.choice_checkbuttons.clear()

        config = self._get_choices_config()
        if not config:
            return

        # Determine which key this config belongs to
        choice_key = self.class_slug
        for k, v in _CLASS_CHOICES.items():
            if v is config:
                choice_key = k
                break

        choice_label = config.get("choice_label", "Choice")
        choice_plural = config.get("choice_plural", "Choices")
        level_str = str(self.new_class_level)
        new_count = config.get("gains_by_level", {}).get(level_str, 0)
        known = self._get_known_choices(choice_key)
        available = self._get_available_options(config)

        # Pool-aware labels (e.g. "Beast Tattoos", "Hunter's Prey")
        active_pool = self._get_active_pool(config)
        pool_heading = f"{active_pool} {choice_plural}" if active_pool else choice_plural
        pool_subtext = f"{active_pool} {choice_label}" if active_pool else choice_label

        # ── Heading ───────────────────────────────────────────────
        ttk.Label(
            self.step2b_frame,
            text=f"Select {pool_heading}",
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(4, 2))
        ttk.Label(
            self.step2b_frame,
            text=f"Choose {new_count} new {pool_subtext}(s)",
            foreground=COLORS["fg"],
        ).pack(anchor="w", padx=4, pady=(0, 2))

        if config.get("can_swap_on_rest"):
            ttk.Label(
                self.step2b_frame,
                text="\u21ba These choices can be changed when you finish a Short or Long Rest.",
                foreground=COLORS["fg_dim"],
                font=("Segoe UI", 9, "italic"),
            ).pack(anchor="w", padx=4, pady=(0, 4))

        # ── Two-column split: list (left) + detail (right) ───────
        cols = ttk.Frame(self.step2b_frame)
        cols.pack(fill=tk.BOTH, expand=True, pady=4)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)
        cols.rowconfigure(0, weight=1)

        # --- LEFT: choices list + optional replace section ---
        left = ttk.Frame(cols)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        left.rowconfigure(1, weight=1)

        # Count label
        self.choice_count_label = ttk.Label(
            left,
            text=f"0 / {new_count} selected",
            style="Dim.TLabel",
        )
        self.choice_count_label.pack(anchor="w", padx=4, pady=(0, 1))

        list_outer = ttk.Frame(left)
        list_outer.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        _, inner = self._make_scrollable_list(list_outer)

        def _section_header(parent, title):
            ttk.Label(
                parent,
                text=f"\u2500\u2500 {title} \u2500\u2500",
                foreground=COLORS["accent"],
                font=FONTS["body"],
            ).pack(anchor="w", pady=(6, 2))

        _section_header(inner, f"Available {choice_plural}")
        for opt in sorted(available, key=lambda o: o["name"]):
            var = tk.BooleanVar(value=False)
            var.trace_add("write", lambda *a, o=opt: self._on_choice_toggle(o))
            self.choice_vars[opt["name"]] = var
            cb = ttk.Checkbutton(inner, text=opt["name"], variable=var)
            cb.pack(anchor="w", pady=1, padx=(8, 0))
            cb.bind("<Enter>", lambda e, o=opt: self._show_choice_detail(o))
            self.choice_checkbuttons[opt["name"]] = cb

        # ── Replace one (optional, only if has existing choices) ──
        if known and config.get("can_replace"):
            ttk.Separator(left, orient="horizontal").pack(fill=tk.X, pady=(8, 4))
            ttk.Label(
                left,
                text="Replace one (optional):",
                foreground=COLORS["fg"],
                font=FONTS["body"],
            ).pack(anchor="w", padx=4)

            replace_cols = ttk.Frame(left)
            replace_cols.pack(fill=tk.X, pady=4)
            replace_cols.columnconfigure(0, weight=1)
            replace_cols.columnconfigure(1, weight=1)

            # Left sub-column: Remove
            remove_lf = ttk.LabelFrame(replace_cols, text="Remove")
            remove_lf.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
            ttk.Radiobutton(
                remove_lf,
                text="Don\u2019t replace",
                variable=self.replace_out_var,
                value="",
            ).pack(anchor="w", pady=1, padx=4)
            for name in sorted(known):
                opt_data = next((o for o in config.get("options", []) if o["name"] == name), {"name": name, "description": ""})
                rb = ttk.Radiobutton(
                    remove_lf,
                    text=name,
                    variable=self.replace_out_var,
                    value=name,
                )
                rb.pack(anchor="w", pady=1, padx=(8, 0))
                rb.bind("<Enter>", lambda e, o=opt_data: self._show_choice_detail(o))

            # Right sub-column: Replace with
            learn_lf = ttk.LabelFrame(replace_cols, text="Replace with")
            learn_lf.grid(row=0, column=1, sticky="nsew", padx=(2, 0))
            ttk.Radiobutton(
                learn_lf,
                text="Nothing",
                variable=self.replace_in_var,
                value="",
            ).pack(anchor="w", pady=1, padx=4)
            # All options not already known (including ones selected as new picks)
            all_not_known = [o for o in config.get("options", []) if o["name"] not in known]
            # Apply level/prereq filter
            all_not_known = self._get_available_options(config)
            for opt in sorted(all_not_known, key=lambda o: o["name"]):
                rb = ttk.Radiobutton(
                    learn_lf,
                    text=opt["name"],
                    variable=self.replace_in_var,
                    value=opt["name"],
                )
                rb.pack(anchor="w", pady=1, padx=(8, 0))
                rb.bind("<Enter>", lambda e, o=opt: self._show_choice_detail(o))

        # --- RIGHT: detail panel ---
        detail_lf = ttk.LabelFrame(cols, text="Details")
        detail_lf.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        self.choice_detail_text = tk.Text(
            detail_lf,
            wrap=tk.WORD,
            bg=COLORS["bg_light"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            state=tk.DISABLED,
        )
        self.choice_detail_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _on_choice_toggle(self, opt: dict):
        if self._updating_choices:
            return
        self._updating_choices = True
        try:
            config = self._get_choices_config()
            if not config:
                return
            level_str = str(self.new_class_level)
            max_count = config.get("gains_by_level", {}).get(level_str, 0)
            selected = [n for n, v in self.choice_vars.items() if v.get()]
            if len(selected) > max_count:
                self.choice_vars[opt["name"]].set(False)
                selected = [n for n, v in self.choice_vars.items() if v.get()]
            self.selected_new_choices = set(selected)
            self.choice_count_label.configure(
                text=f"{len(selected)} / {max_count} selected"
            )
            self._update_choice_states(max_count, selected)
        finally:
            self._updating_choices = False

    def _update_choice_states(self, max_count: int, selected: list[str]):
        at_max = len(selected) >= max_count
        for name, cb in self.choice_checkbuttons.items():
            cb.configure(
                state=tk.DISABLED if at_max and name not in selected else tk.NORMAL
            )

    def _show_choice_detail(self, opt: dict):
        if not hasattr(self, "choice_detail_text"):
            return
        self.choice_detail_text.configure(state=tk.NORMAL)
        self.choice_detail_text.delete("1.0", tk.END)
        lines = [opt.get("name", ""), ""]
        prereq = opt.get("prerequisite_level")
        if prereq:
            lines.append(f"Requires Warlock level {prereq}+")
        prereq_feat = opt.get("prerequisite_feature")
        if prereq_feat:
            lines.append(f"Requires: {prereq_feat}")
        min_lvl = opt.get("min_level")
        if min_lvl:
            lines.append(f"Available at Artificer level {min_lvl}+")
        if prereq or prereq_feat or min_lvl:
            lines.append("")
        lines.append(opt.get("description", ""))
        self.choice_detail_text.insert("1.0", "\n".join(lines))
        self.choice_detail_text.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Step 3 – spell selection
    # ------------------------------------------------------------------

    def _build_spell_step(self):
        """Build (or rebuild) the spell selection UI in step2_frame.

        Layout: left column = single scrollable list (cantrips on top,
        then leveled spells grouped by level with section headers).
        Right column = full spell detail panel.
        """
        for w in self.step2_frame.winfo_children():
            w.destroy()
        self.cantrip_vars.clear()
        self.spell_vars.clear()
        self.cantrip_checkbuttons.clear()
        self.spell_checkbuttons.clear()
        self.selected_new_cantrips.clear()
        self.selected_new_spells.clear()

        new_cantrips, new_prepared, max_spell_level = self._spell_deltas()
        class_name = (
            self.selected_class_data.get("name", "") if self.selected_class_data else ""
        )
        has_cantrips = new_cantrips > 0
        has_spells = new_prepared > 0

        # ── heading ───────────────────────────────────────────────
        ttk.Label(
            self.step2_frame,
            text="Select New Spells",
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(4, 2))

        parts = []
        if has_cantrips:
            parts.append(f"Learn {new_cantrips} new cantrip(s)")
        if has_spells:
            parts.append(f"Prepare {new_prepared} additional spell(s)")
        if parts:
            ttk.Label(
                self.step2_frame,
                text="  •  ".join(parts),
                foreground=COLORS["fg"],
            ).pack(anchor="w", padx=4, pady=(0, 4))

        # ── two-column split: list (left) + detail (right) ───────
        cols = ttk.Frame(self.step2_frame)
        cols.pack(fill=tk.BOTH, expand=True, pady=4)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)
        cols.rowconfigure(0, weight=1)

        # --- LEFT: spell list ---
        left = ttk.Frame(cols)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        # Count labels
        if has_cantrips:
            self.cantrip_count_label = ttk.Label(
                left,
                text=f"0 / {new_cantrips} cantrips selected",
                style="Dim.TLabel",
            )
            self.cantrip_count_label.pack(anchor="w", padx=4, pady=(0, 1))
        if has_spells:
            self.spell_count_label = ttk.Label(
                left,
                text=f"0 / {new_prepared} spells selected",
                style="Dim.TLabel",
            )
            self.spell_count_label.pack(anchor="w", padx=4, pady=(0, 1))

        list_outer = ttk.Frame(left)
        list_outer.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        canvas, inner = self._make_scrollable_list(list_outer)

        # Section header helper (matches SectionedListbox style)
        def _section_header(parent, title):
            ttk.Label(
                parent,
                text=f"\u2500\u2500 {title} \u2500\u2500",
                foreground=COLORS["accent"],
                font=FONTS["body"],
            ).pack(anchor="w", pady=(6, 2))

        # ── cantrips ─────────────────────────────────────────────
        if has_cantrips:
            _section_header(inner, "Cantrips")

            all_cantrips = self.data.cantrips_for_class(class_name)
            known = set(self.character.selected_cantrips)
            available = [s for s in all_cantrips if s["name"] not in known]

            for spell in sorted(available, key=lambda s: s["name"]):
                var = tk.BooleanVar(value=False)
                var.trace_add(
                    "write", lambda *a, s=spell: self._on_new_cantrip_toggle(s)
                )
                self.cantrip_vars[spell["name"]] = {"var": var, "spell": spell}
                cb = ttk.Checkbutton(
                    inner,
                    text=spell["name"],
                    variable=var,
                )
                cb.pack(anchor="w", pady=1, padx=(8, 0))
                cb.bind("<Enter>", lambda e, s=spell: self._show_spell_detail(s))
                self.cantrip_checkbuttons[spell["name"]] = cb

        # ── leveled spells grouped by level ──────────────────────
        if has_spells:
            _LEVEL_NAMES = {
                1: "1st-Level",
                2: "2nd-Level",
                3: "3rd-Level",
                4: "4th-Level",
                5: "5th-Level",
                6: "6th-Level",
                7: "7th-Level",
                8: "8th-Level",
                9: "9th-Level",
            }

            all_spells = self.data.spells_for_class(
                class_name, max_level=max_spell_level
            )
            known = set(self.character.selected_spells)
            available = [
                s
                for s in all_spells
                if s["name"] not in known and s.get("level", 0) >= 1
            ]
            available.sort(key=lambda s: (s["level"], s["name"]))

            # Group by level
            from itertools import groupby

            for lvl, group in groupby(available, key=lambda s: s["level"]):
                _section_header(inner, _LEVEL_NAMES.get(lvl, f"Level {lvl}"))
                for spell in group:
                    var = tk.BooleanVar(value=False)
                    var.trace_add(
                        "write", lambda *a, s=spell: self._on_new_spell_toggle(s)
                    )
                    self.spell_vars[spell["name"]] = {"var": var, "spell": spell}

                    cb = ttk.Checkbutton(inner, text=spell["name"], variable=var)
                    cb.pack(anchor="w", pady=1, padx=(8, 0))
                    cb.bind("<Enter>", lambda e, s=spell: self._show_spell_detail(s))
                    self.spell_checkbuttons[spell["name"]] = cb

        # --- RIGHT: spell detail ---
        detail_lf = ttk.LabelFrame(cols, text="Spell Details")
        detail_lf.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        self.spell_detail_text = tk.Text(
            detail_lf,
            wrap=tk.WORD,
            bg=COLORS["bg_light"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            state=tk.DISABLED,
        )
        self.spell_detail_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    # ── scrollable list helper (same pattern as step_spells.py) ──

    def _make_scrollable_list(self, parent_frame):
        canvas = tk.Canvas(
            parent_frame, bg=COLORS["bg"], highlightthickness=0, borderwidth=0
        )
        scrollbar = ttk.Scrollbar(
            parent_frame, orient=tk.VERTICAL, command=canvas.yview
        )
        inner = ttk.Frame(canvas)

        inner.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        cw = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.bind(
            "<Configure>", lambda e, _cw=cw: canvas.itemconfig(_cw, width=e.width)
        )

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _on_wheel(event):
            canvas.yview_scroll(_wheel_units(event), "units")

        inner.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_wheel))
        inner.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        return canvas, inner

    # ── toggle handlers ──────────────────────────────────────────

    def _on_new_cantrip_toggle(self, spell):
        if self._updating_cantrips:
            return
        self._updating_cantrips = True
        try:
            new_cantrips_max, _, _ = self._spell_deltas()
            selected = [n for n, d in self.cantrip_vars.items() if d["var"].get()]
            if len(selected) > new_cantrips_max:
                self.cantrip_vars[spell["name"]]["var"].set(False)
                selected = [n for n, d in self.cantrip_vars.items() if d["var"].get()]

            self.selected_new_cantrips = selected
            self.cantrip_count_label.configure(
                text=f"{len(selected)} / {new_cantrips_max} selected"
            )
            self._update_cantrip_states(new_cantrips_max, selected)
        finally:
            self._updating_cantrips = False

    def _on_new_spell_toggle(self, spell):
        if self._updating_spells:
            return
        self._updating_spells = True
        try:
            _, new_prepared_max, _ = self._spell_deltas()
            selected = [n for n, d in self.spell_vars.items() if d["var"].get()]
            if len(selected) > new_prepared_max:
                self.spell_vars[spell["name"]]["var"].set(False)
                selected = [n for n, d in self.spell_vars.items() if d["var"].get()]

            self.selected_new_spells = selected
            self.spell_count_label.configure(
                text=f"{len(selected)} / {new_prepared_max} selected"
            )
            self._update_spell_states(new_prepared_max, selected)
        finally:
            self._updating_spells = False

    def _update_cantrip_states(self, max_count, selected):
        at_max = len(selected) >= max_count
        for name, cb in self.cantrip_checkbuttons.items():
            cb.configure(
                state=tk.DISABLED if at_max and name not in selected else tk.NORMAL
            )

    def _update_spell_states(self, max_count, selected):
        at_max = len(selected) >= max_count
        for name, cb in self.spell_checkbuttons.items():
            cb.configure(
                state=tk.DISABLED if at_max and name not in selected else tk.NORMAL
            )

    # ── spell detail hover ───────────────────────────────────────

    def _show_spell_detail(self, spell):
        self.spell_detail_text.configure(state=tk.NORMAL)
        self.spell_detail_text.delete("1.0", tk.END)
        lines = [
            spell["name"],
            f"{'Cantrip' if spell['level'] == 0 else 'Level ' + str(spell['level'])} "
            f"{spell['school']}",
            f"Casting Time: {spell.get('casting_time', '?')}"
            f"{'  (Ritual)' if spell.get('ritual') else ''}",
            f"Range: {spell.get('range', '?')}",
            f"Duration: {'Concentration, ' if spell.get('concentration') else ''}"
            f"{spell.get('duration', '?')}",
            "",
            spell.get("description", ""),
        ]
        if spell.get("higher_levels"):
            lines.extend(["", f"At Higher Levels: {spell['higher_levels']}"])
        if spell.get("cantrip_upgrade"):
            lines.extend(["", f"Cantrip Upgrade: {spell['cantrip_upgrade']}"])
        self.spell_detail_text.insert("1.0", "\n".join(lines))
        self.spell_detail_text.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Step 3 – spell swap
    # ------------------------------------------------------------------

    def _build_swap_step(self):
        """Build (or rebuild) the spell swap UI in step3_frame.
        Unified view: left = pick something to forget, right = pick something to learn.
        """
        for w in self.step3_frame.winfo_children():
            w.destroy()
        self.swap_out_cantrip = None
        self.swap_in_cantrip = None
        self.swap_out_spell = None
        self.swap_in_spell = None

        class_name = (
            self.selected_class_data.get("name", "") if self.selected_class_data else ""
        )
        _, _, max_spell_level = self._spell_deltas()
        # If we didn't gain new slots this level, we use current max slots for swapping
        if max_spell_level == 0 and self.level_data:
            curr_slots = self.level_data.get("spell_slots") or {}
            max_spell_level = max(
                (_SLOT_ORDER.get(k, 0) for k in curr_slots), default=0
            )
            # Pact Magic fallback (Warlock)
            pact_lvl = self.level_data.get("pact_slot_level")
            if pact_lvl and isinstance(pact_lvl, int) and pact_lvl > max_spell_level:
                max_spell_level = pact_lvl

        # ── heading ───────────────────────────────────────────────
        ttk.Label(
            self.step3_frame,
            text="Swap Spells (optional)",
            font=FONTS["heading"],
            foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(4, 2))
        ttk.Label(
            self.step3_frame,
            text="You may replace one known spell or cantrip with a different one from your class list.",
            foreground=COLORS["fg"],
        ).pack(anchor="w", padx=4, pady=(0, 4))

        # ── Gather spell data ──
        def _find_spell(name):
            for s in self.data.spells_for_class(class_name, max_level=9):
                if s["name"] == name:
                    return s
            for s in self.data.cantrips_for_class(class_name):
                if s["name"] == name:
                    return s
            return None

        forget_cantrips = [d for n in self.character.selected_cantrips if (d := _find_spell(n))]
        forget_spells = [d for n in self.character.selected_spells if (d := _find_spell(n))]

        known_c_set = set(self.character.selected_cantrips) | set(self.selected_new_cantrips)
        learn_cantrips = [s for s in self.data.cantrips_for_class(class_name)
                          if s["name"] not in known_c_set]

        known_s_set = set(self.character.selected_spells) | set(self.selected_new_spells)
        learn_spells = [s for s in self.data.spells_for_class(class_name, max_level=max_spell_level)
                        if s["name"] not in known_s_set and s.get("level", 0) >= 1]

        # ── Build shared panel ──
        self._swap_panel = SpellSwapPanel(
            self.step3_frame,
            forget_spells=forget_spells,
            learn_spells=learn_spells,
            forget_cantrips=forget_cantrips,
            learn_cantrips=learn_cantrips,
            allow_cantrips=True,
        )

        # ── Wire panel vars back to instance state for _confirm ──
        def _sync_swap_vars(*_):
            fv = self._swap_panel.forget_var.get()
            lv = self._swap_panel.learn_var.get()
            if not fv:
                self.swap_out_cantrip = None
                self.swap_out_spell = None
                self.swap_in_cantrip = None
                self.swap_in_spell = None
            elif fv.startswith("C:"):
                self.swap_out_cantrip = fv[2:]
                self.swap_out_spell = None
                self.swap_in_cantrip = lv or None
                self.swap_in_spell = None
            else:  # S: prefix
                self.swap_out_spell = fv[2:]
                self.swap_out_cantrip = None
                self.swap_in_spell = lv or None
                self.swap_in_cantrip = None

        self._swap_panel.forget_var.trace_add("write", _sync_swap_vars)
        self._swap_panel.learn_var.trace_add("write", _sync_swap_vars)

    # ------------------------------------------------------------------
    # Confirm
    # ------------------------------------------------------------------

    def _confirm(self):
        """Validate choices, apply the level-up, and close."""
        if not self._validate_step1():
            return
        if self._has_proficiency_step() and not self._validate_proficiency_step():
            return
        if self._has_class_choices() and not self._validate_choices_step():
            return
        if self._has_new_spell_options() and not self._validate_step2():
            return

        # ── validate swap choices (incomplete = picked forget but not learn) ─
        if self.swap_out_cantrip and not self.swap_in_cantrip:
            AlertDialog(
                self,
                "Incomplete Swap",
                "You selected a cantrip to forget but didn't pick one to learn.",
            )
            self._show_step(4)
            return
        if self.swap_out_spell and not self.swap_in_spell:
            AlertDialog(
                self,
                "Incomplete Swap",
                "You selected a spell to forget but didn't pick one to learn.",
            )
            self._show_step(4)
            return

        # ── resolve HP roll ───────────────────────────────────────
        hit_die = (
            self.selected_class_data.get("hit_die", 8)
            if self.selected_class_data
            else 8
        )
        con_mod = self.character.ability_scores.modifier("Constitution")
        average = hit_die // 2 + 1

        mode = self.hp_mode.get()
        if mode == "manual":
            try:
                hp_roll = int(self.hp_manual_var.get().strip())
                if hp_roll < 1:
                    raise ValueError
            except ValueError:
                AlertDialog(self, "Invalid HP", "Please enter a valid number (≥ 1) for your hit points.")
                return
        elif mode == "max":
            hp_roll = hit_die
        else:
            hp_roll = average

        # ── confirmation dialog ──────────────────────────────────
        dlg = ConfirmDialog(
            self,
            "Confirm Level Up",
            "Are you sure? These changes will be permanently saved.",
        )
        if not dlg.result:
            return

        cl = ClassLevel(
            class_slug=self.class_slug,
            class_level=self.new_class_level,
            hp_roll=hp_roll,
            hit_die=hit_die,
        )

        if self.subclass_var.get():
            sub_name = self.subclass_var.get().replace(" (PHB)", "")
            for sc in self.data.get_subclasses_for_class(self.class_slug):
                if sc["name"] == sub_name:
                    cl.subclass_slug = sc["slug"]
                    break
            if not cl.subclass_slug:
                cl.subclass_slug = sub_name.lower().replace(" ", "-")

        if self.feat_var.get():
            cl.feat_choice = self.feat_var.get()

        cl.new_cantrips = list(self.selected_new_cantrips)
        cl.new_spells = list(self.selected_new_spells)

        # Store class choices (maneuvers, invocations, plans, arcane shots)
        if self.selected_new_choices:
            cl.new_choices = list(self.selected_new_choices)
        replace_out = self.replace_out_var.get()
        replace_in = self.replace_in_var.get()
        if replace_out and replace_in:
            cl.replaced_choice = replace_out
            cl.new_choices.append(replace_in)

        # Store subclass proficiency/expertise grants
        prof_picks = [v.get() for v in self.prof_grant_vars if v.get()]
        exp_picks = [v.get() for v in self.expertise_grant_vars if v.get()]
        if prof_picks:
            cl.new_proficiencies = prof_picks
            # Handle from_granted expertise (e.g. Knowledge Domain)
            for g in self._get_subclass_grants():
                ge = g.get("grants_expertise")
                if ge and ge.get("from_granted"):
                    cl.new_expertise = list(prof_picks)
        if exp_picks:
            cl.new_expertise.extend(exp_picks)
        # Handle automatic grants (e.g. Arcana Domain)
        for g in self._get_subclass_grants():
            gp = g.get("grants_proficiency")
            ge = g.get("grants_expertise")
            if gp and gp.get("automatic"):
                for s in gp.get("skills", []):
                    if s not in cl.new_proficiencies:
                        cl.new_proficiencies.append(s)
            if ge and ge.get("automatic"):
                for s in ge.get("skills", []):
                    if s not in cl.new_expertise:
                        cl.new_expertise.append(s)

        # Store swap choices on the ClassLevel
        if self.swap_out_cantrip and self.swap_in_cantrip:
            cl.swapped_out_cantrip = self.swap_out_cantrip
            cl.swapped_in_cantrip = self.swap_in_cantrip
        if self.swap_out_spell and self.swap_in_spell:
            cl.swapped_out_spell = self.swap_out_spell
            cl.swapped_in_spell = self.swap_in_spell

        # Merge new spells into character's overall spell lists
        self.character.selected_cantrips.extend(self.selected_new_cantrips)
        self.character.selected_spells.extend(self.selected_new_spells)

        # Apply swaps to character's spell lists
        if cl.swapped_out_cantrip and cl.swapped_in_cantrip:
            if cl.swapped_out_cantrip in self.character.selected_cantrips:
                self.character.selected_cantrips.remove(cl.swapped_out_cantrip)
            self.character.selected_cantrips.append(cl.swapped_in_cantrip)
        if cl.swapped_out_spell and cl.swapped_in_spell:
            if cl.swapped_out_spell in self.character.selected_spells:
                self.character.selected_spells.remove(cl.swapped_out_spell)
            self.character.selected_spells.append(cl.swapped_in_spell)

        # Apply to character
        self.character.class_levels.append(cl)

        if self.on_complete:
            self.on_complete()

        self.destroy()
