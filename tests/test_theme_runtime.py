from gui.theme import _choose_tk_scaling


def test_choose_tk_scaling_uses_screen_dpi_on_macos():
    assert _choose_tk_scaling(1.0, 144.0, "darwin") == 2.0


def test_choose_tk_scaling_keeps_existing_value_off_macos():
    assert _choose_tk_scaling(1.25, 144.0, "linux") == 1.25


def test_choose_tk_scaling_prefers_manual_override():
    assert _choose_tk_scaling(1.25, 144.0, "darwin", "1.75") == 1.75


def test_choose_tk_scaling_ignores_invalid_override():
    assert _choose_tk_scaling(1.25, 144.0, "darwin", "abc") == 2.0
