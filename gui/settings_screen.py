import tkinter as tk
from tkinter import ttk
from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import SectionHeader, ScrollableFrame, WrappingLabel
from gui.source_config import SECTION_ORDER, UA_CATEGORY, handle_ua_toggle, save_settings

class SettingsScreen:
    """A full-page settings view within the main window."""
    
    def __init__(self, parent, app):
        self.app = app
        self.data = app.data
        self.frame = tk.Frame(parent, bg=COLORS["bg"])
        
        self.toggle_vars = {}
        self.ua_prev_enabled = {}
        
        self._build_ui()
        
    def _build_ui(self):
        # Header Area
        header = tk.Frame(self.frame, bg=COLORS["bg_surface"])
        header.pack(fill=tk.X)
        
        # Heading row
        title_row = tk.Frame(header, bg=COLORS["bg_surface"])
        title_row.pack(fill=tk.X, padx=40, pady=(36, 16))
        
        # Back Button (Arrow)
        back_arrow = tk.Label(
            title_row,
            text="\u25c0",
            font=FONTS["archive_back"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
            cursor="hand2",
        )
        back_arrow.pack(side=tk.LEFT, padx=(0, 10))
        back_arrow.bind("<Button-1>", lambda _: self.app.show_home())
        
        tk.Label(
            title_row,
            text="System Settings",
            font=FONTS["archive_title"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"]
        ).pack(side=tk.LEFT)
        
        tk.Label(
            header,
            text="Configure which game sources and rules are active in your chronicle.",
            font=FONTS["body_large"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_surface"]
        ).pack(anchor="w", padx=40, pady=(0, 24))

        # Main Content Scroll Area
        container = tk.Frame(self.frame, bg=COLORS["bg"])
        container.pack(fill=tk.BOTH, expand=True, padx=40, pady=24)
        
        scroll = ScrollableFrame(container, inner_padding=0, auto_hide_scrollbar=True)
        scroll.pack(fill=tk.BOTH, expand=True)
        inner = scroll.inner
        
        # Section Header Descriptions
        WrappingLabel(
            inner,
            text="Source filters determine which Species, Backgrounds, and Classes appear during character creation and level-up.",
            font=FONTS["body"],
            foreground=COLORS["fg_dim"],
            background=COLORS["bg"]
        ).pack(fill=tk.X, anchor="w", pady=(0, SPACING["lg"]))

        # Sections
        section_titles = {
            "species": "Species Sources",
            "classes": "Class Sources",
            "subclasses": "Subclass Sources",
            "backgrounds": "Background Sources",
            "feats": "Feat Sources"
        }
        
        filters = self.data.source_filters
        
        for context, categories in SECTION_ORDER.items():
            title = section_titles.get(context, context.title())
            SectionHeader(inner, text=title).pack(fill=tk.X, pady=(SPACING["md"], SPACING["sm"]))
            
            # Grid frame for sources (2 columns for better space usage)
            group_inner = tk.Frame(inner, bg=COLORS["bg"])
            group_inner.pack(fill=tk.X, pady=(0, SPACING["xl"]))
            
            self.toggle_vars.setdefault(context, {})
            self.ua_prev_enabled[context] = filters.get(context, {}).get(UA_CATEGORY, False)

            for i, cat in enumerate(categories):
                row = i // 2
                col = i % 2
                
                label_text = "Unearthed Arcana (Playtest)" if cat == UA_CATEGORY else cat
                is_on = filters.get(context, {}).get(cat, cat != UA_CATEGORY)
                var = tk.BooleanVar(value=is_on)
                
                # Container for better hover/click area
                cb_frame = tk.Frame(group_inner, bg=COLORS["bg"])
                cb_frame.grid(row=row, column=col, sticky="w", padx=(20 if col == 1 else 0, 0), pady=4)
                
                def make_command(c=context, v=var):
                    return lambda: self._on_toggle(c, v)
                
                cb = ttk.Checkbutton(
                    cb_frame,
                    text=label_text,
                    variable=var,
                    command=make_command()
                )
                cb.pack(side=tk.LEFT)
                
                self.toggle_vars[context][cat] = var

        # Floating Action Bar at the very bottom
        action_bar = tk.Frame(self.frame, bg=COLORS["bg_surface"])
        action_bar.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Frame(action_bar, bg=COLORS["border_subtle"], height=1).pack(fill=tk.X)
        
        btn_inner = tk.Frame(action_bar, bg=COLORS["bg_surface"])
        btn_inner.pack(padx=40, pady=24, anchor="e")
        
        ttk.Button(
            btn_inner,
            text="Cancel",
            command=self.app.show_home
        ).pack(side=tk.LEFT, padx=(0, 12))
        
        ttk.Button(
            btn_inner,
            text="Save",
            style="WizardAccent.TButton",
            command=self._save_and_close
        ).pack(side=tk.LEFT)

    def _on_toggle(self, context: str, var: tk.BooleanVar):
        if var == self.toggle_vars[context].get(UA_CATEGORY):
            proceed, is_enabled = handle_ua_toggle(
                self.frame, var, self.ua_prev_enabled[context]
            )
            if proceed:
                self.ua_prev_enabled[context] = is_enabled

    def _save_and_close(self):
        new_filters = {}
        for context, cats in self.toggle_vars.items():
            new_filters[context] = {}
            for cat, var in cats.items():
                new_filters[context][cat] = var.get()

        self.data.source_filters = new_filters
        save_settings(new_filters)
        
        # Success feedback could go here if we had a toast/notification
        self.app.show_home()
