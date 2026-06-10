"""Home screen — character roster with a preview pane."""

from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, OptionList, Static
from textual.widgets.option_list import Option

from ..adapter import CharacterView
from ..widgets import HPBar


class HomeScreen(Screen):
    BINDINGS = [
        ("enter", "open_character", "Open"),
        ("q", "app.quit", "Quit"),
    ]

    def __init__(self, characters: list[CharacterView], status: str):
        super().__init__()
        self.characters = characters
        self.status = status

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="home-split"):
            with Vertical(id="roster-pane"):
                yield Label("⚔  CHARACTER ARCHIVE", classes="pane-title")
                yield OptionList(
                    *[Option(self._row(c), id=str(i))
                      for i, c in enumerate(self.characters)],
                    id="roster",
                )
                yield Label(self.status, id="status-line")
            with Vertical(id="preview-pane"):
                yield Label("PREVIEW", classes="pane-title")
                yield Static("", id="preview-body")
                yield HPBar(0, 0, id="preview-hp")
        yield Footer()

    @staticmethod
    def _row(c: CharacterView) -> Text:
        text = Text()
        text.append(f"{c.name:<22}", style="bold #e8dcc0")
        text.append(f"{c.class_line:<20}", style="#d4762c")
        text.append(c.species, style="#a89878")
        return text

    def on_mount(self) -> None:
        roster = self.query_one("#roster", OptionList)
        if self.characters:
            roster.highlighted = 0
        roster.focus()

    def _selected(self) -> CharacterView | None:
        roster = self.query_one("#roster", OptionList)
        if roster.highlighted is None or not self.characters:
            return None
        return self.characters[roster.highlighted]

    def on_option_list_option_highlighted(self, event) -> None:
        c = self._selected()
        if c is None:
            return
        body = Text()
        body.append(f"{c.name}\n", style="bold #d4762c")
        body.append(f"{c.species} · {c.background}\n", style="#a89878")
        body.append(f"{c.class_line}\n\n", style="#e8dcc0")
        body.append(f"AC {c.armor_class}   Speed {c.speed}   "
                    f"Prof +{c.proficiency_bonus}\n", style="#e8dcc0")
        if c.is_caster:
            body.append(f"\n{len(c.spells)} spells known", style="#9d7cd8")
        body.append(f"\n{len(c.inventory)} items · {c.wealth}",
                    style="#d4af37")
        self.query_one("#preview-body", Static).update(body)
        self.query_one("#preview-hp", HPBar).update_hp(c.current_hp, c.max_hp)

    def on_option_list_option_selected(self, event) -> None:
        self.action_open_character()

    def action_open_character(self) -> None:
        c = self._selected()
        if c is not None:
            from .sheet import SheetScreen
            self.app.push_screen(SheetScreen(c))
