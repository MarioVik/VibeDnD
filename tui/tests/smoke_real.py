"""Headless drive of the TUI against real saved characters.

Read-only: navigates every character's sheet and all tabs but presses no
mutating keys, so no save file is touched.

Run from the repo root:  uv run python -m tui.tests.smoke_real
"""
import asyncio

from tui.app import VibeDnDTUI


async def main() -> None:
    app = VibeDnDTUI(demo=False)
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        home = app.screen
        assert type(home).__name__ == "HomeScreen", home
        count = home.query_one("#roster").option_count
        assert count > 0, "no real characters loaded"
        print(f"roster: {count} characters")

        if count > 1:                   # vim roster motion
            await pilot.press("j")
            await pilot.pause()
            assert home.query_one("#roster").highlighted == 1
            await pilot.press("g")
            await pilot.pause()
            assert home.query_one("#roster").highlighted == 0
            print("roster j/g motions ok")

        for i in range(count):
            home.query_one("#roster").highlighted = i
            await pilot.pause()
            await pilot.press("enter")
            await pilot.pause()
            sheet = app.screen
            assert type(sheet).__name__ == "SheetScreen", sheet
            for key in "23451":
                await pilot.press(key)
                await pilot.pause()
            print(f"  ok: {sheet.view.name} ({sheet.view.class_line}) "
                  f"HP {sheet.view.current_hp}/{sheet.view.max_hp}")
            await pilot.press("escape")
            await pilot.pause()

    print("REAL SMOKE PASS")


if __name__ == "__main__":
    asyncio.run(main())
