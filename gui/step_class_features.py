"""Step 6: Level-1 class feature choices."""

import tkinter as tk
from tkinter import ttk

from gui.base_step import WizardStep
from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import (
    CardFrame,
    GradientHeader,
    ScrollableFrame,
    SectionHeader,
    WrappingLabel,
    register_mousewheel_target,
)
from models.level1_class_rules import (
    get_available_fighting_styles,
    get_available_order_options,
    get_available_origin_feats,
    get_available_warlock_invocations,
    get_selected_weapon_mastery_details,
    get_tome_cantrip_options,
    get_tome_ritual_options,
    get_unmet_level1_class_feature_phase_requirements,
    get_unmet_level1_class_requirements,
    get_warlock_invocation_binding_options,
    get_warlock_invocation_followup_kind,
    get_weapon_mastery_count,
    get_weapon_mastery_options,
    requires_level1_class_features_step,
    scrub_level1_class_choices,
)


class ClassFeaturesStep(WizardStep):
    tab_title = "Class Features"

    def __init__(self, parent_notebook, character, game_data):
        self._binding_var = tk.StringVar(value="")
        self._current_substep = 0
        self._rendered_split_active = False
        self._invocation_vars: dict[str, dict] = {}
        self._invocation_checkbuttons: dict[str, ttk.Checkbutton] = {}
        self._invocation_detail_text: tk.Text | None = None
        self._updating_invocations = False
        super().__init__(parent_notebook, character, game_data)

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        hero = GradientHeader(self.frame, min_height=60)
        hero.grid(row=0, column=0, sticky="ew")

        hero_inner = tk.Frame(hero.inner, bg=COLORS["bg_hero"])
        hero_inner.pack(fill=tk.X, padx=SPACING["card_pad"], pady=(SPACING["xl"], 0))

        tk.Label(
            hero_inner,
            text="Class Features",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        tk.Label(
            hero.inner,
            text=(
                "Resolve every required level-1 class feature choice before "
                "continuing to the rest of character creation."
            ),
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xs"], SPACING["xl"]))

        scroll = ScrollableFrame(self.frame)
        scroll.grid(row=1, column=0, sticky="nsew")
        self._content = scroll.inner

    def has_substeps(self) -> bool:
        return self.get_substep_count() > 1

    def get_current_substep(self) -> int:
        return self._current_substep

    def get_substep_count(self) -> int:
        slug = self._class_slug()
        if slug == "fighter":
            return 2
        if slug == "warlock" and self._warlock_followup_kind() is not None:
            return 2
        return 1

    def go_to_substep(self, index: int):
        max_index = max(0, self.get_substep_count() - 1)
        next_index = max(0, min(index, max_index))
        if next_index == self._current_substep:
            return

        self._current_substep = next_index
        self._rebuild()
        self.notify_substep_change()

    def is_primary_action_visible(self) -> bool:
        return True

    def is_primary_action_enabled(self) -> bool:
        return self.is_current_substep_valid()

    def is_current_substep_valid(self) -> bool:
        return not self.get_current_substep_requirements()

    def get_sidebar_title(self) -> str | None:
        if not self.has_substeps():
            return None
        return f"Class Features ({min(self._current_substep, 1) + 1}/2)"

    def get_current_substep_requirements(self) -> list[dict]:
        if not self.has_substeps():
            return get_unmet_level1_class_requirements(
                self.character,
                self.data,
                step_key="class_features",
            )
        return get_unmet_level1_class_feature_phase_requirements(
            self.character,
            self.data,
            self._current_substep,
        )

    def on_enter(self):
        scrub_level1_class_choices(self.character, self.data)
        self._rebuild()

    def _class_slug(self) -> str:
        return str((self.character.character_class or {}).get("slug", "") or "")

    def _choice_map(self) -> dict:
        choices = getattr(self.character, "level1_class_choices", {})
        return choices if isinstance(choices, dict) else {}

    def _choice_value(self, key: str, default=None):
        return self._choice_map().get(key, default)

    def _warlock_followup_kind(self) -> str | None:
        if self._class_slug() != "warlock":
            return None
        invocation = str(self._choice_value("warlock_invocation", "") or "").strip()
        return get_warlock_invocation_followup_kind(invocation)

    def _set_choice(self, key: str, value):
        if not isinstance(self.character.level1_class_choices, dict):
            self.character.level1_class_choices = {}
        if value in (None, "", [], {}):
            self.character.level1_class_choices.pop(key, None)
        else:
            self.character.level1_class_choices[key] = value
        scrub_level1_class_choices(self.character, self.data)
        self._rebuild()
        self.notify_change()

    def _set_slotted_choice(self, key: str, index: int, total: int, value: str):
        current = list(self._choice_value(key, []))
        while len(current) < total:
            current.append("")
        current[index] = value.strip()
        cleaned = [entry for entry in current if entry.strip()]
        self._set_choice(key, cleaned)

    def _clear_content(self):
        for widget in self._content.winfo_children():
            widget.destroy()

    def _sync_substep_state(self) -> bool:
        split_active = self.get_substep_count() > 1
        substep_changed = False
        if split_active != self._rendered_split_active:
            self._rendered_split_active = split_active
            substep_changed = True
        if not split_active and self._current_substep != 0:
            self._current_substep = 0
            substep_changed = True
        max_index = max(0, self.get_substep_count() - 1)
        if self._current_substep > max_index:
            self._current_substep = max_index
            substep_changed = True
        return substep_changed

    def _card(
        self,
        title: str,
        description: str = "",
        *,
        parent=None,
        header_parent=None,
    ) -> CardFrame:
        content_parent = parent or self._content
        section_parent = header_parent or content_parent
        SectionHeader(section_parent, text=title).pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )
        card = CardFrame(content_parent, pad=SPACING["lg"])
        card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))
        if description:
            WrappingLabel(
                card.inner,
                text=description,
                background=COLORS["bg_surface"],
                foreground=COLORS["fg_dim"],
            ).pack(fill=tk.X, anchor="w", pady=(0, SPACING["sm"]))
        return card

    def _build_empty_state(self, text: str):
        card = self._card("No Class Feature Choices", "")
        tk.Label(
            card.inner,
            text=text,
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w")

    def _make_scrollable_list(self, parent_frame):
        canvas = tk.Canvas(
            parent_frame, bg=COLORS["bg"], highlightthickness=0, borderwidth=0
        )
        scrollbar = ttk.Scrollbar(
            parent_frame, orient=tk.VERTICAL, command=canvas.yview
        )
        inner = tk.Frame(canvas, bg=COLORS["bg"])

        inner.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.bind(
            "<Configure>",
            lambda e, cw=canvas_window: canvas.itemconfig(cw, width=e.width),
        )

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        register_mousewheel_target(parent_frame, canvas)
        register_mousewheel_target(canvas, canvas)
        register_mousewheel_target(inner, canvas)

        return canvas, inner

    def _build_radio_group(self, key: str, title: str, options: list[dict]):
        current = str(self._choice_value(key, "") or "")
        card = self._card(title)
        var = tk.StringVar(value=current)

        for option in options:
            name = str(option.get("name", "")).strip()
            if not name:
                continue
            ttk.Radiobutton(
                card.inner,
                text=name,
                variable=var,
                value=name,
                command=lambda n=name: self._set_choice(key, n),
            ).pack(anchor="w", pady=(0, 2))
            desc = str(option.get("description", "") or "").strip()
            if desc:
                WrappingLabel(
                    card.inner,
                    text=desc,
                    background=COLORS["bg_surface"],
                    foreground=COLORS["fg_dim"],
                ).pack(
                    fill=tk.X,
                    anchor="w",
                    padx=(SPACING["lg"], 0),
                    pady=(0, SPACING["xs"]),
                )

    def _build_combo_slots(
        self,
        key: str,
        title: str,
        options: list[str],
        count: int,
        label_prefix: str,
        description: str = "",
    ):
        current = list(self._choice_value(key, []))
        card = self._card(title, description)

        for idx in range(count):
            row = tk.Frame(card.inner, bg=COLORS["bg_surface"])
            row.pack(fill=tk.X, pady=(0, SPACING["xs"]))
            tk.Label(
                row,
                text=f"{label_prefix} {idx + 1}",
                font=FONTS["body_bold"],
                fg=COLORS["fg"],
                bg=COLORS["bg_surface"],
                width=16,
                anchor="w",
            ).pack(side=tk.LEFT)
            var = tk.StringVar(value=current[idx] if idx < len(current) else "")
            combo = ttk.Combobox(
                row,
                textvariable=var,
                values=options,
                state="readonly",
                width=36,
            )
            combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
            combo.bind(
                "<<ComboboxSelected>>",
                lambda _event, i=idx, v=var: self._set_slotted_choice(
                    key, i, count, v.get()
                ),
            )

    def _build_weapon_mastery_section(self):
        count = get_weapon_mastery_count(self.character)
        if not count:
            return

        current = list(self._choice_value("weapon_mastery", []))
        options = get_weapon_mastery_options(self.character, self.data)
        card = self._card(
            "Weapon Mastery",
            (
                "Choose the weapons whose mastery properties you can use at level 1. "
                "Each mastered weapon gives you its listed mastery effect when you "
                "attack with it."
            ),
        )

        for idx in range(count):
            current_value = current[idx] if idx < len(current) else ""
            blocked = {
                value
                for other_idx, value in enumerate(current)
                if other_idx != idx and value
            }
            slot_options = [
                option
                for option in options
                if option == current_value or option not in blocked
            ]
            row = tk.Frame(card.inner, bg=COLORS["bg_surface"])
            row.pack(fill=tk.X, pady=(0, SPACING["xs"]))
            tk.Label(
                row,
                text=f"Weapon {idx + 1}",
                font=FONTS["body_bold"],
                fg=COLORS["fg"],
                bg=COLORS["bg_surface"],
                width=16,
                anchor="w",
            ).pack(side=tk.LEFT)
            var = tk.StringVar(value=current_value)
            combo = ttk.Combobox(
                row,
                textvariable=var,
                values=slot_options,
                state="readonly",
                width=36,
            )
            combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
            combo.bind(
                "<<ComboboxSelected>>",
                lambda _event, i=idx, v=var: self._set_slotted_choice(
                    "weapon_mastery", i, count, v.get()
                ),
            )

        details = get_selected_weapon_mastery_details(self.character, self.data)
        if not details:
            return

        tk.Frame(card.inner, bg=COLORS["border_subtle"], height=1).pack(
            fill=tk.X,
            pady=(SPACING["sm"], SPACING["sm"]),
        )

        for detail in details:
            mastery = str(detail.get("mastery", "") or "").strip()
            description = str(detail.get("description", "") or "").strip()
            weapon_name = str(detail.get("weapon_name", "") or "").strip()
            if not weapon_name:
                continue

            block = tk.Frame(card.inner, bg=COLORS["bg_surface"])
            block.pack(fill=tk.X, anchor="w", pady=(0, SPACING["sm"]))

            title = weapon_name
            if mastery:
                title = f"{weapon_name} - {mastery}"
            tk.Label(
                block,
                text=title,
                font=FONTS["body_bold"],
                fg=COLORS["gold"],
                bg=COLORS["bg_surface"],
                anchor="w",
                justify=tk.LEFT,
            ).pack(anchor="w")

            if description:
                WrappingLabel(
                    block,
                    text=description,
                    background=COLORS["bg_surface"],
                    foreground=COLORS["fg_dim"],
                ).pack(fill=tk.X, anchor="w", pady=(SPACING["xs"], 0))

    def _build_single_combo(
        self,
        key: str,
        title: str,
        options: list[str],
        description: str = "",
    ):
        card = self._card(title, description)
        row = tk.Frame(card.inner, bg=COLORS["bg_surface"])
        row.pack(fill=tk.X)
        var = tk.StringVar(value=str(self._choice_value(key, "") or ""))
        combo = ttk.Combobox(
            row,
            textvariable=var,
            values=options,
            state="readonly",
            width=42,
        )
        combo.pack(fill=tk.X, expand=True)
        combo.bind(
            "<<ComboboxSelected>>",
            lambda _event, v=var: self._set_choice(key, v.get()),
        )

    def _build_warlock_invocation_selector(self):
        self._invocation_vars.clear()
        self._invocation_checkbuttons.clear()

        invocation_options = get_available_warlock_invocations()
        current_invocation = str(self._choice_value("warlock_invocation", "") or "")

        SectionHeader(self._content, text="Eldritch Invocation").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )

        container = tk.Frame(self._content, bg=COLORS["bg"])
        container.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        top_row = tk.Frame(container, bg=COLORS["bg"])
        top_row.pack(fill=tk.X)
        top_row.columnconfigure(0, weight=1)
        top_row.columnconfigure(1, weight=1)

        left = tk.Frame(top_row, bg=COLORS["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["xs"]))

        selected_count = 1 if current_invocation else 0
        tk.Label(
            left,
            text=f"{selected_count} / 1 invocation selected",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
        ).pack(anchor="w", padx=4, pady=(0, 1))

        list_outer = tk.Frame(left, bg=COLORS["bg"], height=300)
        list_outer.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        list_outer.pack_propagate(False)
        _canvas, inner = self._make_scrollable_list(list_outer)

        selected_option = None
        for option in sorted(invocation_options, key=lambda item: item["name"]):
            name = option["name"]
            if name == current_invocation:
                selected_option = option
            var = tk.BooleanVar(value=(name == current_invocation))
            var.trace_add("write", lambda *_args, o=option: self._on_invocation_toggle(o))
            self._invocation_vars[name] = {"var": var, "invocation": option}
            cb = ttk.Checkbutton(inner, text=name, variable=var)
            cb.pack(anchor="w", pady=1, padx=(8, 0))
            cb.bind("<Enter>", lambda _event, o=option: self._show_invocation_detail(o))
            self._invocation_checkbuttons[name] = cb

        self._update_invocation_states()

        right = tk.Frame(top_row, bg=COLORS["bg"])
        right.grid(row=0, column=1, sticky="nsew", padx=(SPACING["xs"], 0))

        SectionHeader(right, text="Invocation Details").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        detail_card = CardFrame(right, pad=SPACING["lg"])
        detail_card.pack(fill=tk.BOTH, expand=True)

        self._invocation_detail_text = tk.Text(
            detail_card.inner,
            wrap=tk.WORD,
            bg=COLORS["bg_surface"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            state=tk.DISABLED,
        )
        self._invocation_detail_text.pack(fill=tk.BOTH, expand=True)

        if selected_option is not None:
            self._show_invocation_detail(selected_option)

    def _build_warlock_binding_section(self, invocation: str):
        card = self._card(
            "Invocation Binding",
            f"Bind {invocation} to one of your damage-dealing Warlock cantrips.",
        )
        options = get_warlock_invocation_binding_options(self.character, self.data)
        if not options:
            WrappingLabel(
                card.inner,
                text=(
                    "Go back to the Spells step and choose a damage-dealing Warlock "
                    "cantrip first. This invocation cannot be completed without one."
                ),
                background=COLORS["bg_surface"],
                foreground=COLORS["fg_dim"],
            ).pack(fill=tk.X, anchor="w")
            return

        row = tk.Frame(card.inner, bg=COLORS["bg_surface"])
        row.pack(fill=tk.X)
        self._binding_var.set(str(self._choice_value("warlock_invocation_cantrip", "") or ""))
        combo = ttk.Combobox(
            row,
            textvariable=self._binding_var,
            values=options,
            state="readonly",
            width=42,
        )
        combo.pack(fill=tk.X, expand=True)
        combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._set_choice(
                "warlock_invocation_cantrip",
                self._binding_var.get().strip(),
            ),
        )

    def _build_warlock_followup_section(self):
        invocation = str(self._choice_value("warlock_invocation", "") or "").strip()
        followup_kind = self._warlock_followup_kind()
        if followup_kind == "binding":
            self._build_warlock_binding_section(invocation)
        elif followup_kind == "tome":
            self._build_combo_slots(
                "warlock_tome_cantrips",
                "Pact Of The Tome Cantrips",
                get_tome_cantrip_options(self.data),
                3,
                "Cantrip",
                "Choose three cantrips from any class list for your Book of Shadows.",
            )
            self._build_combo_slots(
                "warlock_tome_rituals",
                "Pact Of The Tome Rituals",
                get_tome_ritual_options(self.data),
                2,
                "Ritual",
                "Choose two level-1 ritual spells from any class list.",
            )
        elif followup_kind == "feat":
            self._build_single_combo(
                "warlock_lessons_feat",
                "Lessons Of The First Ones Feat",
                [feat["name"] for feat in get_available_origin_feats(self.data)],
                "Choose the Origin feat granted by this invocation.",
            )

    def _build_fighter_step_one(self):
        self._build_radio_group(
            "fighting_style",
            "Fighting Style",
            [
                {
                    "name": feat["name"],
                    "description": " ".join(
                        str(benefit.get("description", "") or "").strip()
                        for benefit in feat.get("benefits", [])
                        if str(benefit.get("description", "") or "").strip()
                    ),
                }
                for feat in get_available_fighting_styles(self.data)
            ],
        )

    def _on_invocation_toggle(self, invocation: dict):
        if self._updating_invocations:
            return
        self._updating_invocations = True
        try:
            name = invocation["name"]
            selected = [n for n, data in self._invocation_vars.items() if data["var"].get()]

            if len(selected) > 1:
                self._invocation_vars[name]["var"].set(False)
                selected = [
                    n for n, data in self._invocation_vars.items() if data["var"].get()
                ]

            chosen = selected[0] if selected else ""
            self._set_choice("warlock_invocation", chosen)
        finally:
            self._updating_invocations = False

    def _show_invocation_detail(self, invocation: dict):
        if self._invocation_detail_text is None:
            return
        self._invocation_detail_text.configure(state=tk.NORMAL)
        self._invocation_detail_text.delete("1.0", tk.END)

        name = invocation.get("name", "")
        desc = str(invocation.get("description", "") or "").strip()
        lines = [name, ""]
        if desc:
            lines.append(desc)

        self._invocation_detail_text.insert("1.0", "\n".join(lines))
        self._invocation_detail_text.configure(state=tk.DISABLED)

    def _update_invocation_states(self):
        selected = [n for n, data in self._invocation_vars.items() if data["var"].get()]
        at_max = len(selected) >= 1

        for name, cb in self._invocation_checkbuttons.items():
            if at_max and name not in selected:
                cb.configure(state=tk.DISABLED)
            else:
                cb.configure(state=tk.NORMAL)

    def _build_current_content(self):
        slug = self._class_slug()
        if slug in {"cleric", "druid"}:
            key = "divine_order" if slug == "cleric" else "primal_order"
            title = "Divine Order" if slug == "cleric" else "Primal Order"
            self._build_radio_group(key, title, get_available_order_options(self.character))
            return

        if slug == "fighter":
            if self._current_substep == 0:
                self._build_fighter_step_one()
            else:
                self._build_weapon_mastery_section()
            return

        if slug == "warlock":
            if self._current_substep == 0 or not self.has_substeps():
                self._build_warlock_invocation_selector()
            else:
                self._build_warlock_followup_section()
            return

        mastery_count = get_weapon_mastery_count(self.character)
        if mastery_count:
            self._build_weapon_mastery_section()

    def _rebuild(self):
        substep_changed = self._sync_substep_state()
        self._clear_content()

        if not self.character.character_class:
            self._build_empty_state("Choose a class first.")
            if substep_changed:
                self.notify_substep_change()
            return

        if not requires_level1_class_features_step(self.character, self.data):
            self._build_empty_state(
                "This class has no extra level-1 class feature choices beyond the other wizard steps."
            )
            if substep_changed:
                self.notify_substep_change()
            return

        self._build_current_content()
        if substep_changed:
            self.notify_substep_change()

    def is_valid(self) -> bool:
        return not get_unmet_level1_class_requirements(
            self.character,
            self.data,
            step_key="class_features",
        )
