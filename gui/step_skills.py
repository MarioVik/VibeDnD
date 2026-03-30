"""Step 5: Skill proficiency selection."""

import tkinter as tk
from tkinter import ttk

from gui.base_step import WizardStep
from gui.widgets import ScrollableFrame, WrappingLabel, Chip, GradientHeader, SectionHeader, CardFrame
from gui.theme import COLORS, FONTS, SPACING
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

        # ── Hero header ─────────────────────────────────────────
        hero = GradientHeader(self.frame, min_height=60)
        hero.grid(row=0, column=0, sticky="ew")

        hero_inner = tk.Frame(hero.inner, bg=COLORS["bg_hero"])
        hero_inner.pack(fill=tk.X, padx=SPACING["card_pad"], pady=(SPACING["xl"], 0))

        tk.Label(
            hero_inner,
            text="Skills",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        tk.Label(
            hero.inner,
            text="Your background grants fixed skill proficiencies. Your class lets you choose additional skills.",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xs"], SPACING["xl"]))

        # ── Scrollable content ──────────────────────────────────
        scroll = ScrollableFrame(self.frame)
        scroll.grid(row=1, column=0, sticky="nsew")
        inner = scroll.inner

        # Fixed skills section
        SectionHeader(inner, text="Fixed Skills").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )

        fixed_card = CardFrame(inner, pad=SPACING["lg"])
        fixed_card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        self.auto_chips_frame = tk.Frame(fixed_card.inner, bg=COLORS["bg_surface"])
        self.auto_chips_frame.pack(fill=tk.X, anchor="w", pady=(0, SPACING["xs"]))

        self.sources_frame = tk.Frame(fixed_card.inner, bg=COLORS["bg_surface"])
        self.sources_frame.pack(fill=tk.X, anchor="w")

        # Choose section header with counter
        self._choose_header_frame = tk.Frame(inner, bg=COLORS["bg"])
        self._choose_header_frame.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"]))

        self.choose_section_header = SectionHeader(self._choose_header_frame, text="Choose Skills")
        self.choose_section_header.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.counter_label = tk.Label(
            self._choose_header_frame,
            text="(0 / 0)",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
        )
        self.counter_label.pack(side=tk.RIGHT, padx=(SPACING["sm"], 0))

        # Class skill options
        options_card = CardFrame(inner, pad=SPACING["lg"])
        options_card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        tk.Label(
            options_card.inner,
            text="CLASS SKILLS",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", pady=(0, SPACING["xs"]))

        self.options_frame = tk.Frame(options_card.inner, bg=COLORS["bg_surface"])
        self.options_frame.pack(fill=tk.X, anchor="w")

        # Selected chips
        SectionHeader(inner, text="Selected").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )
        selected_card = CardFrame(inner, pad=SPACING["lg"])
        selected_card.pack(fill=tk.X, padx=SPACING["lg"])
        self.selected_frame = tk.Frame(selected_card.inner, bg=COLORS["bg_surface"])
        self.selected_frame.pack(fill=tk.X, anchor="w")

    # ── Lifecycle ────────────────────────────────────────────────

    def on_enter(self):
        """Rebuild the UI based on current character choices."""
        sources = compute_skill_sources(self.character)
        auto = sources["auto"]
        class_options = sources["class_options"]
        self._choose_count = sources["choose_count"]

        auto_names = {name for name, _ in auto}

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
            tk.Label(
                self.auto_chips_frame,
                text="No fixed skills yet \u2014 choose a background first.",
                font=FONTS["body"], fg=COLORS["fg_dim"], bg=COLORS["bg_surface"],
            ).pack(anchor="w")
        else:
            for name, _ in auto:
                Chip(self.auto_chips_frame, text=name, style="default").pack(
                    side=tk.LEFT, padx=(0, 4), pady=2
                )

    def _rebuild_sources_info(self, auto: list[tuple[str, str]]):
        for w in self.sources_frame.winfo_children():
            w.destroy()
        _bg = COLORS["bg_surface"]
        for name, source in auto:
            row = tk.Frame(self.sources_frame, bg=_bg)
            row.pack(fill=tk.X, anchor="w", pady=1)
            tk.Label(row, text=f"\u2022 {name}:", font=FONTS["body_bold"], fg=COLORS["fg"], bg=_bg).pack(side=tk.LEFT)
            tk.Label(row, text=f" {source}", font=FONTS["body_small"], fg=COLORS["fg_dim"], bg=_bg).pack(side=tk.LEFT)

    def _rebuild_skill_list(
        self, class_options: list[str], auto_names: set[str]
    ):
        """Rebuild checkbutton list for class skill options."""
        self._skill_vars.clear()
        self._skill_cbs.clear()

        for w in self.options_frame.winfo_children():
            w.destroy()

        if not class_options:
            tk.Label(
                self.options_frame,
                text="No class selected yet.",
                font=FONTS["body"], fg=COLORS["fg_dim"], bg=COLORS["bg_surface"],
            ).pack(anchor="w")
            return

        chosen_set = set(self.character.selected_skills)

        idx = 0
        for skill_name in class_options:
            if skill_name in auto_names:
                continue
            var = tk.BooleanVar(value=skill_name in chosen_set)
            cb = ttk.Checkbutton(
                self.options_frame,
                text=skill_name,
                variable=var,
                command=lambda s=skill_name, v=var: self._on_toggle(s, v),
            )
            col = idx % 3
            row = idx // 3
            cb.grid(row=row, column=col, sticky="w", padx=SPACING["sm"], pady=1)
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
            fg=(
                COLORS["positive"]
                if chosen_count == self._choose_count
                else COLORS["fg_dim"]
            ),
        )

    def _flash_counter(self):
        """Briefly highlight the counter to signal capacity reached."""
        self.counter_label.configure(fg=COLORS["accent"])
        self.frame.after(600, self._update_counter)

    def _update_selected_chips(self):
        for w in self.selected_frame.winfo_children():
            w.destroy()
        chosen = self.character.selected_skills
        if not chosen:
            tk.Label(
                self.selected_frame, text="None chosen yet.",
                font=FONTS["body"], fg=COLORS["fg_dim"], bg=COLORS["bg_surface"],
            ).pack(anchor="w")
        else:
            for skill in chosen:
                Chip(self.selected_frame, text=skill, style="accent").pack(
                    side=tk.LEFT, padx=(0, 4), pady=2
                )

    # ── Validation ───────────────────────────────────────────────

    def is_valid(self) -> bool:
        return len(self.character.selected_skills) == self._choose_count
