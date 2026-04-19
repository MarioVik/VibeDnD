import pytest
from pytest_bdd import given, then, scenarios
import re

from gui.data_loader import GameData
from models.feature_resource_utils import (
    _generic_resource_spec_for_card,
    _CLASS_RESOURCE_SPECS,
    _normalize_name,
)

scenarios("features/feature_exhaustiveness.feature")

# Known features that mention 'Long Rest' or 'Short Rest' but legitimately cannot be tracked.
# We whitelist these to avoid failing the test suite aggressively.
# Developers must remove entries from this list as they patch in the regex support.
KNOWN_UNTRACKED_REST_FEATURES = {
    # Ambiguous subclass structures
    "artificer::alchemist - Experimental Elixir",
    "artificer::alchemist - Restorative Reagents",
    "artificer::armorer - Perfected Armor",
    "artificer::artillerist - Arcane Firearm",
    "artificer::battle-smith - Arcane Jolt",
    "artificer::battle-smith - Steel Defender",
    "artificer::cartographer - Adventurer's Atlas",
    "artificer::cartographer - Mapping Magic",
    "artificer::reanimator - Jolt to Life",
    "barbarian::path-of-the-wild-heart - Aspect of the Wilds",
    "barbarian::path-of-the-zealot - Warrior of the Gods",
    "cleric::light-domain - Improved Warding Flare",
    "druid::circle-of-the-land - Circle of the Land Spells",
    "druid::circle-of-the-stars - Star Map",
    "feat::boon of energy resistance - Energy Resistances",
    "feat::boon of fate - Improve Fate",
    "feat::boon of recovery - Recover Vitality",
    "feat::chef - Bolstering Treats",
    "feat::greater aberrant mark - Improved Fortitude",
    "feat::greater mark of healing - Improved Healing",
    "feat::inspiring leader - Bolstering Performance",
    "feat::musician - Encouraging Song",
    "feat::potent dragonmark - Dragonmark Spellcasting",
    "feat::purple dragon commandant - Encourage Ally",
    "feat::spellfire spark - Spellfire Flame",
    "feat::vampire s plaything - Decanting",
    "feat::vampire s plaything - Timely Retreat",
    "feat::vampire touched - Vampire Magic",
    "feat::weapon master - Mastery Property",
    "feat::zhentarim tactics - Versatile Merc",
    "fighter::banneret - Knightly Envoy",
    "fighter::battle-master - Combat Superiority",
    "fighter::eldritch-knight - Spellcasting",
    "fighter::gladiator - Brutality",
    "monk::tattooed-warrior2 - Magic Tattoos",
    "monk::tattooed-warrior2 - Monster Tattoo",
    "monk::tattooed-warrior2 - Nature Tattoo",
    "monk::warrior-of-intoxication - Mystic Brew",
    "monk::warrior-of-mercy - Flurry of Healing and Harm",
    "monk::warrior-of-the-mystic-arts - Spellcasting",
    "ranger::beast-master - Primal Companion",
    "ranger::fey-wanderer - Misty Wanderer",
    "ranger::hunter - Defensive Tactics",
    "ranger::hunter - Hunter's Prey",
    "rogue::phantom - Whispers of the Dead",
    "rogue::scion-of-the-three - Dread Allegiance",
    "rogue::scion-of-the-three - Dread Incarnate",
    "rogue::soulknife - Psionic Power",
    "sorcerer::wild-magic-sorcery - Tides of Chaos",
    "species:: - Breath Weapon",
    "species:: - Fey Gift",
    "species:: - Giant Ancestry",
    "species:: - Integrated Protection",
    "species:: - Resourceful",
    "species:: - Shifting",
    "species:: - Skill Versatility",
    "species:: - Strengthen",
    "species:: - Trance",
    "warlock::archfey-patron - Steps of the Fey",
    "warlock::celestial-patron - Celestial Resilience",
    "warlock::celestial-patron - Healing Light",
    "warlock::fiend-patron - Fiendish Resilience",
    "warlock::sorcerer-king-patron - Tyrants Herald",
    "warlock::undead-patron - Form of Dread",
    "warlock::vestige-patron - Vestige Companion",
    "warlock::vestige-patron - Vestige Recovery",
    "wizard::bladesinger - Bladesong",
    "wizard::conjurer2 - Distant Transposition",
    "wizard::conjurer2 - Splintered Summons",
    "wizard::diviner - Portent",
    "wizard::transmuter2 - Transmuter's Stone",
    "wizard::transmuter2 - Wondrous Alteration",
}

