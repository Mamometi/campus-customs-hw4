"""Remove photo backgrounds and pick a contrasting backdrop per product (P9).

The source photos mix a white studio background with black letterbox bars, so
dark garments sit on black and light garments on white. This script:

1. Marks as background every near-black or near-white region connected to the
   image border (bars + studio backdrop). Garment pixels are never border-
   connected background, so a navy hoodie touching the frame is kept.
2. Softens the cut edge (1px erode + slight blur) to hide JPEG halos.
3. Measures the garment's median brightness and chooses a contrasting backdrop:
   dark merch -> white, light merch -> charcoal.
4. Writes a transparent WebP to data/products_cutout/<product_id>.webp and a
   manifest.json with the backdrop color, read by db.build_product().

Originals in data/products/ are never modified.
Run from backend/: .venv/bin/python scripts/make_cutouts.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "products"
OUT = ROOT / "data" / "products_cutout"

LIGHT_BG = "#ffffff"
DARK_BG = "#1f2329"
LIGHT_GARMENT_LUMA = 0.5  # median garment luminance above this (whites, creams, heather grays) -> dark backdrop

# Background = border-connected pixels that are near-pure black (letterbox bars)
# or near-pure white (studio backdrop) AND colorless. Tight on purpose: navy
# shadows carry a blue tint and off-white tees sit around 240, so both survive.
NEAR_BLACK = 16
NEAR_WHITE = 246
MAX_CHROMA = 10
MIN_FOREGROUND = 0.15  # below this the cut failed -> keep the original photo


def background_mask(rgb: np.ndarray) -> np.ndarray:
    r, g, b = (rgb[..., i].astype(int) for i in range(3))
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    colorless = (mx - mn) <= MAX_CHROMA
    candidate = colorless & ((mx <= NEAR_BLACK) | (mn >= NEAR_WHITE))
    labels, _ = ndimage.label(candidate)
    border_labels = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    border_labels = border_labels[border_labels != 0]
    return np.isin(labels, border_labels)


def process(path: Path) -> dict:
    img = Image.open(path).convert("RGB")
    rgb = np.asarray(img)
    bg = background_mask(rgb)
    fg = ~bg
    # Drop specks, fill holes inside the garment, shave the halo.
    fg = ndimage.binary_opening(fg, iterations=1)
    fg = ndimage.binary_fill_holes(fg)
    fg = ndimage.binary_erosion(fg, iterations=1)

    if fg.mean() < MIN_FOREGROUND:
        # Safety net: don't ship a broken cutout. Use the photo as-is on its own border color.
        border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
        bg_hex = "#{:02x}{:02x}{:02x}".format(*np.median(border, axis=0).astype(int))
        img.save(OUT / f"{path.stem}.webp", "WEBP", quality=88, method=4)
        return {"bg": bg_hex, "garment_luma": None, "foreground": round(float(fg.mean()), 3), "fallback": True}

    alpha = Image.fromarray((fg * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    rgba = img.copy()
    rgba.putalpha(alpha)

    pixels = rgb[fg].astype(float) / 255.0
    luma = float(np.median(0.2126 * pixels[:, 0] + 0.7152 * pixels[:, 1] + 0.0722 * pixels[:, 2])) if len(pixels) else 0.5
    backdrop = DARK_BG if luma > LIGHT_GARMENT_LUMA else LIGHT_BG

    product_id = path.stem
    rgba.save(OUT / f"{product_id}.webp", "WEBP", quality=88, method=4)
    return {"bg": backdrop, "garment_luma": round(luma, 3), "foreground": round(float(fg.mean()), 3)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for path in sorted(SRC.glob("*.jpg")):
        manifest[path.stem] = process(path)
        info = manifest[path.stem]
        print(f"{path.stem:55s} luma={info['garment_luma']} fg={info['foreground']:.2f} bg={info['bg']}" + (" FALLBACK" if info.get("fallback") else ""), flush=True)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    dark = sum(1 for v in manifest.values() if v["bg"] == DARK_BG)
    print(f"\n{len(manifest)} cutouts written to {OUT} ({dark} on dark backdrop, {len(manifest) - dark} on white)")


if __name__ == "__main__":
    sys.exit(main())
