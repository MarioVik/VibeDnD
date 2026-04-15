"""Runtime tracking for limited-use feature and trait resources."""

from __future__ import annotations

import re

from gui.species_trait_utils import get_species_trait_cards


_COUNT_UNIT = "uses"
_POOL_UNIT = "pool"

_RESOURCE_PATTERN_FLAGS = re.IGNORECASE | re.DOTALL


def _slugify(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def _normalize_name(value: str) -> str:
    return str(value or "").replace("\u2019", "'").strip().casefold()


def species_trait_card_id(species_name: str, trait_name: str) -> str:
    return f"species:{_slugify(species_name)}:{_slugify(trait_name)}"


def class_feature_card_id(class_slug: str, class_level: int, feature_name: str) -> str:
    return f"class:{_slugify(class_slug)}:{int(class_level)}:{_slugify(feature_name)}"


def subclass_feature_card_id(
    class_slug: str,
    subclass_slug: str,
    feature_level: int,
    feature_name: str,
) -> str:
    return (
        f"subclass:{_slugify(class_slug)}:{_slugify(subclass_slug)}:"
        f"{int(feature_level)}:{_slugify(feature_name)}"
    )


def feat_card_id(slot_key: str, feat_name: str) -> str:
    return f"feat:{_slugify(slot_key)}:{_slugify(feat_name)}"


def _rest_display_label(refresh_type: str, short_restore_amount: int = 0) -> str:
    if refresh_type == "short_or_long":
        return "Short or Long Rest resets"
    if refresh_type == "long":
        return "Long Rest resets"
    if refresh_type == "partial_short_full_long":
        return f"{max(0, int(short_restore_amount or 0))} on Short Rest, full on Long Rest"
    return ""


def _format_resource_display(resource: dict) -> str:
    remaining = int(resource.get("remaining_amount", 0) or 0)
    maximum = int(resource.get("max_amount", 0) or 0)
    unit = str(resource.get("unit_label", _COUNT_UNIT) or _COUNT_UNIT)
    refresh_type = str(resource.get("refresh_type", "") or "")
    short_restore_amount = int(resource.get("short_restore_amount", 0) or 0)
    reset_text = _rest_display_label(refresh_type, short_restore_amount)
    return f"{remaining}/{maximum} {unit} ({reset_text})"


def _character_class_level(character, class_slug: str) -> int:
    if not character:
        return 0
    return int(getattr(character, "class_level_in", lambda _slug: 0)(class_slug) or 0)


def _current_level_extra(character, game_data, class_slug: str) -> dict:
    class_level = _character_class_level(character, class_slug)
    if class_level <= 0 or not game_data:
        return {}
    level_data = game_data.get_level_data(class_slug, class_level) or {}
    extra = level_data.get("extra")
    if isinstance(extra, dict):
        return extra
    return {}


def _ability_modifier(character, ability_name: str, minimum: int | None = None) -> int:
    if not character:
        return 0
    score = int(character.ability_scores.total(ability_name) or 0)
    modifier = (score - 10) // 2
    if minimum is not None:
        modifier = max(minimum, modifier)
    return modifier


def _available_spell_slot_levels(character, game_data) -> list[dict]:
    slots: list[dict] = []
    for level_str, total in sorted(
        (character.current_spell_slots(game_data) or {}).items(),
        key=lambda item: int(item[0]),
    ):
        level = int(level_str)
        used = int((getattr(character, "used_spell_slots", {}) or {}).get(level_str, 0) or 0)
        available = max(0, int(total or 0) - used)
        if available > 0:
            slots.append(
                {
                    "level_key": str(level),
                    "level": level,
                    "available": available,
                }
            )

    pact_slots, pact_level = character.current_pact_magic(game_data)
    pact_available = max(0, int(pact_slots or 0) - int(getattr(character, "used_pact_slots", 0) or 0))
    if pact_available > 0 and pact_level > 0:
        slots.append(
            {
                "level_key": "pact",
                "level": int(pact_level),
                "available": pact_available,
            }
        )

    return slots


def _resolve_formula(character, game_data, formula: str, context: dict) -> int:
    card = context.get("card", {})
    class_slug = str(card.get("class_slug", "") or "")

    if formula == "proficiency_bonus":
        return max(0, int(character.proficiency_bonus))
    if formula == "charisma_mod_min_1":
        return max(1, _ability_modifier(character, "Charisma"))
    if formula == "paladin_level_x5":
        return max(0, _character_class_level(character, "paladin") * 5)
    if formula == "fighter_action_surge_uses":
        fighter_level = _character_class_level(character, "fighter")
        return 2 if fighter_level >= 17 else 1
    if formula == "fighter_indomitable_uses":
        fighter_level = _character_class_level(character, "fighter")
        if fighter_level >= 17:
            return 3
        if fighter_level >= 13:
            return 2
        return 1
    if formula == "short_restore_one":
        return 1
    if formula == "half_sorcerer_level":
        return max(0, _character_class_level(character, "sorcerer") // 2)
    if formula == "half_wizard_or_land_druid_level_rounded_up":
        wizard_level = _character_class_level(character, "wizard")
        druid_level = 0
        if str(getattr(character, "current_subclass", "") or "") == "circle-of-the-land":
            druid_level = _character_class_level(character, "druid")
        return max(0, (max(wizard_level, druid_level) + 1) // 2)
    if formula == "half_pact_slots_rounded_up":
        pact_slots, _ = character.current_pact_magic(game_data)
        return max(0, (int(pact_slots or 0) + 1) // 2)
    if formula == "level15_or_higher":
        return 1 if _character_class_level(character, class_slug) >= 15 else 0
    return 0


def _resolve_max_amount(character, game_data, spec: dict, context: dict) -> int:
    if "max_amount" in spec:
        return max(0, int(spec["max_amount"] or 0))
    if "max_formula" in spec:
        return max(0, int(_resolve_formula(character, game_data, str(spec["max_formula"]), context)))
    extra_key = str(spec.get("extra_key", "") or "").strip()
    if extra_key:
        card = context.get("card", {})
        class_slug = str(card.get("class_slug", "") or "")
        extra = _current_level_extra(character, game_data, class_slug)
        value = extra.get(extra_key)
        if value is None:
            return 0
        if isinstance(value, str) and re.fullmatch(r"\d+d\d+", value):
            return 0
        return max(0, int(value or 0))
    return 0


def _spell_grant_like_text(text: str) -> bool:
    compact = str(text or "")
    return "without a spell slot" in compact and "cast" in compact


def _build_feature_cards(character, game_data) -> list[dict]:
    cards: list[dict] = []
    c = character

    if c.species and c.species.get("traits"):
        for trait in get_species_trait_cards(c.species):
            card_id = species_trait_card_id(c.species_name, trait.get("name", ""))
            body_parts = []
            if trait.get("description"):
                body_parts.append(str(trait["description"]))
            for subtrait in trait.get("subtraits", []):
                sub_name = str(subtrait.get("name", "") or "").strip()
                sub_desc = str(subtrait.get("description", "") or "").strip()
                if sub_name and sub_desc:
                    body_parts.append(f"{sub_name}. {sub_desc}")
                elif sub_name:
                    body_parts.append(sub_name)
                elif sub_desc:
                    body_parts.append(sub_desc)
            cards.append(
                {
                    "card_id": card_id,
                    "card_type": "species",
                    "title": str(trait.get("name", "") or "").strip(),
                    "description_text": "\n\n".join(part for part in body_parts if part),
                    "species_name": c.species_name,
                }
            )

    if c.character_class and c.class_levels:
        for cl in c.class_levels:
            level_data = game_data.get_level_data(cl.class_slug, cl.class_level) if game_data else None
            feature_details = []
            if level_data:
                feature_details = [
                    feature
                    for feature in level_data.get("feature_details", [])
                    if isinstance(feature, dict)
                    and feature.get("name") not in ("-", "Ability Score Improvement")
                ]
                if not feature_details:
                    for name in level_data.get("features", []) or []:
                        if name not in ("-", "Ability Score Improvement"):
                            feature_details.append({"name": name, "description": ""})

            extra_items = []
            if cl.feat_choice:
                extra_items.append({"name": f"Feat: {cl.feat_choice}", "description": ""})
            if cl.subclass_slug:
                extra_items.append(
                    {
                        "name": f"Subclass: {cl.subclass_slug.replace('-', ' ').title()}",
                        "description": "",
                    }
                )

            for feature in feature_details + extra_items:
                title = str(feature.get("name", "") or "").strip()
                if not title:
                    continue
                cards.append(
                    {
                        "card_id": class_feature_card_id(cl.class_slug, cl.class_level, title),
                        "card_type": "class",
                        "title": title,
                        "description_text": str(feature.get("description", "") or "").strip(),
                        "class_slug": cl.class_slug,
                        "class_level": int(cl.class_level),
                    }
                )

    if c.current_subclass and c.character_class and game_data:
        subclass_data = game_data.get_subclass(c.character_class.get("slug", ""), c.current_subclass)
        if subclass_data:
            features_by_level = subclass_data.get("features", {}) or {}
            for level_key in sorted(
                features_by_level.keys(),
                key=lambda value: int(value) if str(value).isdigit() else 99,
            ):
                try:
                    feature_level = int(level_key)
                except (TypeError, ValueError):
                    continue
                if feature_level > c.level:
                    continue
                for feature in features_by_level.get(level_key, []) or []:
                    title = str(feature.get("name", "") or "").strip()
                    if not title:
                        continue
                    cards.append(
                        {
                            "card_id": subclass_feature_card_id(
                                c.character_class.get("slug", ""),
                                c.current_subclass,
                                feature_level,
                                title,
                            ),
                            "card_type": "subclass",
                            "title": title,
                            "description_text": str(feature.get("description", "") or "").strip(),
                            "class_slug": c.character_class.get("slug", ""),
                            "subclass_slug": c.current_subclass,
                            "feature_level": feature_level,
                        }
                    )

    if c.feat:
        benefit_parts = [
            f"{benefit.get('name', '')}: {benefit.get('description', '')}".strip(": ")
            for benefit in c.feat.get("benefits", []) or []
        ]
        feat_name = c.background.get("feat", c.feat.get("name", "")) if c.background else c.feat.get("name", "")
        cards.append(
            {
                "card_id": feat_card_id("background", feat_name),
                "card_type": "feat",
                "title": str(feat_name or "").strip(),
                "description_text": "\n\n".join(part for part in benefit_parts if part),
                "feat_name": str(feat_name or "").strip(),
                "feat_slot": "background",
            }
        )

    if c.species_origin_feat:
        benefit_parts = [
            f"{benefit.get('name', '')}: {benefit.get('description', '')}".strip(": ")
            for benefit in c.species_origin_feat.get("benefits", []) or []
        ]
        feat_name = c.species_origin_feat.get("name", "")
        cards.append(
            {
                "card_id": feat_card_id("species_origin", feat_name),
                "card_type": "feat",
                "title": str(feat_name or "").strip(),
                "description_text": "\n\n".join(part for part in benefit_parts if part),
                "feat_name": str(feat_name or "").strip(),
                "feat_slot": "species_origin",
            }
        )

    return cards


_CLASS_RESOURCE_SPECS = {
    ("barbarian", "rage"): {
        "resource_label": "Rage",
        "resource_kind": "count",
        "unit_label": _COUNT_UNIT,
        "extra_key": "Rages",
        "refresh_type": "partial_short_full_long",
        "short_restore_amount": 1,
    },
    ("bard", "bardic inspiration"): {
        "resource_label": "Bardic Inspiration",
        "resource_kind": "count",
        "unit_label": _COUNT_UNIT,
        "max_formula": "charisma_mod_min_1",
        "refresh_type": "long",
    },
    ("cleric", "channel divinity"): {
        "resource_label": "Channel Divinity",
        "resource_kind": "count",
        "unit_label": _COUNT_UNIT,
        "extra_key": "Channel Divinity",
        "refresh_type": "partial_short_full_long",
        "short_restore_amount": 1,
    },
    ("druid", "wild shape"): {
        "resource_label": "Wild Shape",
        "resource_kind": "count",
        "unit_label": _COUNT_UNIT,
        "extra_key": "Wild Shape",
        "refresh_type": "partial_short_full_long",
        "short_restore_amount": 1,
    },
    ("fighter", "second wind"): {
        "resource_label": "Second Wind",
        "resource_kind": "count",
        "unit_label": _COUNT_UNIT,
        "extra_key": "Second Wind",
        "refresh_type": "partial_short_full_long",
        "short_restore_amount": 1,
    },
    ("fighter", "action surge"): {
        "resource_label": "Action Surge",
        "resource_kind": "count",
        "unit_label": _COUNT_UNIT,
        "max_formula": "fighter_action_surge_uses",
        "refresh_type": "short_or_long",
    },
    ("fighter", "indomitable"): {
        "resource_label": "Indomitable",
        "resource_kind": "count",
        "unit_label": _COUNT_UNIT,
        "max_formula": "fighter_indomitable_uses",
        "refresh_type": "long",
    },
    ("monk", "monk's focus"): {
        "resource_label": "Focus Points",
        "resource_kind": "pool",
        "unit_label": _POOL_UNIT,
        "extra_key": "Focus Points",
        "refresh_type": "short_or_long",
    },
    ("monk", "monk’s focus"): {
        "resource_label": "Focus Points",
        "resource_kind": "pool",
        "unit_label": _POOL_UNIT,
        "extra_key": "Focus Points",
        "refresh_type": "short_or_long",
    },
    ("paladin", "lay on hands"): {
        "resource_label": "Lay On Hands",
        "resource_kind": "pool",
        "unit_label": _POOL_UNIT,
        "max_formula": "paladin_level_x5",
        "refresh_type": "long",
    },
    ("paladin", "channel divinity"): {
        "resource_label": "Channel Divinity",
        "resource_kind": "count",
        "unit_label": _COUNT_UNIT,
        "extra_key": "Channel Divinity",
        "refresh_type": "partial_short_full_long",
        "short_restore_amount": 1,
    },
    ("ranger", "favored enemy"): {
        "resource_label": "Favored Enemy",
        "resource_kind": "count",
        "unit_label": _COUNT_UNIT,
        "extra_key": "Favored Enemy",
        "refresh_type": "long",
    },
    ("sorcerer", "innate sorcery"): {
        "resource_label": "Innate Sorcery",
        "resource_kind": "count",
        "unit_label": _COUNT_UNIT,
        "max_amount": 2,
        "refresh_type": "long",
    },
    ("sorcerer", "font of magic"): {
        "resource_label": "Sorcery Points",
        "resource_kind": "pool",
        "unit_label": _POOL_UNIT,
        "extra_key": "Sorcery Points",
        "refresh_type": "long",
    },
}


def _maybe_adjust_resource_spec(character, card: dict, spec: dict) -> dict:
    adjusted = dict(spec)
    card_type = str(card.get("card_type", "") or "")
    title_key = _normalize_name(card.get("title", ""))
    class_slug = str(card.get("class_slug", "") or "")

    if card_type == "class" and class_slug == "bard" and title_key == "bardic inspiration":
        if _character_class_level(character, "bard") >= 5:
            adjusted["refresh_type"] = "short_or_long"
    return adjusted


def _resource_spec_for_card(character, card: dict) -> dict | None:
    if str(card.get("card_type", "") or "") == "class":
        key = (str(card.get("class_slug", "") or ""), _normalize_name(card.get("title", "")))
        spec = _CLASS_RESOURCE_SPECS.get(key)
        if spec is not None:
            return _maybe_adjust_resource_spec(character, card, spec)
    return None


_GENERIC_COUNT_PB_PATTERN = re.compile(
    r"You can use this (?:trait|feature|benefit|ability) a number of times equal to your Proficiency Bonus,"
    r"\s*and you regain all expended uses when you finish a (Long Rest|Short or Long Rest)\.",
    _RESOURCE_PATTERN_FLAGS,
)

_GENERIC_COUNT_ONCE_PATTERN = re.compile(
    r"Once you use this (?:trait|feature|benefit|ability|counterattack),\s*you can(?:'|’)?t "
    r"(?:use it again|do so again) until you finish a (Long Rest|Short or Long Rest)\.",
    _RESOURCE_PATTERN_FLAGS,
)

_GENERIC_COUNT_TWICE_PATTERN = re.compile(
    r"You can use this feature twice,\s*and you regain all expended uses of it when you finish a (Long Rest|Short or Long Rest)\.",
    _RESOURCE_PATTERN_FLAGS,
)

_GENERIC_POOL_PB_PATTERN = re.compile(
    r"You have a number of ([A-Za-z'’ ]+?) equal to your Proficiency Bonus and can spend the points.*?"
    r"You regain (?:your|all) expended \1 when you finish a (Long Rest|Short or Long Rest)\.",
    _RESOURCE_PATTERN_FLAGS,
)


def _generic_resource_spec_for_card(card: dict) -> dict | None:
    text = str(card.get("description_text", "") or "").strip()
    if not text or _spell_grant_like_text(text):
        return None

    pool_match = _GENERIC_POOL_PB_PATTERN.search(text)
    if pool_match:
        resource_label = str(pool_match.group(1) or "").replace("\u2019", "'").strip()
        refresh_text = str(pool_match.group(2) or "").strip()
        return {
            "resource_label": resource_label,
            "resource_kind": "pool",
            "unit_label": _POOL_UNIT,
            "max_formula": "proficiency_bonus",
            "refresh_type": "short_or_long" if refresh_text == "Short or Long Rest" else "long",
        }

    count_pb_match = _GENERIC_COUNT_PB_PATTERN.search(text)
    if count_pb_match:
        refresh_text = str(count_pb_match.group(1) or "").strip()
        return {
            "resource_label": str(card.get("title", "") or "").strip(),
            "resource_kind": "count",
            "unit_label": _COUNT_UNIT,
            "max_formula": "proficiency_bonus",
            "refresh_type": "short_or_long" if refresh_text == "Short or Long Rest" else "long",
        }

    count_twice_match = _GENERIC_COUNT_TWICE_PATTERN.search(text)
    if count_twice_match:
        refresh_text = str(count_twice_match.group(1) or "").strip()
        return {
            "resource_label": str(card.get("title", "") or "").strip(),
            "resource_kind": "count",
            "unit_label": _COUNT_UNIT,
            "max_amount": 2,
            "refresh_type": "short_or_long" if refresh_text == "Short or Long Rest" else "long",
        }

    count_once_match = _GENERIC_COUNT_ONCE_PATTERN.search(text)
    if count_once_match:
        refresh_text = str(count_once_match.group(1) or "").strip()
        return {
            "resource_label": str(card.get("title", "") or "").strip(),
            "resource_kind": "count",
            "unit_label": _COUNT_UNIT,
            "max_amount": 1,
            "refresh_type": "short_or_long" if refresh_text == "Short or Long Rest" else "long",
        }

    return None


def _build_resource_from_card(character, game_data, card: dict) -> dict | None:
    spec = _resource_spec_for_card(character, card) or _generic_resource_spec_for_card(card)
    if spec is None:
        return None

    max_amount = _resolve_max_amount(character, game_data, spec, {"card": card})
    if max_amount <= 0:
        return None

    resource_label = str(spec.get("resource_label", card.get("title", "")) or card.get("title", "")).strip()
    resource_id = f"feature:{_slugify(card['card_id'])}:{_slugify(resource_label)}"
    spent_resources = getattr(character, "spent_feature_resources", {}) or {}
    spent_amount = max(0, min(int(spent_resources.get(resource_id, 0) or 0), max_amount))
    remaining_amount = max(0, max_amount - spent_amount)

    resource = {
        "resource_id": resource_id,
        "card_id": card["card_id"],
        "card_title": card["title"],
        "resource_label": resource_label,
        "resource_kind": str(spec.get("resource_kind", "count") or "count"),
        "unit_label": str(spec.get("unit_label", _COUNT_UNIT) or _COUNT_UNIT),
        "refresh_type": str(spec.get("refresh_type", "long") or "long"),
        "short_restore_amount": int(spec.get("short_restore_amount", 0) or 0),
        "max_amount": max_amount,
        "spent_amount": spent_amount,
        "remaining_amount": remaining_amount,
        "description_text": str(card.get("description_text", "") or ""),
    }
    resource["display_text"] = _format_resource_display(resource)
    return resource


def _resource_sort_key(resource: dict) -> tuple:
    return (
        str(resource.get("card_id", "") or ""),
        str(resource.get("resource_label", "") or "").casefold(),
    )


def _collect_active_feature_resources(character, game_data) -> list[dict]:
    resources: list[dict] = []
    for card in _build_feature_cards(character, game_data):
        resource = _build_resource_from_card(character, game_data, card)
        if resource is not None:
            resources.append(resource)
    resources.sort(key=_resource_sort_key)
    return resources


def scrub_feature_resource_state(character, game_data) -> bool:
    current = getattr(character, "spent_feature_resources", None)
    if not isinstance(current, dict):
        character.spent_feature_resources = {}
        return False

    changed = False
    active_resources = {
        resource["resource_id"]: resource for resource in _collect_active_feature_resources(character, game_data)
    }

    for resource_id in list(current.keys()):
        resource = active_resources.get(resource_id)
        if resource is None:
            current.pop(resource_id, None)
            changed = True
            continue

        max_amount = int(resource.get("max_amount", 0) or 0)
        spent_amount = int(current.get(resource_id, 0) or 0)
        clamped = max(0, min(spent_amount, max_amount))
        if clamped <= 0:
            current.pop(resource_id, None)
            changed = True
        elif clamped != spent_amount:
            current[resource_id] = clamped
            changed = True

    return changed


def get_active_feature_resources(character, game_data) -> list[dict]:
    scrub_feature_resource_state(character, game_data)
    return _collect_active_feature_resources(character, game_data)


def get_feature_card_resources(character, game_data, card_id: str) -> list[dict]:
    return [
        resource
        for resource in get_active_feature_resources(character, game_data)
        if resource.get("card_id") == card_id
    ]


_LINKED_RESOURCE_NAMES = (
    "Second Wind",
    "Channel Divinity",
    "Wild Shape",
    "Focus Points",
    "Sorcery Points",
    "Bardic Inspiration",
    "Luck Points",
)


def get_feature_card_linked_resources(character, game_data, card_id: str) -> list[dict]:
    cards = {card["card_id"]: card for card in _build_feature_cards(character, game_data)}
    card = cards.get(card_id)
    if card is None:
        return []

    own_resources = {resource["resource_id"] for resource in get_feature_card_resources(character, game_data, card_id)}
    description_text = str(card.get("description_text", "") or "")
    if not description_text:
        return []

    linked: list[dict] = []
    for resource in get_active_feature_resources(character, game_data):
        if resource["resource_id"] in own_resources:
            continue
        label = str(resource.get("resource_label", "") or "")
        if label not in _LINKED_RESOURCE_NAMES:
            continue
        if label in description_text:
            linked.append(
                {
                    "resource_id": resource["resource_id"],
                    "label": label,
                    "display_text": str(resource.get("display_text", "") or ""),
                }
            )
    linked.sort(key=lambda item: (item["label"].casefold(), item["resource_id"]))
    return linked


def get_feature_card_counter_text(character, game_data, card_id: str) -> str:
    resources = get_feature_card_resources(character, game_data, card_id)
    if not resources:
        return ""
    return str(resources[0].get("display_text", "") or "")


def spend_feature_resource(character, game_data, resource_id: str, amount: int = 1) -> bool:
    if amount <= 0:
        return False
    for resource in get_active_feature_resources(character, game_data):
        if resource["resource_id"] != resource_id:
            continue
        remaining_amount = int(resource.get("remaining_amount", 0) or 0)
        if remaining_amount < amount:
            return False
        spent_resources = getattr(character, "spent_feature_resources", None)
        if not isinstance(spent_resources, dict):
            spent_resources = {}
            character.spent_feature_resources = spent_resources
        spent_resources[resource_id] = int(spent_resources.get(resource_id, 0) or 0) + amount
        return True
    return False


def restore_feature_resources(character, game_data, rest_type: str) -> bool:
    if rest_type not in {"short", "long"}:
        return False

    spent_resources = getattr(character, "spent_feature_resources", None)
    if not isinstance(spent_resources, dict) or not spent_resources:
        return False

    changed = False
    for resource in get_active_feature_resources(character, game_data):
        resource_id = resource["resource_id"]
        if resource_id not in spent_resources:
            continue
        refresh_type = str(resource.get("refresh_type", "") or "")
        if rest_type == "long":
            if refresh_type in {"long", "short_or_long", "partial_short_full_long"}:
                spent_resources.pop(resource_id, None)
                changed = True
            continue

        if refresh_type == "short_or_long":
            spent_resources.pop(resource_id, None)
            changed = True
            continue
        if refresh_type == "partial_short_full_long":
            current = int(spent_resources.get(resource_id, 0) or 0)
            updated = max(0, current - int(resource.get("short_restore_amount", 0) or 0))
            if updated <= 0:
                spent_resources.pop(resource_id, None)
            else:
                spent_resources[resource_id] = updated
            changed = True

    return changed


def get_restorable_feature_resources(character, game_data, rest_type: str) -> list[dict]:
    resources = get_active_feature_resources(character, game_data)
    if rest_type == "long":
        return [
            resource
            for resource in resources
            if resource.get("refresh_type") in {"long", "short_or_long", "partial_short_full_long"}
        ]
    if rest_type == "short":
        return [
            resource
            for resource in resources
            if resource.get("refresh_type") in {"short_or_long", "partial_short_full_long"}
        ]
    return []
