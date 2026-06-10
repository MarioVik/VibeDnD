"""Loader tests: discovery, degradation, demo fallback."""

from tui import loader


def test_demo_mode():
    chars, status = loader.load_characters(demo=True)
    assert status == "demo mode"
    assert len(chars) == 1
    assert chars[0].name == "Thorn Ironvale"


def test_load_one_real_save(save_path):
    view = loader._load_one(save_path)
    assert view is not None
    assert view.name == "Test"
    assert view.source_path == save_path


def test_load_one_skips_broken_file(tmp_path):
    bad = tmp_path / "broken.json"
    bad.write_text("{not json", encoding="utf-8")
    assert loader._load_one(str(bad)) is None


def test_character_files_lists_only_json(monkeypatch, tmp_path):
    import paths
    (tmp_path / "b.json").write_text("{}")
    (tmp_path / "a.json").write_text("{}")
    (tmp_path / "notes.txt").write_text("x")
    monkeypatch.setattr(paths, "characters_dir", lambda: str(tmp_path))
    files = loader._character_files()
    assert [f.split("/")[-1] for f in files] == ["a.json", "b.json"]


def test_missing_characters_dir(monkeypatch, tmp_path):
    import paths
    monkeypatch.setattr(paths, "characters_dir",
                        lambda: str(tmp_path / "nowhere"))
    assert loader._character_files() == []
    chars, status = loader.load_characters()
    assert chars == []
    assert "no saved characters" in status
