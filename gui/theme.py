"""TTK theme configuration — Mythic Modern dark design system."""

import json
import os
import sys
import tkinter as tk
from datetime import datetime, UTC
from tkinter import ttk
import tkinter.font as tkfont

from paths import is_frozen, ui_diagnostics_path


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
    "accent": "#4a2028",
    "accent_text": "#ffb3b5",
    "accent_on": "#35161c",
    # Secondary accent — gold
    "gold": "#e9c176",
    "gold_dark": "#604403",
    "gold_on_dark": "#dab36a",
    # Foreground / text
    "fg": "#e5e2e1",
    "fg_dim": "#e0bfbf",
    "fg_disabled": "#7d7777",
    # Borders
    "outline": "#a78a8a",
    "outline_dim": "#584141",
    "control_disabled": "#4d4949",
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
    "accent_dark": "#4a2028",   # → accent
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
    "heading_serif_lg": (_SERIF, 28, "bold"),
    "heading_serif": (_SERIF, 20),
    "heading_serif_sm": (_SERIF, 14),
    "hero_eyebrow": (_SERIF, 14),
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


def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError, tk.TclError):
        return None


def _parse_scale_override(raw_value: str | None) -> float | None:
    if raw_value is None:
        return None
    text = raw_value.strip()
    if not text:
        return None
    value = _safe_float(text)
    if value is None or value <= 0:
        return None
    return round(value, 4)


def _choose_tk_scaling(
    current_scaling: float | None,
    screen_dpi: float | None,
    platform_name: str,
    override: str | None = None,
) -> float | None:
    manual_override = _parse_scale_override(override)
    if manual_override is not None:
        return manual_override
    if platform_name != "darwin":
        return current_scaling
    if screen_dpi is None or screen_dpi <= 0:
        return current_scaling
    return round(screen_dpi / 72.0, 4)


def normalize_tk_runtime(root: tk.Tk) -> dict[str, object]:
    """Normalize Tk scaling so point-sized fonts render consistently.

    On macOS, frozen app bundles can start with a different Tk scaling factor
    than the same interpreter in development, which makes fixed point fonts
    look smaller and disrupts hand-tuned spacing. Normalize scaling from the
    measured screen DPI before the widget tree is built.
    """
    current_scaling = _safe_float(root.tk.call("tk", "scaling"))
    screen_dpi = _safe_float(root.winfo_fpixels("1i"))
    override = os.environ.get("VIBEDND_UI_SCALE")
    target_scaling = _choose_tk_scaling(current_scaling, screen_dpi, sys.platform, override)

    applied = False
    if (
        current_scaling is not None
        and target_scaling is not None
        and 0.5 <= target_scaling <= 4.0
        and abs(current_scaling - target_scaling) > 0.01
    ):
        root.tk.call("tk", "scaling", target_scaling)
        applied = True

    effective_scaling = _safe_float(root.tk.call("tk", "scaling"))
    return {
        "override": override.strip() if isinstance(override, str) else "",
        "platform": sys.platform,
        "screen_dpi": screen_dpi,
        "initial_scaling": current_scaling,
        "target_scaling": target_scaling,
        "effective_scaling": effective_scaling,
        "applied": applied,
    }


def _font_snapshot(root: tk.Misc, font_spec) -> dict[str, object]:
    font = tkfont.Font(root=root, font=font_spec)
    actual = font.actual()
    metrics = font.metrics()
    return {
        "family": actual.get("family", ""),
        "size": actual.get("size", ""),
        "weight": actual.get("weight", ""),
        "slant": actual.get("slant", ""),
        "underline": actual.get("underline", 0),
        "overstrike": actual.get("overstrike", 0),
        "metrics": {
            "linespace": metrics.get("linespace", 0),
            "ascent": metrics.get("ascent", 0),
            "descent": metrics.get("descent", 0),
        },
    }


