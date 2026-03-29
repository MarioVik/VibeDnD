"""Step 5: Skill proficiency selection."""

import tkinter as tk
from tkinter import ttk

from gui.base_step import WizardStep
from gui.widgets import ScrollableFrame, WrappingLabel, Chip
from gui.theme import COLORS, FONTS
from models.skill_utils import compute_skill_sources


class SkillsStep(WizardStep):
    tab_title = "Skills"

    def __init__(self, parent, character, game_data):
        self._skill_vars: dict[str, tk.BooleanVar] = {}
        self._skill_cbs: dict[str, ttk.Checkbutton] = {}
        self._choose_count: int = 0
        super().__init__(parent, character, game_data)

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # ── Top: description + fixed skills ──────────────────────
        top = ttk.Frame(self.frame)
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        top.columnconfigure(0, weight=1)

        ttk.Label(top, text="Skills", style="Heading.TLabel").pack(
            anchor="w", pady=(0, 4)
        )
        WrappingLabel(
            top,
            text=(
                "Your background grants fixed skill proficiencies. "
                "Your class lets you choose additional skills from its list."
            ),
            foreground=COLORS["fg_dim"],
        ).pack(fill=tk.X, anchor="w", pady=(0, 12))

        ttk.Label(top, text="FIXED SKILLS", style="Dim.TLabel").pack(
            anchor="w", pady=(0, 4)
        )
        self.auto_chips_frame = tk.Frame(top, bg=COLORS["bg_surface"])
        self.auto_chips_frame.pack(fill=tk.X, anchor="w", pady=(0, 4))

        self.sources_frame = ttk.Frame(top)
        self.sources_frame.pack(fill=tk.X, anchor="w", pady=(0, 8))

        ttk.Separator(top, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(4, 0))

        # ── Bottom: scrollable choose section ────────────────────
        scroll = ScrollableFrame(self.frame)
        scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 12))
        inner = scroll.inner

        # Counter header
        header = ttk.Frame(inner)
        header.pack(fill=tk.X, anchor="w", pady=(0, 8))
        self.choose_label = ttk.Label(
            header, text="Choose Skills", style="Subheading.TLabel"
        )
        self.choose_label.pack(side=tk.LEFT)
        self.counter_label = ttk.Label(header, text="(0 / 0)", style="Dim.TLabel")
        self.counter_label.pack(side=tk.LEFT, padx=(8, 0))

        # Class skill options
        ttk.Label(inner, text="CLASS SKILLS", style="Dim.TLabel").pack(
            anchor="w", pady=(0, 4)
        )
        self.options_frame = ttk.Frame(inner)
        self.options_frame.pack(fill=tk.X, anchor="w", pady=(0, 12))

        # Selected chips
        ttk.Separator(inner, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Label(inner, text="SELECTED", style="Dim.TLabel").pack(
            anchor="w", pady=(0, 4)
        )
        self.selected_frame = tk.Frame(inner, bg=COLORS["bg_surface"])
        self.selected_frame.pack(fill=tk.X, anchor="w")

    # ── Lifecycle ────────────────────────────────────────────────

    def on_enter(self):
        """Rebuild the UI based on current character choices."""
        sources = compute_skill_sources(self.character)
        auto = sources["auto"]
        class_options = sources["class_options"]
        self._choose_count = sources["choose_count"]

        auto_names = {name for name, _ in auto}

        # Sanitise selected_skills: remove any that are now auto-granted
        # or no longer in class options.
        valid_options = set(class_options) - auto_names
        self.character.selected_skills = [
            s for s in self.character.selected_skills if s in valid_options
        ]

        self._rebuild_auto_chips(auto)
        self._rebuild_sources_info(auto)
        self._rebuild_skill_list(class_options, auto_names)
        self._update_counter()
        self._update_selected_chips()

    def _rebuild_auto_chips(self, auto: list[tuple[str, str]]):
        for w in self.auto_chips_frame.winfo_children():
            w.destroy()
        if not auto:
            ttk.Label(
                self.auto_chips_frame,
                text="No fixed skills yet — choose a background first.",
                style="Dim.TLabel",
            ).pack(anchor="w")
        else:
            for name, _ in auto:
                Chip(self.auto_chips_frame, text=name, style="default").pack(
                    side=tk.LEFT, padx=(0, 4), pady=2
                )

    def _rebuild_sources_info(self, auto: list[tuple[str, str]]):
        for w in self.sources_frame.winfo_children():
            w.destroy()
        for name, source in auto:
            row = ttk.Frame(self.sources_frame)
            row.pack(fill=tk.X, anchor="w", pady=1)
            ttk.Label(row, text=f"• {name}:", font=FONTS["body_bold"]).pack(
                side=tk.LEFT
            )
            ttk.Label(row, text=f" {source}", style="Dim.TLabel").pack(side=tk.LEFT)

    def _rebuild_skill_list(
        self, class_options: list[str], auto_names: set[str]
    ):
        """Rebuild checkbutton list for class skill options."""
        self._skill_vars.clear()
        self._skill_cbs.clear()

        for w in self.options_frame.winfo_children():
            w.destroy()

        if not class_options:
            ttk.Label(
                self.options_frame,
                text="No class selected yet.",
                style="Dim.TLabel",
            ).pack(anchor="w")
            return

        chosen_set = set(self.character.selected_skills)

        cols_frame = ttk.Frame(self.options_frame)
        cols_frame.pack(fill=tk.X)

        idx = 0
        for skill_name in class_options:
            if skill_name in auto_names:
                # Already granted by background — skip from choosable list
                continue
            var = tk.BooleanVar(value=skill_name in chosen_set)
            cb = ttk.Checkbutton(
                cols_frame,
                text=skill_name,
                variable=var,
                command=lambda s=skill_name, v=var: self._on_toggle(s, v),
            )
            col = idx % 3
            row = idx // 3
            cb.grid(row=row, column=col, sticky="w", padx=8, pady=1)
            self._skill_vars[skill_name] = var
            self._skill_cbs[skill_name] = cb
            idx += 1

        self._enforce_capacity()

    def _on_toggle(self, skill: str, var: tk.BooleanVar):
        chosen = self.character.selected_skills
        if var.get():
            if len(chosen) >= self._choose_count:
                var.set(False)
                self._flash_counter()
                return
            if skill not in chosen:
                chosen.append(skill)
        else:
            if skill in chosen:
                chosen.remove(skill)

        self._enforce_capacity()
        self._update_counter()
        self._update_selected_chips()
        self.notify_change()

    def _enforce_capacity(self):
        """Disable unchosen checkbuttons when at capacity."""
        chosen = self.character.selected_skills
        at_cap = len(chosen) >= self._choose_count
        for skill, cb in self._skill_cbs.items():
            var = self._skill_vars[skill]
            if not var.get():
                cb.configure(state="disabled" if at_cap else "normal")

    def _update_counter(self):
        chosen_count = len(self.character.selected_skills)
        self.counter_label.configure(
            text=f"({chosen_count} / {self._choose_count})",
            foreground=(
                COLORS["positive"]
                if chosen_count == self._choose_count
                else COLORS["fg_dim"]
            ),
        )

    def _flash_counter(self):
        """Briefly highlight the counter to signal capacity reached."""
        self.counter_label.configure(foreground=COLORS["accent"])
        self.frame.after(600, self._update_counter)

    def _update_selected_chips(self):
        for w in self.selected_frame.winfo_children():
            w.destroy()
        chosen = self.character.selected_skills
        if not chosen:
            ttk.Label(
                self.selected_frame, text="None chosen yet.", style="Dim.TLabel"
            ).pack(anchor="w")
        else:
            for skill in chosen:
                Chip(self.selected_frame, text=skill, style="accent").pack(
                    side=tk.LEFT, padx=(0, 4), pady=2
                )

    # ── Validation ───────────────────────────────────────────────

    def is_valid(self) -> bool:
        return len(self.character.selected_skills) == self._choose_count
