"""Shared fixtures for the TUI test suite (plain pytest, no GUI)."""

import os
import shutil

import pytest

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "druid.json")


@pytest.fixture(scope="session")
def game_data():
    from tui.loader import game_data
    return game_data()


@pytest.fixture
def save_path(tmp_path):
    """A throwaway copy of the fixture save, safe to write through."""
    path = tmp_path / "druid.json"
    shutil.copy(FIXTURE, path)
    return str(path)


@pytest.fixture
def view(save_path, game_data):
    from models.character_store import load_character
    from tui.adapter import from_model
    return from_model(load_character(save_path, game_data), game_data,
                      source_path=save_path)
