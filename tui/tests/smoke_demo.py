"""Headless smoke drive of the TUI in demo mode (not a pytest test).

Run from the repo root:  uv run python tui/tests/smoke_demo.py
Walks roster -> sheet -> all tabs -> dice roller -> HP keys -> back.
"""
import asyncio

from tui.app import VibeDnDTUI


async def main() -> None:
    app = VibeDnDTUI(demo=True)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert type(app.screen).__name__ == "HomeScreen", app.screen
        print("home screen ok, roster rows:",
              app.screen.query_one("#roster").option_count)

        await pilot.press("enter")
        await pilot.pause()
        assert type(app.screen).__name__ == "SheetScreen", app.screen
        print("sheet open ok")

        # vim motions: focus follows tabs, j/k/g/G move the table cursor
        await pilot.press("2")          # skills tab
        await pilot.pause()
        table = app.screen.query_one("#skills-table")
        assert app.focused is table, f"focus should follow tab: {app.focused}"
        assert table.cursor_row == 0
        await pilot.press("j", "j", "k")
        await pilot.pause()
        assert table.cursor_row == 1, table.cursor_row
        await pilot.press("G")
        await pilot.pause()
        assert table.cursor_row == table.row_count - 1
        await pilot.press("g")
        await pilot.pause()
        assert table.cursor_row == 0
        await pilot.press("right_square_bracket")   # ] -> spells tab
        await pilot.pause()
        assert app.screen.query_one("#sheet-tabs").active == "tab-spells"
        await pilot.press("left_square_bracket")    # [ -> back to skills
        await pilot.pause()
        assert app.screen.query_one("#sheet-tabs").active == "tab-skills"
        print("vim motions ok")

        for key, tab in [("2", "tab-skills"), ("3", "tab-spells"),
                         ("4", "tab-inventory"), ("5", "tab-features"),
                         ("1", "tab-overview")]:
            await pilot.press(key)
            await pilot.pause()
            active = app.screen.query_one("#sheet-tabs").active
            assert active == tab, f"pressed {key}: active={active}, want {tab}"
        print("all 5 tabs ok")

        hp = app.screen.query_one("#sheet-hp")
        before = hp.current
        await pilot.press("h")
        await pilot.pause()
        assert hp.current == before - 1, (before, hp.current)
        await pilot.press("H")
        await pilot.pause()
        assert hp.current == before, (before, hp.current)
        print("h/H HP keys ok")

        await pilot.press("3")          # spells tab
        await pilot.pause()
        used_before = dict(app.screen.view.spell_slots_used)
        await pilot.press("s")
        await pilot.pause()
        assert sum(app.screen.view.spell_slots_used.values()) == \
            sum(used_before.values()) + 1, app.screen.view.spell_slots_used
        await pilot.press("S")
        await pilot.pause()
        assert app.screen.view.spell_slots_used == used_before
        print("s/S slot keys ok")

        await pilot.press("m")          # coin pouch modal
        await pilot.pause()
        assert type(app.screen).__name__ == "MoneyModal", app.screen
        for ch in "+2gp 5sp":
            await pilot.press(ch if ch != " " else "space")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert type(app.screen).__name__ == "SheetScreen", app.screen
        assert app.screen.view.coins == (37, 5, 0), app.screen.view.coins
        await pilot.press("m")
        await pilot.pause()
        for ch in "-2gp5sp":
            await pilot.press(ch)
        await pilot.press("enter")
        await pilot.pause()
        assert app.screen.view.coins == (35, 0, 0), app.screen.view.coins
        print("money modal ok")

        await pilot.press("r")
        await pilot.pause()
        assert type(app.screen).__name__ == "DiceRoller", app.screen
        await asyncio.sleep(1.0)  # let the spin animation settle
        face = str(app.screen.query_one("#dice-face").render())
        assert face.strip(), "dice face empty after settle"
        print("dice roller ok, settled on:", face.splitlines()[0])
        await pilot.press("escape")
        await pilot.pause()
        assert type(app.screen).__name__ == "SheetScreen", app.screen

        await pilot.press("escape")
        await pilot.pause()
        assert type(app.screen).__name__ == "HomeScreen", app.screen
        print("esc navigation ok")

    print("SMOKE PASS")


if __name__ == "__main__":
    asyncio.run(main())
