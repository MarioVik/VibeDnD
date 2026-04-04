"""Step 9: Equipment selection."""

from decimal import Decimal
import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.widgets import GradientHeader, SectionHeader, CardFrame, ScrollableFrame
from gui.theme import COLORS, FONTS, SPACING
from gui.equipment_utils import extract_gp, gp_to_coins, strip_wealth

CARD_RADIO_STYLE = "Card.TRadiobutton"


class EquipmentStep(WizardStep):
    tab_title = "Equipment"

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
            text="Starting Equipment",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(side=tk.LEFT)

        tk.Label(
            hero.inner,
            text="Choose equipment from your class and background options.",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_hero"],
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xs"], SPACING["xl"]))

        # ── Scrollable content ──────────────────────────────────
        scroll = ScrollableFrame(self.frame)
        scroll.grid(row=1, column=0, sticky="nsew")
        inner = scroll.inner

        # Class equipment
        SectionHeader(inner, text="Class Equipment").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )
        self.class_equip_card = CardFrame(inner, pad=SPACING["lg"])
        self.class_equip_card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))
        self.class_equip_frame = self.class_equip_card.inner
        self.class_equip_var = tk.StringVar(value="")
        self.class_equip_var.trace_add("write", self._on_change)

        # Background equipment
        SectionHeader(inner, text="Background Equipment").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )
        self.bg_equip_card = CardFrame(inner, pad=SPACING["lg"])
        self.bg_equip_card.pack(fill=tk.X, padx=SPACING["lg"], pady=(0, SPACING["sm"]))
        self.bg_equip_frame = self.bg_equip_card.inner
        self.bg_equip_var = tk.StringVar(value="A")
        self.bg_equip_var.trace_add("write", self._on_change)

        # Combined summary
        SectionHeader(inner, text="Your Equipment").pack(
            fill=tk.X, padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"])
        )
        summary_card = CardFrame(inner, pad=SPACING["lg"])
        summary_card.pack(fill=tk.BOTH, expand=True, padx=SPACING["lg"], pady=(0, SPACING["lg"]))
        self.summary_text = tk.Text(
            summary_card.inner,
            wrap=tk.WORD,
            height=8,
            bg=COLORS["bg_surface"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            state=tk.DISABLED,
        )
        self.summary_text.pack(fill=tk.BOTH, expand=True)

    def on_enter(self):
        saved_class = self.character.equipment_choice_class
        saved_bg = self.character.equipment_choice_background
        self._populate_class_equipment()
        self._populate_bg_equipment()
        if saved_class:
            self.class_equip_var.set(saved_class)
        else:
            self.class_equip_var.set("")
        if saved_bg:
            self.bg_equip_var.set(saved_bg)
        self._update_summary()

    def _populate_class_equipment(self):
        for w in self.class_equip_frame.winfo_children():
            w.destroy()

        _bg = COLORS["bg_surface"]
        cls = self.character.character_class
        if not cls:
            tk.Label(
                self.class_equip_frame, text="No class selected",
                font=FONTS["body"], fg=COLORS["fg_dim"], bg=_bg,
            ).pack(anchor="w")
            return

        equip_options = cls.get("starting_equipment", [])
        if not equip_options:
            tk.Label(
                self.class_equip_frame, text="No equipment options available",
                font=FONTS["body"], fg=COLORS["fg_dim"], bg=_bg,
            ).pack(anchor="w")
            return

        tk.Label(
            self.class_equip_frame,
            text=f"{cls['name']} Starting Equipment:",
            font=FONTS["subheading"],
            fg=COLORS["fg"],
            bg=_bg,
        ).pack(anchor="w", pady=(0, SPACING["xs"]))

        for i, opt in enumerate(equip_options):
            if i > 0:
                tk.Label(
                    self.class_equip_frame,
                    text="or",
                    font=FONTS["body_small"],
                    fg=COLORS["fg_dim"],
                    bg=_bg,
                ).pack(anchor="w", padx=SPACING["2xl"])

            ttk.Radiobutton(
                self.class_equip_frame,
                text=f"({opt['option']}) {opt['items']}",
                variable=self.class_equip_var,
                value=opt["option"],
                style=CARD_RADIO_STYLE,
            ).pack(anchor="w", padx=SPACING["lg"], pady=2)

    def _populate_bg_equipment(self):
        for w in self.bg_equip_frame.winfo_children():
            w.destroy()

        _bg = COLORS["bg_surface"]
        bg = self.character.background
        if not bg:
            tk.Label(
                self.bg_equip_frame, text="No background selected",
                font=FONTS["body"], fg=COLORS["fg_dim"], bg=_bg,
            ).pack(anchor="w")
            return

        equip_options = bg.get("equipment", [])
        if not equip_options:
            tk.Label(
                self.bg_equip_frame, text="No equipment options available",
                font=FONTS["body"], fg=COLORS["fg_dim"], bg=_bg,
            ).pack(anchor="w")
            return

        tk.Label(
            self.bg_equip_frame,
            text=f"{bg['name']} Equipment:",
            font=FONTS["subheading"],
            fg=COLORS["fg"],
            bg=_bg,
        ).pack(anchor="w", pady=(0, SPACING["xs"]))

        for i, opt in enumerate(equip_options):
            if i > 0:
                tk.Label(
                    self.bg_equip_frame,
                    text="or",
                    font=FONTS["body_small"],
                    fg=COLORS["fg_dim"],
                    bg=_bg,
                ).pack(anchor="w", padx=SPACING["2xl"])

            ttk.Radiobutton(
                self.bg_equip_frame,
                text=f"({opt['option']}) {opt['items']}",
                variable=self.bg_equip_var,
                value=opt["option"],
                style=CARD_RADIO_STYLE,
            ).pack(anchor="w", padx=SPACING["lg"], pady=2)

        if equip_options:
            self.bg_equip_var.set(equip_options[0]["option"])

    def _on_change(self, *args):
        self.character.equipment_choice_class = self.class_equip_var.get()
        self.character.equipment_choice_background = self.bg_equip_var.get()
        self._update_summary()
        self.notify_change()

    def _update_summary(self):
        self.summary_text.configure(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)

        lines = []
        total_gp = Decimal("0")

        cls = self.character.character_class
        if cls:
            choice = self.class_equip_var.get()
            for opt in cls.get("starting_equipment", []):
                if opt["option"] == choice:
                    total_gp += extract_gp(opt["items"])
                    items_text = strip_wealth(opt["items"])
                    lines.append(f"From {cls['name']}:")
                    lines.append(f"  {items_text or '(No item bundle)'}")
                    lines.append("")
                    break

        bg = self.character.background
        if bg:
            choice = self.bg_equip_var.get()
            for opt in bg.get("equipment", []):
                if opt["option"] == choice:
                    total_gp += extract_gp(opt["items"])
                    items_text = strip_wealth(opt["items"])
                    lines.append(f"From {bg['name']}:")
                    lines.append(f"  {items_text or '(No item bundle)'}")
                    lines.append("")
                    break

        gp, sp, cp = gp_to_coins(total_gp)
        lines.append("Wealth:")
        lines.append(f"  Gold: {gp} gp")
        lines.append(f"  Silver: {sp} sp")
        lines.append(f"  Copper: {cp} cp")

        self.summary_text.insert(
            "1.0", "\n".join(lines) if lines else "No equipment selected"
        )
        self.summary_text.configure(state=tk.DISABLED)

    def is_valid(self) -> bool:
        cls = self.character.character_class or {}
        options = {
            str(opt.get("option", "")).strip()
            for opt in cls.get("starting_equipment", [])
            if str(opt.get("option", "")).strip()
        }
        if options:
            return str(self.character.equipment_choice_class or "").strip() in options
        return True
