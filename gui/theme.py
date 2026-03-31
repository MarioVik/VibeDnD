"""TTK theme configuration — Mythic Modern dark design system."""

import sys
import tkinter as tk
from tkinter import ttk


def _clear_button_focus(event):
    widget = getattr(event, "widget", None)
    if widget is None:
        return

    def _after_idle():
        try:
            if not widget.winfo_exists():
                return
            if widget.focus_displayof() is not widget:
                return
            widget.winfo_toplevel().focus_set()
        except tk.TclError:
            pass

    try:
        widget.after_idle(_after_idle)
    except tk.TclError:
        pass


def _defocus_button_after_activate(event):
    widget = getattr(event, "widget", event)
    if not hasattr(widget, "after_idle") or not hasattr(widget, "winfo_toplevel"):
        return

    try:
        widget.after_idle(lambda: widget.winfo_toplevel().focus_set())
    except (tk.TclError, AttributeError):
        pass

# ---------------------------------------------------------------------------
# Color palette — Mythic Modern (crimson / charcoal)
# ---------------------------------------------------------------------------
COLORS = {
    # Surface hierarchy (darkest → lightest)
    "bg_deepest": "#0e0e0e",
    "bg": "#131313",
    "bg_surface": "#1b1b1b",
    "bg_container": "#20201f",
    "bg_hero": "#171717",
    "bg_high": "#2a2a2a",
    "bg_highest": "#353535",
    # Primary accent — crimson
    "accent": "#9B1B30",
    "accent_text": "#ffb3b5",
    "accent_on": "#680018",
    # Secondary accent — gold
    "gold": "#e9c176",
    "gold_dark": "#604403",
    "gold_on_dark": "#dab36a",
    # Foreground / text
    "fg": "#e5e2e1",
    "fg_dim": "#e0bfbf",
    # Borders
    "outline": "#a78a8a",
    "outline_dim": "#584141",
    # Semantic
    "positive": "#6aaa64",
    "negative": "#ffb4ab",
    "error_bg": "#93000a",
    # Selection
    "select_bg": "#353535",
    "select_fg": "#ffb3b5",
    # Pre-blended transparency colors (Tkinter has no opacity)
    "border_subtle":    "#231f1f",   # outline_dim at 10% on bg_surface
    "border_medium":    "#2d2525",   # outline_dim at 20% on bg_surface
    "badge_glass":      "#303030",   # bg_highest at 80% on bg_surface
    "badge_glass_dim":  "#252525",   # bg_highest at 40% on bg
    "border_subtle_bg": "#191616",   # outline_dim at 10% on bg
    "border_medium_bg": "#201c1c",   # outline_dim at 20% on bg
    # Tile grid
    "tile_bg": "#1e1e1e",
    "tile_border": "#2d2525",
    "tile_hover": "#2a2222",
    "tile_selected_border": "#9B1B30",
    # Sidebar
    "sidebar_locked_fg": "#5a4a4a",
    "sidebar_completed_fg": "#8a7a7a",
    "sidebar_indicator_active_outer": "#9B1B30",
    "sidebar_indicator_active_inner": "#ffb3b5",
    "sidebar_indicator_completed_outer": "#584141",
    "sidebar_indicator_completed_inner": "#8a7a7a",
    "sidebar_indicator_locked_outer": "#231f1f",
    "sidebar_indicator_locked_inner": "#3a2d2d",
    # ----- backward-compat aliases (old code still referencing these) -----
    "bg_light": "#2a2a2a",      # → bg_high
    "bg_card": "#1b1b1b",       # → bg_surface
    "fg_bright": "#e5e2e1",     # → fg
    "accent_dark": "#9B1B30",   # → accent
    "border": "#584141",        # → outline_dim
}

