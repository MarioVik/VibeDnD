"""Step 4: Language selection."""

import tkinter as tk
from tkinter import ttk

from gui.base_step import WizardStep
from gui.widgets import ScrollableFrame, WrappingLabel, Chip
from gui.theme import COLORS, FONTS
from models.language_utils import (
    STANDARD_LANGUAGES,
    RARE_LANGUAGES,
    compute_language_sources,
)


class LanguagesStep(WizardStep):
    tab_title = "Languages"

    def __init__(self, parent, character, game_data):
        self._lang_vars: dict[str, tk.BooleanVar] = {}
        self._lang_cbs: dict[str, ttk.Checkbutton] = {}
        super().__init__(parent, character, game_data)

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # ── Top: description + fixed languages ───────────────────
        top = ttk.Frame(self.frame)
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 0))
        top.columnconfigure(0, weight=1)

        ttk.Label(top, text="Languages", style="Heading.TLabel").pack(
            anchor="w", pady=(0, 4)
        )
        WrappingLabel(
            top,
            text=(
                "All characters speak Common plus two languages of their choice. "
                "Some classes grant additional fixed languages."
            ),
            foreground=COLORS["fg_dim"],
        ).pack(fill=tk.X, anchor="w", pady=(0, 12))

        ttk.Label(top, text="FIXED LANGUAGES", style="Dim.TLabel").pack(
            anchor="w", pady=(0, 4)
        )
        self.auto_chips_frame = tk.Frame(top, bg=COLORS["bg_surface"])
        self.auto_chips_frame.pack(fill=tk.X, anchor="w", pady=(0, 4))

        self.sources_frame = ttk.Frame(top)
        self.sources_frame.pack(fill=tk.X, anchor="w", pady=(0, 8))

        ttk.Separator(top, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(4, 0))

        # ── Bottom: scrollable choose section ────────────────────
        scroll = ScrollableFrame(self.frame)
        scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 12))
        inner = scroll.inner

        # Counter header
        header = ttk.Frame(inner)
        header.pack(fill=tk.X, anchor="w", pady=(0, 8))
        self.choose_label = ttk.Label(
            header, text="Choose Languages", style="Subheading.TLabel"
        )
        self.choose_label.pack(side=tk.LEFT)
        self.counter_label = ttk.Label(header, text="(0 / 2)", style="Dim.TLabel")
        self.counter_label.pack(side=tk.LEFT, padx=(8, 0))

        # Standard languages section
        ttk.Label(inner, text="STANDARD LANGUAGES", style="Dim.TLabel").pack(
            anchor="w", pady=(0, 4)
        )
        self.standard_frame = ttk.Frame(inner)
        self.standard_frame.pack(fill=tk.X, anchor="w", pady=(0, 12))

        # Rare languages section (hidden until Linguist unlocks it)
        self.rare_outer = ttk.Frame(inner)
        ttk.Label(self.rare_outer, text="RARE LANGUAGES", style="Dim.TLabel").pack(
            anchor="w", pady=(0, 4)
        )
        self.rare_hint = WrappingLabel(
            self.rare_outer,
            text="Unlocked by the Linguist feat.",
            foreground=COLORS["fg_dim"],
        )
        self.rare_hint.pack(fill=tk.X, anchor="w", pady=(0, 4))
        self.rare_frame = ttk.Frame(self.rare_outer)
        self.rare_frame.pack(fill=tk.X, anchor="w", pady=(0, 12))

        # Selected chips
        ttk.Separator(inner, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Label(inner, text="SELECTED", style="Dim.TLabel").pack(
            anchor="w", pady=(0, 4)
        )
        self.selected_frame = tk.Frame(inner, bg=COLORS["bg_surface"])
        self.selected_frame.pack(fill=tk.X, anchor="w")

    # ── Lifecycle ────────────────────────────────────────────────

    def on_enter(self):
        """Rebuild the UI based on current character choices."""
        sources = compute_language_sources(self.character)
        auto = sources["auto"]
        free_count = sources["free_count"]
        can_rare = sources["can_choose_rare"]

        # Sanitise chosen_languages: remove any that are now in auto (e.g.
        # class was changed) or no longer available.
        available = set(STANDARD_LANGUAGES)
        if can_rare:
            available |= set(RARE_LANGUAGES)
        available -= set(auto)
        self.character.chosen_languages = [
            l for l in self.character.chosen_languages if l in available
        ]

        self._rebuild_auto_chips(auto)
        self._rebuild_sources_info(auto)
        self._rebuild_language_list(auto, free_count, can_rare)
        self._update_counter(free_count)
        self._update_selected_chips()

    def _rebuild_auto_chips(self, auto: list[str]):
        for w in self.auto_chips_frame.winfo_children():
            w.destroy()
        for lang in auto:
            Chip(self.auto_chips_frame, text=lang, style="default").pack(
                side=tk.LEFT, padx=(0, 4), pady=2
            )

    def _rebuild_sources_info(self, auto: list[str]):
        for w in self.sources_frame.winfo_children():
            w.destroy()

        class_slug = ""
        if self.character.character_class:
            class_slug = self.character.character_class.get("slug", "")

        entries = [("Common", "Base character creation")]
        if class_slug == "druid":
            entries.append(("Druidic", "Druid — Druidic (level 1)"))
        elif class_slug == "rogue":
            entries.append(("Thieves' Cant", "Rogue — Thieves' Cant (level 1)"))

        for lang, source in entries:
            row = ttk.Frame(self.sources_frame)
            row.pack(fill=tk.X, anchor="w", pady=1)
            ttk.Label(row, text=f"• {lang}:", font=FONTS["body_bold"]).pack(
                side=tk.LEFT
            )
            ttk.Label(row, text=f" {source}", style="Dim.TLabel").pack(side=tk.LEFT)

    def _rebuild_language_list(
        self, auto: list[str], free_count: int, can_rare: bool
    ):
        """Rebuild checkbutton lists for Standard and Rare languages."""
        self._lang_vars.clear()
        self._lang_cbs.clear()

        for w in self.standard_frame.winfo_children():
            w.destroy()
        for w in self.rare_frame.winfo_children():
            w.destroy()

        auto_set = set(auto)
        chosen_set = set(self.character.chosen_languages)

        def _add_lang(parent, lang: str):
            var = tk.BooleanVar(value=lang in chosen_set)
            disabled = lang in auto_set
            state = "disabled" if disabled else "normal"
            cb = ttk.Checkbutton(
                parent,
                text=lang,
                variable=var,
                state=state,
                command=lambda l=lang, v=var: self._on_toggle(l, v, free_count),
            )
            cb.pack(anchor="w", pady=1)
            self._lang_vars[lang] = var
            self._lang_cbs[lang] = cb

        for lang in STANDARD_LANGUAGES:
            if lang not in auto_set:
                _add_lang(self.standard_frame, lang)

        if can_rare:
            self.rare_outer.pack(fill=tk.X, anchor="w", before=self.selected_frame)
            for lang in RARE_LANGUAGES:
                _add_lang(self.rare_frame, lang)
        else:
            self.rare_outer.pack_forget()

        self._enforce_capacity(free_count)

    def _on_toggle(self, lang: str, var: tk.BooleanVar, free_count: int):
        chosen = self.character.chosen_languages
        if var.get():
            if len(chosen) >= free_count:
                # Already at capacity — block this selection
                var.set(False)
                self._flash_counter()
                return
            if lang not in chosen:
                chosen.append(lang)
        else:
            if lang in chosen:
                chosen.remove(lang)

        self._enforce_capacity(free_count)
        self._update_counter(free_count)
        self._update_selected_chips()
        self.notify_change()

    def _enforce_capacity(self, free_count: int):
        """Disable unchosen checkbuttons when at capacity."""
        chosen = self.character.chosen_languages
        at_cap = len(chosen) >= free_count
        for lang, cb in self._lang_cbs.items():
            var = self._lang_vars[lang]
            if not var.get():
                cb.configure(state="disabled" if at_cap else "normal")

    def _update_counter(self, free_count: int):
        chosen_count = len(self.character.chosen_languages)
        self.counter_label.configure(
            text=f"({chosen_count} / {free_count})",
            foreground=(
                COLORS["positive"] if chosen_count == free_count else COLORS["fg_dim"]
            ),
        )

    def _flash_counter(self):
        """Briefly highlight the counter to signal capacity reached."""
        self.counter_label.configure(foreground=COLORS["accent"])
        self.frame.after(
            600, lambda: self._update_counter_from_state()
        )

    def _update_counter_from_state(self):
        sources = compute_language_sources(self.character)
        self._update_counter(sources["free_count"])

    def _update_selected_chips(self):
        for w in self.selected_frame.winfo_children():
            w.destroy()
        chosen = self.character.chosen_languages
        if not chosen:
            ttk.Label(
                self.selected_frame, text="None chosen yet.", style="Dim.TLabel"
            ).pack(anchor="w")
        else:
            for lang in chosen:
                Chip(self.selected_frame, text=lang, style="accent").pack(
                    side=tk.LEFT, padx=(0, 4), pady=2
                )

    # ── Validation ───────────────────────────────────────────────

    def is_valid(self) -> bool:
        sources = compute_language_sources(self.character)
        return len(self.character.chosen_languages) == sources["free_count"]
