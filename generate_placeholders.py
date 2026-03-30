"""Generate placeholder tile images for species and classes.

Creates dark gradient PNG images with the name overlaid in a serif font.
Images are saved to images/species/{slug}.png and images/classes/{slug}.png.

Usage:
    python generate_placeholders.py [--force]
"""

import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

WIDTH = 300
HEIGHT = 200


def _slug(name: str) -> str:
    return name.lower().replace(" ", "_").replace("'", "")


def _make_gradient(w: int, h: int, top_rgb: tuple, bot_rgb: tuple) -> Image.Image:
    img = Image.new("RGB", (w, h))
    for y in range(h):
        ratio = y / max(h - 1, 1)
        r = int(top_rgb[0] + (bot_rgb[0] - top_rgb[0]) * ratio)
        g = int(top_rgb[1] + (bot_rgb[1] - top_rgb[1]) * ratio)
        b = int(top_rgb[2] + (bot_rgb[2] - top_rgb[2]) * ratio)
        for x in range(w):
            img.putpixel((x, y), (r, g, b))
    return img


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Try common serif fonts
    for name in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/System/Library/Fonts/Georgia.ttf",
        "C:/Windows/Fonts/georgia.ttf",
    ]:
        if os.path.exists(name):
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def generate_image(name: str, out_path: str, palette: str = "blue", force: bool = False):
    if os.path.exists(out_path) and not force:
        return

    if palette == "blue":
        top, bot = (26, 26, 46), (22, 33, 62)
    else:  # red/crimson for classes
        top, bot = (45, 27, 27), (26, 18, 22)

    img = _make_gradient(WIDTH, HEIGHT, top, bot)
    draw = ImageDraw.Draw(img)

    # Draw name centered
    font = _get_font(28)
    bbox = draw.textbbox((0, 0), name, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (WIDTH - tw) // 2
    y = (HEIGHT - th) // 2
    # Subtle shadow
    draw.text((x + 1, y + 1), name, fill=(0, 0, 0), font=font)
    draw.text((x, y), name, fill=(220, 210, 200), font=font)

    # Thin border
    draw.rectangle([0, 0, WIDTH - 1, HEIGHT - 1], outline=(45, 37, 37), width=1)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path)


def main():
    force = "--force" in sys.argv

    base = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(base, "data")

    with open(os.path.join(data_path, "species.json")) as f:
        species = json.load(f)
    with open(os.path.join(data_path, "classes.json")) as f:
        classes = json.load(f)

    img_dir = os.path.join(base, "images")

    for sp in species:
        slug = _slug(sp["name"])
        out = os.path.join(img_dir, "species", f"{slug}.png")
        generate_image(sp["name"], out, palette="blue", force=force)
        print(f"  species/{slug}.png")

    for cls in classes:
        slug = _slug(cls["name"])
        out = os.path.join(img_dir, "classes", f"{slug}.png")
        generate_image(cls["name"], out, palette="red", force=force)
        print(f"  classes/{slug}.png")

    print(f"\nDone. Images in {img_dir}")


if __name__ == "__main__":
    main()
