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
from gui.theme import COLORS, FONTS, SPACING
from gui.widgets import (
    ScrollableFrame,
    GradientHeader,
    SectionHeader,
    CardFrame,
    AlertDialog,
)


class BiographyStep(WizardStep):
    """Optional biography details: name, backstory, personality, description, portrait."""

    tab_title = "Biography"
    _DEFAULT_NAME = "New Character"

    def build_ui(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)
        self._name_placeholder_armed = False

        # ── Hero header ─────────────────────────────────────────
        hero = GradientHeader(self.frame, min_height=60)
        hero.grid(row=0, column=0, sticky="ew")

        tk.Label(
            hero.inner,
            text="Biography",
            font=FONTS["heading_serif_lg"],
            fg=COLORS["fg"],
            bg=COLORS["bg_hero"],
        ).pack(anchor="w", padx=SPACING["card_pad"], pady=(SPACING["xl"], SPACING["xl"]))

        # ── Scrollable content ──────────────────────────────────
        scroll = ScrollableFrame(self.frame)
        scroll.grid(row=1, column=0, sticky="nsew")
        inner = scroll.inner

        # Grid layout: portrait left + description/personality right, backstory full-width bottom
        inner.columnconfigure(0, weight=1)
        inner.columnconfigure(1, weight=1)
        inner.rowconfigure(2, weight=1)
        inner.rowconfigure(3, weight=1)

        # ── Character Name (full width, top) ────────────────────
        name_section = tk.Frame(inner, bg=COLORS["bg"])
        name_section.grid(row=0, column=0, columnspan=2, sticky="ew",
                          padx=SPACING["lg"], pady=(SPACING["sm"], SPACING["sm"]))

        SectionHeader(name_section, text="Character Name").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        name_card = CardFrame(name_section, pad=SPACING["lg"])
        name_card.pack(fill=tk.X)

        initial_name = self.character.name or self._DEFAULT_NAME
        self.name_var = tk.StringVar(value=initial_name)
        self.name_var.trace_add("write", self._on_name_change)
        self._name_placeholder_armed = initial_name == self._DEFAULT_NAME

        self.name_entry = tk.Entry(
            name_card.inner,
            textvariable=self.name_var,
            font=FONTS["heading_serif"],
            bg=COLORS["bg_container"],
            fg=COLORS["fg"],
            insertbackground=COLORS["fg"],
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=COLORS["border_subtle"],
            highlightcolor=COLORS["accent"],
        )
        self.name_entry.pack(fill=tk.X, ipady=6)
        self.name_entry.bind("<FocusIn>", self._on_name_focus_in, add="+")

        # ── Row 1: Portrait (left) ─────────────────────────────
        portrait_section = tk.Frame(inner, bg=COLORS["bg"])
        portrait_section.grid(row=1, column=0, rowspan=2, sticky="nsew",
                              padx=(SPACING["lg"], SPACING["sm"]),
                              pady=(0, SPACING["sm"]))
        portrait_section.columnconfigure(0, weight=1)

        SectionHeader(portrait_section, text="Portrait").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )

        portrait_card = tk.Frame(portrait_section, bg=COLORS["bg_surface"])
        portrait_card.pack(fill=tk.BOTH, expand=True)
        portrait_card.columnconfigure(0, weight=1)
        self._portrait_frame = portrait_card

        self._canvas = tk.Canvas(
            portrait_card,
            width=260,
            height=100,
            bg=COLORS["bg_container"],
            highlightthickness=0,
            relief=tk.FLAT,
        )
        self._canvas.pack(padx=12, pady=(12, 8), fill=tk.BOTH, expand=True)
        self._canvas.create_text(
            130, 50,
            text="No image selected",
            fill=COLORS["fg_dim"],
            font=FONTS["body"],
            justify=tk.CENTER,
            tags=("placeholder",),
        )
        self._last_portrait_width = 0
        portrait_card.bind("<Configure>", self._on_portrait_frame_configure)

        btns = tk.Frame(portrait_card, bg=COLORS["bg_surface"])
        btns.pack(pady=(0, 12))
        ttk.Button(btns, text="Choose Image...", command=self._choose_image).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(btns, text="Clear Image", command=self._clear_image).pack(
            side=tk.LEFT, padx=(4, 0)
        )

        # ── Row 1 right: Physical Description + Personality stacked ─
        right_stack = tk.Frame(inner, bg=COLORS["bg"])
        right_stack.grid(row=1, column=1, rowspan=2, sticky="nsew",
                         padx=(SPACING["sm"], SPACING["lg"]),
                         pady=(0, SPACING["sm"]))
        right_stack.columnconfigure(0, weight=1)
        right_stack.rowconfigure(1, weight=1)
        right_stack.rowconfigure(3, weight=1)

        SectionHeader(right_stack, text="Physical Description").grid(
            row=0, column=0, sticky="ew", pady=(0, SPACING["sm"])
        )
        self._description = self._make_bio_textbox(right_stack)
        self._description.configure(height=6)
        self._description.grid(row=1, column=0, sticky="nsew", pady=(0, SPACING["sm"]))

        SectionHeader(right_stack, text="Personality").grid(
            row=2, column=0, sticky="ew", pady=(0, SPACING["sm"])
        )
        self._personality = self._make_bio_textbox(right_stack)
        self._personality.configure(height=6)
        self._personality.grid(row=3, column=0, sticky="nsew")

        # ── Row 2: Backstory (full width) ───────────────────────
        backstory_section = tk.Frame(inner, bg=COLORS["bg"])
        backstory_section.grid(row=3, column=0, columnspan=2, sticky="nsew",
                               padx=SPACING["lg"],
                               pady=(SPACING["sm"], SPACING["lg"]))
        backstory_section.columnconfigure(0, weight=1)
        backstory_section.rowconfigure(1, weight=1)

        SectionHeader(backstory_section, text="Character Backstory").pack(
            fill=tk.X, pady=(0, SPACING["sm"])
        )
        self._backstory = self._make_bio_textbox(backstory_section)
        self._backstory.configure(height=8)
        self._backstory.pack(fill=tk.BOTH, expand=True)

        # Bind focus-out to save
        for w in (self._backstory, self._personality, self._description):
            w.bind("<FocusOut>", self._save_text_fields)

        # Keep references so PhotoImage isn't garbage-collected
        self._photo = None
        self._photo_display = None

    # ── helpers ──────────────────────────────────────────────────

    def _make_bio_textbox(self, parent) -> tk.Text:
        return tk.Text(
            parent,
            wrap=tk.WORD,
            bg=COLORS["bg_container"],
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

    def _normalized_name(self) -> str:
        return str(self.name_var.get() or "").strip()

    # ── data sync ────────────────────────────────────────────────

    def on_enter(self):
        if self.character.name and self.character.name != self.name_var.get():
            self.name_var.set(self.character.name)
            self._name_placeholder_armed = self.character.name == self._DEFAULT_NAME
        elif not self.character.name:
            self.character.name = self.name_var.get()
            self._name_placeholder_armed = self.name_var.get() == self._DEFAULT_NAME
        self._set_text(self._backstory, self.character.biography_backstory or "")
        self._set_text(self._personality, self.character.biography_personality or "")
        self._set_text(self._description, self.character.biography_description or "")
        self._refresh_image()

    def _on_name_focus_in(self, _event=None):
        if not self._name_placeholder_armed:
            return
        if self.name_var.get() != self._DEFAULT_NAME:
            self._name_placeholder_armed = False
            return
        self._name_placeholder_armed = False
        self.name_var.set("")
        self.name_entry.icursor(tk.END)

    def _on_name_change(self, *args):
        self.character.name = self.name_var.get()
        self.notify_change()

    def is_valid(self) -> bool:
        name = self._normalized_name()
        return bool(name) and name != self._DEFAULT_NAME

    def _save_text_fields(self, _event=None):
        self.character.biography_backstory = self._text_value(self._backstory)
        self.character.biography_personality = self._text_value(self._personality)
        self.character.biography_description = self._text_value(self._description)
        self.notify_change()

    # ── image handling ──────────────────────────────────────────

    def _on_portrait_frame_configure(self, event):
        new_width = event.width
        if new_width > 1 and new_width != self._last_portrait_width:
            self._last_portrait_width = new_width
            self._refresh_image()

    def _get_portrait_width(self):
        fw = self._portrait_frame.winfo_width()
        if fw > 1:
            return max(100, fw - 24)
        return 260

    def _refresh_image(self):
        self._canvas.delete("all")
        self._photo = None
        self._photo_display = None
        cw = self._get_portrait_width()

        data = self.character.biography_image_data or ""
        if not data:
            self._canvas.configure(height=100)
            self._canvas.create_text(
                cw // 2, 50,
                text="No image selected",
                fill=COLORS["fg_dim"],
                font=FONTS["body"],
                justify=tk.CENTER,
            )
            return

        try:
            raw = base64.b64decode(data)
        except Exception:
            self._canvas.configure(height=100)
            self._canvas.create_text(
                cw // 2, 50,
                text="Image data is invalid",
                fill=COLORS["fg_dim"],
                font=FONTS["body_small"],
                justify=tk.CENTER,
            )
            return

        try:
            if Image is not None and ImageTk is not None:
                pil_img = Image.open(io.BytesIO(raw))
                pil_img.thumbnail((cw, cw * 4))
                iw, ih = pil_img.size
                self._canvas.configure(width=iw, height=ih)
                display = ImageTk.PhotoImage(pil_img)
                self._photo_display = display
                self._canvas.create_image(iw // 2, ih // 2, image=display)
                return

            img_format = (self.character.biography_image_format or "").lower()
            if img_format in {"png", ""}:
                photo = tk.PhotoImage(data=base64.b64encode(raw).decode("ascii"))
            else:
                raise tk.TclError("Unsupported preview format")
        except Exception:
            self._canvas.configure(height=100)
            self._canvas.create_text(
                cw // 2, 50,
                text="Image loaded for export\nbut preview is unavailable",
                fill=COLORS["fg_dim"],
                font=FONTS["body_small"],
                justify=tk.CENTER,
            )
            return

        w = max(1, int(photo.width()))
        h = max(1, int(photo.height()))
        scale = max((w + cw - 1) // cw, 1)
        display = photo.subsample(scale) if scale > 1 else photo
        dw, dh = int(display.width()), int(display.height())
        self._canvas.configure(width=dw, height=dh)
        self._photo = photo
        self._photo_display = display
        self._canvas.create_image(dw // 2, dh // 2, image=display)

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
