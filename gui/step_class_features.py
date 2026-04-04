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
    get_selected_weapon_mastery_details,
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

    def __init__(self, parent_notebook, character, game_data):
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

    def _build_warlock_sections(self):
        self._invocation_vars.clear()
        self._invocation_checkbuttons.clear()

        invocation_options = get_available_warlock_invocations()
        current_invocation = str(self._choice_value("warlock_invocation", "") or "")

        # ── Section header ────────────────────────────────────────
        SectionHeader(self._content, text="Eldritch Invocation").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )

        container = tk.Frame(self._content, bg=COLORS["bg"])
        container.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        # ── Two-column layout ─────────────────────────────────────
        top_row = tk.Frame(container, bg=COLORS["bg"])
        top_row.pack(fill=tk.X)
        top_row.columnconfigure(0, weight=1)
        top_row.columnconfigure(1, weight=1)

        # --- LEFT: invocation list ---
        left = tk.Frame(top_row, bg=COLORS["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["xs"]))

        selected_count = 1 if current_invocation else 0
        self._invocation_count_label = tk.Label(
            left,
            text=f"{selected_count} / 1 invocation selected",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
        )
        self._invocation_count_label.pack(anchor="w", padx=4, pady=(0, 1))

        list_outer = tk.Frame(left, bg=COLORS["bg"], height=300)
        list_outer.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        list_outer.pack_propagate(False)
        canvas, inner = self._make_scrollable_list(list_outer)

        for option in sorted(invocation_options, key=lambda o: o["name"]):
            name = option["name"]
            var = tk.BooleanVar(value=(name == current_invocation))
            var.trace_add("write", lambda *a, o=option: self._on_invocation_toggle(o))
            self._invocation_vars[name] = {"var": var, "invocation": option}
            cb = ttk.Checkbutton(inner, text=name, variable=var)
            cb.pack(anchor="w", pady=1, padx=(8, 0))
            cb.bind("<Enter>", lambda e, o=option: self._show_invocation_detail(o))
            self._invocation_checkbuttons[name] = cb

        self._update_invocation_states()

        # --- RIGHT: detail panel ---
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

        # ── Sub-selections (below two-column area) ────────────────
        if not current_invocation:
            return

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

    def _on_invocation_toggle(self, invocation: dict):
        if self._updating_invocations:
            return
        self._updating_invocations = True
        try:
            name = invocation["name"]
            selected = [n for n, d in self._invocation_vars.items() if d["var"].get()]

            if len(selected) > 1:
                self._invocation_vars[name]["var"].set(False)
                selected = [n for n, d in self._invocation_vars.items() if d["var"].get()]

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
        selected = [n for n, d in self._invocation_vars.items() if d["var"].get()]
        at_max = len(selected) >= 1

        for name, cb in self._invocation_checkbuttons.items():
            if at_max and name not in selected:
                cb.configure(state=tk.DISABLED)
            else:
                cb.configure(state=tk.NORMAL)

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
            self._build_weapon_mastery_section()

        if slug == "warlock":
            self._build_warlock_sections()

    def is_valid(self) -> bool:
        return not get_unmet_level1_class_requirements(
            self.character,
            self.data,
            step_key="class_features",
        )
