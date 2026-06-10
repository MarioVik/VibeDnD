"""Custom widgets for the VibeDnD TUI."""

from __future__ import annotations

import random

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from .adapter import ABILITIES, CharacterView, fmt_mod, mod

BAR_FULL = "█"
BAR_EMPTY = "░"
PIP_FULL = "◆"
PIP_EMPTY = "◇"


class HPBar(Static):
    """Manually rendered HP bar with color thresholds."""

    def __init__(self, current: int, maximum: int, width: int = 24, **kw):
        super().__init__(**kw)
        self.current, self.maximum, self.bar_width = current, maximum, width

    def update_hp(self, current: int, maximum: int | None = None) -> None:
        self.current = current
        if maximum is not None:
            self.maximum = maximum
        self.refresh()

    def render(self) -> Text:
        frac = 0.0 if not self.maximum else max(0.0, min(1.0, self.current / self.maximum))
        filled = round(frac * self.bar_width)
        color = "#5fa05f" if frac > 0.5 else "#d4a02c" if frac > 0.25 else "#c0392b"
        text = Text()
        text.append("HP ", style="bold #e8dcc0")
        text.append(BAR_FULL * filled, style=color)
        text.append(BAR_EMPTY * (self.bar_width - filled), style="#3a2f24")
        text.append(f" {self.current}/{self.maximum}", style="bold " + color)
        return text


class SlotPips(Static):
    """Spell slots as diamond pips, e.g.  1st ◆◆◇"""

    def __init__(self, slots: dict[str, int], used: dict[str, int], **kw):
        super().__init__(**kw)
        self.slots, self.used = slots, used

    def render(self) -> Text:
        text = Text()
        if not self.slots:
            return text.append("no spell slots", style="dim") or text
        for i, (lvl, total) in enumerate(sorted(self.slots.items())):
            spent = int(self.used.get(lvl, 0) or 0)
            left = max(0, int(total) - spent)
            if i:
                text.append("   ")
            text.append(f"{lvl} ", style="#9d7cd8")
            text.append(PIP_FULL * left, style="bold #9d7cd8")
            text.append(PIP_EMPTY * spent, style="#3a2f24")
        return text


class AbilityRow(Static):
    """The six ability scores as compact blocks."""

    def __init__(self, view: CharacterView, **kw):
        super().__init__(**kw)
        self.view = view

    def render(self) -> Text:
        text = Text()
        for i, ability in enumerate(ABILITIES):
            score = self.view.abilities.get(ability)
            if i:
                text.append("  ")
            text.append(f" {ability[:3].upper()} ", style="bold #1a1410 on #d4762c")
            text.append(f" {score if score is not None else '—':>2} ",
                        style="bold #e8dcc0")
            text.append(f"({fmt_mod(mod(score))})", style="#a89878")
        return text


# ------------------------------------------------------------ dice roller --

DICE = (4, 6, 8, 10, 12, 20, 100)


class DiceRoller(ModalScreen[None]):
    """Animated dice overlay — the app's signature flourish.

    Open with `r` anywhere. Numbers spin briefly, then settle.
    """

    BINDINGS = [("escape", "dismiss", "Close"), ("r", "reroll", "Reroll")]

    def __init__(self, sides: int = 20, count: int = 1, modifier: int = 0):
        super().__init__()
        self.sides, self.count, self.modifier = sides, count, modifier
        self._ticks = 0
        self._timer = None

    def compose(self) -> ComposeResult:
        with Vertical(id="dice-box"):
            yield Label(self._title(), id="dice-title")
            yield Static("", id="dice-face")
            with Horizontal(id="dice-buttons"):
                for d in DICE:
                    yield Button(f"d{d}", id=f"die-{d}", classes="die-btn")
            yield Label("r reroll · 1-9 count · esc close", id="dice-hint")

    def _title(self) -> str:
        m = f" {fmt_mod(self.modifier)}" if self.modifier else ""
        return f"Rolling {self.count}d{self.sides}{m}"

    def on_mount(self) -> None:
        self._spin()

    def _spin(self) -> None:
        if self._timer:
            self._timer.stop()
        self._ticks = 0
        self.query_one("#dice-title", Label).update(self._title())
        self._timer = self.set_interval(0.05, self._tick)

    def _tick(self) -> None:
        self._ticks += 1
        face = self.query_one("#dice-face", Static)
        rolls = [random.randint(1, self.sides) for _ in range(self.count)]
        total = sum(rolls) + self.modifier
        settled = self._ticks >= 14
        text = Text(justify="center")
        text.append(f"{total}", style=("bold #d4762c" if settled
                                       else "#a89878"))
        if self.count > 1 or self.modifier:
            detail = " + ".join(str(r) for r in rolls)
            if self.modifier:
                detail += f" {fmt_mod(self.modifier)}"
            text.append(f"\n{detail}", style="#6f6354")
        if settled:
            if self.sides == 20 and self.count == 1:
                if rolls[0] == 20:
                    text.append("\nNAT 20!", style="bold #5fa05f")
                elif rolls[0] == 1:
                    text.append("\ncritical failure", style="bold #c0392b")
            self._timer.stop()
        face.update(text)

    def action_reroll(self) -> None:
        self._spin()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("die-"):
            self.sides = int(event.button.id.removeprefix("die-"))
            self._spin()

    def on_key(self, event) -> None:
        if event.character and event.character.isdigit():
            n = int(event.character)
            if 1 <= n <= 9:
                self.count = n
                self._spin()
