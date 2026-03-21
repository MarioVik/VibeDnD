"""TTK theme configuration for the D&D character creator."""

import sys
import tkinter as tk
from tkinter import ttk

# Color palette - parchment/fantasy inspired
COLORS = {
    "bg": "#2b2b2b",
    "bg_light": "#3c3c3c",
    "bg_card": "#404040",
    "fg": "#ede2d0",
    "fg_dim": "#bfab94",
    "fg_bright": "#f8f0e0",
    "accent": "#c4956a",
    "accent_dark": "#8b6542",
    "positive": "#6aaa64",
    "negative": "#c9534a",
    "border": "#555555",
    "select_bg": "#5a4a3a",
    "select_fg": "#f5ead6",
}

if sys.platform == "darwin":
    _SANS = "Helvetica Neue"
    _MONO = "Menlo"
elif sys.platform == "win32":
    _SANS = "Segoe UI"
    _MONO = "Consolas"
else:
    _SANS = "DejaVu Sans"
    _MONO = "DejaVu Sans Mono"

FONTS = {
    "heading": (_SANS, 18, "bold"),
    "subheading": (_SANS, 13, "bold"),
    "body": (_SANS, 11),
    "body_small": (_SANS, 10),
    "mono": (_MONO, 11),
    "stat": (_SANS, 15, "bold"),
    "stat_mod": (_SANS, 12),
}