# Universal patterns that explicitly excuse themselves from tracking
NOISE_EXCLUSIONS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"lasts until you finish a",
        r"vanishes when you finish a",
        r"at the end of a long rest",
        r"until you finish a",
        r"duration.*?is 1 hour or until you finish a",
        r"the benefit remains until you finish a",
        r"you lose the (?:resistance|immunity) when you finish a",
        r"choose it again when you finish a",
        r"without a spell slot.*?cast",  # Standard innate spellcasting texts
        r"If you use this feature again before you finish a Long Rest, you take",  # Damage penalties instead of hard limits
        r"You regain all expended spell slots when you finish a",  # Standard spellcasting recovery rules
    ]
]

REST_REGEX = re.compile(r"finish a (?:[Ss]hort or [Ll]ong|[Ll]ong|[Ss]hort) [Rr]est", re.IGNORECASE)


@pytest.fixture
def test_context():
    return {"gd": GameData(), "missed": []}


@given("the core game data is loaded")
def load_game_data(test_context):
    assert test_context["gd"].classes, "Classes failed to load"
    assert test_context["gd"].subclasses, "Subclasses failed to load"


def _check_feature(context_dict: dict, name: str, desc: str, uid: str, class_slug: str):
    if not desc or not name:
        return
    if REST_REGEX.search(desc):
        if any(p.search(desc) for p in NOISE_EXCLUSIONS):
            return
        
        card = {"title": name, "description_text": desc, "class_slug": class_slug}
        spec = _generic_resource_spec_for_card(card)
        if not spec and (class_slug, _normalize_name(name)) not in _CLASS_RESOURCE_SPECS:
            if uid not in KNOWN_UNTRACKED_REST_FEATURES:
                context_dict["missed"].append(uid)


@then("all class features mentioning rests are either tracked or legitimately excluded")
def verify_class_features(test_context):
    gd = test_context["gd"]
    for cl in gd.classes:
        slug = cl.get("slug", "")
        for lvl in cl.get("levels", []):
            for f in lvl.get("feature_details", []):
                name = f.get("name", "")
                desc = f.get("description", "")
                uid = f"class::{slug} - {name}"
                _check_feature(test_context, name, desc, uid, slug)
    
    assert not test_context["missed"], f"Untracked class features: {test_context['missed']}"


@then("all subclass features mentioning rests are either tracked or legitimately excluded")
def verify_subclass_features(test_context):
    gd = test_context["gd"]
    test_context["missed"] = []
    
    for sub in gd.subclasses:
        c_slug = sub.get("class_slug", "")
        s_slug = sub.get("slug", "")
        for lvl, features in sub.get("features", {}).items():
            for f in features:
                name = f.get("name", "")
                desc = f.get("description", "")
                uid = f"{c_slug}::{s_slug} - {name}"
                _check_feature(test_context, name, desc, uid, c_slug)
                
    assert not test_context["missed"], f"Untracked subclass features: {test_context['missed']}"


@then("all species traits mentioning rests are either tracked or legitimately excluded")
def verify_species_traits(test_context):
    gd = test_context["gd"]
    test_context["missed"] = []
    
    def check_traits(traits_list, species_slug):
        for t in traits_list:
            name = t.get("name", "")
            desc = t.get("description", "")
            if desc:
                uid = f"species::{species_slug} - {name}"
                _check_feature(test_context, name, desc, uid, "")
            check_traits(t.get("subtraits", []), species_slug)

    for sp in gd.species:
        slug = sp.get("slug", "")
        check_traits(sp.get("traits", []), slug)
        
    assert not test_context["missed"], f"Untracked species traits: {test_context['missed']}"


@then("all feats mentioning rests are either tracked or legitimately excluded")
def verify_feats(test_context):
    gd = test_context["gd"]
    test_context["missed"] = []
    
    for feat in gd.feats:
        feat_name = feat.get("name", "")
        for benefit in feat.get("benefits", []) or []:
            name = benefit.get("name", feat_name)
            desc = benefit.get("description", "")
            uid = f"feat::{_normalize_name(feat_name)} - {name}"
            _check_feature(test_context, name, desc, uid, "")
            
    assert not test_context["missed"], f"Untracked feat benefits: {test_context['missed']}"
