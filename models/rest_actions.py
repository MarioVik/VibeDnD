"""Unified framework for character decisions and actions during Short and Long Rests."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, TYPE_CHECKING
import json
import os
import random

if TYPE_CHECKING:
    from models.character import Character
    from gui.data_loader import GameData

@dataclass
class RestAction:
    id: str
    name: str
    description: str
    rest_type: str  # "short", "long", or "both"
    kind: str  # "choice", "checklist", "button"
    
    # For "choice" kind
    options: list[str] = field(default_factory=list)
    current_value: str | None = None
    
    # Logic hooks
    is_available: Callable[[Character, GameData], bool] = lambda c, gd: True
    apply: Callable[[Character, GameData, Any], bool] = lambda c, gd, res: False
    get_state: Callable[[Character, GameData], Any] = lambda c, gd: None

def get_available_rest_actions(character: Character, game_data: GameData, rest_type: str) -> list[RestAction]:
    """Discover all rest actions available to the character for the given rest type."""
    from paths import data_dir
    choices_path = os.path.join(data_dir(), "class_choices.json")
    try:
        with open(choices_path, encoding="utf-8") as f:
            class_choices = json.load(f)
    except:
        class_choices = {}

    actions = []
    
    for action_def in REST_ACTION_REGISTRY:
        if action_def.rest_type != "both" and action_def.rest_type != rest_type:
            continue
        if action_def.is_available(character, game_data):
            # Create a shallow copy to avoid mutating the registry instances
            # and populate current value/options dynamically
            instance = RestAction(
                id=action_def.id,
                name=action_def.name,
                description=action_def.description,
                rest_type=action_def.rest_type,
                kind=action_def.kind,
                options=list(action_def.options),
                is_available=action_def.is_available,
                apply=action_def.apply,
                get_state=action_def.get_state
            )
            instance.current_value = instance.get_state(character, game_data)
            
            # Special case for Zhentarim options which depend on character skills
            if instance.id == "feat:zhentarim_tactics":
                from models.skill_utils import get_selectable_expertise_grants, ZHENTARIM_TACTICS
                grants = get_selectable_expertise_grants(character)
                instance.options = [g["skill"] for g in grants if g.get("kind") == "feat" and g.get("feat_name") == ZHENTARIM_TACTICS]

            actions.append(instance)
    
    actions.extend(_get_class_choice_rest_actions(character, game_data, rest_type, class_choices))
    
    return actions

def _get_class_choice_rest_actions(character: Character, game_data: GameData, rest_type: str, class_choices: dict) -> list[RestAction]:
    actions = []
    all_keys = set()
    for cl in character.class_levels:
        all_keys.add(cl.class_slug)
        if cl.subclass_slug:
            all_keys.add(cl.subclass_slug)

    for key in sorted(all_keys):
        config = class_choices.get(key)
        if not config or not config.get("can_swap_on_rest"):
            continue
        
        swap_type = config.get("swap_rest_type", "long")
        if rest_type == "short" and swap_type not in ("short", "short_or_long"):
            continue
            
        known = []
        for cl in character.class_levels:
            if cl.class_slug == key or cl.subclass_slug == key:
                known.extend(cl.new_choices)
                if cl.replaced_choice and cl.replaced_choice in known:
                    known.remove(cl.replaced_choice)
        
        if not known:
            continue

        for item_name in known:
            actions.append(RestAction(
                id=f"class_choice:{key}:{item_name}",
                name=f"Swap {config.get('choice_label', 'Choice')}: {item_name}",
                description=f"You can replace {item_name} with another option from the {config.get('choice_plural', 'Choices')} list.",
                rest_type=swap_type,
                kind="choice",
                options=[o["name"] for o in config.get("options", []) if o["name"] not in known],
                apply=lambda c, gd, res, k=key, old=item_name: _apply_choice_swap_internal(c, k, old, res)
            ))
            
    return actions

def _apply_choice_swap_internal(character: Character, key: str, remove_name: str, replace_name: str) -> bool:
    if not replace_name:
        return False
    for cl in character.class_levels:
        if (cl.class_slug == key or cl.subclass_slug == key) and remove_name in cl.new_choices:
            cl.new_choices.remove(remove_name)
            cl.new_choices.append(replace_name)
            cl.replaced_choice = remove_name
            cl.choice_sub_selections.pop(remove_name, None)
            return True
    return False

REST_ACTION_REGISTRY: list[RestAction] = [
    RestAction(
        id="feat:zhentarim_tactics",
        name="Zhentarim Tactics Expertise",
        description="Choose one proficient skill to gain Expertise in until your next Long Rest.",
        rest_type="long",
        kind="choice",
        is_available=lambda c, gd: _has_feat(c, "Zhentarim Tactics"),
        get_state=lambda c, gd: _get_zhentarim_state(c),
        apply=lambda c, gd, res: _apply_zhentarim_internal(c, res)
    ),
    RestAction(
        id="feat:boon_of_energy_resistance",
        name="Energy Resistance",
        description="Choose a damage type to gain resistance to until your next Long Rest.",
        rest_type="long",
        kind="choice",
        options=["Acid", "Cold", "Fire", "Force", "Lightning", "Necrotic", "Poison", "Psychic", "Radiant", "Thunder"],
        is_available=lambda c, gd: _has_feat(c, "Boon of Energy Resistance"),
        get_state=lambda c, gd: _get_feat_sub_choice(c, "Boon of Energy Resistance"),
        apply=lambda c, gd, res: _set_feat_sub_choice(c, "Boon of Energy Resistance", res)
    ),
    RestAction(
        id="species:trance",
        name="Trance Proficiency",
        description="Replace one weapon or tool proficiency with another.",
        rest_type="long",
        kind="choice",
        is_available=lambda c, gd: (c.species or {}).get("name") == "Elf",
        get_state=lambda c, gd: _get_feat_sub_choice(c, "Trance"),
        apply=lambda c, gd, res: _set_feat_sub_choice(c, "Trance", res)
    ),
    RestAction(
        id="subclass:fiend_resilience",
        name="Fiendish Resilience",
        description="Choose a damage type to gain resistance to. This resistance lasts until you choose a different one or finish a rest.",
        rest_type="long",
        kind="choice",
        options=["Acid", "Cold", "Fire", "Force", "Lightning", "Necrotic", "Poison", "Psychic", "Radiant", "Thunder"],
        is_available=lambda c, gd: c.current_subclass == "fiend",
        get_state=lambda c, gd: c.get_feature_state("Fiendish Resilience"),
        apply=lambda c, gd, res: c.set_feature_state("Fiendish Resilience", res)
    ),
    RestAction(
        id="subclass:transmuter_stone",
        name="Transmuter's Stone",
        description="Create a Transmuter's Stone. Choose the benefit it grants.",
        rest_type="long",
        kind="choice",
        options=["Darkvision", "Resilience (Con Saves)", "Resistance (Acid)", "Resistance (Cold)", "Resistance (Fire)", "Resistance (Lightning)", "Resistance (Thunder)", "Speed (+10 ft)"],
        is_available=lambda c, gd: c.current_subclass == "school-of-transmutation" and c.class_level_in("wizard") >= 6,
        get_state=lambda c, gd: c.get_feature_state("Transmuter's Stone"),
        apply=lambda c, gd, res: _apply_transmuter_stone(c, gd, res)
    ),
    RestAction(
        id="subclass:circle_of_land_biome",
        name="Circle of the Land: Biome",
        description="Choose a biome to determine your Circle spells.",
        rest_type="long",
        kind="choice",
        options=["Arid", "Polar", "Temperate", "Tropical"],
        is_available=lambda c, gd: c.current_subclass == "circle-of-the-land",
        get_state=lambda c, gd: c.get_feature_state("Circle of the Land Biome"),
        apply=lambda c, gd, res: c.set_feature_state("Circle of the Land Biome", res)
    ),
    RestAction(
        id="button:experimental_elixir",
        name="Experimental Elixir",
        description="Generate an Experimental Elixir in your inventory.",
        rest_type="long",
        kind="button",
        is_available=lambda c, gd: c.current_subclass == "alchemist",
        apply=lambda c, gd, res: _generate_alchemist_elixir(c, gd)
    ),
    RestAction(
        id="checklist:musician",
        name="Musician: Encouraging Song",
        description="Grant Heroic Inspiration to your allies as you finish your rest.",
        rest_type="both",
        kind="checklist",
        is_available=lambda c, gd: _has_feat(c, "Musician")
    ),
    RestAction(
        id="checklist:inspiring_leader",
        name="Inspiring Leader: Bolstering Performance",
        description="Give Temporary Hit Points to your allies as you finish your rest.",
        rest_type="both",
        kind="checklist",
        is_available=lambda c, gd: _has_feat(c, "Inspiring Leader")
    ),
]

def _has_feat(character: Character, feat_name: str) -> bool:
    """Check if character has a feat by name, including background and leveled-up feats."""
    if character.feat and character.feat.get("name") == feat_name:
        return True
    if character.species_origin_feat and character.species_origin_feat.get("name") == feat_name:
        return True
    for cl in character.class_levels:
        if cl.feat_choice == feat_name:
            return True
    return False

def _get_zhentarim_state(character) -> str | None:
    from models.skill_utils import get_feat_expertise_skill, ZHENTARIM_TACTICS
    return get_feat_expertise_skill(character, ZHENTARIM_TACTICS)

def _apply_zhentarim_internal(character: Character, skill_name: str) -> bool:
    from models.skill_utils import set_feat_expertise_skill, ZHENTARIM_TACTICS
    if not skill_name: return False
    set_feat_expertise_skill(character, ZHENTARIM_TACTICS, skill_name)
    return True

def _get_feat_sub_choice(character, feat_name: str) -> str | None:
    raw = (character.feat_sub_choices or {}).get(feat_name)
    if isinstance(raw, dict): return raw.get("choice") or raw.get("skill")
    return str(raw) if raw else None

def _set_feat_sub_choice(character, feat_name: str, value: str) -> bool:
    if not character.feat_sub_choices: character.feat_sub_choices = {}
    if not value:
        if feat_name in character.feat_sub_choices:
            del character.feat_sub_choices[feat_name]
            return True
        return False
    character.feat_sub_choices[feat_name] = value
    return True

def _apply_transmuter_stone(character: Character, game_data: GameData, benefit: str) -> bool:
    character.set_feature_state("Transmuter's Stone", benefit)
    from models.inventory_service import add_item
    item_name = f"Transmuter's Stone ({benefit})"
    add_item(character, {"name": item_name, "id": f"magic-item:transmuters-stone-{benefit.lower().replace(' ', '-')}", "category": "Adventuring Gear"}, 1, "free")
    return True

def _generate_alchemist_elixir(character: Character, game_data: GameData) -> bool:
    from models.inventory_service import add_item
    elixirs = ["Healing", "Swiftness", "Resilience", "Boldness", "Flight", "Transformation"]
    elixir = random.choice(elixirs)
    add_item(character, {"name": f"Experimental Elixir ({elixir})", "id": "magic-item:experimental-elixir", "category": "Adventuring Gear"}, 1, "free")
    return True