# ---------------------------------------------------------------------------
# Spacing constants
# ---------------------------------------------------------------------------
SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "2xl": 32,
    "card_pad": 20,
    "section_gap": 16,
    "card_gap": 8,
    "tile_gap": 12,
    "tile_pad": 12,
}

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
if sys.platform == "darwin":
    _SANS = "Helvetica Neue"
    _SERIF = "Georgia"
    _MONO = "Menlo"
elif sys.platform == "win32":
    _SANS = "Segoe UI"
    _SERIF = "Georgia"
    _MONO = "Consolas"
else:
    _SANS = "DejaVu Sans"
    _SERIF = "DejaVu Serif"
    _MONO = "DejaVu Sans Mono"

FONTS = {
    # Serif headings (Newsreader equivalent)
    "heading_serif_lg": (_SERIF, 28, "bold italic"),
    "heading_serif": (_SERIF, 20, "italic"),
    "heading_serif_sm": (_SERIF, 14, "italic"),
    "hero_eyebrow": (_SERIF, 14, "italic"),
    "hero_title": (_SERIF, 48, "bold"),
    "hero_title_italic": (_SERIF, 56, "bold italic"),
    "archive_title": (_SERIF, 28),
    "archive_back": (_SERIF, 24),
    "card_title_lg": (_SERIF, 22),
    # Sans headings (legacy)
    "heading": (_SANS, 18, "bold"),
    "subheading": (_SANS, 13, "bold"),
    # Body
    "body": (_SANS, 11),
    "body_small": (_SANS, 10),
    "body_large": (_SANS, 13),
    "body_bold": (_SANS, 11, "bold"),
    # Labels — small uppercase style
    "label_upper": (_SANS, 9),
    "label_upper_bold": (_SANS, 9, "bold"),
    "label_tiny": (_SANS, 8, "bold"),
    # Stats
    "stat": (_SANS, 15, "bold"),
    "stat_large": (_SERIF, 28, "bold"),
    "stat_mod": (_SANS, 12),
    # Monospace
    "mono": (_MONO, 11),
    # Tile grid
    "tile_name": (_SERIF, 13, "bold"),
    "tile_desc": (_SANS, 9),
    "tile_trait": (_SANS, 9, "bold"),
    # Sidebar / nav
    "step_counter": (_SANS, 10, "bold"),
    "nav_subtitle": (_SANS, 8),
}


