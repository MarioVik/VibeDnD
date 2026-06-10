"""Adapter snapshot + write-back tests against a fixture Druid save."""

from tui import adapter


# ------------------------------------------------------------- snapshot ---

def test_identity_fields(view):
    assert view.name == "Test"
    assert view.species == "Orc"
    assert view.background == "Sage"
    assert view.class_line == "Druid 1"
    assert view.level == 1


def test_vitals(view):
    assert view.max_hp == 10
    assert 0 <= view.current_hp <= view.max_hp
    assert isinstance(view.armor_class, int)
    assert view.speed == "30 ft."
    assert view.proficiency_bonus == 2


def test_abilities_and_skills(view):
    assert set(view.abilities) == set(adapter.ABILITIES)
    assert all(isinstance(v, int) for v in view.abilities.values())
    assert set(view.skill_mods) == set(adapter.SKILL_ABILITY)
    # Proficient skill must beat its bare ability modifier.
    skill = next(iter(view.skill_profs & set(adapter.SKILL_ABILITY)))
    bare = adapter.mod(view.abilities[adapter.SKILL_ABILITY[skill]])
    assert view.skill_mod(skill) >= bare + view.proficiency_bonus


def test_saves(view):
    assert view.save_profs == {"Intelligence", "Wisdom"}
    for ability in adapter.ABILITIES:
        assert view.save_mod(ability) is not None


def test_spells_and_slots(view):
    assert view.is_caster
    names = {s.name for s in view.spells}
    assert "Goodberry" in names          # class-selected
    goodberry = next(s for s in view.spells if s.name == "Goodberry")
    assert goodberry.level == 1
    assert goodberry.school and goodberry.description
    assert goodberry.prepared
    assert view.spell_slots == {"1st": 2}
    assert view.spell_slots_used == {"1st": 0}


def test_inventory_and_wealth(view):
    assert view.inventory, "druid should have starting equipment"
    leather = next(it for it in view.inventory if it.name == "Leather Armor")
    assert leather.category == "Armor"
    assert leather.cost_cp == 1000
    assert leather.description
    assert view.wealth != "—"


def test_features(view):
    by_name = {f.name: f for f in view.features}
    assert "Druidic" in by_name
    assert by_name["Druidic"].source == "Level 1"
    assert by_name["Druidic"].description
    assert any(f.source == "Species" for f in view.features)


def test_skill_and_save_fallback_math_without_model():
    """Demo characters (no skill_mods/save_mods) still compute mods."""
    v = adapter.CharacterView(
        abilities={"dexterity": 16}, proficiency_bonus=2,
        skill_profs={"Stealth"}, expertise={"Acrobatics"},
        save_profs={"Dexterity"},
    )
    assert v.skill_mod("Stealth") == 5        # 3 + prof
    assert v.skill_mod("Acrobatics") == 7     # 3 + 2*prof
    assert v.save_mod("dexterity") == 5
    assert v.skill_mod("Arcana") is None      # unknown ability score


def test_slot_key_for_level():
    assert [adapter.slot_key_for_level(n) for n in (1, 2, 3, 4, 9)] == \
        ["1st", "2nd", "3rd", "4th", "9th"]


# ----------------------------------------------------------- write-backs --

def _reload(view, game_data):
    from models.character_store import load_character
    return load_character(view.source_path, game_data)


def test_hp_writes_through_and_persists(view, game_data):
    assert adapter.set_hp(view, -3)
    assert view.current_hp == 7
    assert _reload(view, game_data).current_hit_points == 7
    assert adapter.set_hp(view, +99)          # clamped to max
    assert view.current_hp == view.max_hp
    assert adapter.set_hp(view, -99)          # clamped to zero
    assert view.current_hp == 0


def test_slot_spend_restore_persists(view, game_data):
    assert adapter.spend_slot(view, "1st")
    assert view.spell_slots_used["1st"] == 1
    assert _reload(view, game_data).used_spell_slots == {"1st": 1}

    assert adapter.spend_slot(view, "1st")
    assert not adapter.spend_slot(view, "1st")     # only 2 slots
    assert view.spell_slots_used["1st"] == 2

    assert adapter.restore_slot(view, "1st")
    assert _reload(view, game_data).used_spell_slots == {"1st": 1}
    assert adapter.restore_slot(view, "1st")
    assert not adapter.restore_slot(view, "1st")   # nothing spent
    assert not adapter.spend_slot(view, "9th")     # unknown key
    assert not adapter.restore_slot(view, adapter.PACT_KEY)


def test_roundtrip_save_stays_gui_compatible(view, game_data):
    """A TUI save must reload through the GUI's own loader unchanged."""
    adapter.set_hp(view, -1)
    c = _reload(view, game_data)
    assert c.name == "Test"
    assert c.hit_points == 10
    assert c.current_hit_points == 9
    assert c.character_class and c.character_class["name"] == "Druid"
    assert len(c.class_levels) == 1


def test_demo_character_needs_no_model():
    from tui.loader import demo_character
    v = demo_character()
    assert v.raw is None and v.source_path is None
    assert adapter.set_hp(v, -1)              # in-memory only, still "ok"
    assert adapter.spend_slot(v, "1st")
    assert v.spell_slots_used["1st"] == 2