def apply_theme(root: tk.Tk):
    """Apply the dark parchment theme to the application."""
    style = ttk.Style(root)
    style.theme_use("clam")

    # General
    style.configure(
        ".", background=COLORS["bg"], foreground=COLORS["fg"], font=FONTS["body"]
    )

    # Frames
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Card.TFrame", background=COLORS["bg_card"])

    # Labels
    style.configure(
        "TLabel", background=COLORS["bg"], foreground=COLORS["fg"], font=FONTS["body"]
    )
    style.configure(
        "Heading.TLabel", font=FONTS["heading"], foreground=COLORS["accent"]
    )
    style.configure(
        "Subheading.TLabel", font=FONTS["subheading"], foreground=COLORS["fg_bright"]
    )
    style.configure("Dim.TLabel", foreground=COLORS["fg_dim"])
    style.configure("Stat.TLabel", font=FONTS["stat"], foreground=COLORS["fg_bright"])
    style.configure("StatMod.TLabel", font=FONTS["stat_mod"])
    style.configure("Positive.TLabel", foreground=COLORS["positive"])
    style.configure("Negative.TLabel", foreground=COLORS["negative"])
    style.configure(
        "Card.TLabel", background=COLORS["bg_card"], foreground=COLORS["fg"]
    )
    style.configure(
        "CardHeading.TLabel",
        background=COLORS["bg_card"],
        foreground=COLORS["accent"],
        font=FONTS["subheading"],
    )

    # LabelFrame
    style.configure("TLabelframe", background=COLORS["bg"], foreground=COLORS["fg"])
    style.configure(
        "TLabelframe.Label",
        background=COLORS["bg"],
        foreground=COLORS["accent"],
        font=FONTS["subheading"],
    )
    style.configure("Card.TLabelframe", background=COLORS["bg_card"])
    style.configure(
        "Card.TLabelframe.Label",
        background=COLORS["bg_card"],
        foreground=COLORS["accent"],
        font=FONTS["subheading"],
    )

    # Notebook
    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=COLORS["bg_light"],
        foreground=COLORS["fg_dim"],
        padding=[14, 7],
        font=FONTS["body"],
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLORS["bg_card"])],
        foreground=[("selected", COLORS["accent"])],
    )

    # Buttons
    style.configure(
        "TButton",
        background=COLORS["accent_dark"],
        foreground=COLORS["fg_bright"],
        padding=[12, 6],
        font=FONTS["body"],
    )
    style.map(
        "TButton",
        background=[("active", COLORS["accent"]), ("disabled", COLORS["bg_light"])],
        foreground=[("disabled", COLORS["fg_dim"])],
    )

    style.configure(
        "Accent.TButton",
        background=COLORS["accent"],
        foreground=COLORS["fg_bright"],
        font=FONTS["body"],
    )
    style.map("Accent.TButton", background=[("active", COLORS["accent_dark"])])

    # Radiobuttons and Checkbuttons
    style.configure(
        "TRadiobutton",
        background=COLORS["bg"],
        foreground=COLORS["fg"],
        font=FONTS["body"],
    )
    style.configure(
        "Card.TRadiobutton", background=COLORS["bg_card"], foreground=COLORS["fg"]
    )
    style.configure(
        "TCheckbutton",
        background=COLORS["bg"],
        foreground=COLORS["fg"],
        font=FONTS["body"],
    )
    style.configure(
        "Card.TCheckbutton", background=COLORS["bg_card"], foreground=COLORS["fg"]
    )

    # Combobox
    style.configure(
        "TCombobox",
        fieldbackground=COLORS["bg_light"],
        foreground=COLORS["fg"],
        selectbackground=COLORS["select_bg"],
        selectforeground=COLORS["select_fg"],
    )
    style.map("TCombobox", fieldbackground=[("readonly", COLORS["bg_light"])])

    # Entry
    style.configure(
        "TEntry", fieldbackground=COLORS["bg_light"], foreground=COLORS["fg"]
    )

    # Spinbox
    style.configure(
        "TSpinbox",
        fieldbackground=COLORS["bg_light"],
        foreground=COLORS["fg"],
        arrowcolor=COLORS["fg"],
    )

    # Treeview
    style.configure(
        "Treeview",
        background=COLORS["bg_light"],
        foreground=COLORS["fg"],
        fieldbackground=COLORS["bg_light"],
        font=FONTS["body"],
    )
    style.configure(
        "Treeview.Heading",
        background=COLORS["bg_card"],
        foreground=COLORS["accent"],
        font=FONTS["subheading"],
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS["select_bg"])],
        foreground=[("selected", COLORS["select_fg"])],
    )

    # Scrollbar – fully themed so every scrollbar is consistently dark
    style.configure(
        "TScrollbar",
        background=COLORS["bg_light"],
        troughcolor=COLORS["bg"],
        bordercolor=COLORS["bg"],
        arrowcolor=COLORS["fg_dim"],
        lightcolor=COLORS["bg_light"],
        darkcolor=COLORS["bg"],
        gripcount=0,
    )
    style.map(
        "TScrollbar",
        background=[
            ("active", COLORS["accent_dark"]),
            ("pressed", COLORS["accent_dark"]),
            ("disabled", COLORS["bg"]),
        ],
        arrowcolor=[
            ("active", COLORS["fg_bright"]),
            ("pressed", COLORS["fg_bright"]),
            ("disabled", COLORS["fg_dim"]),
        ],
    )
    # Ensure vertical/horizontal sub-styles also pick up the dark colours
    for orient in ("Vertical", "Horizontal"):
        style.configure(
            f"{orient}.TScrollbar",
            background=COLORS["bg_light"],
            troughcolor=COLORS["bg"],
            bordercolor=COLORS["bg"],
            arrowcolor=COLORS["fg_dim"],
            lightcolor=COLORS["bg_light"],
            darkcolor=COLORS["bg"],
            gripcount=0,
        )
        style.map(
            f"{orient}.TScrollbar",
            background=[
                ("active", COLORS["accent_dark"]),
                ("pressed", COLORS["accent_dark"]),
                ("disabled", COLORS["bg"]),
            ],
            arrowcolor=[
                ("active", COLORS["fg_bright"]),
                ("pressed", COLORS["fg_bright"]),
                ("disabled", COLORS["fg_dim"]),
            ],
        )

    # Separator
    style.configure("TSeparator", background=COLORS["border"])

    # PanedWindow
    style.configure("TPanedwindow", background=COLORS["border"])

    # Progressbar (for point buy budget)
    style.configure(
        "TProgressbar", background=COLORS["accent"], troughcolor=COLORS["bg_light"]
    )

    # Root window
    root.configure(bg=COLORS["bg"])

    # Override native Tk scrollbar defaults (affects any tk.Scrollbar or
    # internal scrollbar rendering that bypasses ttk theming)
    root.option_add("*Scrollbar.background", COLORS["bg_light"])
    root.option_add("*Scrollbar.troughColor", COLORS["bg"])
    root.option_add("*Scrollbar.activeBackground", COLORS["accent_dark"])
    root.option_add("*Scrollbar.highlightBackground", COLORS["bg"])
    root.option_add("*Scrollbar.highlightColor", COLORS["bg"])
    root.option_add("*Scrollbar.borderWidth", 0)
