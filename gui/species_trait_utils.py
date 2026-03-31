"""Helpers for presenting grouped species traits in the UI."""

from __future__ import annotations


_TRAIT_GROUPS: dict[str, dict[str, list[str]]] = {
    "Aasimar": {
        "Celestial Revelation": [
            "Heavenly Wings",
            "Inner Radiance",
            "Necrotic Shroud",
        ],
    },
}


def get_species_trait_cards(
    species: dict | None,
    excluded_names: set[str] | None = None,
) -> list[dict]:
    """Return display-ready species trait cards with optional nested subtraits."""
    if not species:
        return []

    traits = species.get("traits", []) or []
    species_name = species.get("name", "")
    groups = _TRAIT_GROUPS.get(species_name, {})
    grouped_child_names = {
        child_name
        for child_names in groups.values()
        for child_name in child_names
    }
    traits_by_name = {
        trait.get("name", ""): trait
        for trait in traits
        if trait.get("name", "")
    }

    excluded = set(excluded_names or ())
    consumed = set(excluded)
    cards: list[dict] = []

    for trait in traits:
        name = trait.get("name", "")
        if not name or name in consumed:
            continue

        if name in grouped_child_names:
            consumed.add(name)
            continue

        child_names = groups.get(name, [])
        subtraits = []
        for child_name in child_names:
            child_trait = traits_by_name.get(child_name)
            if child_trait is None or child_name in excluded:
                continue
            subtraits.append(
                {
                    "name": child_trait.get("name", ""),
                    "description": child_trait.get("description", ""),
                }
            )
            consumed.add(child_name)

        cards.append(
            {
                "name": name,
                "description": trait.get("description", ""),
                "subtraits": subtraits,
            }
        )
        consumed.add(name)

    return cards
