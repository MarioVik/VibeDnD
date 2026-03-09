"""Level-up wizard dialog for advancing a character by one level.

Two-step flow:
  Step 1 – class features, HP, ASI / feat, subclass
  Step 2 – spell selection (only shown when the level grants new spells)
"""

import tkinter as tk
from tkinter import ttk, messagebox

from gui.theme import COLORS, FONTS
from gui.widgets import ScrollableFrame, WrappingLabel, ConfirmDialog, AlertDialog
from models.character import Character
from models.class_level import ClassLevel

_SLOT_ORDER = {
    "1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5,
    "6th": 6, "7th": 7, "8th": 8, "9th": 9,
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
        width = 750
        height = 600
        
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
        self.minsize(650, 500)
        self.configure(bg=COLORS["bg"])

        self.transient(top)
        self.grab_set()
        self.focus_set()

        # Determine what the next level will be
        self.new_total_level = character.level + 1
        self.primary_class_slug = (
            character.character_class.get("slug", "") if character.character_class else ""
        )
        self.class_slug = self.primary_class_slug
        self.class_var = tk.StringVar(value=self.class_slug)

        self._update_level_data()

        # Choices to collect
        self.hp_choice = tk.IntVar(value=0)
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

        self._build_ui()

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def _update_level_data(self):
        """Update progression data for the currently selected class."""
        self.class_slug = self.class_var.get()
        self.new_class_level = self.character.class_level_in(self.class_slug) + 1
        self.progression = self.data.get_progression(self.class_slug)
        self.level_data = self.data.get_level_data(self.class_slug, self.new_class_level)

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

        curr_cantrips = self.level_data.get("cantrips", 0) or 0
        prev_cantrips = prev.get("cantrips", 0) or 0
        curr_prepared = self.level_data.get("prepared_spells", 0) or 0
        prev_prepared = prev.get("prepared_spells", 0) or 0

        curr_slots = self.level_data.get("spell_slots") or {}
        max_spell_level = max((_SLOT_ORDER.get(k, 0) for k in curr_slots), default=0)

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

    # ------------------------------------------------------------------
    # UI skeleton
    # ------------------------------------------------------------------

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────
        self.header_frame = ttk.Frame(self)
        self.header_frame.pack(fill=tk.X, padx=16, pady=(16, 8))

        self.header_label = ttk.Label(
            self.header_frame, text=self._header_text(),
            font=("Segoe UI", 16, "bold"), foreground=COLORS["accent"],
        )
        self.header_label.pack(side=tk.LEFT)

        ttk.Label(
            self.header_frame, text=f"(Total Level {self.new_total_level})",
            font=FONTS["body"], foreground=COLORS["fg_dim"],
        ).pack(side=tk.LEFT, padx=8)

        # ── Multiclass selector ───────────────────────────────────
        self.mc_frame = ttk.Frame(self)
        self.mc_frame.pack(fill=tk.X, padx=16, pady=(0, 4))

        ttk.Label(self.mc_frame, text="Class:", foreground=COLORS["fg"]).pack(side=tk.LEFT)
        class_options = [cls["slug"] for cls in self.data.classes]
        self.class_combo = ttk.Combobox(
            self.mc_frame, textvariable=self.class_var,
            values=class_options, state="readonly", width=20,
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

        # Step 2 – spell selection (built lazily)
        self.step2_frame = ttk.Frame(self.content_container)

        # Step 3 – spell swap (built lazily)
        self.step3_frame = ttk.Frame(self.content_container)

        # ── Bottom buttons (pack BEFORE content so they always get space) ──
        self.btn_frame = ttk.Frame(self)
        self.btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=(8, 16))

        # Now pack content container to fill remaining space
        self.content_container.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)

        self.cancel_btn = ttk.Button(self.btn_frame, text="Cancel", command=self.destroy)
        self.cancel_btn.pack(side=tk.LEFT)

        self.confirm_btn = ttk.Button(
            self.btn_frame, text="Confirm Level Up",
            style="Accent.TButton", command=self._confirm,
        )

        self.next_btn = ttk.Button(
            self.btn_frame, text="Next: Spells \u2192",
            style="Accent.TButton", command=lambda: self._try_go_next(2),
        )

        self.back_btn = ttk.Button(
            self.btn_frame, text="\u2190 Back",
            command=lambda: self._show_step(1),
        )

        # Build step 1 content and show it
        self._rebuild_content()
        self._show_step(1)

    def _try_go_next(self, target_step: int):
        if target_step == 2 or target_step == 3:
            if not self._validate_step1():
                return
        if target_step == 3 and self._has_new_spell_options():
            if not self._validate_step2():
                return
        self._show_step(target_step)

    def _validate_step1(self) -> bool:
        if (self.class_slug != self.primary_class_slug
                and self.character.class_level_in(self.class_slug) == 0):
            met, reason = self.character.multiclass_prereqs_met(self.class_slug)
            if not met:
                AlertDialog(
                    self, "Prerequisites Not Met",
                    f"Cannot multiclass into {self.class_slug.title()}:\n{reason}")
                return False
            pri_met, pri_reason = self.character.multiclass_prereqs_met(
                self.primary_class_slug)
            if not pri_met:
                AlertDialog(
                    self, "Prerequisites Not Met",
                    f"Cannot multiclass out of {self.primary_class_slug.title()}:\n{pri_reason}")
                return False

        if self.level_data:
            features = self.level_data.get("features", [])
            if any("Ability Score Improvement" in f for f in features):
                if not self.feat_var.get():
                    AlertDialog(
                        self, "Missing Choice",
                        "Please select a feat for your Ability Score Improvement.")
                    return False
            if any("Subclass" in f and "Feature" not in f for f in features):
                if not self.subclass_var.get():
                    AlertDialog(
                        self, "Missing Choice", "Please select a subclass.")
                    return False
        return True

    def _validate_step2(self) -> bool:
        if self._has_new_spell_options():
            new_cantrips_max, new_prepared_max, _ = self._spell_deltas()
            if new_cantrips_max > 0 and len(self.selected_new_cantrips) < new_cantrips_max:
                AlertDialog(
                    self, "Missing Choice",
                    f"Please select {new_cantrips_max} new cantrip(s) on the Spells step.")
                return False
            if new_prepared_max > 0 and len(self.selected_new_spells) < new_prepared_max:
                AlertDialog(
                    self, "Missing Choice",
                    f"Please select {new_prepared_max} new spell(s) on the Spells step.")
                return False
        return True

    def _show_step(self, step: int):
        """Show *step* (1, 2, or 3) and update bottom buttons."""
        self.step1_scroll.pack_forget()
        self.step2_frame.pack_forget()
        self.step3_frame.pack_forget()
        self.confirm_btn.pack_forget()
        self.next_btn.pack_forget()
        self.back_btn.pack_forget()

        # Only show multiclass selector on step 1
        if step == 1:
            self.mc_frame.pack(fill=tk.X, padx=16, pady=(0, 4),
                               after=self.header_frame)
        else:
            self.mc_frame.pack_forget()

        has_spells = self._has_new_spell_options()
        has_swap = self._has_swap_step()

        if step == 1:
            self.step1_scroll.pack(in_=self.content_container,
                                   fill=tk.BOTH, expand=True)
            if has_spells:
                self.next_btn.configure(text="Next: Spells \u2192",
                                        command=lambda: self._try_go_next(2))
                self.next_btn.pack(side=tk.RIGHT)
            elif has_swap:
                self.next_btn.configure(text="Next: Swap Spells \u2192",
                                        command=lambda: self._try_go_next(3))
                self.next_btn.pack(side=tk.RIGHT)
            else:
                self.confirm_btn.pack(side=tk.RIGHT)

        elif step == 2:
            self._build_spell_step()
            self.step2_frame.pack(in_=self.content_container,
                                  fill=tk.BOTH, expand=True)
            self.back_btn.configure(command=lambda: self._show_step(1))
            self.back_btn.pack(side=tk.LEFT, padx=(8, 0))
            if has_swap:
                self.next_btn.configure(text="Next: Swap Spells \u2192",
                                        command=lambda: self._try_go_next(3))
                self.next_btn.pack(side=tk.RIGHT)
            else:
                self.confirm_btn.pack(side=tk.RIGHT)

        elif step == 3:
            self._build_swap_step()
            self.step3_frame.pack(in_=self.content_container,
                                  fill=tk.BOTH, expand=True)
            prev_step = 2 if has_spells else 1
            self.back_btn.configure(command=lambda: self._show_step(prev_step))
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

        if (self.class_slug != self.primary_class_slug
                and self.character.class_level_in(self.class_slug) == 0):
            met, reason = self.character.multiclass_prereqs_met(self.class_slug)
            pri_met, pri_reason = self.character.multiclass_prereqs_met(self.primary_class_slug)
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
            self.step1_content, text="New Features",
            font=FONTS["heading"], foreground=COLORS["accent"],
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
                frame, text=feat_name, font=FONTS["subheading"],
                foreground=COLORS["fg_bright"], background=COLORS["bg_card"],
            ).pack(anchor="w", padx=8, pady=(4, 0))

            desc = ""
            for d in details:
                if d["name"].lower() == feat_name.lower():
                    desc = d["description"]
                    break
            if desc:
                WrappingLabel(
                    frame, text=desc,
                    foreground=COLORS["fg_dim"], background=COLORS["bg_card"],
                ).pack(fill=tk.X, anchor="w", padx=8, pady=(0, 4))

        extra = self.level_data.get("extra", {})
        if extra:
            for col_name, val in extra.items():
                if val is not None:
                    ttk.Label(
                        self.step1_content, text=f"{col_name}: {val}",
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
                frame, text=f"{feat['name']} (Subclass)",
                font=FONTS["subheading"], foreground=COLORS["fg_bright"],
                background=COLORS["bg_card"],
            ).pack(anchor="w", padx=8, pady=(4, 0))
            desc = feat.get("description", "")
            if desc:
                WrappingLabel(
                    frame, text=desc,
                    foreground=COLORS["fg_dim"], background=COLORS["bg_card"],
                ).pack(fill=tk.X, anchor="w", padx=8, pady=(0, 4))

    # ── HP ────────────────────────────────────────────────────────

    def _build_hp_section(self):
        ttk.Separator(self.step1_content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Label(
            self.step1_content, text="Hit Points",
            font=FONTS["heading"], foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(4, 4))

        hit_die = self.selected_class_data.get("hit_die", 8) if self.selected_class_data else 8
        con_mod = self.character.ability_scores.modifier("Constitution")
        average = hit_die // 2 + 1

        hp_frame = ttk.Frame(self.step1_content)
        hp_frame.pack(fill=tk.X, padx=12)

        ttk.Radiobutton(
            hp_frame,
            text=f"Take average ({average} + {con_mod} CON = {average + con_mod} HP)",
            variable=self.hp_choice, value=average,
        ).pack(anchor="w", pady=2)

        ttk.Radiobutton(
            hp_frame,
            text=f"Take max ({hit_die} + {con_mod} CON = {hit_die + con_mod} HP)",
            variable=self.hp_choice, value=hit_die,
        ).pack(anchor="w", pady=2)

        self.hp_choice.set(average)

    # ── ASI ───────────────────────────────────────────────────────

    def _build_asi_section(self):
        ttk.Separator(self.step1_content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Label(
            self.step1_content, text="Ability Score Improvement",
            font=FONTS["heading"], foreground=COLORS["accent"],
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
            feat_frame, textvariable=self.feat_var,
            values=feat_options, state="readonly", width=40,
        ).pack(anchor="w")

    # ── Subclass ──────────────────────────────────────────────────

    def _build_subclass_section(self):
        ttk.Separator(self.step1_content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Label(
            self.step1_content, text="Choose Subclass",
            font=FONTS["heading"], foreground=COLORS["accent"],
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
            sub_frame, textvariable=self.subclass_var,
            values=sorted(options), state="readonly", width=40,
        ).pack(anchor="w")

        self.sub_desc_label = WrappingLabel(
            self.step1_content, text="", foreground=COLORS["fg_dim"],
        )
        self.sub_desc_label.pack(fill=tk.X, anchor="w", padx=12, pady=4)

        def on_sub_select(*_):
            name = self.subclass_var.get().replace(" (PHB)", "")
            for sc in subclasses:
                if sc["name"] == name:
                    self.sub_desc_label.configure(text=sc.get("description", ""))
                    return
            self.sub_desc_label.configure(text="(Core subclass - feature data not available)")

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
            self.step1_content, text="Spellcasting Changes",
            font=FONTS["heading"], foreground=COLORS["accent"],
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
                f"{k}: {v}" for k, v in sorted(
                    curr_slots.items(), key=lambda x: _SLOT_ORDER.get(x[0], 99)))
            parts.append(f"Total spell slots: {s}")

        for p in parts:
            ttk.Label(
                self.step1_content, text=f"  {p}", foreground=COLORS["fg"],
            ).pack(anchor="w", padx=12, pady=1)

        ttk.Label(
            self.step1_content,
            text='(Choose your new spells on the next step)',
            foreground=COLORS["fg_dim"], font=("Segoe UI", 9),
        ).pack(anchor="w", padx=12, pady=(4, 0))

    # ------------------------------------------------------------------
    # Step 2 – spell selection
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
        class_name = (self.selected_class_data.get("name", "")
                      if self.selected_class_data else "")
        has_cantrips = new_cantrips > 0
        has_spells = new_prepared > 0

        # ── heading ───────────────────────────────────────────────
        ttk.Label(
            self.step2_frame, text="Select New Spells",
            font=FONTS["heading"], foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(4, 2))

        parts = []
        if has_cantrips:
            parts.append(f"Learn {new_cantrips} new cantrip(s)")
        if has_spells:
            parts.append(f"Prepare {new_prepared} additional spell(s)")
        if parts:
            ttk.Label(
                self.step2_frame, text="  •  ".join(parts),
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
                left, text=f"0 / {new_cantrips} cantrips selected",
                style="Dim.TLabel",
            )
            self.cantrip_count_label.pack(anchor="w", padx=4, pady=(0, 1))
        if has_spells:
            self.spell_count_label = ttk.Label(
                left, text=f"0 / {new_prepared} spells selected",
                style="Dim.TLabel",
            )
            self.spell_count_label.pack(anchor="w", padx=4, pady=(0, 1))

        list_outer = ttk.Frame(left)
        list_outer.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        canvas, inner = self._make_scrollable_list(list_outer)

        # Section header helper (matches SectionedListbox style)
        def _section_header(parent, title):
            ttk.Label(
                parent, text=f"\u2500\u2500 {title} \u2500\u2500",
                foreground=COLORS["accent"], font=FONTS["body"],
            ).pack(anchor="w", pady=(6, 2))

        # ── cantrips ─────────────────────────────────────────────
        if has_cantrips:
            _section_header(inner, "Cantrips")

            all_cantrips = self.data.cantrips_for_class(class_name)
            known = set(self.character.selected_cantrips)
            available = [s for s in all_cantrips if s["name"] not in known]

            for spell in sorted(available, key=lambda s: s["name"]):
                var = tk.BooleanVar(value=False)
                var.trace_add("write",
                              lambda *a, s=spell: self._on_new_cantrip_toggle(s))
                self.cantrip_vars[spell["name"]] = {"var": var, "spell": spell}
                cb = ttk.Checkbutton(
                    inner, text=f"{spell['name']} ({spell['school']})",
                    variable=var,
                )
                cb.pack(anchor="w", pady=1, padx=(8, 0))
                cb.bind("<Enter>",
                        lambda e, s=spell: self._show_spell_detail(s))
                self.cantrip_checkbuttons[spell["name"]] = cb

        # ── leveled spells grouped by level ──────────────────────
        if has_spells:
            _LEVEL_NAMES = {
                1: "1st-Level", 2: "2nd-Level", 3: "3rd-Level",
                4: "4th-Level", 5: "5th-Level", 6: "6th-Level",
                7: "7th-Level", 8: "8th-Level", 9: "9th-Level",
            }

            all_spells = self.data.spells_for_class(
                class_name, max_level=max_spell_level)
            known = set(self.character.selected_spells)
            available = [s for s in all_spells
                         if s["name"] not in known and s.get("level", 0) >= 1]
            available.sort(key=lambda s: (s["level"], s["name"]))

            # Group by level
            from itertools import groupby
            for lvl, group in groupby(available, key=lambda s: s["level"]):
                _section_header(inner, _LEVEL_NAMES.get(lvl, f"Level {lvl}"))
                for spell in group:
                    var = tk.BooleanVar(value=False)
                    var.trace_add(
                        "write",
                        lambda *a, s=spell: self._on_new_spell_toggle(s))
                    self.spell_vars[spell["name"]] = {
                        "var": var, "spell": spell}

                    text = f"{spell['name']} ({spell['school']}"
                    if spell.get("concentration"):
                        text += ", C"
                    if spell.get("ritual"):
                        text += ", R"
                    text += ")"

                    cb = ttk.Checkbutton(inner, text=text, variable=var)
                    cb.pack(anchor="w", pady=1, padx=(8, 0))
                    cb.bind("<Enter>",
                            lambda e, s=spell: self._show_spell_detail(s))
                    self.spell_checkbuttons[spell["name"]] = cb

        # --- RIGHT: spell detail ---
        detail_lf = ttk.LabelFrame(cols, text="Spell Details")
        detail_lf.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        self.spell_detail_text = tk.Text(
            detail_lf, wrap=tk.WORD,
            bg=COLORS["bg_light"], fg=COLORS["fg"],
            font=FONTS["body"], borderwidth=0, state=tk.DISABLED,
        )
        self.spell_detail_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    # ── scrollable list helper (same pattern as step_spells.py) ──

    def _make_scrollable_list(self, parent_frame):
        canvas = tk.Canvas(parent_frame, bg=COLORS["bg"],
                           highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(parent_frame, orient=tk.VERTICAL,
                                  command=canvas.yview)
        inner = ttk.Frame(canvas)

        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        cw = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.bind("<Configure>",
                    lambda e, _cw=cw: canvas.itemconfig(_cw, width=e.width))

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def _on_wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

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
                text=f"{len(selected)} / {new_cantrips_max} selected")
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
                text=f"{len(selected)} / {new_prepared_max} selected")
            self._update_spell_states(new_prepared_max, selected)
        finally:
            self._updating_spells = False

    def _update_cantrip_states(self, max_count, selected):
        at_max = len(selected) >= max_count
        for name, cb in self.cantrip_checkbuttons.items():
            cb.configure(state=tk.DISABLED if at_max and name not in selected
                         else tk.NORMAL)

    def _update_spell_states(self, max_count, selected):
        at_max = len(selected) >= max_count
        for name, cb in self.spell_checkbuttons.items():
            cb.configure(state=tk.DISABLED if at_max and name not in selected
                         else tk.NORMAL)

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

        class_name = (self.selected_class_data.get("name", "")
                      if self.selected_class_data else "")
        _, _, max_spell_level = self._spell_deltas()
        # If we didn't gain new slots this level, we use current max slots for swapping
        if max_spell_level == 0 and self.level_data:
             curr_slots = self.level_data.get("spell_slots") or {}
             max_spell_level = max((_SLOT_ORDER.get(k, 0) for k in curr_slots), default=0)

        # ── heading ───────────────────────────────────────────────
        ttk.Label(
            self.step3_frame, text="Swap Spells (optional)",
            font=FONTS["heading"], foreground=COLORS["accent"],
        ).pack(anchor="w", pady=(4, 2))
        ttk.Label(
            self.step3_frame,
            text="You may replace one known spell or cantrip with a different one from your class list.",
            foreground=COLORS["fg"],
        ).pack(anchor="w", padx=4, pady=(0, 4))

        # ── Two-column split ──
        cols = ttk.Frame(self.step3_frame)
        cols.pack(fill=tk.BOTH, expand=True, pady=4)
        cols.columnconfigure(0, weight=1)
        cols.columnconfigure(1, weight=1)
        cols.rowconfigure(0, weight=1)

        LEVEL_NAMES = {
            1: "1st-Level", 2: "2nd-Level", 3: "3rd-Level",
            4: "4th-Level", 5: "5th-Level", 6: "6th-Level",
            7: "7th-Level", 8: "8th-Level", 9: "9th-Level",
        }

        def _section_header(parent, title):
            ttk.Label(
                parent, text=f"\u2500\u2500 {title} \u2500\u2500",
                foreground=COLORS["accent"], font=FONTS["body"],
            ).pack(anchor="w", pady=(6, 2))

        # --- LEFT: Forget ---
        left_lf = ttk.LabelFrame(cols, text="Forget")
        left_lf.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        left_outer = ttk.Frame(left_lf)
        left_outer.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        _, left_inner = self._make_scrollable_list(left_outer)

        forget_var = tk.StringVar(value="")
        ttk.Radiobutton(
            left_inner, text="Don't swap", variable=forget_var, value="",
        ).pack(anchor="w", pady=1)

        # Cantrips to forget
        cantrips_to_forget = []
        for name in self.character.selected_cantrips:
            d = self._find_spell(name, class_name)
            if d: cantrips_to_forget.append(d)
        
        if cantrips_to_forget:
            _section_header(left_inner, "Cantrips")
            for spell in sorted(cantrips_to_forget, key=lambda s: s["name"]):
                rb = ttk.Radiobutton(left_inner, text=spell["name"], variable=forget_var, value=f"C:{spell['name']}")
                rb.pack(anchor="w", pady=1, padx=8)
                rb.bind("<Enter>", lambda e, s=spell: self._show_swap_detail(s))

        # Spells to forget
        spells_to_forget = []
        for name in self.character.selected_spells:
            d = self._find_spell(name, class_name)
            if d: spells_to_forget.append(d)
        
        if spells_to_forget:
            from itertools import groupby
            spells_to_forget.sort(key=lambda s: (s["level"], s["name"]))
            for lvl, group in groupby(spells_to_forget, key=lambda s: s["level"]):
                _section_header(left_inner, LEVEL_NAMES.get(lvl, f"Level {lvl}"))
                for spell in group:
                    rb = ttk.Radiobutton(left_inner, text=spell["name"], variable=forget_var, value=f"S:{spell['name']}")
                    rb.pack(anchor="w", pady=1, padx=8)
                    rb.bind("<Enter>", lambda e, s=spell: self._show_swap_detail(s))

        # --- RIGHT: Learn ---
        right_lf = ttk.LabelFrame(cols, text="Learn")
        right_lf.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        right_outer = ttk.Frame(right_lf)
        right_outer.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        _, right_inner = self._make_scrollable_list(right_outer)

        learn_var = tk.StringVar(value="")
        
        # Available cantrips
        all_avail_cantrips = self.data.cantrips_for_class(class_name)
        known_c_set = set(self.character.selected_cantrips)
        known_c_set.update(self.selected_new_cantrips)
        avail_cantrips = sorted([s for s in all_avail_cantrips if s["name"] not in known_c_set], key=lambda s: s["name"])
        
        cantrip_rbs = []
        if avail_cantrips:
            _section_header(right_inner, "Cantrips")
            for spell in avail_cantrips:
                rb = ttk.Radiobutton(right_inner, text=spell["name"], variable=learn_var, value=spell["name"])
                rb.pack(anchor="w", pady=1, padx=8)
                rb.bind("<Enter>", lambda e, s=spell: self._show_swap_detail(s))
                cantrip_rbs.append((rb, spell))

        # Available spells
        all_avail_spells = self.data.spells_for_class(class_name, max_level=max_spell_level)
        known_s_set = set(self.character.selected_spells)
        known_s_set.update(self.selected_new_spells)
        avail_spells = [s for s in all_avail_spells if s["name"] not in known_s_set and s.get("level", 0) >= 1]
        avail_spells.sort(key=lambda s: (s["level"], s["name"]))

        spell_rbs = []
        from itertools import groupby
        for lvl, group in groupby(avail_spells, key=lambda s: s["level"]):
            _section_header(right_inner, LEVEL_NAMES.get(lvl, f"Level {lvl}"))
            for spell in group:
                text = f"{spell['name']} ({spell['school']}"
                if spell.get("concentration"): text += ", C"
                if spell.get("ritual"): text += ", R"
                text += ")"
                rb = ttk.Radiobutton(right_inner, text=text, variable=learn_var, value=spell["name"])
                rb.pack(anchor="w", pady=1, padx=8)
                rb.bind("<Enter>", lambda e, s=spell: self._show_swap_detail(s))
                spell_rbs.append((rb, spell))

        # --- Shared Detail Panel ---
        detail_lf = ttk.LabelFrame(self.step3_frame, text="Spell Details")
        detail_lf.pack(fill=tk.X, pady=(4, 0))
        self.swap_detail_text = tk.Text(detail_lf, wrap=tk.WORD, height=6, bg=COLORS["bg_light"], fg=COLORS["fg"], font=FONTS["body"], borderwidth=0, state=tk.DISABLED)
        self.swap_detail_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ── Logic ─────────────────────────────────────────────
        def _on_change(*_):
            val = forget_var.get()
            if not val:
                 self.swap_out_cantrip = None
                 self.swap_out_spell = None
                 learn_var.set("")
                 for rb, _ in cantrip_rbs + spell_rbs: rb.configure(state=tk.DISABLED)
            elif val.startswith("C:"):
                 self.swap_out_cantrip = val[2:]
                 self.swap_out_spell = None
                 # can only learn cantrips
                 for rb, s in cantrip_rbs: rb.configure(state=tk.NORMAL)
                 for rb, s in spell_rbs: rb.configure(state=tk.DISABLED)
                 if learn_var.get() and not any(s["name"] == learn_var.get() for _, s in cantrip_rbs):
                      learn_var.set("")
            else: # S:
                 self.swap_out_spell = val[2:]
                 self.swap_out_cantrip = None
                 # can only learn spells
                 for rb, s in cantrip_rbs: rb.configure(state=tk.DISABLED)
                 for rb, s in spell_rbs: rb.configure(state=tk.NORMAL)
                 if learn_var.get() and not any(s["name"] == learn_var.get() for _, s in spell_rbs):
                      learn_var.set("")
            
            # update instance vars for _confirm
            lv = learn_var.get()
            if self.swap_out_cantrip:
                 self.swap_in_cantrip = lv or None
                 self.swap_in_spell = None
            elif self.swap_out_spell:
                 self.swap_in_spell = lv or None
                 self.swap_in_cantrip = None
            else:
                 self.swap_in_cantrip = None
                 self.swap_in_spell = None

        forget_var.trace_add("write", _on_change)
        learn_var.trace_add("write", _on_change)
        _on_change()

    def _find_spell(self, name: str, class_name: str) -> dict | None:
        """Find a spell dict by name from the class spell list."""
        for s in self.data.spells_for_class(class_name, max_level=9):
            if s["name"] == name:
                return s
        for s in self.data.cantrips_for_class(class_name):
            if s["name"] == name:
                return s
        return None

    def _show_swap_detail(self, spell):
        """Show spell detail in the swap step's detail panel."""
        self.swap_detail_text.configure(state=tk.NORMAL)
        self.swap_detail_text.delete("1.0", tk.END)
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
        self.swap_detail_text.insert("1.0", "\n".join(lines))
        self.swap_detail_text.configure(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Confirm
    # ------------------------------------------------------------------

    def _confirm(self):
        """Validate choices, apply the level-up, and close."""
        if not self._validate_step1():
            return
        if self._has_new_spell_options() and not self._validate_step2():
            return

        # ── validate swap choices (incomplete = picked forget but not learn) ─
        if self.swap_out_cantrip and not self.swap_in_cantrip:
            AlertDialog(
                self, "Incomplete Swap",
                "You selected a cantrip to forget but didn't pick one to learn.")
            self._show_step(3)
            return
        if self.swap_out_spell and not self.swap_in_spell:
            AlertDialog(
                self, "Incomplete Swap",
                "You selected a spell to forget but didn't pick one to learn.")
            self._show_step(3)
            return

        # ── confirmation dialog ──────────────────────────────────
        dlg = ConfirmDialog(
            self, "Confirm Level Up", 
            "Are you sure? These changes will be permanently saved."
        )
        if not dlg.result:
            return

        # ── build ClassLevel ──────────────────────────────────────
        hit_die = (self.selected_class_data.get("hit_die", 8)
                   if self.selected_class_data else 8)

        cl = ClassLevel(
            class_slug=self.class_slug,
            class_level=self.new_class_level,
            hp_roll=self.hp_choice.get(),
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