def apply_theme(root: tk.Tk):
    """Apply the Mythic Modern dark theme to the application."""
    style = ttk.Style(root)
    style.theme_use("clam")

    # Prevent buttons from taking focus by default so macOS/Tk doesn't draw
    # the bright focus ring after mouse clicks.
    root.option_add("*Button.takeFocus", 0)
    root.option_add("*Button.takefocus", 0)
    root.option_add("*TButton.takeFocus", 0)
    root.option_add("*TButton.takefocus", 0)
    if not getattr(root, "_button_focus_cleanup_installed", False):
        root.bind_class("Button", "<FocusIn>", _clear_button_focus, add="+")
        root.bind_class("TButton", "<FocusIn>", _clear_button_focus, add="+")
        root.bind_class(
            "Button", "<ButtonRelease-1>", _defocus_button_after_activate, add="+"
        )
        root.bind_class(
            "TButton", "<ButtonRelease-1>", _defocus_button_after_activate, add="+"
        )
        root._button_focus_cleanup_installed = True

    # ------------------------------------------------------------------
    # General defaults
    # ------------------------------------------------------------------
    style.configure(
        ".",
        background=COLORS["bg"],
        foreground=COLORS["fg"],
        font=FONTS["body"],
    )

    # ------------------------------------------------------------------
    # Frames
    # ------------------------------------------------------------------
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Card.TFrame", background=COLORS["bg_surface"])
    style.configure("Surface.TFrame", background=COLORS["bg_surface"])
    style.configure("Container.TFrame", background=COLORS["bg_container"])
    style.configure("High.TFrame", background=COLORS["bg_high"])
    style.configure("Highest.TFrame", background=COLORS["bg_highest"])
    style.configure("Sidebar.TFrame", background=COLORS["bg_surface"])
    style.configure("Accent.TFrame", background=COLORS["accent"])

    # ------------------------------------------------------------------
    # Labels
    # ------------------------------------------------------------------
    style.configure(
        "TLabel",
        background=COLORS["bg"],
        foreground=COLORS["fg"],
        font=FONTS["body"],
    )
    style.configure(
        "Heading.TLabel",
        font=FONTS["heading_serif"],
        foreground=COLORS["fg"],
    )
    style.configure(
        "HeadingLg.TLabel",
        font=FONTS["heading_serif_lg"],
        foreground=COLORS["fg"],
    )
    style.configure(
        "HeadingSm.TLabel",
        font=FONTS["heading_serif_sm"],
        foreground=COLORS["fg"],
    )
    style.configure(
        "Subheading.TLabel",
        font=FONTS["subheading"],
        foreground=COLORS["fg"],
    )
    style.configure("Dim.TLabel", foreground=COLORS["fg_dim"])
    style.configure(
        "Accent.TLabel",
        foreground=COLORS["accent_text"],
    )
    style.configure(
        "AccentHeading.TLabel",
        font=FONTS["heading_serif"],
        foreground=COLORS["accent_text"],
    )
    style.configure("Stat.TLabel", font=FONTS["stat"], foreground=COLORS["fg"])
    style.configure("StatLarge.TLabel", font=FONTS["stat_large"], foreground=COLORS["fg"])
    style.configure("StatMod.TLabel", font=FONTS["stat_mod"])
    style.configure("Positive.TLabel", foreground=COLORS["positive"])
    style.configure("Negative.TLabel", foreground=COLORS["negative"])
    style.configure("Gold.TLabel", foreground=COLORS["gold"])
    # Card-background labels
    style.configure(
        "Card.TLabel",
        background=COLORS["bg_surface"],
        foreground=COLORS["fg"],
    )
    style.configure(
        "CardHeading.TLabel",
        background=COLORS["bg_surface"],
        foreground=COLORS["accent_text"],
        font=FONTS["heading_serif_sm"],
    )
    # Uppercase label (for stat names, section labels)
    style.configure(
        "Upper.TLabel",
        font=FONTS["label_upper_bold"],
        foreground=COLORS["fg_dim"],
    )
    # Nav labels (sidebar)
    style.configure(
        "Nav.TLabel",
        background=COLORS["bg_surface"],
        foreground=COLORS["fg_dim"],
        font=FONTS["label_upper_bold"],
    )
    style.configure(
        "NavActive.TLabel",
        background=COLORS["bg_highest"],
        foreground=COLORS["accent_text"],
        font=FONTS["label_upper_bold"],
    )
    # Chip labels (tags/badges)
    style.configure(
        "Chip.TLabel",
        background=COLORS["gold_dark"],
        foreground=COLORS["gold_on_dark"],
        font=FONTS["label_tiny"],
        padding=[6, 2],
    )
    style.configure(
        "AccentChip.TLabel",
        background=COLORS["accent"],
        foreground=COLORS["accent_text"],
        font=FONTS["label_tiny"],
        padding=[6, 2],
    )

    # ------------------------------------------------------------------
    # LabelFrame
    # ------------------------------------------------------------------
    style.configure(
        "TLabelframe",
        background=COLORS["bg"],
        foreground=COLORS["fg"],
    )
    style.configure(
        "TLabelframe.Label",
        background=COLORS["bg"],
        foreground=COLORS["accent_text"],
        font=FONTS["heading_serif_sm"],
    )
    style.configure("Card.TLabelframe", background=COLORS["bg_surface"])
    style.configure(
        "Card.TLabelframe.Label",
        background=COLORS["bg_surface"],
        foreground=COLORS["accent_text"],
        font=FONTS["heading_serif_sm"],
    )

    # ------------------------------------------------------------------
    # Notebook (still used by wizard steps internally)
    # ------------------------------------------------------------------
    style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=COLORS["bg_high"],
        foreground=COLORS["fg_dim"],
        padding=[14, 7],
        font=FONTS["body"],
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLORS["bg_surface"])],
        foreground=[("selected", COLORS["accent_text"])],
    )

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    # Remove the default focus-ring element from all button styles so clicks
    # don't draw a bright native outline against the dark UI.
    button_layout = [
        (
            "Button.border",
            {
                "sticky": "nswe",
                "border": "1",
                "children": [
                    (
                        "Button.padding",
                        {
                            "sticky": "nswe",
                            "children": [("Button.label", {"sticky": "nswe"})],
                        },
                    )
                ],
            },
        )
    ]
    button_styles = (
        "TButton",
        "Accent.TButton",
        "Gold.TButton",
        "Compact.TButton",
        "HomeLoad.TButton",
        "HomeLoadAccent.TButton",
        "HomeDelete.TButton",
        "Footer.TButton",
        "FooterAccent.TButton",
    )
    for style_name in button_styles:
        style.layout(style_name, button_layout)

    style.configure(
        "TButton",
        background=COLORS["bg_highest"],
        foreground=COLORS["fg"],
        padding=[12, 6],
        font=FONTS["body"],
        bordercolor=COLORS["outline_dim"],
        lightcolor=COLORS["bg_highest"],
        darkcolor=COLORS["bg_surface"],
    )
    style.map(
        "TButton",
        background=[
            ("active", COLORS["bg_high"]),
            ("disabled", COLORS["bg_high"]),
        ],
        foreground=[("disabled", COLORS["fg_dim"])],
        bordercolor=[("active", COLORS["outline"]), ("disabled", COLORS["outline_dim"])],
        lightcolor=[("active", COLORS["bg_high"])],
        darkcolor=[("active", COLORS["bg_surface"])],
    )

    style.configure(
        "Footer.TButton",
        background=COLORS["bg_highest"],
        foreground=COLORS["fg"],
        padding=[12, 6],
        font=FONTS["body"],
        bordercolor=COLORS["outline_dim"],
        lightcolor=COLORS["bg_highest"],
        darkcolor=COLORS["bg_surface"],
    )
    style.map(
        "Footer.TButton",
        background=[
            ("active", COLORS["bg_high"]),
            ("disabled", COLORS["bg_high"]),
        ],
        foreground=[("disabled", COLORS["fg_dim"])],
        bordercolor=[("active", COLORS["outline"]), ("disabled", COLORS["outline_dim"])],
        lightcolor=[("active", COLORS["bg_high"])],
        darkcolor=[("active", COLORS["bg_surface"])],
    )

    style.configure(
        "Accent.TButton",
        background=COLORS["accent"],
        foreground=COLORS["fg"],
        font=FONTS["body_bold"],
        bordercolor=COLORS["accent_on"],
        lightcolor=COLORS["accent"],
        darkcolor=COLORS["accent_on"],
    )
    style.map(
        "Accent.TButton",
        background=[("active", COLORS["accent_on"])],
        bordercolor=[("active", COLORS["accent_on"])],
        lightcolor=[("active", COLORS["accent_on"])],
        darkcolor=[("active", COLORS["accent_on"])],
    )

    style.configure(
        "FooterAccent.TButton",
        background=COLORS["accent"],
        foreground=COLORS["fg"],
        font=FONTS["body_bold"],
        padding=[12, 6],
        bordercolor=COLORS["accent_on"],
        lightcolor=COLORS["accent"],
        darkcolor=COLORS["accent_on"],
    )
    style.map(
        "FooterAccent.TButton",
        background=[("active", COLORS["accent_on"])],
        bordercolor=[("active", COLORS["accent_on"])],
        lightcolor=[("active", COLORS["accent_on"])],
        darkcolor=[("active", COLORS["accent_on"])],
    )

    style.configure(
        "Gold.TButton",
        background=COLORS["gold_dark"],
        foreground=COLORS["gold"],
        font=FONTS["body_bold"],
        bordercolor=COLORS["gold"],
        lightcolor=COLORS["gold_dark"],
        darkcolor=COLORS["bg_surface"],
    )
    style.map(
        "Gold.TButton",
        background=[("active", COLORS["gold"])],
        foreground=[("active", COLORS["gold_dark"])],
        bordercolor=[("active", COLORS["gold"])],
        lightcolor=[("active", COLORS["gold"])],
        darkcolor=[("active", COLORS["gold_dark"])],
    )

    style.configure(
        "Compact.TButton",
        background=COLORS["bg_highest"],
        foreground=COLORS["fg"],
        padding=[6, 1],
        font=FONTS["body"],
        bordercolor=COLORS["outline_dim"],
        lightcolor=COLORS["bg_highest"],
        darkcolor=COLORS["bg_surface"],
    )
    style.map(
        "Compact.TButton",
        background=[
            ("active", COLORS["bg_high"]),
            ("disabled", COLORS["bg_high"]),
        ],
        foreground=[("disabled", COLORS["fg_dim"])],
        bordercolor=[("active", COLORS["outline"]), ("disabled", COLORS["outline_dim"])],
        lightcolor=[("active", COLORS["bg_high"])],
        darkcolor=[("active", COLORS["bg_surface"])],
    )

    style.configure(
        "HomeLoad.TButton",
        background=COLORS["bg_high"],
        foreground=COLORS["fg"],
        padding=[14, 10],
        font=FONTS["label_upper_bold"],
        bordercolor=COLORS["outline_dim"],
        lightcolor=COLORS["bg_high"],
        darkcolor=COLORS["bg_surface"],
    )
    style.map(
        "HomeLoad.TButton",
        background=[("active", COLORS["bg_highest"])],
        bordercolor=[("active", COLORS["outline"])],
        lightcolor=[("active", COLORS["bg_highest"])],
        darkcolor=[("active", COLORS["bg_high"])],
    )

    style.configure(
        "HomeLoadAccent.TButton",
        background=COLORS["accent"],
        foreground=COLORS["fg"],
        padding=[14, 10],
        font=FONTS["label_upper_bold"],
        bordercolor=COLORS["accent_on"],
        lightcolor=COLORS["accent"],
        darkcolor=COLORS["accent_on"],
    )
    style.map(
        "HomeLoadAccent.TButton",
        background=[("active", COLORS["accent_on"])],
        bordercolor=[("active", COLORS["accent_on"])],
        lightcolor=[("active", COLORS["accent_on"])],
        darkcolor=[("active", COLORS["accent_on"])],
    )

    style.configure(
        "HomeDelete.TButton",
        background=COLORS["bg_container"],
        foreground=COLORS["fg_dim"],
        padding=[8, 3],
        font=FONTS["body_small"],
        bordercolor=COLORS["outline_dim"],
        lightcolor=COLORS["bg_container"],
        darkcolor=COLORS["bg_surface"],
    )
    style.map(
        "HomeDelete.TButton",
        background=[("active", COLORS["bg_high"])],
        foreground=[("active", COLORS["fg"])],
        bordercolor=[("active", COLORS["outline"])],
        lightcolor=[("active", COLORS["bg_high"])],
        darkcolor=[("active", COLORS["bg_surface"])],
    )

    # ------------------------------------------------------------------
    # Radiobuttons and Checkbuttons
    # ------------------------------------------------------------------
    style.configure(
        "TRadiobutton",
        background=COLORS["bg"],
        foreground=COLORS["fg"],
        font=FONTS["body"],
    )
    style.configure(
        "Card.TRadiobutton",
        background=COLORS["bg_surface"],
        foreground=COLORS["fg"],
    )
    style.configure(
        "TCheckbutton",
        background=COLORS["bg"],
        foreground=COLORS["fg"],
        font=FONTS["body"],
    )
    style.configure(
        "Card.TCheckbutton",
        background=COLORS["bg_surface"],
        foreground=COLORS["fg"],
    )

    # ------------------------------------------------------------------
    # Combobox
    # ------------------------------------------------------------------
    style.configure(
        "TCombobox",
        fieldbackground=COLORS["bg_high"],
        foreground=COLORS["fg"],
        selectbackground=COLORS["select_bg"],
        selectforeground=COLORS["select_fg"],
    )
    style.map("TCombobox", fieldbackground=[("readonly", COLORS["bg_high"])])

    # ------------------------------------------------------------------
    # Entry
    # ------------------------------------------------------------------
    style.configure(
        "TEntry",
        fieldbackground=COLORS["bg_high"],
        foreground=COLORS["fg"],
    )

    # ------------------------------------------------------------------
    # Spinbox
    # ------------------------------------------------------------------
    style.configure(
        "TSpinbox",
        fieldbackground=COLORS["bg_high"],
        foreground=COLORS["fg"],
        arrowcolor=COLORS["fg"],
    )

    # ------------------------------------------------------------------
    # Treeview
    # ------------------------------------------------------------------
    style.configure(
        "Treeview",
        background=COLORS["bg_surface"],
        foreground=COLORS["fg"],
        fieldbackground=COLORS["bg_surface"],
        font=FONTS["body"],
    )
    style.configure(
        "Treeview.Heading",
        background=COLORS["bg_highest"],
        foreground=COLORS["fg_dim"],
        font=FONTS["label_upper_bold"],
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS["select_bg"])],
        foreground=[("selected", COLORS["select_fg"])],
    )

    # ------------------------------------------------------------------
    # Scrollbar
    # ------------------------------------------------------------------
    _sb_cfg = dict(
        background=COLORS["bg_high"],
        troughcolor=COLORS["bg"],
        bordercolor=COLORS["bg"],
        arrowcolor=COLORS["fg_dim"],
        lightcolor=COLORS["bg_high"],
        darkcolor=COLORS["bg"],
        gripcount=0,
    )
    _sb_map = dict(
        background=[
            ("active", COLORS["outline_dim"]),
            ("pressed", COLORS["outline_dim"]),
            ("disabled", COLORS["bg"]),
        ],
        arrowcolor=[
            ("active", COLORS["fg"]),
            ("pressed", COLORS["fg"]),
            ("disabled", COLORS["fg_dim"]),
        ],
    )
    style.configure("TScrollbar", **_sb_cfg)
    style.map("TScrollbar", **_sb_map)
    for orient in ("Vertical", "Horizontal"):
        style.configure(f"{orient}.TScrollbar", **_sb_cfg)
        style.map(f"{orient}.TScrollbar", **_sb_map)

    # ------------------------------------------------------------------
    # Separator
    # ------------------------------------------------------------------
    style.configure("TSeparator", background=COLORS["outline_dim"])
    style.configure("Subtle.TSeparator", background=COLORS["border_subtle"])

    # ------------------------------------------------------------------
    # PanedWindow
    # ------------------------------------------------------------------
    style.configure("TPanedwindow", background=COLORS["outline_dim"])

    # ------------------------------------------------------------------
    # Progressbar
    # ------------------------------------------------------------------
    style.configure(
        "TProgressbar",
        background=COLORS["accent"],
        troughcolor=COLORS["bg_high"],
    )

    # ------------------------------------------------------------------
    # Root window
    # ------------------------------------------------------------------
    root.configure(bg=COLORS["bg"])

    # Override native Tk scrollbar defaults
    root.option_add("*Scrollbar.background", COLORS["bg_high"])
    root.option_add("*Scrollbar.troughColor", COLORS["bg"])
    root.option_add("*Scrollbar.activeBackground", COLORS["outline_dim"])
    root.option_add("*Scrollbar.highlightBackground", COLORS["bg"])
    root.option_add("*Scrollbar.highlightColor", COLORS["bg"])
    root.option_add("*Scrollbar.borderWidth", 0)
