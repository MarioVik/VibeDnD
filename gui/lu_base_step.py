"""Base class for level-up wizard steps."""

from gui.base_step import WizardStep
from models.level_up_logic import LevelUpContext


class LevelUpStep(WizardStep):
    """WizardStep subclass that adds access to the shared LevelUpContext."""

    tab_title = "Level Up Step"

    def __init__(self, parent, character, game_data, *, level_up_ctx: LevelUpContext):
        self.ctx = level_up_ctx
        super().__init__(parent, character, game_data)