def write_ui_diagnostics(
    root: tk.Tk,
    scaling_snapshot: dict[str, object] | None = None,
) -> str | None:
    """Write a startup diagnostics report for comparing dev vs frozen UI."""
    try:
        families = set(tkfont.families(root=root))
        path = ui_diagnostics_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        report = {
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "frozen": is_frozen(),
            "sys_executable": sys.executable,
            "python_version": sys.version,
            "tk_patchlevel": str(root.tk.call("info", "patchlevel")),
            "tk_version": tk.TkVersion,
            "tcl_version": tk.TclVersion,
            "windowing_system": str(root.tk.call("tk", "windowingsystem")),
            "screen": {
                "width": root.winfo_screenwidth(),
                "height": root.winfo_screenheight(),
                "pixels_per_inch": _safe_float(root.winfo_fpixels("1i")),
            },
            "scaling": scaling_snapshot or {},
            "font_families": {
                "sans_requested": _SANS,
                "serif_requested": _SERIF,
                "mono_requested": _MONO,
                "sans_available": _SANS in families,
                "serif_available": _SERIF in families,
                "mono_available": _MONO in families,
            },
            "fonts": {
                "body": _font_snapshot(root, FONTS["body"]),
                "hero_title": _font_snapshot(root, FONTS["hero_title"]),
                "hero_title_italic": _font_snapshot(root, FONTS["hero_title_italic"]),
                "label_upper_bold": _font_snapshot(root, FONTS["label_upper_bold"]),
            },
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)
        return path
    except (OSError, tk.TclError):
        return None


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
        "WizardAccent.TButton",
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
        bordercolor=COLORS["bg_highest"],
        lightcolor=COLORS["bg_highest"],
        darkcolor=COLORS["bg_highest"],
    )
    style.map(
        "TButton",
        background=[
            ("active", COLORS["bg_high"]),
            ("disabled", COLORS["bg_high"]),
        ],
        foreground=[("disabled", COLORS["fg_dim"])],
        bordercolor=[
            ("active", COLORS["bg_high"]),
            ("disabled", COLORS["bg_high"]),
        ],
        lightcolor=[("active", COLORS["bg_high"])],
        darkcolor=[("active", COLORS["bg_high"])],
    )

    style.configure(
        "Footer.TButton",
        background=COLORS["bg_highest"],
        foreground=COLORS["fg"],
        padding=[12, 6],
        font=FONTS["body"],
        bordercolor=COLORS["bg_highest"],
        lightcolor=COLORS["bg_highest"],
        darkcolor=COLORS["bg_highest"],
    )
    style.map(
        "Footer.TButton",
        background=[
            ("active", COLORS["bg_high"]),
            ("disabled", COLORS["bg_high"]),
        ],
        foreground=[("disabled", COLORS["fg_dim"])],
        bordercolor=[
            ("active", COLORS["bg_high"]),
            ("disabled", COLORS["bg_high"]),
        ],
        lightcolor=[("active", COLORS["bg_high"])],
        darkcolor=[("active", COLORS["bg_high"])],
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
        "WizardAccent.TButton",
        background=COLORS["accent"],
        foreground=COLORS["fg"],
        font=FONTS["body_bold"],
        bordercolor=COLORS["accent_on"],
        lightcolor=COLORS["accent"],
        darkcolor=COLORS["accent_on"],
    )
    style.map(
        "WizardAccent.TButton",
        background=[
            ("active", COLORS["accent_on"]),
            ("disabled", COLORS["control_disabled"]),
        ],
        foreground=[("disabled", COLORS["fg_disabled"])],
        bordercolor=[
            ("active", COLORS["accent_on"]),
            ("disabled", COLORS["outline_dim"]),
        ],
        lightcolor=[
            ("active", COLORS["accent_on"]),
            ("disabled", COLORS["control_disabled"]),
        ],
        darkcolor=[
            ("active", COLORS["accent_on"]),
            ("disabled", COLORS["control_disabled"]),
        ],
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
        background=COLORS["bg_highest"],
        foreground=COLORS["gold_on_dark"],
        font=FONTS["body"],
        bordercolor=COLORS["bg_highest"],
        lightcolor=COLORS["bg_highest"],
        darkcolor=COLORS["bg_highest"],
    )
    style.map(
        "Gold.TButton",
        background=[("active", COLORS["bg_high"])],
        foreground=[("active", COLORS["gold"])],
        bordercolor=[("active", COLORS["bg_high"])],
        lightcolor=[("active", COLORS["bg_high"])],
        darkcolor=[("active", COLORS["bg_high"])],
    )

    style.configure(
        "Compact.TButton",
        background=COLORS["bg_highest"],
        foreground=COLORS["fg"],
        padding=[6, 1],
        font=FONTS["body"],
        bordercolor=COLORS["bg_highest"],
        lightcolor=COLORS["bg_highest"],
        darkcolor=COLORS["bg_highest"],
    )
    style.map(
        "Compact.TButton",
        background=[
            ("active", COLORS["bg_high"]),
            ("disabled", COLORS["bg_high"]),
        ],
        foreground=[("disabled", COLORS["fg_dim"])],
        bordercolor=[
            ("active", COLORS["bg_high"]),
            ("disabled", COLORS["bg_high"]),
        ],
        lightcolor=[("active", COLORS["bg_high"])],
        darkcolor=[("active", COLORS["bg_high"])],
    )

    style.configure(
        "HomeLoad.TButton",
        background=COLORS["bg_high"],
        foreground=COLORS["fg"],
        padding=[14, 10],
        font=FONTS["label_upper_bold"],
        bordercolor=COLORS["bg_high"],
        lightcolor=COLORS["bg_high"],
        darkcolor=COLORS["bg_high"],
    )
    style.map(
        "HomeLoad.TButton",
        background=[("active", COLORS["bg_highest"])],
        bordercolor=[("active", COLORS["bg_highest"])],
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
        bordercolor=COLORS["bg_container"],
        lightcolor=COLORS["bg_container"],
        darkcolor=COLORS["bg_container"],
    )
    style.map(
        "HomeDelete.TButton",
        background=[("active", COLORS["bg_high"])],
        foreground=[("active", COLORS["fg"])],
        bordercolor=[("active", COLORS["bg_high"])],
        lightcolor=[("active", COLORS["bg_high"])],
        darkcolor=[("active", COLORS["bg_high"])],
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
    style.map(
        "TRadiobutton",
        background=[
            ("active", COLORS["bg"]),
            ("selected", COLORS["bg"]),
            ("disabled", COLORS["bg"]),
        ],
        foreground=[("disabled", COLORS["fg_dim"])],
    )
    style.configure(
        "Card.TRadiobutton",
        background=COLORS["bg_surface"],
        foreground=COLORS["fg"],
    )
    style.map(
        "Card.TRadiobutton",
        background=[
            ("active", COLORS["bg_surface"]),
            ("selected", COLORS["bg_surface"]),
            ("disabled", COLORS["bg_surface"]),
        ],
        foreground=[("disabled", COLORS["fg_dim"])],
    )
    style.configure(
        "Container.TRadiobutton",
        background=COLORS["bg_container"],
        foreground=COLORS["fg"],
    )
    style.map(
        "Container.TRadiobutton",
        background=[
            ("active", COLORS["bg_container"]),
            ("selected", COLORS["bg_container"]),
            ("disabled", COLORS["bg_container"]),
        ],
        foreground=[("disabled", COLORS["fg_dim"])],
    )
    style.configure(
        "TCheckbutton",
        background=COLORS["bg"],
        foreground=COLORS["fg"],
        font=FONTS["body"],
    )
    style.map(
        "TCheckbutton",
        background=[
            ("active", COLORS["bg"]),
            ("selected", COLORS["bg"]),
            ("disabled", COLORS["bg"]),
        ],
        foreground=[("disabled", COLORS["fg_disabled"])],
        indicatorcolor=[("disabled", COLORS["control_disabled"])],
    )
    style.configure(
        "Card.TCheckbutton",
        background=COLORS["bg_surface"],
        foreground=COLORS["fg"],
    )
    style.map(
        "Card.TCheckbutton",
        background=[
            ("active", COLORS["bg_surface"]),
            ("selected", COLORS["bg_surface"]),
            ("disabled", COLORS["bg_surface"]),
        ],
        foreground=[("disabled", COLORS["fg_disabled"])],
        indicatorcolor=[("disabled", COLORS["control_disabled"])],
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
    root.option_add("*Checkbutton.disabledForeground", COLORS["fg_disabled"])
