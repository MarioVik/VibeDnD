"""Landing screen and saved-character archive views."""

import base64
import io
import tkinter as tk
from tkinter import filedialog, ttk

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover
    Image = None
    ImageTk = None

from gui.theme import COLORS, FONTS
from gui.widgets import ScrollableFrame, ConfirmDialog, AlertDialog
from models.character_store import list_saved_characters, delete_character
from paths import characters_dir


class HomeScreen:
    """The landing flow shown when the app starts."""

    _ACTION_CARD_WIDTH = 380
    _ACTION_CARD_HEIGHT = 238
    _ARCHIVE_CARD_WIDTH = 320
    _ARCHIVE_CARD_HEIGHT = 468
    _ARCHIVE_ART_HEIGHT = 328
    _ARCHIVE_CARD_GAP = 18
    _MAX_ARCHIVE_COLUMNS = 3

    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent, bg=COLORS["bg"])

        self._current_view = "landing"
        self._landing_actions_vertical = False
        self._archive_columns = 0
        self._archive_layout_job = None
        self._archive_chars: list[dict] = []

        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_landing(self):
        """Show the cinematic landing screen."""
        self._current_view = "landing"
        self._archive_view.pack_forget()
        self._landing_view.pack(fill=tk.BOTH, expand=True)
        self._refresh_landing_layout()

    def show_archive(self):
        """Show the saved-character archive."""
        self._current_view = "archive"
        self._landing_view.pack_forget()
        self._archive_view.pack(fill=tk.BOTH, expand=True)
        self.refresh_archive()

    def refresh(self):
        """Backward-compatible refresh hook."""
        self.refresh_archive()

    def refresh_archive(self):
        """Reload the archive list from disk."""
        self._archive_chars = list_saved_characters(characters_dir())
        if self._archive_chars:
            if self._empty_note.winfo_manager():
                self._empty_note.pack_forget()
        else:
            self._empty_note.configure(
                text=(
                    "No saved characters yet. Import one from a file, or head back to "
                    "the main menu to start a new legend."
                )
            )
            if not self._empty_note.winfo_manager():
                self._empty_note.pack(fill=tk.X, pady=(0, 18), before=self._archive_scroll)
        self._schedule_archive_layout()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        self._build_landing_view()
        self._build_archive_view()
        self.show_landing()

    def _build_landing_view(self):
        self._landing_view = tk.Frame(self.frame, bg=COLORS["bg"])

        self._landing_bg = tk.Canvas(
            self._landing_view,
            bg=COLORS["bg"],
            highlightthickness=0,
            bd=0,
        )
        self._landing_bg.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._landing_bg.bind("<Configure>", self._draw_landing_background)

        self._landing_content = tk.Frame(self._landing_view, bg=COLORS["bg"])
        self._landing_content.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            self._landing_content,
            text="Vibe Dungeoneering",
            font=FONTS["hero_eyebrow"],
            fg=COLORS["accent_text"],
            bg=COLORS["bg"],
        ).pack(pady=(0, 10))

        tk.Label(
            self._landing_content,
            text="Chronicle Your",
            font=FONTS["hero_title"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
        ).pack()

        tk.Label(
            self._landing_content,
            text="Legend",
            font=FONTS["hero_title_italic"],
            fg=COLORS["gold"],
            bg=COLORS["bg"],
        ).pack()

        self._landing_body = tk.Label(
            self._landing_content,
            text=(
                "A digital sanctum for the modern hero. Precisely curated, anciently "
                "inspired. Welcome back to VibeDnD."
            ),
            font=FONTS["body_large"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
            justify=tk.CENTER,
            wraplength=760,
        )
        self._landing_body.pack(pady=(16, 34))

        self._landing_action_row = tk.Frame(self._landing_content, bg=COLORS["bg"])
        self._landing_action_row.pack()

        self._create_card = self._build_action_card(
            self._landing_action_row,
            title="Create a New Character",
            body="Begin a fresh journey with guided steps and build your hero from scratch.",
            accent=COLORS["accent"],
            label="NEW LEGEND",
            command=self._on_create_new,
        )
        self._load_card = self._build_action_card(
            self._landing_action_row,
            title="Load Saved Character",
            body="Return to the fray. Browse portraits, imports, and archived characters.",
            accent=COLORS["gold_dark"],
            label="THE ARCHIVES",
            command=self.app.show_archive,
            accent_text=COLORS["gold"],
        )
        self._refresh_landing_layout()
        self._landing_view.bind("<Configure>", self._on_landing_configure)

    def _build_archive_view(self):
        self._archive_view = tk.Frame(self.frame, bg=COLORS["bg"])

        content = tk.Frame(self._archive_view, bg=COLORS["bg"])
        content.pack(fill=tk.BOTH, expand=True, padx=40, pady=(36, 24))

        header = tk.Frame(content, bg=COLORS["bg"])
        header.pack(fill=tk.X, pady=(0, 16))

        title_row = tk.Frame(header, bg=COLORS["bg"])
        title_row.pack(anchor="w")

        back_arrow = tk.Label(
            title_row,
            text="\u25c0",
            font=FONTS["archive_back"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
            cursor="hand2",
        )
        back_arrow.pack(side=tk.LEFT, padx=(0, 10))
        back_arrow.bind("<Button-1>", lambda _event: self.app.show_home())
        back_arrow.bind(
            "<Enter>",
            lambda _event, widget=back_arrow: self._animate_label_color(
                widget,
                COLORS["accent_text"],
            ),
        )
        back_arrow.bind(
            "<Leave>",
            lambda _event, widget=back_arrow: self._animate_label_color(
                widget,
                COLORS["fg"],
            ),
        )

        tk.Label(
            title_row,
            text="The Archives",
            font=FONTS["archive_title"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
            anchor="w",
        ).pack(side=tk.LEFT)

        tk.Label(
            header,
            text=(
                "Your legacy is recorded in the halls of fate. Select a vessel to resume "
                "your journey."
            ),
            font=FONTS["body_large"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
            justify=tk.LEFT,
            wraplength=740,
            anchor="w",
        ).pack(anchor="w", pady=(12, 0))

        self._empty_note = tk.Label(
            content,
            text="",
            font=FONTS["body"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
            justify=tk.LEFT,
            wraplength=740,
            anchor="w",
        )
        self._empty_note.pack(fill=tk.X, pady=(0, 18))

        self._archive_scroll = ScrollableFrame(
            content,
            inner_padding=0,
            auto_hide_scrollbar=True,
        )
        self._archive_scroll.pack(fill=tk.BOTH, expand=True, pady=(24, 0))
        self._archive_scroll.canvas.configure(bg=COLORS["bg"])
        self._archive_scroll.inner.configure(style="TFrame")
        self._archive_scroll.canvas.bind("<Configure>", self._on_archive_canvas_configure)

        self._archive_grid = tk.Frame(self._archive_scroll.inner, bg=COLORS["bg"])
        self._archive_grid.pack(fill=tk.X, anchor="n")

    # ------------------------------------------------------------------
    # Landing layout
    # ------------------------------------------------------------------

    def _on_landing_configure(self, _event=None):
        self._refresh_landing_layout()

    def _refresh_landing_layout(self):
        width = max(self._landing_view.winfo_width(), self.frame.winfo_width(), 1)
        vertical = width < 1180
        if vertical != self._landing_actions_vertical:
            self._landing_actions_vertical = vertical
            self._create_card.pack_forget()
            self._load_card.pack_forget()

            if vertical:
                self._create_card.pack(fill=tk.X, pady=(0, 16))
                self._load_card.pack(fill=tk.X)
            else:
                self._create_card.pack(side=tk.LEFT, padx=(0, 16))
                self._load_card.pack(side=tk.LEFT)

        self._landing_body.configure(wraplength=min(max(width - 260, 540), 820))

    def _draw_landing_background(self, event=None):
        canvas = self._landing_bg
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 1)
        canvas.delete("bg")
        canvas.create_rectangle(0, 0, width, height, fill=COLORS["bg"], outline="", tags="bg")

    def _build_action_card(
        self,
        parent,
        title: str,
        body: str,
        accent: str,
        label: str,
        command,
        accent_text: str | None = None,
    ) -> tk.Frame:
        card = tk.Frame(
            parent,
            width=self._ACTION_CARD_WIDTH,
            height=self._ACTION_CARD_HEIGHT,
            bg=COLORS["bg_highest"],
            highlightbackground=COLORS["border_medium"],
            highlightthickness=1,
            cursor="hand2",
        )
        card.pack_propagate(False)

        inner = tk.Frame(card, bg=COLORS["bg_highest"], padx=28, pady=24)
        inner.pack(fill=tk.BOTH, expand=True)

        top_row = tk.Frame(inner, bg=COLORS["bg_highest"])
        top_row.pack(fill=tk.X)

        token = tk.Label(
            top_row,
            text=label,
            font=FONTS["label_upper_bold"],
            fg=accent_text or COLORS["accent_text"],
            bg=accent,
            padx=10,
            pady=8,
        )
        token.pack(side=tk.LEFT)

        bottom = tk.Frame(inner, bg=COLORS["bg_highest"])
        bottom.pack(side=tk.BOTTOM, fill=tk.X)

        tk.Label(
            bottom,
            text=title,
            font=FONTS["card_title_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_highest"],
            anchor="w",
            justify=tk.LEFT,
        ).pack(fill=tk.X)

        tk.Label(
            bottom,
            text=body,
            font=FONTS["body_large"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg_highest"],
            anchor="w",
            justify=tk.LEFT,
            wraplength=self._ACTION_CARD_WIDTH - 68,
        ).pack(fill=tk.X, pady=(12, 0))

        accent_bar = tk.Frame(card, bg=accent, height=4)
        accent_bar.pack(side=tk.BOTTOM, fill=tk.X)

        def on_enter(_event):
            card.configure(
                bg=COLORS["bg_high"],
                highlightbackground=accent,
                highlightthickness=1,
            )
            inner.configure(bg=COLORS["bg_high"])
            top_row.configure(bg=COLORS["bg_high"])
            bottom.configure(bg=COLORS["bg_high"])
            for widget in (token,):
                widget.configure(bg=accent)
            for widget in bottom.winfo_children():
                widget.configure(bg=COLORS["bg_high"])
            for widget in top_row.winfo_children():
                if widget is not token:
                    widget.configure(bg=COLORS["bg_high"])

        def on_leave(_event):
            card.configure(
                bg=COLORS["bg_highest"],
                highlightbackground=COLORS["border_medium"],
                highlightthickness=1,
            )
            inner.configure(bg=COLORS["bg_highest"])
            top_row.configure(bg=COLORS["bg_highest"])
            bottom.configure(bg=COLORS["bg_highest"])
            for widget in bottom.winfo_children():
                widget.configure(bg=COLORS["bg_highest"])
            for widget in top_row.winfo_children():
                if widget is not token:
                    widget.configure(bg=COLORS["bg_highest"])

        self._bind_clickable(card, command, on_enter, on_leave)
        return card

    # ------------------------------------------------------------------
    # Archive layout
    # ------------------------------------------------------------------

    def _on_archive_canvas_configure(self, _event=None):
        self._schedule_archive_layout()

    def _schedule_archive_layout(self):
        if self._archive_layout_job:
            self.frame.after_cancel(self._archive_layout_job)
        self._archive_layout_job = self.frame.after(25, self._layout_archive_cards)

    def _layout_archive_cards(self):
        self._archive_layout_job = None

        for child in self._archive_grid.winfo_children():
            child.destroy()

        available_width = max(self._archive_scroll.canvas.winfo_width() - 2, 1)
        if self._archive_chars:
            total_tiles = len(self._archive_chars) + 1  # include import tile
            if available_width >= 980:
                columns = min(self._MAX_ARCHIVE_COLUMNS, total_tiles)
            elif available_width >= 640:
                columns = min(2, total_tiles)
            else:
                columns = 1
        else:
            columns = 1
        self._archive_columns = columns

        for column in range(columns):
            self._archive_grid.grid_columnconfigure(column, weight=1, uniform="archive")

        tile_pad = self._ARCHIVE_CARD_GAP // 2
        card_width = max(
            280,
            (available_width - (columns * self._ARCHIVE_CARD_GAP)) // columns,
        )

        tiles: list[tuple[str, dict | None]] = [("character", info) for info in self._archive_chars]
        tiles.append(("import", None))

        for index, (kind, payload) in enumerate(tiles):
            row = index // columns
            column = index % columns
            if kind == "character":
                tile = self._build_archive_card(
                    self._archive_grid,
                    payload or {},
                    width=card_width,
                )
            else:
                tile = self._build_import_tile(self._archive_grid, width=card_width)
            tile.grid(
                row=row,
                column=column,
                sticky="n",
                padx=(tile_pad, tile_pad),
                pady=(0, self._ARCHIVE_CARD_GAP),
            )

    def _build_archive_card(self, parent, info: dict, width: int) -> tk.Frame:
        card = tk.Frame(
            parent,
            width=width,
            height=self._ARCHIVE_CARD_HEIGHT,
            bg=COLORS["bg_surface"],
            highlightbackground=COLORS["border_medium"],
            highlightthickness=1,
        )
        card.grid_propagate(False)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        art = tk.Canvas(
            card,
            width=width,
            height=self._ARCHIVE_ART_HEIGHT,
            bg=COLORS["bg_high"],
            highlightthickness=0,
            bd=0,
        )
        art.grid(row=0, column=0, sticky="ew")
        self._render_archive_art(
            art,
            info=info,
            width=width,
            height=self._ARCHIVE_ART_HEIGHT,
            surface_fill=COLORS["bg_surface"],
            placeholder_fill=COLORS["bg_high"],
        )
        self._add_archive_delete_control(art, info["path"], width=width)

        body = tk.Frame(card, bg=COLORS["bg_surface"], padx=24, pady=14)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        body.grid_rowconfigure(3, weight=1)

        name_label = tk.Label(
            body,
            text=info.get("name", "Unknown"),
            font=FONTS["card_title_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_surface"],
            anchor="w",
            justify=tk.LEFT,
        )
        name_label.grid(row=1, column=0, sticky="nw", pady=(0, 0))

        summary = (
            f"LEVEL {info.get('level', 1)} "
            f"{str(info.get('species', '?')).upper()} "
            f"{str(info.get('class_name', '?')).upper()}"
        )
        summary_label = tk.Label(
            body,
            text=summary,
            font=FONTS["label_upper_bold"],
            fg=COLORS["gold"],
            bg=COLORS["bg_surface"],
            anchor="w",
            justify=tk.LEFT,
        )
        summary_label.grid(row=2, column=0, sticky="nw", pady=(10, 0))

        def on_enter(_event):
            card.configure(bg=COLORS["bg_high"], highlightbackground=COLORS["gold_dark"])
            body.configure(bg=COLORS["bg_high"])
            name_label.configure(bg=COLORS["bg_high"])
            summary_label.configure(bg=COLORS["bg_high"])
            self._render_archive_art(
                art,
                info=info,
                width=width,
                height=self._ARCHIVE_ART_HEIGHT,
                surface_fill=COLORS["bg_high"],
                placeholder_fill=COLORS["bg_highest"],
            )
            self._add_archive_delete_control(art, info["path"], width=width)

        def on_leave(_event):
            card.configure(bg=COLORS["bg_surface"], highlightbackground=COLORS["border_medium"])
            body.configure(bg=COLORS["bg_surface"])
            name_label.configure(bg=COLORS["bg_surface"])
            summary_label.configure(bg=COLORS["bg_surface"])
            self._render_archive_art(
                art,
                info=info,
                width=width,
                height=self._ARCHIVE_ART_HEIGHT,
                surface_fill=COLORS["bg_surface"],
                placeholder_fill=COLORS["bg_high"],
            )
            self._add_archive_delete_control(art, info["path"], width=width)

        self._bind_clickable(
            card,
            lambda p=info["path"]: self._on_view(p),
            on_enter,
            on_leave,
        )

        return card

    def _build_import_tile(self, parent, width: int) -> tk.Frame:
        tile = tk.Frame(
            parent,
            width=width,
            height=self._ARCHIVE_CARD_HEIGHT,
            bg=COLORS["bg"],
            cursor="hand2",
        )
        tile.grid_propagate(False)
        tile.pack_propagate(False)

        surface = tk.Canvas(
            tile,
            bg=COLORS["bg"],
            highlightthickness=0,
            bd=0,
        )
        surface.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(surface, bg=COLORS["bg"])

        icon = tk.Canvas(
            inner,
            width=96,
            height=96,
            bg=COLORS["bg_highest"],
            highlightthickness=0,
            bd=0,
        )
        icon.pack(pady=(0, 28))
        self._draw_import_icon(icon)

        tk.Label(
            inner,
            text="Import Character",
            font=FONTS["card_title_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
            justify=tk.CENTER,
        ).pack()

        tk.Label(
            inner,
            text="LOAD FROM FILE",
            font=FONTS["label_upper_bold"],
            fg=COLORS["fg_dim"],
            bg=COLORS["bg"],
            justify=tk.CENTER,
        ).pack(pady=(16, 0))

        inner_window = surface.create_window(0, 0, window=inner, anchor="center")

        def redraw_surface(border_color: str):
            width_px = max(surface.winfo_width(), 1)
            height_px = max(surface.winfo_height(), 1)
            surface.delete("border")
            surface.create_rectangle(
                1,
                1,
                width_px - 2,
                height_px - 2,
                outline=border_color,
                width=1,
                tags="border",
            )
            surface.coords(inner_window, width_px // 2, height_px // 2)

        def on_surface_configure(_event):
            redraw_surface(COLORS["border_medium"])

        surface.bind("<Configure>", on_surface_configure)

        def on_enter(_event):
            surface.configure(bg=COLORS["bg_surface"])
            redraw_surface(COLORS["outline_dim"])
            inner.configure(bg=COLORS["bg_surface"])
            icon.configure(bg=COLORS["bg_highest"])
            for widget in inner.winfo_children():
                if isinstance(widget, tk.Label):
                    widget.configure(bg=COLORS["bg_surface"])

        def on_leave(_event):
            surface.configure(bg=COLORS["bg"])
            redraw_surface(COLORS["border_medium"])
            inner.configure(bg=COLORS["bg"])
            icon.configure(bg=COLORS["bg_highest"])
            for widget in inner.winfo_children():
                if isinstance(widget, tk.Label):
                    widget.configure(bg=COLORS["bg"])

        self._bind_clickable(surface, self._on_import, on_enter, on_leave)
        return tile

    def _render_archive_art(
        self,
        canvas,
        info: dict,
        width: int,
        height: int,
        surface_fill: str,
        placeholder_fill: str,
    ):
        canvas.delete("all")
        photo = self._build_portrait_photo(
            info.get("biography_image_data", ""),
            width=width,
            height=height,
        )
        if photo is not None:
            canvas.create_image(width // 2, height // 2, image=photo)
            canvas._portrait_photo = photo
        else:
            canvas.configure(bg=placeholder_fill)
            canvas.create_rectangle(0, 0, width, height, fill=placeholder_fill, outline="")
            initial = (info.get("name", "?") or "?")[0].upper()
            canvas.create_text(
                width // 2,
                height // 2 - 18,
                text=initial,
                font=FONTS["hero_title"],
                fill=COLORS["fg"],
            )
            canvas.create_text(
                width // 2,
                height // 2 + 34,
                text="Portrait not set",
                font=FONTS["body_small"],
                fill=COLORS["fg_dim"],
            )

    def _add_archive_delete_control(self, canvas, path: str, width: int):
        canvas.create_rectangle(
            width - 42,
            8,
            width - 8,
            40,
            outline="",
            fill="",
            tags=("delete_control",),
        )
        icon = canvas.create_text(
            width - 18,
            14,
            text="×",
            font=FONTS["heading"],
            fill=COLORS["fg_dim"],
            anchor="ne",
            tags=("delete_control",),
        )

        def on_enter(_event):
            canvas.itemconfigure(icon, fill=COLORS["fg"])

        def on_leave(_event):
            canvas.itemconfigure(icon, fill=COLORS["fg_dim"])

        def on_click(_event, p=path):
            self._on_delete(p)
            return "break"

        canvas.tag_bind("delete_control", "<Enter>", on_enter)
        canvas.tag_bind("delete_control", "<Leave>", on_leave)
        canvas.tag_bind("delete_control", "<Button-1>", on_click)

    def _build_portrait_photo(self, image_data: str, width: int, height: int):
        if not image_data or Image is None or ImageTk is None:
            return None
        try:
            raw = base64.b64decode(image_data)
            source = Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception:
            return None

        src_w, src_h = source.size
        if src_w <= 0 or src_h <= 0:
            return None

        target_ratio = width / float(height)
        source_ratio = src_w / float(src_h)
        if source_ratio > target_ratio:
            crop_w = int(src_h * target_ratio)
            left = max((src_w - crop_w) // 2, 0)
            box = (left, 0, left + crop_w, src_h)
        else:
            crop_h = int(src_w / target_ratio)
            top = max((src_h - crop_h) // 2, 0)
            box = (0, top, src_w, top + crop_h)

        try:
            cropped = source.crop(box).resize((width, height), Image.LANCZOS)
        except Exception:
            return None
        return ImageTk.PhotoImage(cropped)

    def _draw_import_icon(self, canvas):
        canvas.delete("all")
        size = int(min(float(canvas.cget("width")), float(canvas.cget("height"))))
        mid = size // 2
        stroke = max(3, size // 24)

        canvas.create_oval(0, 0, size, size, fill=COLORS["bg_highest"], outline="")
        canvas.create_line(
            mid,
            int(size * 0.25),
            mid,
            int(size * 0.60),
            fill=COLORS["accent_text"],
            width=stroke,
        )
        canvas.create_line(
            int(size * 0.38),
            int(size * 0.38),
            mid,
            int(size * 0.25),
            fill=COLORS["accent_text"],
            width=stroke,
        )
        canvas.create_line(
            int(size * 0.62),
            int(size * 0.38),
            mid,
            int(size * 0.25),
            fill=COLORS["accent_text"],
            width=stroke,
        )
        canvas.create_line(
            int(size * 0.34),
            int(size * 0.70),
            int(size * 0.66),
            int(size * 0.70),
            fill=COLORS["accent_text"],
            width=stroke,
        )
        canvas.create_line(
            int(size * 0.34),
            int(size * 0.70),
            int(size * 0.34),
            int(size * 0.58),
            fill=COLORS["accent_text"],
            width=stroke,
        )
        canvas.create_line(
            int(size * 0.66),
            int(size * 0.70),
            int(size * 0.66),
            int(size * 0.58),
            fill=COLORS["accent_text"],
            width=stroke,
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_create_new(self):
        self.app.show_wizard()

    def _on_import(self):
        path = filedialog.askopenfilename(
            title="Import Character",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        from models.character_store import import_character_from_export, save_character

        try:
            character = import_character_from_export(path, self.app.data)
            save_path = save_character(character, characters_dir())
            self.app.show_viewer(character, save_path)
        except Exception as exc:
            AlertDialog(self.frame, "Import Error", f"Could not import character:\n{exc}")

    def _on_view(self, path):
        from models.character_store import load_character

        try:
            character = load_character(path, self.app.data)
            self.app.show_viewer(character, path)
        except Exception as exc:
            AlertDialog(self.frame, "Load Error", f"Could not load character:\n{exc}")

    def _on_delete(self, path):
        dlg = ConfirmDialog(
            self.frame,
            "Delete Character",
            "Are you sure you want to delete this character?",
        )
        if dlg.result:
            delete_character(path)
            self.refresh_archive()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _bind_clickable(self, widget, command, on_enter=None, on_leave=None):
        def handle_leave(event):
            if on_leave is None:
                return
            try:
                pointer_x, pointer_y = widget.winfo_pointerxy()
                hovered = widget.winfo_containing(pointer_x, pointer_y)
            except tk.TclError:
                hovered = None

            current = hovered
            while current is not None:
                if current is widget:
                    return
                current = getattr(current, "master", None)

            on_leave(event)

        def handle_click(event):
            current_widget = event.widget
            if isinstance(current_widget, tk.Canvas):
                current_items = current_widget.find_withtag("current")
                if current_items:
                    tags = current_widget.gettags(current_items[0])
                    if "delete_control" in tags:
                        return "break"

            command()
            return "break"

        def recurse(current):
            current.configure(cursor="hand2")
            current.bind("<Button-1>", handle_click)
            current.bind("<Enter>", on_enter or (lambda _event: None))
            current.bind("<Leave>", handle_leave)
            for child in current.winfo_children():
                recurse(child)

        recurse(widget)

    def _animate_label_color(self, widget: tk.Label, target_color: str, steps: int = 6, delay: int = 18):
        current_job = getattr(widget, "_color_anim_job", None)
        if current_job:
            try:
                widget.after_cancel(current_job)
            except tk.TclError:
                pass

        start_color = widget.cget("fg")
        start_rgb = self._hex_to_rgb(start_color)
        target_rgb = self._hex_to_rgb(target_color)

        def step(index: int):
            ratio = index / float(steps)
            blended = tuple(
                int(start + ((target - start) * ratio))
                for start, target in zip(start_rgb, target_rgb)
            )
            try:
                widget.configure(fg=self._rgb_to_hex(blended))
            except tk.TclError:
                return

            if index < steps:
                widget._color_anim_job = widget.after(delay, lambda: step(index + 1))
            else:
                widget._color_anim_job = None

        step(1)

    def _hex_to_rgb(self, value: str) -> tuple[int, int, int]:
        color = value.strip().lstrip("#")
        if len(color) == 3:
            color = "".join(ch * 2 for ch in color)
        return tuple(int(color[idx:idx + 2], 16) for idx in (0, 2, 4))

    def _rgb_to_hex(self, value: tuple[int, int, int]) -> str:
        return "#{:02x}{:02x}{:02x}".format(*value)
