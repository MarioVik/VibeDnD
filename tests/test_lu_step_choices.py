from models.level_up_logic import LevelUpContext
from gui.lu_step_choices import LuChoicesStep


class _FakeSelector:
    def __init__(self, selected: list[str]):
        self.selected = list(selected)
        self.deselected: list[str] = []
        self.set_selected_calls: list[list[str]] = []

    def deselect_item(self, name: str):
        self.deselected.append(name)
        self.selected = [item for item in self.selected if item != name]

    def set_selected_items(self, names: list[str]):
        self.set_selected_calls.append(list(names))
        self.selected = list(names)


def _build_step(
    selected: list[str],
    *,
    sub_selections: dict[str, str] | None = None,
    options: dict[str, dict] | None = None,
):
    step = LuChoicesStep.__new__(LuChoicesStep)
    step._updating_choices = False
    step._choice_list = _FakeSelector(selected)
    step.ctx = LevelUpContext(class_slug="warlock", new_class_level=2)
    step.ctx.selected_new_choices = list(selected)
    step.ctx.choice_sub_selections = dict(sub_selections or {})
    step._choice_options_by_name = options or {}

    count_updates: list[int] = []
    shown_sub_choices: list[tuple[str, dict]] = []
    hidden_sub_choices: list[str] = []
    changes: list[str] = []

    step._update_count = lambda max_count: count_updates.append(max_count)
    step._show_sub_choice_ui = lambda name, sub_choice: shown_sub_choices.append(
        (name, sub_choice)
    )
    step._hide_sub_choice_ui = lambda: hidden_sub_choices.append("hide")
    step.notify_change = lambda: changes.append("change")

    return step, count_updates, shown_sub_choices, hidden_sub_choices, changes


def test_choice_toggle_replaces_max_one_selection_and_clears_stale_subchoice():
    step, count_updates, shown_sub_choices, hidden_sub_choices, changes = _build_step(
        ["Armor of Shadows"],
        sub_selections={"Armor of Shadows": "Longsword"},
        options={
            "Armor of Shadows": {"name": "Armor of Shadows", "sub_choice": {"type": "weapon"}},
            "Agonizing Blast": {"name": "Agonizing Blast"},
        },
    )

    step._on_choice_toggle_manual("Agonizing Blast", 1)

    assert step.ctx.selected_new_choices == ["Agonizing Blast"]
    assert step.ctx.choice_sub_selections == {}
    assert step._choice_list.deselected == []
    assert step._choice_list.set_selected_calls == [["Agonizing Blast"]]
    assert count_updates == [1]
    assert shown_sub_choices == []
    assert hidden_sub_choices == ["hide"]
    assert changes == ["change"]


def test_choice_toggle_clears_selected_item_and_subchoice_at_max_one():
    step, count_updates, shown_sub_choices, hidden_sub_choices, changes = _build_step(
        ["Armor of Shadows"],
        sub_selections={"Armor of Shadows": "Longsword"},
        options={
            "Armor of Shadows": {"name": "Armor of Shadows", "sub_choice": {"type": "weapon"}},
        },
    )

    step._on_choice_toggle_manual("Armor of Shadows", 1)

    assert step.ctx.selected_new_choices == []
    assert step.ctx.choice_sub_selections == {}
    assert step._choice_list.deselected == []
    assert step._choice_list.set_selected_calls == [[]]
    assert count_updates == [1]
    assert shown_sub_choices == []
    assert hidden_sub_choices == ["hide"]
    assert changes == ["change"]
