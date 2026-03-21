"""Biography step for the character creation wizard."""

import base64
import io
import tkinter as tk
from tkinter import ttk, filedialog

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover
    Image = None
    ImageTk = None

from gui.base_step import WizardStep
from gui.theme import COLORS, FONTS
from gui.widgets import AlertDialog


class BiographyStep(WizardStep):
    """Optional biography details: backstory, personality, description, portrait."""

    tab_title = "Biography"

    def build_ui(self):
        self.frame.columnconfigure(0, weight=2)
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(0, weight=1)

        # --- Left column: text fields ---
        left = ttk.Frame(self.frame)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=(8, 8))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        left.rowconfigure(3, weight=1)
        left.rowconfigure(5, weight=1)

        ttk.Label(left, text="Backstory", style="Subheading.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self._backstory = self._make_textbox(left)
        self._backstory.grid(row=1, column=0, sticky="nsew", pady=(0, 8))

        ttk.Label(left, text="Personality", style="Subheading.TLabel").grid(
            row=2, column=0, sticky="w", pady=(0, 4)
        )
        self._personality = self._make_textbox(left)
        self._personality.grid(row=3, column=0, sticky="nsew", pady=(0, 8))

        ttk.Label(left, text="Description", style="Subheading.TLabel").grid(
            row=4, column=0, sticky="w", pady=(0, 4)
        )
        self._description = self._make_textbox(left)
        self._description.grid(row=5, column=0, sticky="nsew")

        for w in (self._backstory, self._personality, self._description):
            w.bind("<FocusOut>", self._save_text_fields)

        # --- Right column: portrait ---
        right = ttk.LabelFrame(self.frame, text="Portrait")
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 8), pady=(8, 8))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(
            right,
            width=260,
            height=320,
            bg=COLORS["bg_light"],
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            relief=tk.FLAT,
        )
        self._canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self._canvas.create_text(
            130, 160,
            text="No image selected",
            fill=COLORS["fg_dim"],
            font=FONTS["body"],
            justify=tk.CENTER,
            tags=("placeholder",),
        )
        self._last_canvas_size = (0, 0)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        btns = ttk.Frame(right)
        btns.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Choose Image...", command=self._choose_image).pack(
            side=tk.LEFT
        )
        ttk.Button(btns, text="Clear Image", command=self._clear_image).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        # Keep references so PhotoImage isn't garbage-collected
        self._photo = None
        self._photo_display = None

    # ---- helpers ----

    def _make_textbox(self, parent) -> tk.Text:
        return tk.Text(
            parent,
            wrap=tk.WORD,
            bg=COLORS["bg_light"],
            fg=COLORS["fg"],
            font=FONTS["body"],
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT,
            spacing1=2,
            spacing3=2,
            padx=10,
            pady=8,
        )

    def _text_value(self, widget: tk.Text) -> str:
        return widget.get("1.0", tk.END).rstrip("\n")

    def _set_text(self, widget: tk.Text, value: str):
        widget.delete("1.0", tk.END)
        widget.insert("1.0", value)

    # ---- data sync ----

    def on_enter(self):
        self._set_text(self._backstory, self.character.biography_backstory or "")
        self._set_text(self._personality, self.character.biography_personality or "")
        self._set_text(self._description, self.character.biography_description or "")
        self._refresh_image()

    def _save_text_fields(self, _event=None):
        self.character.biography_backstory = self._text_value(self._backstory)
        self.character.biography_personality = self._text_value(self._personality)
        self.character.biography_description = self._text_value(self._description)
        self.notify_change()

    # ---- image handling ----

    def _canvas_center(self):
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        if cw <= 1:
            cw = self._canvas.winfo_reqwidth()
        if ch <= 1:
            ch = self._canvas.winfo_reqheight()
        return cw, ch

    def _on_canvas_configure(self, event):
        new_size = (event.width, event.height)
        if new_size != self._last_canvas_size and new_size[0] > 1 and new_size[1] > 1:
            self._last_canvas_size = new_size
            self._refresh_image()

    def _refresh_image(self):
        self._canvas.delete("all")
        self._photo = None
        self._photo_display = None
        cw, ch = self._canvas_center()
        cx, cy = cw // 2, ch // 2

        data = self.character.biography_image_data or ""
        if not data:
            self._canvas.create_text(
                cx, cy,
                text="No image selected",
                fill=COLORS["fg_dim"],
                font=FONTS["body"],
                justify=tk.CENTER,
            )
            return

        try:
            raw = base64.b64decode(data)
        except Exception:
            self._canvas.create_text(
                cx, cy,
                text="Image data is invalid",
                fill=COLORS["fg_dim"],
                font=FONTS["body_small"],
                justify=tk.CENTER,
            )
            return

        try:
            if Image is not None and ImageTk is not None:
                pil_img = Image.open(io.BytesIO(raw))
                pil_img.thumbnail((cw, ch))
                display = ImageTk.PhotoImage(pil_img)
                self._photo_display = display
                self._canvas.create_image(cx, cy, image=display)
                return

            img_format = (self.character.biography_image_format or "").lower()
            if img_format in {"png", ""}:
                photo = tk.PhotoImage(data=base64.b64encode(raw).decode("ascii"))
            else:
                raise tk.TclError("Unsupported preview format")
        except Exception:
            self._canvas.create_text(
                cx, cy,
                text="Image loaded for export\nbut preview is unavailable",
                fill=COLORS["fg_dim"],
                font=FONTS["body_small"],
                justify=tk.CENTER,
            )
            return

        max_w, max_h = cw, ch
        w = max(1, int(photo.width()))
        h = max(1, int(photo.height()))
        scale = max((w + max_w - 1) // max_w, (h + max_h - 1) // max_h, 1)
        display = photo.subsample(scale) if scale > 1 else photo
        self._photo = photo
        self._photo_display = display
        self._canvas.create_image(cx, cy, image=display)

    def _choose_image(self):
        path = filedialog.askopenfilename(
            title="Choose Character Portrait",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError as e:
            AlertDialog(
                self.frame.winfo_toplevel(),
                "Biography Image",
                f"Could not load image:\n{e}",
            )
            return

        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        img_format = "jpeg" if ext in {"jpg", "jpeg"} else "png"
        if Image is not None:
            try:
                pil_img = Image.open(io.BytesIO(raw))
                fmt = (pil_img.format or "").lower()
                if fmt in {"jpg", "jpeg"}:
                    img_format = "jpeg"
                elif fmt == "png":
                    img_format = "png"
            except Exception:
                pass

        self.character.biography_image_data = base64.b64encode(raw).decode("ascii")
        self.character.biography_image_format = img_format
        self._refresh_image()
        self.notify_change()

    def _clear_image(self):
        if not (self.character.biography_image_data or self.character.biography_image_format):
            return
        self.character.biography_image_data = ""
        self.character.biography_image_format = ""
        self._refresh_image()
        self.notify_change()
