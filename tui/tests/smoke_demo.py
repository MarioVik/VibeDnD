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
