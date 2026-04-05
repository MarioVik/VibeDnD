from __future__ import annotations

import json
from pathlib import Path

import pytest

from gui.data_loader import GameData
from models.level1_class_rules import (
    get_available_fighting_styles,
    get_available_origin_feats,
)
from parsers.feat_parser import parse_feats

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = REPO_ROOT / "dnd2024_data.json"

EXPECTED_ORIGIN_FEATS = {
    "Alert",
    "Crafter",
    "Healer",
    "Lucky",
    "Magic Initiate",
    "Musician",
    "Savage Attacker",
    "Skilled",
    "Tavern Brawler",
    "Tough",
    "Cult Of The Dragon Initiate",
    "Emerald Enclave Fledgling",
    "Harper Agent",
    "Lords Alliance Agent",
    "Purple Dragon Rook",
    "Spellfire Spark",
    "Tyro Of The Gauntlet",
    "Zhentarim Ruffian",
    "Child Of The Sun",
    "Shadowmoor Hexer",
    "Tireless Reveler",
    "Vampire Hunter",
    "Vampire S Plaything",
}

EXPECTED_FIGHTING_STYLE_FEATS = {
    "Archery",
    "Blind Fighting",
    "Defense",
    "Dueling",
    "Great Weapon Fighting",
    "Interception",
    "Protection",
    "Thrown Weapon Fighting",
    "Two Weapon Fighting",
    "Unarmed Fighting",
}


@pytest.fixture(scope="session")
def raw_feat_entries() -> list[dict]:
    with RAW_DATA_PATH.open("r", encoding="utf-8") as handle:
        raw_data = json.load(handle)
    return raw_data["feats"]


@pytest.fixture(scope="session")
def parsed_feats(raw_feat_entries: list[dict]) -> dict[str, dict]:
    return {feat["name"]: feat for feat in parse_feats(raw_feat_entries)}


@pytest.fixture(scope="session")
def game_data() -> GameData:
    return GameData()


@pytest.mark.parametrize(
    ("feat_name", "expected_category"),
    [
        ("Alert", "origin"),
        ("Archery", "fighting_style"),
        ("Cold Caster", "general"),
        ("Boon Of Bloodshed", "epic_boon"),
        ("Mark Of Detection", "dragonmark"),
        ("Greater Mark Of Detection", "greater_dragonmark"),
    ],
)
def test_parse_feats_uses_explicit_category_metadata(
    parsed_feats: dict[str, dict],
    feat_name: str,
    expected_category: str,
):
    assert parsed_feats[feat_name]["category"] == expected_category


def test_parse_feats_fails_when_feat_family_heading_is_missing(raw_feat_entries: list[dict]):
    alert_entry = dict(next(entry for entry in raw_feat_entries if entry["url"].endswith("feat:alert")))
    alert_entry.pop("feat_family_heading", None)

    with pytest.raises(ValueError, match="Alert.*feat_family_heading"):
        parse_feats([alert_entry])


def test_parse_feats_fails_when_heading_and_tags_conflict(raw_feat_entries: list[dict]):
    mark_entry = dict(
        next(entry for entry in raw_feat_entries if entry["url"].endswith("feat:mark-of-detection"))
    )
    mark_entry["feat_family_heading"] = "Origin Feats"

    with pytest.raises(ValueError, match="Mark Of Detection.*category mismatch"):
        parse_feats([mark_entry])


def test_origin_feat_catalog_matches_feat_all_source(game_data: GameData):
    origin_names = {feat["name"] for feat in get_available_origin_feats(game_data)}

    assert origin_names == EXPECTED_ORIGIN_FEATS
    assert "Archery" not in origin_names
    assert "Mark Of Detection" not in origin_names
    assert "Boon Of Bloodshed" not in origin_names


def test_fighting_style_catalog_uses_exact_fighting_style_category(game_data: GameData):
    style_names = {feat["name"] for feat in get_available_fighting_styles(game_data)}
    assert style_names == EXPECTED_FIGHTING_STYLE_FEATS
