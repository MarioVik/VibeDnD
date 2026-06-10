"""VibeDnD TUI — main application."""

from __future__ import annotations

from textual.app import App

from .loader import load_characters
from .screens.home import HomeScreen
from .widgets import DiceRoller


class VibeDnDTUI(App):
    TITLE = "VibeDnD"
    SUB_TITLE = "arcane ledger"
    CSS_PATH = "vibednd.tcss"

    BINDINGS = [
        ("r", "roll_dice", "Roll dice"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, demo: bool = False):
        super().__init__()
        self.demo = demo

    def on_mount(self) -> None:
        characters, status = load_characters(demo=self.demo)
        self.push_screen(HomeScreen(characters, status))

    def action_roll_dice(self) -> None:
        # Don't stack dice modals.
        if not isinstance(self.screen, DiceRoller):
            self.push_screen(DiceRoller())


def run(demo: bool = False) -> None:
    VibeDnDTUI(demo=demo).run()
