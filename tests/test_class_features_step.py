from gui.step_class_features import ClassFeaturesStep


class _FakeSelector:
    def __init__(self, selected: list[str]):
        self.selected = list(selected)
        self.deselected: list[str] = []

    def get_selected_items(self) -> list[str]:
        return list(self.selected)

    def deselect_item(self, name: str):
        self.deselected.append(name)
        self.selected = [item for item in self.selected if item != name]


def _build_step(selector: _FakeSelector) -> tuple[ClassFeaturesStep, list[tuple[str, str]]]:
    step = ClassFeaturesStep.__new__(ClassFeaturesStep)
    step._updating_invocations = False
    step._invocation_selector = selector

    choices: list[tuple[str, str]] = []

    def _capture_choice(key: str, value: str):
        choices.append((key, value))

    step._set_choice = _capture_choice
    return step, choices


def test_warlock_invocation_toggle_uses_selector_state():
    selector = _FakeSelector(["Armor of Shadows"])
    step, choices = _build_step(selector)

    step._on_invocation_toggle({"name": "Armor of Shadows"})

    assert selector.deselected == []
    assert choices == [("warlock_invocation", "Armor of Shadows")]


def test_warlock_invocation_toggle_rejects_second_selection():
    selector = _FakeSelector(["Armor of Shadows", "Agonizing Blast"])
    step, choices = _build_step(selector)

    step._on_invocation_toggle({"name": "Agonizing Blast"})

    assert selector.deselected == ["Agonizing Blast"]
    assert choices == [("warlock_invocation", "Armor of Shadows")]
