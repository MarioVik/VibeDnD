"""Spell selection and granted-spell follow-up choices."""

import tkinter as tk
from tkinter import ttk

from gui.base_step import WizardStep
from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import (
    CardFrame,
    ConfirmDialog,
    GradientHeader,
    SectionHeader,
    WrappingLabel,
    register_mousewheel_target,
)
from models.level1_class_rules import (
    get_effective_cantrips_known,
    get_effective_prepared_spells,
)
from models.spell_grant_utils import (
    apply_default_spell_grant_abilities,
    character_has_spell_step_content,
    format_spellbook_entry_label,
    get_active_spell_grant_sources,
    get_selectable_class_cantrip_options,
    get_selectable_class_spell_options,
    get_spell_grant_choice_value,
    get_spell_grant_followup_sources,
    get_spell_grant_requirements,
    get_spellbook_entries,
    set_spell_grant_choice_value,
    scrub_spell_grant_choices,
)


class SpellsStep(WizardStep):
    tab_title = "Spells"

    def __init__(self, parent_notebook, character, game_data):
        self._current_substep = 0
        self._split_enabled = False
        self._active_spell_row_name = ""
        self._updating_cantrips = False
        self._updating_spells = False
        self.cantrip_vars = {}
        self.spell_vars = {}
        self.cantrip_checkbuttons = {}
        self.spell_checkbuttons = {}
        self.spell_row_widgets = {}
        self._followup_cantrip_vars: dict[str, dict[str, dict]] = {}
        self._followup_spell_vars: dict[str, dict[str, dict]] = {}
        self._followup_cantrip_cbs: dict[str, dict[str, ttk.Checkbutton]] = {}
        self._followup_spell_cbs: dict[str, dict[str, ttk.Checkbutton]] = {}
        super().__init__(parent_notebook, character, game_data)

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        hero = GradientHeader(self.frame, min_height=60)
        hero.grid(row=0, column=0, sticky="ew")

        hero_row = tk.Frame(hero.inner, bg=COLORS["bg_hero"])
        hero_row.pack(
            fill=tk.X,
            padx=SPACING["card_pad"],
            pady=(SPACING["xl"], SPACING["xl"]),
        )

        tk.Label(
            hero_row,
            text="Spells",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        self.info_label = tk.Label(
            hero_row,
            text="",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        )
        self.info_label.pack(side=tk.RIGHT)

        self.content_frame = tk.Frame(self.frame, bg=COLORS["bg"])
        self.content_frame.grid(row=1, column=0, sticky="nsew")
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1)

    # ── Substep protocol ──────────────────────────────────────

    def has_substeps(self) -> bool:
        return self._split_enabled

    def get_current_substep(self) -> int:
        return self._current_substep

    def get_substep_count(self) -> int:
        return 2 if self._split_enabled else 1

    def go_to_substep(self, index: int):
        max_index = self.get_substep_count() - 1
        new_index = max(0, min(max_index, index))
        if new_index == self._current_substep:
            return
        self._current_substep = new_index
        self._render()
        self.notify_substep_change()

    def is_primary_action_visible(self) -> bool:
        return True

    def is_primary_action_enabled(self) -> bool:
        return self.is_current_substep_valid()

    def is_current_substep_valid(self) -> bool:
        if self._split_enabled and self._current_substep == 0:
            return not self._class_spell_requirements()
        if self._split_enabled and self._current_substep == 1:
            return not self.get_current_substep_requirements()
        return self.is_valid()

    def get_sidebar_title(self) -> str | None:
        if not self._split_enabled:
            return None
        return f"Spells ({self._current_substep + 1}/2)"

    # ── Step lifecycle ────────────────────────────────────────

    def on_enter(self):
        changed = False
        changed = apply_default_spell_grant_abilities(self.character, self.data) or changed
        changed = scrub_spell_grant_choices(self.character, self.data) or changed
        split_changed = self._sync_substep_state()
        self._render()
        if changed:
            self.notify_change()
        if split_changed:
            self.notify_substep_change()

    def _sync_substep_state(self) -> bool:
        old_split = self._split_enabled
        old_substep = self._current_substep
        self._split_enabled = bool(
            getattr(self.character, "is_caster", False)
            and get_spell_grant_followup_sources(self.character, self.data)
        )
        if not self._split_enabled:
            self._current_substep = 0
        else:
            self._current_substep = min(self._current_substep, 1)
        return old_split != self._split_enabled or old_substep != self._current_substep

    # ── Validation helpers ────────────────────────────────────

    def _class_spell_requirements(self) -> list[str]:
        if not getattr(self.character, "is_caster", False):
            return []
        cantrip_target = get_effective_cantrips_known(self.character)
        spell_target = get_effective_prepared_spells(self.character)
        cantrip_count = len(getattr(self.character, "selected_cantrips", []) or [])
        spell_count = len(getattr(self.character, "selected_spells", []) or [])
        messages: list[str] = []
        if cantrip_target > cantrip_count:
            messages.append(
                f"Choose {cantrip_target - cantrip_count} more cantrip(s)."
            )
        if spell_target > spell_count:
            messages.append(
                f"Choose {spell_target - spell_count} more prepared spell(s)."
            )
        return messages

    def get_current_substep_requirements(self) -> list[dict]:
        if self._split_enabled and self._current_substep == 1:
            return get_spell_grant_requirements(self.character, self.data)
        if not self._split_enabled:
            return get_spell_grant_requirements(self.character, self.data)
        return []

    def is_valid(self) -> bool:
        return not self._class_spell_requirements() and not get_spell_grant_requirements(
            self.character,
            self.data,
        )

    # ── Rendering ─────────────────────────────────────────────

    def _clear_content(self):
        for child in self.content_frame.winfo_children():
            child.destroy()
        self._active_spell_row_name = ""
        self.cantrip_vars.clear()
        self.spell_vars.clear()
        self.cantrip_checkbuttons.clear()
        self.spell_checkbuttons.clear()
        self.spell_row_widgets.clear()
        self._followup_cantrip_vars.clear()
        self._followup_spell_vars.clear()
        self._followup_cantrip_cbs.clear()
        self._followup_spell_cbs.clear()

    def _render(self):
        self._clear_content()

        if not character_has_spell_step_content(self.character, self.data):
            self.info_label.configure(text="")
            card = CardFrame(self.content_frame, pad=SPACING["xl"])
            card.grid(
                row=0,
                column=0,
                padx=SPACING["lg"],
                pady=SPACING["xl"],
                sticky="ew",
            )
            tk.Label(
                card.inner,
                text="No spell selections are needed for this character.",
                font=FONTS["body"],
                fg=COLORS["fg_dim"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w")
            return

        cls = self.character.character_class or {}
        if getattr(self.character, "is_caster", False):
            self.info_label.configure(
                text=(
                    f"{cls.get('name', 'Caster')}: "
                    f"{get_effective_cantrips_known(self.character)} cantrips, "
                    f"{get_effective_prepared_spells(self.character)} prepared spells"
                )
            )
        else:
            self.info_label.configure(text="Granted spells and magical traits")

        if self._split_enabled and self._current_substep == 1:
            self._build_followup_only_view()
            return

        outer = tk.Frame(self.content_frame, bg=COLORS["bg"])
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        if not self._split_enabled:
            followup_sources = get_spell_grant_followup_sources(self.character, self.data)
            if followup_sources:
                outer.rowconfigure(0, weight=1)
                self._build_followup_cards(
                    outer,
                    followup_sources,
                    row=0,
                    pady=(SPACING["sm"], SPACING["sm"]),
                )

        if getattr(self.character, "is_caster", False) or get_spellbook_entries(
            self.character, self.data
        ):
            self._build_spell_list_area(outer, row=1)

    def _build_followup_only_view(self):
        sources = get_spell_grant_followup_sources(self.character, self.data)
        wrapper = tk.Frame(self.content_frame, bg=COLORS["bg"])
        wrapper.grid(row=0, column=0, sticky="nsew", padx=SPACING["lg"])
        wrapper.columnconfigure(0, weight=1)
        wrapper.rowconfigure(1, weight=1)

        SectionHeader(wrapper, text="Granted Spell Choices").grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(SPACING["sm"], SPACING["sm"]),
        )

        self._build_followup_cards(
            wrapper,
            sources,
            row=1,
            pady=(0, SPACING["sm"]),
        )

    def _build_followup_cards(self, parent, sources: list[dict], *, row: int, pady):
        cards = tk.Frame(parent, bg=COLORS["bg"])
        cards.grid(row=row, column=0, sticky="nsew", pady=pady)
        cards.columnconfigure(0, weight=1)

        for source in sources:
            card = CardFrame(cards, pad=SPACING["lg"])
            card.pack(fill=tk.BOTH, expand=True, pady=(0, SPACING["sm"]))

            tk.Label(
                card.inner,
                text=source["source_label"],
                font=FONTS["heading_serif_sm"],
                fg=COLORS["fg"],
                bg=COLORS["bg_surface"],
            ).pack(anchor="w")

            self._build_source_followup_controls(card.inner, source)

    def _build_source_followup_controls(self, parent, source: dict):
        source_id = source["source_id"]
        bg = COLORS["bg_surface"]

        if source.get("ability_choice_required"):
            row = tk.Frame(parent, bg=bg)
            row.pack(fill=tk.X, pady=(SPACING["xs"], 0))
            tk.Label(
                row,
                text="Spellcasting Ability",
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg_dim"],
                bg=bg,
            ).pack(anchor="w")

            value = str(source.get("ability_value", "") or "")
            var = tk.StringVar(value=value)
            combo = ttk.Combobox(
                row,
                textvariable=var,
                values=source["ability_options"],
                state="readonly",
            )
            combo.pack(fill=tk.X, pady=(2, 0))
            combo.bind(
                "<<ComboboxSelected>>",
                lambda _event, sid=source_id, v=var: self._on_ability_selected(
                    sid,
                    v.get().strip(),
                ),
            )

        if source["source_list_options"]:
            row = tk.Frame(parent, bg=bg)
            row.pack(fill=tk.X, pady=(SPACING["xs"], 0))
            tk.Label(
                row,
                text="Spell List",
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg_dim"],
                bg=bg,
            ).pack(anchor="w")

            value = str(source.get("source_list_value", "") or "")
            var = tk.StringVar(value=value)
            combo = ttk.Combobox(
                row,
                textvariable=var,
                values=source["source_list_options"],
                state="readonly",
            )
            combo.pack(fill=tk.X, pady=(2, 0))
            combo.bind(
                "<<ComboboxSelected>>",
                lambda _event, sid=source_id, v=var: self._on_source_list_selected(
                    sid, v.get().strip()
                ),
            )

        if source["source_list_options"] and not source.get("source_list_value"):
            WrappingLabel(
                parent,
                text="Choose a spell list first to unlock this source's cantrips and spell options.",
                background=bg,
                foreground=COLORS["fg_dim"],
            ).pack(fill=tk.X, anchor="w", pady=(SPACING["xs"], 0))
            return

        self._build_followup_spell_list(parent, source)

    def _find_spell_by_name(self, spell_name: str) -> dict | None:
        """Look up a spell dict by exact name."""
        if hasattr(self.data, "_spell_name_index"):
            return self.data._spell_name_index.get(spell_name)
        return next(
            (
                s
                for s in getattr(self.data, "spells", [])
                if str(s.get("name", "")).strip() == spell_name
            ),
            None,
        )

    def _build_followup_spell_list(self, parent, source: dict):
        """Build a browsable split-detail spell list for a followup source."""
        source_id = source["source_id"]
        cantrip_options = source.get("cantrip_options") or []
        spell_options = source.get("spell_options") or []
        cantrip_max = source.get("cantrip_choice_count") or 0
        spell_max = source.get("spell_choice_count") or 0

        if not cantrip_options and not spell_options:
            return

        selected_cantrips = list(
            get_spell_grant_choice_value(
                self.character, source_id, "cantrips", []
            )
            or []
        )
        selected_spells = list(
            get_spell_grant_choice_value(
                self.character, source_id, "spells", []
            )
            or []
        )

        # Per-source tracking state
        src_cantrip_vars: dict[str, dict] = {}
        src_spell_vars: dict[str, dict] = {}
        src_cantrip_cbs: dict[str, ttk.Checkbutton] = {}
        src_spell_cbs: dict[str, ttk.Checkbutton] = {}
        self._followup_cantrip_vars[source_id] = src_cantrip_vars
        self._followup_spell_vars[source_id] = src_spell_vars
        self._followup_cantrip_cbs[source_id] = src_cantrip_cbs
        self._followup_spell_cbs[source_id] = src_spell_cbs

        bg = COLORS["bg"]
        row_widgets: dict[str, dict] = {}

        # ── Two-column layout ──────────────────────────────────
        area = tk.Frame(parent, bg=bg)
        area.pack(fill=tk.BOTH, expand=True, pady=(SPACING["sm"], 0))
        area.columnconfigure(0, weight=1)
        area.columnconfigure(1, weight=1)
        area.rowconfigure(0, weight=1)

        # ── Left: scrollable spell list ────────────────────────
        left = tk.Frame(area, bg=bg)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["xs"]))

        cantrip_count_lbl = None
        spell_count_lbl = None
        if cantrip_max:
            cantrip_count_lbl = tk.Label(
                left,
                text=f"{len(selected_cantrips)} / {cantrip_max} cantrips selected",
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg_dim"],
                bg=bg,
            )
            cantrip_count_lbl.pack(anchor="w", padx=4, pady=(0, 1))

        if spell_max:
            spell_count_lbl = tk.Label(
                left,
                text=f"{len(selected_spells)} / {spell_max} spell(s) selected",
                font=FONTS["label_upper_bold"],
                fg=COLORS["fg_dim"],
                bg=bg,
            )
            spell_count_lbl.pack(anchor="w", padx=4, pady=(0, 1))

        list_outer = tk.Frame(left, bg=bg)
        list_outer.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        _canvas, inner = self._make_scrollable_list(list_outer)

        # ── Right: detail panel ────────────────────────────────
        right = tk.Frame(area, bg=bg)
        right.grid(row=0, column=1, sticky="nsew", padx=(SPACING["xs"], 0))

        SectionHeader(right, text="Spell Details").pack(
            fill=tk.X, pady=(0, SPACING["sm"]),
        )

        detail_card = CardFrame(right, pad=SPACING["lg"])
        detail_card.pack(fill=tk.BOTH, expand=True)

        detail_text = tk.Text(
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
        detail_text.pack(fill=tk.BOTH, expand=True)

        # ── Active-row styling (closure-based) ─────────────────
        active_name = [""]

        def _apply_style(widgets: dict, *, active: bool):
            c = COLORS["bg_container"] if active else COLORS["bg"]
            border = COLORS["accent"] if active else COLORS["bg"]
            rail_c = COLORS["accent_text"] if active else COLORS["bg"]
            widgets["row"].configure(bg=c, highlightbackground=border)
            if widgets.get("rail"):
                widgets["rail"].configure(bg=rail_c)

        def _set_active(spell_name: str):
            prev = active_name[0]
            if prev == spell_name:
                return
            if prev and prev in row_widgets:
                _apply_style(row_widgets[prev], active=False)
            active_name[0] = spell_name
            if spell_name and spell_name in row_widgets:
                _apply_style(row_widgets[spell_name], active=True)

        def _show_detail(entry: dict):
            spell = entry.get("spell") or {}
            name = str(entry.get("spell_name", "") or "").strip()
            if not name:
                return
            _set_active(name)
            level = int(spell.get("level", entry.get("level", 0)) or 0)
            level_text = "Cantrip" if level == 0 else f"Level {level}"
            lines = [
                name,
                f"Level: {level_text}",
                f"School: {spell.get('school', 'Unknown')}",
                f"Casting Time: {spell.get('casting_time', 'Unknown')}",
                f"Range: {spell.get('range', 'Unknown')}",
                f"Duration: {spell.get('duration', 'Unknown')}",
            ]
            lines.extend(
                ["", str(spell.get("description", "") or "No description available.")]
            )
            higher = str(spell.get("higher_levels", "") or "").strip()
            if higher:
                lines.extend(["", f"At Higher Levels: {higher}"])
            upgrade = str(spell.get("cantrip_upgrade", "") or "").strip()
            if upgrade:
                lines.extend(["", f"Cantrip Upgrade: {upgrade}"])
            detail_text.configure(state=tk.NORMAL)
            detail_text.delete("1.0", tk.END)
            detail_text.insert("1.0", "\n".join(lines))
            detail_text.configure(state=tk.DISABLED)

        # ── Toggle handlers ────────────────────────────────────
        updating_cantrips = [False]
        updating_spells = [False]

        def _on_cantrip_toggle(spell_name: str):
            if updating_cantrips[0]:
                return
            updating_cantrips[0] = True
            try:
                selected = [
                    n for n, d in src_cantrip_vars.items() if d["var"].get()
                ]
                if len(selected) > cantrip_max:
                    src_cantrip_vars[spell_name]["var"].set(False)
                    selected = [
                        n for n, d in src_cantrip_vars.items() if d["var"].get()
                    ]
                set_spell_grant_choice_value(
                    self.character, source_id, "cantrips", selected
                )
                if cantrip_count_lbl:
                    cantrip_count_lbl.configure(
                        text=f"{len(selected)} / {cantrip_max} cantrips selected"
                    )
                _update_cantrip_states()
                self.notify_change()
            finally:
                updating_cantrips[0] = False

        def _on_spell_toggle(spell_name: str):
            if updating_spells[0]:
                return
            updating_spells[0] = True
            try:
                selected = [
                    n for n, d in src_spell_vars.items() if d["var"].get()
                ]
                if len(selected) > spell_max:
                    src_spell_vars[spell_name]["var"].set(False)
                    selected = [
                        n for n, d in src_spell_vars.items() if d["var"].get()
                    ]
                set_spell_grant_choice_value(
                    self.character, source_id, "spells", selected
                )
                if spell_count_lbl:
                    spell_count_lbl.configure(
                        text=f"{len(selected)} / {spell_max} spell(s) selected"
                    )
                _update_spell_states()
                self.notify_change()
            finally:
                updating_spells[0] = False

        def _update_cantrip_states():
            selected = [
                n for n, d in src_cantrip_vars.items() if d["var"].get()
            ]
            at_max = len(selected) >= cantrip_max if cantrip_max else False
            for name, cb in src_cantrip_cbs.items():
                cb.configure(
                    state=tk.DISABLED
                    if at_max and name not in selected
                    else tk.NORMAL
                )

        def _update_spell_states():
            selected = [
                n for n, d in src_spell_vars.items() if d["var"].get()
            ]
            at_max = len(selected) >= spell_max if spell_max else False
            for name, cb in src_spell_cbs.items():
                cb.configure(
                    state=tk.DISABLED
                    if at_max and name not in selected
                    else tk.NORMAL
                )

        # ── Build rows ─────────────────────────────────────────
        def _build_row(spell_name: str, kind: str, is_selected: bool):
            spell = self._find_spell_by_name(spell_name) or {}
            var = tk.BooleanVar(value=is_selected)
            entry = {
                "spell_name": spell_name,
                "spell": spell,
                "level": int(spell.get("level", 0) or 0),
                "source_labels": [],
                "free_casts": [],
                "ritual_only": False,
                "dragonmark_eligible": False,
                "detail_notes": [],
            }

            row_frame = tk.Frame(
                inner,
                bg=COLORS["bg"],
                highlightthickness=1,
                highlightbackground=COLORS["bg"],
                highlightcolor=COLORS["accent"],
            )
            row_frame.pack(fill=tk.X, padx=(4, 0), pady=1)
            rail = tk.Frame(row_frame, width=6, bg=COLORS["bg"])
            rail.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
            cb = ttk.Checkbutton(row_frame, text=spell_name, variable=var)
            cb.pack(side=tk.LEFT, anchor="w", pady=3)

            row_widgets[spell_name] = {"row": row_frame, "rail": rail}
            row_frame.bind("<Enter>", lambda _e, e=entry: _show_detail(e))
            cb.bind("<Enter>", lambda _e, e=entry: _show_detail(e))

            if kind == "cantrip":
                src_cantrip_vars[spell_name] = {"var": var, "spell": spell}
                src_cantrip_cbs[spell_name] = cb
                var.trace_add(
                    "write", lambda *_a, sn=spell_name: _on_cantrip_toggle(sn)
                )
            else:
                src_spell_vars[spell_name] = {"var": var, "spell": spell}
                src_spell_cbs[spell_name] = cb
                var.trace_add(
                    "write", lambda *_a, sn=spell_name: _on_spell_toggle(sn)
                )

        # ── Populate sections ──────────────────────────────────
        if cantrip_options:
            self._section_header(inner, "Cantrips")
            for name in cantrip_options:
                _build_row(name, "cantrip", name in selected_cantrips)

        if spell_options:
            self._section_header(inner, "Level 1 Spells")
            for name in spell_options:
                _build_row(name, "spell", name in selected_spells)

        # Show first spell's details
        first = (cantrip_options or spell_options or [None])[0]
        if first:
            spell = self._find_spell_by_name(first)
            if spell:
                _show_detail({
                    "spell_name": first,
                    "spell": spell,
                    "level": int(spell.get("level", 0) or 0),
                    "source_labels": [],
                    "free_casts": [],
                    "ritual_only": False,
                    "dragonmark_eligible": False,
                    "detail_notes": [],
                })

        _update_cantrip_states()
        _update_spell_states()

    def _build_spell_list_area(self, parent, *, row: int):
        area = tk.Frame(parent, bg=COLORS["bg"])
        area.grid(
            row=row,
            column=0,
            sticky="nsew",
            padx=SPACING["lg"],
            pady=(0, SPACING["sm"]),
        )
        area.columnconfigure(0, weight=1)
        area.columnconfigure(1, weight=1)
        area.rowconfigure(0, weight=1)

        left = tk.Frame(area, bg=COLORS["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["xs"]))

        if getattr(self.character, "is_caster", False):
            cantrip_target = get_effective_cantrips_known(self.character)
            spell_target = get_effective_prepared_spells(self.character)
            current_cantrips = len(getattr(self.character, "selected_cantrips", []) or [])
            current_spells = len(getattr(self.character, "selected_spells", []) or [])

            if cantrip_target > 0:
                self.cantrip_count_label = tk.Label(
                    left,
                    text=f"{current_cantrips} / {cantrip_target} cantrips selected",
                    font=FONTS["label_upper_bold"],
                    fg=COLORS["fg_dim"],
                    bg=COLORS["bg"],
                )
                self.cantrip_count_label.pack(anchor="w", padx=4, pady=(0, 1))
            else:
                self.cantrip_count_label = None

            if spell_target > 0:
                self.spell_count_label = tk.Label(
                    left,
                    text=f"{current_spells} / {spell_target} spells selected",
                    font=FONTS["label_upper_bold"],
                    fg=COLORS["fg_dim"],
                    bg=COLORS["bg"],
                )
                self.spell_count_label.pack(anchor="w", padx=4, pady=(0, 1))
            else:
                self.spell_count_label = None
        else:
            self.cantrip_count_label = None
            self.spell_count_label = None

        list_outer = tk.Frame(left, bg=COLORS["bg"])
        list_outer.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        _canvas, inner = self._make_scrollable_list(list_outer)

        fixed_entries_by_level: dict[int, list[dict]] = {}
        for entry in get_spellbook_entries(self.character, self.data):
            if not entry["source_labels"] and not entry["dragonmark_eligible"]:
                continue
            fixed_entries_by_level.setdefault(int(entry["level"] or 0), []).append(entry)

        selectable_cantrips = get_selectable_class_cantrip_options(self.character, self.data)
        selectable_spells = get_selectable_class_spell_options(self.character, self.data, level=1)

        levels = sorted(set(fixed_entries_by_level.keys()) | {0 if selectable_cantrips else None, 1 if selectable_spells else None} - {None})
        if not levels:
            levels = sorted(fixed_entries_by_level.keys())

        for level in levels:
            self._section_header(inner, "Cantrips" if level == 0 else f"Level {level}")
            for entry in fixed_entries_by_level.get(level, []):
                self._build_fixed_row(inner, entry)
            if level == 0:
                for spell_name in selectable_cantrips:
                    self._build_selectable_row(inner, spell_name, kind="cantrip")
            if level == 1:
                for spell_name in selectable_spells:
                    self._build_selectable_row(inner, spell_name, kind="spell")

        right = tk.Frame(area, bg=COLORS["bg"])
        right.grid(row=0, column=1, sticky="nsew", padx=(SPACING["xs"], 0))

        SectionHeader(right, text="Spell Details").pack(
            fill=tk.X,
            pady=(0, SPACING["sm"]),
        )

        detail_card = CardFrame(right, pad=SPACING["lg"])
        detail_card.pack(fill=tk.BOTH, expand=True)

        self.spell_detail_text = tk.Text(
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
        self.spell_detail_text.pack(fill=tk.BOTH, expand=True)

        first_entry = next(iter(get_spellbook_entries(self.character, self.data)), None)
        if first_entry:
            self._show_detail(first_entry)
        else:
            self._set_detail_text("No spells are currently available for this character.")

        self._update_cantrip_states()
        self._update_spell_states()

    def _section_header(self, parent, title: str):
        tk.Label(
            parent,
            text=f"\u2500\u2500 {title} \u2500\u2500",
            font=FONTS["body_bold"],
            fg=COLORS["accent_text"],
            bg=COLORS["bg"],
        ).pack(anchor="w", pady=(6, 2))

    def _build_fixed_row(self, parent, entry: dict):
        row = tk.Frame(
            parent,
            bg=COLORS["bg"],
            highlightthickness=1,
            highlightbackground=COLORS["bg"],
            highlightcolor=COLORS["accent"],
        )
        row.pack(fill=tk.X, padx=(4, 0), pady=1)
        rail = tk.Frame(row, width=6, bg=COLORS["bg"])
        rail.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        label = tk.Label(
            row,
            text=format_spellbook_entry_label(entry),
            font=FONTS["body"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
            anchor="w",
            justify=tk.LEFT,
        )
        label.pack(anchor="w", fill=tk.X, pady=4)
        self._register_spell_row(entry["spell_name"], row, label=label, rail=rail)
        row.bind("<Enter>", lambda _event, e=entry: self._show_detail(e))
        label.bind("<Enter>", lambda _event, e=entry: self._show_detail(e))

    def _build_selectable_row(self, parent, spell_name: str, *, kind: str):
        spell = self.data._spell_name_index.get(spell_name) if hasattr(self.data, "_spell_name_index") else None
        if spell is None:
            spell = next(
                (
                    item
                    for item in getattr(self.data, "spells", [])
                    if str(item.get("name", "")).strip() == spell_name
                ),
                {},
            )

        selected = spell_name in (
            getattr(self.character, "selected_cantrips", [])
            if kind == "cantrip"
            else getattr(self.character, "selected_spells", [])
        )
        var = tk.BooleanVar(value=selected)
        if kind == "cantrip":
            var.trace_add("write", lambda *_args, s=spell: self._on_cantrip_toggle(s))
            self.cantrip_vars[spell_name] = {"var": var, "spell": spell}
        else:
            var.trace_add("write", lambda *_args, s=spell: self._on_spell_toggle(s))
            self.spell_vars[spell_name] = {"var": var, "spell": spell}

        row = tk.Frame(
            parent,
            bg=COLORS["bg"],
            highlightthickness=1,
            highlightbackground=COLORS["bg"],
            highlightcolor=COLORS["accent"],
        )
        row.pack(fill=tk.X, padx=(4, 0), pady=1)
        rail = tk.Frame(row, width=6, bg=COLORS["bg"])
        rail.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))

        cb = ttk.Checkbutton(row, text=spell_name, variable=var)
        cb.pack(side=tk.LEFT, anchor="w", pady=3)
        entry = {
            "spell_name": spell_name,
            "spell": spell,
            "level": int(spell.get("level", 0) or 0),
            "source_labels": [],
            "free_casts": [],
            "ritual_only": False,
            "dragonmark_eligible": False,
            "detail_notes": [],
        }
        self._register_spell_row(spell_name, row, rail=rail)
        row.bind("<Enter>", lambda _event, e=entry: self._show_detail(e))
        cb.bind("<Enter>", lambda _event, e=entry: self._show_detail(e))
        if kind == "cantrip":
            self.cantrip_checkbuttons[spell_name] = cb
        else:
            self.spell_checkbuttons[spell_name] = cb

    def _make_scrollable_list(self, parent_frame):
        canvas = tk.Canvas(
            parent_frame,
            bg=COLORS["bg"],
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(
            parent_frame,
            orient=tk.VERTICAL,
            command=canvas.yview,
        )
        inner = tk.Frame(canvas, bg=COLORS["bg"])

        inner.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind(
            "<Configure>",
            lambda event, cw=canvas_window: canvas.itemconfig(cw, width=event.width),
        )

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        register_mousewheel_target(parent_frame, canvas)
        register_mousewheel_target(canvas, canvas)
        register_mousewheel_target(inner, canvas)

        return canvas, inner

    # ── Change handlers ────────────────────────────────────────

    def _refresh_after_spell_choice(self):
        changed = False
        changed = apply_default_spell_grant_abilities(self.character, self.data) or changed
        changed = scrub_spell_grant_choices(self.character, self.data) or changed
        split_changed = self._sync_substep_state()
        self._render()
        self.notify_change()
        if split_changed or changed:
            self.notify_substep_change()

    def _on_source_list_selected(self, source_id: str, value: str):
        set_spell_grant_choice_value(self.character, source_id, "source_list", value)
        set_spell_grant_choice_value(self.character, source_id, "cantrips", None)
        set_spell_grant_choice_value(self.character, source_id, "spells", None)
        self._refresh_after_spell_choice()

    def _on_ability_selected(self, source_id: str, value: str):
        class_ability = str(
            (self.character.character_class or {}).get("spellcasting_ability", "") or ""
        ).strip()
        if class_ability and value and value != class_ability:
            dlg = ConfirmDialog(
                self.frame.winfo_toplevel(),
                "Different Spellcasting Ability",
                (
                    f"Use {value} instead of your class spellcasting ability "
                    f"({class_ability}) for this granted spell source?"
                ),
            )
            if not dlg.result:
                set_spell_grant_choice_value(self.character, source_id, "ability", class_ability)
                self._refresh_after_spell_choice()
                return

        set_spell_grant_choice_value(self.character, source_id, "ability", value)
        self._refresh_after_spell_choice()

    def _on_cantrip_toggle(self, spell: dict):
        if self._updating_cantrips:
            return
        self._updating_cantrips = True
        try:
            cantrip_max = get_effective_cantrips_known(self.character)
            selected = [
                name for name, data in self.cantrip_vars.items() if data["var"].get()
            ]
            if len(selected) > cantrip_max:
                self.cantrip_vars[spell["name"]]["var"].set(False)
                selected = [
                    name
                    for name, data in self.cantrip_vars.items()
                    if data["var"].get()
                ]
            self.character.selected_cantrips = selected
            scrub_spell_grant_choices(self.character, self.data)
            if self.cantrip_count_label is not None:
                self.cantrip_count_label.configure(
                    text=f"{len(selected)} / {cantrip_max} cantrips selected"
                )
            self._update_cantrip_states()
            self.notify_change()
        finally:
            self._updating_cantrips = False

    def _on_spell_toggle(self, spell: dict):
        if self._updating_spells:
            return
        self._updating_spells = True
        try:
            spell_max = get_effective_prepared_spells(self.character)
            selected = [
                name for name, data in self.spell_vars.items() if data["var"].get()
            ]
            if len(selected) > spell_max:
                self.spell_vars[spell["name"]]["var"].set(False)
                selected = [
                    name
                    for name, data in self.spell_vars.items()
                    if data["var"].get()
                ]
            self.character.selected_spells = selected
            scrub_spell_grant_choices(self.character, self.data)
            if self.spell_count_label is not None:
                self.spell_count_label.configure(
                    text=f"{len(selected)} / {spell_max} spells selected"
                )
            self._update_spell_states()
            self.notify_change()
        finally:
            self._updating_spells = False

    def _update_cantrip_states(self):
        cantrip_max = get_effective_cantrips_known(self.character)
        selected = [name for name, data in self.cantrip_vars.items() if data["var"].get()]
        at_max = len(selected) >= cantrip_max if cantrip_max else False
        for name, cb in self.cantrip_checkbuttons.items():
            cb.configure(
                state=tk.DISABLED if at_max and name not in selected else tk.NORMAL
            )

    def _update_spell_states(self):
        spell_max = get_effective_prepared_spells(self.character)
        selected = [name for name, data in self.spell_vars.items() if data["var"].get()]
        at_max = len(selected) >= spell_max if spell_max else False
        for name, cb in self.spell_checkbuttons.items():
            cb.configure(
                state=tk.DISABLED if at_max and name not in selected else tk.NORMAL
            )

    def _register_spell_row(self, spell_name: str, row, *, label=None, rail=None):
        self.spell_row_widgets[spell_name] = {
            "row": row,
            "label": label,
            "rail": rail,
        }

    def _set_spell_row_active(self, spell_name: str):
        if spell_name == self._active_spell_row_name:
            return
        previous = self._active_spell_row_name
        self._active_spell_row_name = spell_name
        if previous:
            self._apply_spell_row_style(previous, active=False)
        if spell_name:
            self._apply_spell_row_style(spell_name, active=True)

    def _apply_spell_row_style(self, spell_name: str, *, active: bool):
        widgets = self.spell_row_widgets.get(spell_name)
        if not widgets:
            return
        bg = COLORS["bg_container"] if active else COLORS["bg"]
        border = COLORS["accent"] if active else COLORS["bg"]
        rail_color = COLORS["accent_text"] if active else COLORS["bg"]
        row = widgets["row"]
        row.configure(bg=bg, highlightbackground=border)
        rail = widgets.get("rail")
        if rail is not None:
            rail.configure(bg=rail_color)
        label = widgets.get("label")
        if label is not None:
            label.configure(bg=bg)

    # ── Detail pane ────────────────────────────────────────────

    def _show_detail(self, entry: dict):
        spell = entry.get("spell") or {}
        name = str(entry.get("spell_name", "") or spell.get("name", "") or "").strip()
        if not name:
            self._set_detail_text("No spell data found for this entry.")
            return
        self._set_spell_row_active(name)

        level = int(spell.get("level", entry.get("level", 0)) or 0)
        level_text = "Cantrip" if level == 0 else f"Level {level}"
        school = str(spell.get("school", "Unknown") or "Unknown")

        lines = [
            name,
            f"Level: {level_text}",
            f"School: {school}",
            f"Casting Time: {spell.get('casting_time', 'Unknown')}",
            f"Range: {spell.get('range', 'Unknown')}",
            f"Duration: {spell.get('duration', 'Unknown')}",
        ]

        source_labels = entry.get("source_labels", []) or []
        if source_labels:
            lines.append(f"Granted By: {', '.join(source_labels)}")
        free_casts = entry.get("free_casts", []) or []
        if free_casts:
            lines.append(f"Free Casting: {', '.join(free_casts)}")
        if entry.get("ritual_only"):
            lines.append("Special: Ritual only")
        if entry.get("dragonmark_eligible"):
            lines.append("Special: Dragonmark spell")
        for note in entry.get("detail_notes", []) or []:
            lines.append(f"Special: {note}")

        lines.extend(["", str(spell.get("description", "") or "No description available.")])

        higher = str(spell.get("higher_levels", "") or "").strip()
        if higher:
            lines.extend(["", f"At Higher Levels: {higher}"])
        upgrade = str(spell.get("cantrip_upgrade", "") or "").strip()
        if upgrade:
            lines.extend(["", f"Cantrip Upgrade: {upgrade}"])

        self._set_detail_text("\n".join(lines))

    def _set_detail_text(self, text: str):
        if not getattr(self, "spell_detail_text", None):
            return
        self.spell_detail_text.configure(state=tk.NORMAL)
        self.spell_detail_text.delete("1.0", tk.END)
        self.spell_detail_text.insert("1.0", text)
        self.spell_detail_text.configure(state=tk.DISABLED)
