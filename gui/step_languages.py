"""Step 4: Language selection."""

import tkinter as tk
from tkinter import ttk

from gui.base_step import WizardStep
from gui.widgets import ScrollableFrame, Chip, GradientHeader, SectionHeader, CardFrame
from gui.theme import COLORS, FONTS, SPACING
from models.language_utils import (
    STANDARD_LANGUAGES,
    RARE_LANGUAGES,
    compute_language_sources,
)

CARD_CHECK_STYLE = "Card.TCheckbutton"
SOURCE_LABEL_FONT = (FONTS["body_small"][0], FONTS["body_small"][1], "italic")


class LanguagesStep(WizardStep):
    tab_title = "Languages"

    def __init__(self, parent, character, game_data):
        self._lang_vars: dict[str, tk.BooleanVar] = {}
        self._lang_cbs: dict[str, ttk.Checkbutton] = {}
        super().__init__(parent, character, game_data)

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        # ── Hero header ─────────────────────────────────────────
        hero = GradientHeader(self.frame, min_height=60)
        hero.grid(row=0, column=0, sticky="ew")

        hero_inner = tk.Frame(hero.inner, bg=COLORS["bg_hero"])
        hero_inner.pack(fill=tk.X, padx=SPACING["card_pad"], pady=(SPACING["xl"], 0))

        tk.Label(
            hero_inner,
            text="Languages",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        tk.Label(
            hero.inner,
            text="All characters speak Common plus two languages of their choice.",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xs"], SPACING["xl"]))

        # ── Scrollable content ──────────────────────────────────
        scroll = ScrollableFrame(self.frame)
        scroll.grid(row=1, column=0, sticky="nsew")
        inner = scroll.inner

        # Fixed languages section
        SectionHeader(inner, text="Fixed Languages").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )

        fixed_card = CardFrame(inner, pad=SPACING["lg"])
        fixed_card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        self.sources_frame = tk.Frame(fixed_card.inner, bg=COLORS["bg_surface"])
        self.sources_frame.pack(fill=tk.X, anchor="w")

        # Choose section
        self.choose_section_header = SectionHeader(inner, text="Choose Languages")
        self.choose_section_header.pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )
        self.counter_label = self._install_inline_counter(self.choose_section_header)

        # Standard languages
        std_card = CardFrame(inner, pad=SPACING["lg"])
        std_card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))

        tk.Label(
            std_card.inner,
            text="STANDARD LANGUAGES",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", pady=(0, SPACING["xs"]))

        self.standard_frame = tk.Frame(std_card.inner, bg=COLORS["bg_surface"])
        self.standard_frame.pack(fill=tk.X, anchor="w")

        # Rare languages (hidden until Linguist unlocks it)
        self.rare_card = CardFrame(inner, pad=SPACING["lg"])
        # Not packed by default

        tk.Label(
            self.rare_card.inner,
            text="RARE LANGUAGES",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        ).pack(anchor="w", pady=(0, SPACING["xs"]))

        self.rare_hint = tk.Label(
            self.rare_card.inner,
            text="Unlocked by the Linguist feat.",
            font=FONTS["body_small"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"],
        )
        self.rare_hint.pack(anchor="w", pady=(0, SPACING["xs"]))
        self.rare_frame = tk.Frame(self.rare_card.inner, bg=COLORS["bg_surface"])
        self.rare_frame.pack(fill=tk.X, anchor="w")

    # ── Lifecycle ────────────────────────────────────────────────

    def on_enter(self):
        """Rebuild the UI based on current character choices."""
        sources = compute_language_sources(self.character)
        auto = sources["auto"]
        free_count = sources["free_count"]
        can_rare = sources["can_choose_rare"]

        available = set(STANDARD_LANGUAGES)
        if can_rare:
            available |= set(RARE_LANGUAGES)
        available -= set(auto)
        self.character.chosen_languages = [
            l for l in self.character.chosen_languages if l in available
        ]

        self._rebuild_sources_info(auto)
        self._rebuild_language_list(auto, free_count, can_rare)
        self._update_counter(free_count)

    def _install_inline_counter(self, header: SectionHeader) -> tk.Label:
        counter = tk.Label(
            header,
            text="(0 / 0)",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
        )
        header._line.pack_forget()
        counter.pack(side=tk.LEFT, padx=(0, 12))
        header._line.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=1)
        return counter

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

        _bg = COLORS["bg_surface"]
        for lang, source in entries:
            row = tk.Frame(self.sources_frame, bg=_bg)
            row.pack(fill=tk.X, anchor="w", pady=1)
            tk.Label(
                row,
                text="\u2022",
                font=FONTS["body_bold"],
                fg=COLORS["fg"],
                bg=_bg,
            ).pack(side=tk.LEFT, padx=(0, SPACING["sm"]))
            Chip(row, text=lang, style="default").pack(
                side=tk.LEFT,
                padx=(0, SPACING["sm"]),
                pady=2,
            )
            tk.Label(
                row,
                text=f"({source})",
                font=SOURCE_LABEL_FONT,
                fg=COLORS["fg_dim"],
                bg=_bg,
            ).pack(side=tk.LEFT)

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
                style=CARD_CHECK_STYLE,
                command=lambda l=lang, v=var: self._on_toggle(l, v, free_count),
            )
            cb.pack(anchor="w", pady=1)
            self._lang_vars[lang] = var
            self._lang_cbs[lang] = cb

        for lang in STANDARD_LANGUAGES:
            if lang not in auto_set:
                _add_lang(self.standard_frame, lang)

        if can_rare:
            self.rare_card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))
            for lang in RARE_LANGUAGES:
                _add_lang(self.rare_frame, lang)
        else:
            self.rare_card.pack_forget()

        self._enforce_capacity(free_count)

    def _on_toggle(self, lang: str, var: tk.BooleanVar, free_count: int):
        chosen = self.character.chosen_languages
        if var.get():
            if len(chosen) >= free_count:
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
            fg=(
                COLORS["positive"] if chosen_count == free_count else COLORS["fg_dim"]
            ),
        )

    def _flash_counter(self):
        """Briefly highlight the counter to signal capacity reached."""
        self.counter_label.configure(fg=COLORS["accent"])
        self.frame.after(
            600, lambda: self._update_counter_from_state()
        )

    def _update_counter_from_state(self):
        sources = compute_language_sources(self.character)
        self._update_counter(sources["free_count"])

    # ── Validation ───────────────────────────────────────────────

    def is_valid(self) -> bool:
        sources = compute_language_sources(self.character)
        return len(self.character.chosen_languages) == sources["free_count"]
