from types import SimpleNamespace

import gui.step_class_features as step_class_features_module
from gui.step_class_features import ClassFeaturesStep


class _FakeSelector:
    def __init__(self, selected: list[str]):
        self.selected = list(selected)
        self.deselected: list[str] = []
        self.set_selected_calls: list[list[str]] = []
        self.select_calls: list[str] = []

    def get_selected_items(self) -> list[str]:
        return list(self.selected)

    def deselect_item(self, name: str):
        self.deselected.append(name)
        self.selected = [item for item in self.selected if item != name]

    def set_selected_items(self, names: list[str]):
        self.set_selected_calls.append(list(names))
        self.selected = list(names)

    def select_item(self, name: str):
        self.select_calls.append(name)
        if name and name not in self.selected:
            self.selected.append(name)


def _build_step(selector: _FakeSelector) -> tuple[ClassFeaturesStep, list[str]]:
    step = ClassFeaturesStep.__new__(ClassFeaturesStep)
    step._updating_invocations = False
    step._invocation_selector = selector

    choices: list[str] = []

    def _capture_choice(value: str):
        choices.append(value)

    step._set_warlock_invocation_choice = _capture_choice
    return step, choices


def test_warlock_invocation_toggle_uses_selector_state():
    selector = _FakeSelector(["Armor of Shadows"])
    step, choices = _build_step(selector)

    step._on_invocation_toggle({"name": "Armor of Shadows"})

    assert selector.deselected == []
    assert choices == ["Armor of Shadows"]


def test_warlock_invocation_toggle_replaces_second_selection():
    selector = _FakeSelector(["Armor of Shadows", "Agonizing Blast"])
    step, choices = _build_step(selector)

    step._on_invocation_toggle({"name": "Agonizing Blast"})

    assert selector.deselected == []
    assert choices == ["Agonizing Blast"]


def _build_invocation_choice_step(
    invocation_name: str,
) -> tuple[ClassFeaturesStep, list[str], list[str], list[str]]:
    step = ClassFeaturesStep.__new__(ClassFeaturesStep)
    step.character = SimpleNamespace(
        level1_class_choices={"warlock_invocation": invocation_name},
        character_class={"slug": "warlock"},
    )
    step.data = object()
    step._invocation_count_label = None
    step._invocation_selector = None
    step._invocation_detail_text = None
    step._invocation_vars = {}
    step._updating_invocations = False

    rebuilds: list[str] = []
    syncs: list[str] = []
    changes: list[str] = []

    step._rebuild = lambda: rebuilds.append("rebuild")
    step._sync_invocation_ui = lambda: syncs.append("sync")
    step.notify_change = lambda: changes.append("change")
    return step, rebuilds, syncs, changes


def test_set_warlock_invocation_choice_skips_rebuild_when_followup_unchanged(monkeypatch):
    monkeypatch.setattr(
        step_class_features_module,
        "scrub_level1_class_choices",
        lambda character, data: None,
    )
    step, rebuilds, syncs, changes = _build_invocation_choice_step("Armor of Shadows")

    step._set_warlock_invocation_choice("Devil's Sight")

    assert step.character.level1_class_choices["warlock_invocation"] == "Devil's Sight"
    assert rebuilds == []
    assert syncs == ["sync"]
    assert changes == ["change"]


def test_set_warlock_invocation_choice_rebuilds_when_followup_changes(monkeypatch):
    monkeypatch.setattr(
        step_class_features_module,
        "scrub_level1_class_choices",
        lambda character, data: None,
    )
    step, rebuilds, syncs, changes = _build_invocation_choice_step("Armor of Shadows")

    step._set_warlock_invocation_choice("Pact of the Tome")

    assert step.character.level1_class_choices["warlock_invocation"] == "Pact of the Tome"
    assert rebuilds == ["rebuild"]
    assert syncs == []
    assert changes == ["change"]


def test_set_warlock_binding_choice_updates_state_without_rebuild(monkeypatch):
    monkeypatch.setattr(
        step_class_features_module,
        "scrub_level1_class_choices",
        lambda character, data: None,
    )
    step = ClassFeaturesStep.__new__(ClassFeaturesStep)
    step.character = SimpleNamespace(
        level1_class_choices={"warlock_invocation": "Agonizing Blast"},
    )
    step.data = object()

    style_updates: list[str] = []
    changes: list[str] = []

    step._update_warlock_binding_tile_styles = lambda: style_updates.append("style")
    step.notify_change = lambda: changes.append("change")

    step._set_warlock_binding_choice("Eldritch Blast")

    assert (
        step.character.level1_class_choices["warlock_invocation_cantrip"]
        == "Eldritch Blast"
    )
    assert style_updates == ["style"]
    assert changes == ["change"]


def test_warlock_followups_do_not_create_internal_substeps():
    step = ClassFeaturesStep.__new__(ClassFeaturesStep)
    step.character = SimpleNamespace(
        level1_class_choices={"warlock_invocation": "Agonizing Blast"},
        character_class={"slug": "warlock"},
    )

    assert step.get_substep_count() == 1
    assert step.has_substeps() is False


def test_build_current_content_renders_tome_followup_on_same_step():
    step = ClassFeaturesStep.__new__(ClassFeaturesStep)
    step.character = SimpleNamespace(
        level1_class_choices={"warlock_invocation": "Pact of the Tome"},
        character_class={"slug": "warlock"},
    )
    step._current_substep = 0

    calls: list[str] = []
    step._build_warlock_invocation_selector = lambda: calls.append("selector")
    step._build_warlock_followup_section = lambda: calls.append("followup")

    step._build_current_content()

    assert calls == ["selector", "followup"]
