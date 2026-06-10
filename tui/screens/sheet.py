"""Character sheet screen — tabbed ledger view."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (DataTable, Footer, Header, Label, Static,
                             TabbedContent, TabPane)

from ..adapter import (SKILL_ABILITY, CharacterView, fmt_mod,
                       restore_slot, set_hp, slot_key_for_level, spend_slot)
from ..widgets import AbilityRow, HPBar, SlotPips


class SheetScreen(Screen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("h", "damage", "-1 HP"),
        ("H", "heal", "+1 HP"),
        ("s", "spend_slot", "Spend slot"),
        ("S", "restore_slot", "Restore slot"),
        ("1", "tab('tab-overview')", "Overview"),
        ("2", "tab('tab-skills')", "Skills"),
        ("3", "tab('tab-spells')", "Spells"),
        ("4", "tab('tab-inventory')", "Inventory"),
        ("5", "tab('tab-features')", "Features"),
    ]

    def __init__(self, view: CharacterView):
        super().__init__()
        self.view = view

    # ------------------------------------------------------------ layout --

    def compose(self) -> ComposeResult:
        c = self.view
        yield Header(show_clock=True)
        with Vertical(id="sheet-banner"):
            yield Label(c.name, id="sheet-name")
            yield Label(f"{c.species} · {c.class_line} · {c.background}",
                        id="sheet-subtitle")
            with Horizontal(id="sheet-vitals"):
                yield HPBar(c.current_hp, c.max_hp, id="sheet-hp")
                yield Static(self._vitals_text(), id="sheet-stats")
        yield AbilityRow(c, id="sheet-abilities")
        with TabbedContent(initial="tab-overview", id="sheet-tabs"):
            with TabPane("Overview", id="tab-overview"):
                yield VerticalScroll(Static(self._overview_text()),
                                     classes="tab-scroll")
            with TabPane("Skills", id="tab-skills"):
                yield self._skills_table()
            with TabPane("Spells", id="tab-spells"):
                with Vertical():
                    yield SlotPips(c.spell_slots, c.spell_slots_used,
                                   id="slot-pips")
                    yield self._spells_table()
                    yield VerticalScroll(Static("", id="spell-detail"),
                                         classes="detail-scroll")
            with TabPane("Inventory", id="tab-inventory"):
                with Vertical():
                    yield self._inventory_table()
                    yield VerticalScroll(Static("", id="item-detail"),
                                         classes="detail-scroll")
            with TabPane("Features", id="tab-features"):
                yield VerticalScroll(Static(self._features_text()),
                                     classes="tab-scroll")
        yield Footer()

    # ----------------------------------------------------------- content --

    def _vitals_text(self) -> Text:
        c = self.view
        text = Text()
        text.append(" AC ", style="bold #1a1410 on #a89878")
        text.append(f" {c.armor_class}   ", style="bold #e8dcc0")
        text.append(" SPD ", style="bold #1a1410 on #a89878")
        text.append(f" {c.speed}   ", style="bold #e8dcc0")
        text.append(" PROF ", style="bold #1a1410 on #a89878")
        text.append(f" +{c.proficiency_bonus}", style="bold #e8dcc0")
        return text

    def _overview_text(self) -> Text:
        c = self.view
        text = Text()
        text.append("Saving Throws\n", style="bold #d4762c")
        for ability in c.abilities:
            prof = ability.title() in c.save_profs
            value = c.save_mod(ability)
            marker = "●" if prof else "○"
            text.append(f"  {marker} {ability.title():<14}"
                        f"{fmt_mod(value)}\n",
                        style="#e8dcc0" if prof else "#a89878")
        text.append(f"\nWealth  ", style="bold #d4762c")
        text.append(f"{c.wealth}\n", style="#d4af37")
        return text

    def _skills_table(self) -> DataTable:
        table = DataTable(id="skills-table", cursor_type="row",
                          zebra_stripes=True)
        table.add_columns("", "Skill", "Ability", "Mod")
        c = self.view
        for skill in sorted(SKILL_ABILITY):
            marker = ("◆" if skill in c.expertise
                      else "●" if skill in c.skill_profs else "○")
            table.add_row(marker, skill,
                          SKILL_ABILITY[skill][:3].upper(),
                          fmt_mod(c.skill_mod(skill)))
        return table

    def _spells_table(self) -> DataTable:
        table = DataTable(id="spells-table", cursor_type="row",
                          zebra_stripes=True)
        table.add_columns("Lvl", "Spell", "School", "Time", "Range", "")
        for s in sorted(self.view.spells, key=lambda s: (s.level, s.name)):
            tags = " ".join(t for t, on in
                            (("C", s.concentration), ("R", s.ritual),
                             ("✓", s.prepared)) if on)
            table.add_row("Cantrip" if s.level == 0 else str(s.level),
                          s.name, s.school, s.casting_time, s.range, tags)
        return table

    def _inventory_table(self) -> DataTable:
        table = DataTable(id="inv-table", cursor_type="row",
                          zebra_stripes=True)
        table.add_columns("Qty", "Item", "Category", "Value")
        for it in self.view.inventory:
            value = "—"
            if it.cost_cp is not None:
                gp = it.cost_cp / 100
                value = f"{gp:g} GP" if gp >= 1 else f"{it.cost_cp} CP"
            table.add_row(str(it.quantity), it.name, it.category, value)
        return table

    def _features_text(self) -> Text:
        text = Text()
        for f in self.view.features:
            text.append(f"{f.name}", style="bold #d4762c")
            if f.source:
                text.append(f"  [{f.source}]", style="#6f6354")
            if f.uses_max is not None:
                left = f.uses_left if f.uses_left is not None else f.uses_max
                text.append(f"  {left}/{f.uses_max} uses", style="#9d7cd8")
            text.append(f"\n{f.description}\n\n", style="#e8dcc0")
        if not self.view.features:
            text.append("No features recorded.", style="dim")
        return text

    # ----------------------------------------------------------- actions --

    def action_tab(self, tab_id: str) -> None:
        self.query_one("#sheet-tabs", TabbedContent).active = tab_id

    def action_damage(self) -> None:
        self._change_hp(-1)

    def action_heal(self) -> None:
        self._change_hp(+1)

    def _change_hp(self, delta: int) -> None:
        if not set_hp(self.view, delta):
            self.notify("HP change could not be saved", severity="error")
        self.query_one("#sheet-hp", HPBar).update_hp(self.view.current_hp)

    # spell slot spend/restore -- prefers the highlighted spell's level ----

    def _highlighted_spell(self):
        spells = sorted(self.view.spells, key=lambda s: (s.level, s.name))
        row = self.query_one("#spells-table", DataTable).cursor_row
        if row is not None and 0 <= row < len(spells):
            return spells[row]
        return None

    def _pick_slot_key(self, spending: bool) -> str | None:
        slots, used = self.view.spell_slots, self.view.spell_slots_used

        def usable(key: str) -> bool:
            spent = used.get(key, 0)
            return spent < slots[key] if spending else spent > 0

        spell = self._highlighted_spell()
        if spell and spell.level > 0:
            key = slot_key_for_level(spell.level)
            if key in slots and usable(key):
                return key
        return next((k for k in sorted(slots) if usable(k)), None)

    def _slot_action(self, spending: bool) -> None:
        if not self.view.spell_slots:
            self.notify("No spell slots", severity="warning")
            return
        self.action_tab("tab-spells")
        key = self._pick_slot_key(spending)
        if key is None:
            self.notify("No slots left to spend" if spending
                        else "No spent slots to restore", severity="warning")
            return
        change = spend_slot if spending else restore_slot
        if not change(self.view, key):
            self.notify("Slot change could not be saved", severity="error")
        self.query_one("#slot-pips", SlotPips).refresh()

    def action_spend_slot(self) -> None:
        self._slot_action(spending=True)

    def action_restore_slot(self) -> None:
        self._slot_action(spending=False)

    # detail panes follow table cursors -----------------------------------

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "spells-table":
            spells = sorted(self.view.spells, key=lambda s: (s.level, s.name))
            if 0 <= event.cursor_row < len(spells):
                s = spells[event.cursor_row]
                detail = Text()
                detail.append(f"{s.name}\n", style="bold #9d7cd8")
                detail.append(s.description or "(no description)",
                              style="#e8dcc0")
                self.query_one("#spell-detail", Static).update(detail)
        elif event.data_table.id == "inv-table":
            items = self.view.inventory
            if 0 <= event.cursor_row < len(items):
                it = items[event.cursor_row]
                detail = Text()
                detail.append(f"{it.name}\n", style="bold #d4af37")
                detail.append(it.description or "(no description)",
                              style="#e8dcc0")
                self.query_one("#item-detail", Static).update(detail)
