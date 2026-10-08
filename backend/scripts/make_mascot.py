"""Cut Handsome Dan (Yale's bulldog) out of the store's own product photos (P10).

Two Campus Customs products carry a classic white-print bulldog graphic:
  - district-vit-crewneck-vintage-bulldog          -> head  (chat avatar/launcher)
  - district-vit-crewneck-vintage-standing-bulldog -> full  (chat welcome, home)

The print is white ink on heather fabric, so the "linework" is fabric showing
through. We isolate the largest white-ink shape in the lower part of the shirt,
fill its silhouette, upscale 4x, and re-render it as crisp two-tone art: white
body + Yale-navy lines on a transparent background.

Output: frontend/public/handsome-dan-head.png, frontend/public/handsome-dan.png
Run from backend/: .venv/bin/python scripts/make_mascot.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "products"
OUT = ROOT / "frontend" / "public"

NAVY = (0, 53, 107)
WHITE = (255, 255, 255)
SCALE = 4


def luminance(rgb: np.ndarray) -> np.ndarray:
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def extract(product_id: str, min_y: int, out_name: str) -> None:
    rgb = np.asarray(Image.open(SRC / f"{product_id}.jpg").convert("RGB")).astype(float)
    lum = luminance(rgb)
    chroma = rgb.max(-1) - rgb.min(-1)
    ink = (lum > 200) & (chroma < 40)

    # Ignore the photo's own white background (border-connected) and anything above min_y (the YALE wordmark).
    labels, n = ndimage.label(ink)
    border = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])))
    sizes = ndimage.sum(ink, labels, range(1, n + 1))
    centers = ndimage.center_of_mass(ink, labels, range(1, n + 1))
    # The dog is printed as several white shapes (head, sweater, legs): keep every
    # sizeable non-background shape below the wordmark.
    keep = [
        i for i, (size, (cy, _)) in enumerate(zip(sizes, centers), start=1)
        if i not in border and size > 30 and cy > min_y
    ]
    dog = np.isin(labels, keep)

    # Silhouette = the ink shape with its interior line gaps filled.
    silhouette = ndimage.binary_fill_holes(ndimage.binary_closing(dog, iterations=4))
    ys, xs = np.where(silhouette)
    pad = 6
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, lum.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, lum.shape[1])

    size = ((x1 - x0) * SCALE, (y1 - y0) * SCALE)
    lum_up = np.asarray(Image.fromarray(lum[y0:y1, x0:x1].astype(np.uint8)).resize(size, Image.BICUBIC)).astype(float)
    sil_up = np.asarray(
        Image.fromarray((silhouette[y0:y1, x0:x1] * 255).astype(np.uint8)).resize(size, Image.BICUBIC)
    ) > 127

    # Inside the silhouette: bright = white ink, dark = navy line.
    is_white = lum_up > 165
    out = np.zeros((*lum_up.shape, 4), dtype=np.uint8)
    out[..., :3] = np.where(is_white[..., None], WHITE, NAVY)
    alpha = Image.fromarray((sil_up * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))
    img = Image.fromarray(out, "RGBA")
    img.putalpha(alpha)
    img = img.filter(ImageFilter.SMOOTH)
    img.save(OUT / out_name, optimize=True)
    print(f"{out_name}: {img.size[0]}x{img.size[1]}")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    extract("district-vit-crewneck-vintage-bulldog", min_y=180, out_name="handsome-dan-head.png")
    extract("district-vit-crewneck-vintage-standing-bulldog", min_y=100, out_name="handsome-dan.png")
