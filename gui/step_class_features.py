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
)
from models.level1_class_rules import (
    get_available_fighting_styles,
    get_available_order_options,
    get_available_origin_feats,
    get_available_warlock_invocations,
    get_tome_cantrip_options,
    get_tome_ritual_options,
    get_unmet_level1_class_requirements,
    get_weapon_mastery_count,
    get_weapon_mastery_options,
    requires_level1_class_features_step,
    scrub_level1_class_choices,
)


class ClassFeaturesStep(WizardStep):
    tab_title = "Class Features"

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

    def on_enter(self):
        scrub_level1_class_choices(self.character, self.data)
        self._rebuild()

    def _choice_map(self) -> dict:
        choices = getattr(self.character, "level1_class_choices", {})
        return choices if isinstance(choices, dict) else {}

    def _choice_value(self, key: str, default=None):
        return self._choice_map().get(key, default)

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

    def _card(self, title: str, description: str = "") -> CardFrame:
        SectionHeader(self._content, text=title).pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )
        card = CardFrame(self._content, pad=SPACING["lg"])
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
                ).pack(fill=tk.X, anchor="w", padx=(SPACING["lg"], 0), pady=(0, SPACING["xs"]))

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
                lambda _event, i=idx, v=var: self._set_slotted_choice(key, i, count, v.get()),
            )

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

    def _build_warlock_sections(self):
        invocation_options = get_available_warlock_invocations()
        option_names = [option["name"] for option in invocation_options]
        self._build_single_combo(
            "warlock_invocation",
            "Eldritch Invocation",
            option_names,
            "Choose one level-1 invocation. Additional invocation-specific choices appear below when needed.",
        )

        current_invocation = str(self._choice_value("warlock_invocation", "") or "")
        if not current_invocation:
            return

        invocation_lookup = {
            option["name"]: str(option.get("description", "") or "").strip()
            for option in invocation_options
        }
        desc = invocation_lookup.get(current_invocation, "")
        if desc:
            card = self._card(current_invocation)
            WrappingLabel(
                card.inner,
                text=desc,
                background=COLORS["bg_surface"],
                foreground=COLORS["fg_dim"],
            ).pack(fill=tk.X, anchor="w")

        if current_invocation == "Pact of the Tome":
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
        elif current_invocation == "Lessons of the First Ones":
            self._build_single_combo(
                "warlock_lessons_feat",
                "Lessons Of The First Ones Feat",
                [feat["name"] for feat in get_available_origin_feats(self.data)],
                "Choose the Origin feat granted by this invocation.",
            )
        elif current_invocation in {
            "Agonizing Blast",
            "Eldritch Spear",
            "Repelling Blast",
        }:
            card = self._card("Invocation Binding")
            tk.Label(
                card.inner,
                text=(
                    "Finish choosing your Warlock cantrips on the Spells step, then "
                    "bind this invocation to one of your damage-dealing cantrips."
                ),
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
                justify=tk.LEFT,
                wraplength=720,
            ).pack(anchor="w")

    def _rebuild(self):
        self._clear_content()

        if not self.character.character_class:
            self._build_empty_state("Choose a class first.")
            return

        if not requires_level1_class_features_step(self.character, self.data):
            self._build_empty_state(
                "This class has no extra level-1 class feature choices beyond the other wizard steps."
            )
            return

        slug = str(self.character.character_class.get("slug", "") or "")
        class_name = self.character.character_class.get("name", "This class")

        intro = tk.Frame(self._content, bg=COLORS["bg"])
        intro.pack(fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"]))
        tk.Label(
            intro,
            text=f"{class_name} Level 1 Choices",
            font=FONTS["subheading"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
        ).pack(anchor="w")

        blockers = get_unmet_level1_class_requirements(
            self.character,
            self.data,
            step_key="class_features",
        )
        if blockers:
            tk.Label(
                intro,
                text="Selections still required before completion.",
                font=FONTS["body_small"],
                fg=COLORS["accent"],
                bg=COLORS["bg"],
            ).pack(anchor="w", pady=(SPACING["xs"], 0))

        if slug in {"cleric", "druid"}:
            key = "divine_order" if slug == "cleric" else "primal_order"
            title = "Divine Order" if slug == "cleric" else "Primal Order"
            self._build_radio_group(key, title, get_available_order_options(self.character))

        if slug == "fighter":
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

        mastery_count = get_weapon_mastery_count(self.character)
        if mastery_count:
            self._build_combo_slots(
                "weapon_mastery",
                "Weapon Mastery",
                get_weapon_mastery_options(self.character, self.data),
                mastery_count,
                "Weapon",
                "Choose the weapons whose mastery properties you can use at level 1.",
            )

        if slug == "warlock":
            self._build_warlock_sections()

    def is_valid(self) -> bool:
        return not get_unmet_level1_class_requirements(
            self.character,
            self.data,
            step_key="class_features",
        )
