from types import SimpleNamespace

import gui.step_spells as step_spells_module
from gui.step_spells import SpellsStep


class _FakeWidget:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = dict(kwargs)
        self.text = ""

    def pack(self, *args, **kwargs):
        return None

    def grid(self, *args, **kwargs):
        return None

    def columnconfigure(self, *args, **kwargs):
        return None

    def rowconfigure(self, *args, **kwargs):
        return None

    def bind(self, *args, **kwargs):
        return None

    def configure(self, **kwargs):
        self.kwargs.update(kwargs)

    def delete(self, *args, **kwargs):
        self.text = ""

    def insert(self, *args):
        if len(args) >= 2:
            self.text += str(args[1])


class _FakeCardFrame:
    def __init__(self, *args, **kwargs):
        self.inner = _FakeWidget()

    def pack(self, *args, **kwargs):
        return None


class _FakeBooleanVar:
    def __init__(self, value=False):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value

    def trace_add(self, *args, **kwargs):
        return None


class _FakeModernSectionedListbox:
    def __init__(self, *args, **kwargs):
        self.on_hover = kwargs.get("on_hover")
        self.on_select = kwargs.get("on_select")
        self.sections = []
        self.selected = []
        self.deselected = []

    def pack(self, *args, **kwargs):
        return None

    def set_sectioned_items(self, sections, selected_names=None, **kwargs):
        self.sections = list(sections)
        if selected_names is not None:
            self.selected = list(selected_names)

    def set_selected_items(self, names):
        self.selected = list(names)

    def deselect_item(self, name):
        self.deselected.append(name)
        self.selected = [item for item in self.selected if item != name]


def test_update_info_label_for_noncaster_sets_granted_text():
    step = SpellsStep.__new__(SpellsStep)
    step.character = SimpleNamespace(is_caster=False, character_class={})
    step.info_label = _FakeWidget()

    step._update_info_label()

    assert step.info_label.kwargs["text"] == "Granted spells and magical traits"


def test_followup_spell_list_builds_and_selects_without_missing_helpers(monkeypatch):
    monkeypatch.setattr(step_spells_module.tk, "Frame", _FakeWidget)
    monkeypatch.setattr(step_spells_module.tk, "Label", _FakeWidget)
    monkeypatch.setattr(step_spells_module.tk, "Text", _FakeWidget)
    monkeypatch.setattr(step_spells_module.tk, "BooleanVar", _FakeBooleanVar)
    monkeypatch.setattr(step_spells_module, "CardFrame", _FakeCardFrame)
    monkeypatch.setattr(step_spells_module, "SectionHeader", _FakeWidget)
    monkeypatch.setattr(
        step_spells_module,
        "ModernSectionedListbox",
        _FakeModernSectionedListbox,
    )
    monkeypatch.setattr(step_spells_module, "get_effective_cantrips_known", lambda _c: 2)
    monkeypatch.setattr(step_spells_module, "get_effective_prepared_spells", lambda _c: 3)

    stored_choices: dict[tuple[str, str], list[str] | None] = {}

    def _get_choice(_character, source_id, key, default=None):
        return stored_choices.get((source_id, key), default)

    def _set_choice(_character, source_id, key, value):
        stored_choices[(source_id, key)] = value

    monkeypatch.setattr(step_spells_module, "get_spell_grant_choice_value", _get_choice)
    monkeypatch.setattr(step_spells_module, "set_spell_grant_choice_value", _set_choice)

    step = SpellsStep.__new__(SpellsStep)
    step.character = SimpleNamespace(
        is_caster=True,
        character_class={"name": "Warlock"},
    )
    step.data = SimpleNamespace(
        _spell_name_index={
            "Eldritch Blast": {
                "name": "Eldritch Blast",
                "level": 0,
                "school": "Evocation",
                "casting_time": "Action",
                "range": "120 feet",
                "duration": "Instantaneous",
                "description": "A beam of crackling energy streaks toward a creature.",
            }
        },
        spells=[],
    )
    step.info_label = _FakeWidget()
    step._followup_cantrip_vars = {}
    step._followup_spell_vars = {}
    step._followup_cantrip_cbs = {}
    step._followup_spell_cbs = {}
    changes: list[str] = []
    step.notify_change = lambda: changes.append("change")

    source = {
        "source_id": "test-source",
        "cantrip_options": ["Eldritch Blast"],
        "spell_options": [],
        "cantrip_choice_count": 1,
        "spell_choice_count": 0,
    }

    step._build_followup_spell_list(_FakeWidget(), source)
    step._followup_list.on_select("Eldritch Blast")

    assert step._followup_list.sections == [("Cantrips", ["Eldritch Blast"])]
    assert stored_choices[("test-source", "cantrips")] == ["Eldritch Blast"]
    assert changes == ["change"]
    assert "Warlock: 2 cantrips, 3 prepared spells" in step.info_label.kwargs["text"]
