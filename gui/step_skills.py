"""Step 5: Skill proficiency and expertise selection."""

import tkinter as tk
from tkinter import ttk

from gui.base_step import WizardStep
from gui.widgets import (
    ScrollableFrame,
    Chip,
    GradientHeader,
    SectionHeader,
    CardFrame,
)
from gui.theme import COLORS, FONTS, SPACING
from models.skill_utils import (
    compute_skill_sources,
    scrub_expertise_selections,
    set_feat_expertise_skill,
)

CARD_CHECK_STYLE = "Card.TCheckbutton"


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
            text=(
                "Your background grants fixed skill proficiencies, your class adds "
                "skill picks, and some features can grant Expertise."
            ),
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xs"], SPACING["xl"]))

        scroll = ScrollableFrame(self.frame)
        scroll.grid(row=1, column=0, sticky="nsew")
        inner = scroll.inner

        SectionHeader(inner, text="Fixed Skills").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )

        fixed_card = CardFrame(inner, pad=SPACING["lg"])
        fixed_card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        self.auto_chips_frame = tk.Frame(fixed_card.inner, bg=COLORS["bg_surface"])
        self.auto_chips_frame.pack(fill=tk.X, anchor="w", pady=(0, SPACING["xs"]))

        self.sources_frame = tk.Frame(fixed_card.inner, bg=COLORS["bg_surface"])
        self.sources_frame.pack(fill=tk.X, anchor="w")

        self.choose_section_header = SectionHeader(inner, text="Choose Skills")
        self.choose_section_header.pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )
        self.counter_label = self._install_inline_counter(self.choose_section_header)

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

        SectionHeader(inner, text="Selected").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )
        selected_card = CardFrame(inner, pad=SPACING["lg"])
        selected_card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))
        self.selected_frame = tk.Frame(selected_card.inner, bg=COLORS["bg_surface"])
        self.selected_frame.pack(fill=tk.X, anchor="w")

        self.expertise_section_header = SectionHeader(inner, text="Choose Expertise")
        self.expertise_section_header.pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )
        self.expertise_counter_label = self._install_inline_counter(
            self.expertise_section_header
        )
        self.expertise_card = CardFrame(inner, pad=SPACING["lg"])
        self.expertise_card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["lg"]))
        self.expertise_frame = tk.Frame(self.expertise_card.inner, bg=COLORS["bg_surface"])
        self.expertise_frame.pack(fill=tk.X, anchor="w")

    def _install_inline_counter(self, header: SectionHeader) -> tk.Label:
        counter = tk.Label(
            header,
            text="(0 / 0)",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
        )
        header._line.pack_forget()
        counter.pack(side=tk.LEFT, padx=(0, 12))
        header._line.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=1)
        return counter

    def on_enter(self):
        self._refresh_step(scrub_expertise=True)

    def _refresh_step(self, *, scrub_expertise: bool):
        sources = compute_skill_sources(self.character)
        auto = sources["auto"]
        class_options = sources["class_options"]
        auto_names = {name for name, _ in auto}

        valid_options = set(class_options) - auto_names
        cleaned_skills = [
            skill for skill in self.character.selected_skills if skill in valid_options
        ]
        skills_changed = cleaned_skills != self.character.selected_skills
        if skills_changed:
            self.character.selected_skills = cleaned_skills

        if scrub_expertise or skills_changed:
            scrub_expertise_selections(self.character)

        sources = compute_skill_sources(self.character)
        auto_names = {name for name, _ in sources["auto"]}
        self._choose_count = sources["choose_count"]
        skills_complete = len(self.character.selected_skills) == self._choose_count

        self._rebuild_auto_chips(sources["auto"])
        self._rebuild_sources_info(sources["auto"])
        self._rebuild_skill_list(sources["class_options"], auto_names)
        self._update_counter()
        has_expertise = bool(
            sources["expertise_auto"]
            or sources["expertise_selectable"]
            or sources["expertise_choose_count"]
        )
        self._set_expertise_visibility(has_expertise)
        if has_expertise:
            self._update_expertise_counter(sources, enabled=skills_complete)
            self._rebuild_expertise_section(
                sources["expertise_auto"],
                sources["expertise_selectable"],
                enabled=skills_complete,
            )
        self._update_selected_chips()

    def _set_expertise_visibility(self, visible: bool):
        if visible:
            if not self.expertise_section_header.winfo_manager():
                self.expertise_section_header.pack(
                    fill=tk.X,
                    padx=SPACING["lg"],
                    pady=(SPACING["sm"], SPACING["sm"]),
                )
            if not self.expertise_card.winfo_manager():
                self.expertise_card.pack(
                    fill=tk.X,
                    padx=SPACING["lg"],
                    pady=(0, SPACING["lg"]),
                )
            return

        self.expertise_section_header.pack_forget()
        self.expertise_card.pack_forget()

    def _rebuild_auto_chips(self, auto: list[tuple[str, str]]):
        for widget in self.auto_chips_frame.winfo_children():
            widget.destroy()

        if not auto:
            tk.Label(
                self.auto_chips_frame,
                text="No fixed skills yet - choose a background first.",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w")
            return

        seen: set[str] = set()
        for name, _source in auto:
            if name in seen:
                continue
            seen.add(name)
            Chip(self.auto_chips_frame, text=name, style="default").pack(
                side=tk.LEFT, padx=(0, 4), pady=2
            )

    def _rebuild_sources_info(self, auto: list[tuple[str, str]]):
        for widget in self.sources_frame.winfo_children():
            widget.destroy()

        background = COLORS["bg_surface"]
        for name, source in auto:
            row = tk.Frame(self.sources_frame, bg=background)
            row.pack(fill=tk.X, anchor="w", pady=1)
            tk.Label(
                row,
                text=f"\u2022 {name}:",
                font=FONTS["body_bold"],
                fg=COLORS["fg"],
                bg=background,
            ).pack(side=tk.LEFT)
            tk.Label(
                row,
                text=f" {source}",
                font=FONTS["body_small"],
                fg=COLORS["fg_dim"],
                bg=background,
            ).pack(side=tk.LEFT)

    def _rebuild_skill_list(self, class_options: list[str], auto_names: set[str]):
        self._skill_vars.clear()
        self._skill_cbs.clear()

        for widget in self.options_frame.winfo_children():
            widget.destroy()

        if not class_options:
            tk.Label(
                self.options_frame,
                text="No class selected yet.",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
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
                style=CARD_CHECK_STYLE,
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
        elif skill in chosen:
            chosen.remove(skill)

        self._refresh_step(scrub_expertise=True)
        self.notify_change()

    def _enforce_capacity(self):
        chosen = self.character.selected_skills
        at_capacity = len(chosen) >= self._choose_count
        for skill, cb in self._skill_cbs.items():
            var = self._skill_vars[skill]
            if not var.get():
                cb.configure(state="disabled" if at_capacity else "normal")

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

    def _update_expertise_counter(self, sources: dict, *, enabled: bool):
        chosen_count = sources["expertise_chosen_count"]
        total = sources["expertise_choose_count"]
        color = COLORS["fg_dim"]
        if enabled and chosen_count == total:
            color = COLORS["positive"]
        self.expertise_counter_label.configure(
            text=f"({chosen_count} / {total})",
            fg=color,
        )

    def _flash_counter(self):
        self.counter_label.configure(fg=COLORS["accent"])
        self.frame.after(600, self._update_counter)

    def _update_selected_chips(self):
        for widget in self.selected_frame.winfo_children():
            widget.destroy()

        chosen = self.character.selected_skills
        if not chosen:
            tk.Label(
                self.selected_frame,
                text="None chosen yet.",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w")
            return

        for skill in chosen:
            Chip(self.selected_frame, text=skill, style="accent").pack(
                side=tk.LEFT, padx=(0, 4), pady=2
            )

    def _rebuild_expertise_section(
        self,
        auto_expertise: list,
        grants: list[dict],
        *,
        enabled: bool,
    ):
        for widget in self.expertise_frame.winfo_children():
            widget.destroy()

        background = COLORS["bg_surface"]
        if not enabled:
            tk.Label(
                self.expertise_frame,
                text="Choose all class skills first to unlock Expertise.",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=background,
            ).pack(anchor="w", pady=(0, SPACING["sm"]))

        for skill_name, source in auto_expertise:
            block = tk.Frame(self.expertise_frame, bg=background)
            block.pack(fill=tk.X, anchor="w", pady=(0, SPACING["sm"]))

            header = tk.Frame(block, bg=background)
            header.pack(fill=tk.X, anchor="w")
            tk.Label(
                header,
                text=source.upper(),
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg_dim"],
                bg=background,
            ).pack(side=tk.LEFT)
            tk.Label(
                header,
                text="Automatic Expertise",
                font=FONTS["body_small"],
                fg=COLORS["fg_dim"],
                bg=background,
            ).pack(side=tk.LEFT, padx=(SPACING["sm"], 0))

            skill_row = tk.Frame(block, bg=background)
            skill_row.pack(fill=tk.X, anchor="w", pady=(SPACING["xs"], 0))
            Chip(skill_row, text=skill_name, style="gold").pack(
                side=tk.LEFT, padx=(0, 4), pady=2
            )

        for grant in grants:
            block = tk.Frame(self.expertise_frame, bg=background)
            block.pack(fill=tk.X, anchor="w", pady=(0, SPACING["sm"]))

            header = tk.Frame(block, bg=background)
            header.pack(fill=tk.X, anchor="w")
            chosen_count = len(grant["current_selections"])
            tk.Label(
                header,
                text=grant["label"].upper(),
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg_dim"],
                bg=background,
            ).pack(side=tk.LEFT)
            tk.Label(
                header,
                text=f"({chosen_count} / {grant['count']})",
                font=FONTS["label_upper_bold"],
                fg=(
                    COLORS["positive"]
                    if chosen_count == grant["count"]
                    else COLORS["fg_dim"]
                ),
                bg=background,
            ).pack(side=tk.RIGHT)
            if grant.get("temporary"):
                tk.Label(
                    header,
                    text="Temporary until Long Rest",
                    font=FONTS["body_small"],
                    fg=COLORS["fg_dim"],
                    bg=background,
                ).pack(side=tk.LEFT, padx=(SPACING["sm"], 0))

            options: list[str] = []
            seen_options: set[str] = set()
            for slot in grant["slots"]:
                for option in slot["options"]:
                    if option not in seen_options:
                        seen_options.add(option)
                        options.append(option)

            if not options and not grant["current_selections"]:
                tk.Label(
                    block,
                    text="No eligible proficient skills are currently available.",
                    font=FONTS["body"],
                    fg=COLORS["fg_dim"],
                    bg=background,
                ).pack(anchor="w", pady=(SPACING["xs"], 0))
                continue

            tk.Label(
                block,
                text="EXPERTISE SKILLS",
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg_dim"],
                bg=background,
            ).pack(anchor="w", pady=(SPACING["xs"], SPACING["xs"]))

            options_frame = tk.Frame(block, bg=background)
            options_frame.pack(fill=tk.X, anchor="w")

            selected = set(grant["current_selections"])
            at_capacity = len(selected) >= grant["count"]
            for idx, skill_name in enumerate(options):
                var = tk.BooleanVar(value=skill_name in selected)
                cb = ttk.Checkbutton(
                    options_frame,
                    text=skill_name,
                    variable=var,
                    style=CARD_CHECK_STYLE,
                    command=lambda g=grant, s=skill_name, v=var: self._on_expertise_toggle(
                        g, s, v
                    ),
                )
                if not enabled:
                    cb.configure(state="disabled")
                if at_capacity and skill_name not in selected:
                    cb.configure(state="disabled")
                col = idx % 3
                row = idx // 3
                cb.grid(row=row, column=col, sticky="w", padx=SPACING["sm"], pady=1)

    def _apply_expertise_grant_selection(self, grant: dict, selections: list[str]):
        cleaned = [skill for skill in selections if skill][: grant["count"]]

        if grant["kind"] == "class_level":
            idx = grant["class_level_index"]
            if 0 <= idx < len(self.character.class_levels):
                self.character.class_levels[idx].new_expertise = cleaned
        elif grant["kind"] == "feat":
            set_feat_expertise_skill(
                self.character,
                grant["feat_name"],
                cleaned[0] if cleaned else None,
            )

    def _on_expertise_toggle(self, grant: dict, skill_name: str, var: tk.BooleanVar):
        current = list(grant["current_selections"])

        if var.get():
            if skill_name in current:
                return
            if len(current) >= grant["count"]:
                var.set(False)
                return
            current.append(skill_name)
        elif skill_name in current:
            current.remove(skill_name)

        self._apply_expertise_grant_selection(grant, current)
        self._refresh_step(scrub_expertise=True)
        self.notify_change()

    def is_valid(self) -> bool:
        sources = compute_skill_sources(self.character)
        return (
            len(self.character.selected_skills) == sources["choose_count"]
            and sources["expertise_missing_count"] == 0
        )
