"""Step 7: Equipment selection."""

from decimal import Decimal
import tkinter as tk
from tkinter import ttk
from gui.base_step import WizardStep
from gui.theme import COLORS, FONTS
from gui.equipment_utils import extract_gp, gp_to_coins, strip_wealth


class EquipmentStep(WizardStep):
    tab_title = "Equipment"

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)

        ttk.Label(self.frame, text="Starting Equipment", style="Heading.TLabel").pack(
            anchor="w", padx=12, pady=(12, 4)
        )
        ttk.Label(
            self.frame,
            text="Choose equipment from your class and background options.",
            style="Dim.TLabel",
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # Class equipment
        self.class_equip_frame = ttk.LabelFrame(self.frame, text="Class Equipment")
        self.class_equip_frame.pack(fill=tk.X, padx=12, pady=4)
        self.class_equip_var = tk.StringVar(value="A")
        self.class_equip_var.trace_add("write", self._on_change)

        # Background equipment
        self.bg_equip_frame = ttk.LabelFrame(self.frame, text="Background Equipment")
        self.bg_equip_frame.pack(fill=tk.X, padx=12, pady=4)
        self.bg_equip_var = tk.StringVar(value="A")
        self.bg_equip_var.trace_add("write", self._on_change)

        # Combined summary
        self.summary_frame = ttk.LabelFrame(self.frame, text="Your Equipment")
        self.summary_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(8, 12))
        self.summary_text = tk.Text(
            self.summary_frame,
            wrap=tk.WORD,
            height=8,
            bg=COLORS["bg_light"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            state=tk.DISABLED,
        )
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def on_enter(self):
        # Snapshot choices before populate resets them to first option
        saved_class = self.character.equipment_choice_class
        saved_bg = self.character.equipment_choice_background
        self._populate_class_equipment()
        self._populate_bg_equipment()
        # Restore saved equipment choices
        if saved_class:
            self.class_equip_var.set(saved_class)
        if saved_bg:
            self.bg_equip_var.set(saved_bg)
        self._update_summary()

    def _populate_class_equipment(self):
        for w in self.class_equip_frame.winfo_children():
            w.destroy()

        cls = self.character.character_class
        if not cls:
            ttk.Label(
                self.class_equip_frame, text="No class selected", style="Dim.TLabel"
            ).pack(padx=8, pady=4)
            return

        equip_options = cls.get("starting_equipment", [])
        if not equip_options:
            ttk.Label(
                self.class_equip_frame,
                text="No equipment options available",
                style="Dim.TLabel",
            ).pack(padx=8, pady=4)
            return

        ttk.Label(
            self.class_equip_frame,
            text=f"{cls['name']} Starting Equipment:",
            style="Subheading.TLabel",
        ).pack(anchor="w", padx=8, pady=(4, 2))

        for i, opt in enumerate(equip_options):
            if i > 0:
                ttk.Label(
                    self.class_equip_frame,
                    text="   or",
                    foreground=COLORS["fg_dim"],
                    font=("Segoe UI", 9, "italic"),
                ).pack(anchor="w", padx=32)

            ttk.Radiobutton(
                self.class_equip_frame,
                text=f"({opt['option']}) {opt['items']}",
                variable=self.class_equip_var,
                value=opt["option"],
            ).pack(anchor="w", padx=16, pady=2)

        if equip_options:
            self.class_equip_var.set(equip_options[0]["option"])

    def _populate_bg_equipment(self):
        for w in self.bg_equip_frame.winfo_children():
            w.destroy()

        bg = self.character.background
        if not bg:
            ttk.Label(
                self.bg_equip_frame, text="No background selected", style="Dim.TLabel"
            ).pack(padx=8, pady=4)
            return

        equip_options = bg.get("equipment", [])
        if not equip_options:
            ttk.Label(
                self.bg_equip_frame,
                text="No equipment options available",
                style="Dim.TLabel",
            ).pack(padx=8, pady=4)
            return

        ttk.Label(
            self.bg_equip_frame,
            text=f"{bg['name']} Equipment:",
            style="Subheading.TLabel",
        ).pack(anchor="w", padx=8, pady=(4, 2))

        for i, opt in enumerate(equip_options):
            if i > 0:
                ttk.Label(
                    self.bg_equip_frame,
                    text="   or",
                    foreground=COLORS["fg_dim"],
                    font=("Segoe UI", 9, "italic"),
                ).pack(anchor="w", padx=32)

            ttk.Radiobutton(
                self.bg_equip_frame,
                text=f"({opt['option']}) {opt['items']}",
                variable=self.bg_equip_var,
                value=opt["option"],
            ).pack(anchor="w", padx=16, pady=2)

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

        # Class equipment
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

        # Background equipment
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
