#!/usr/bin/env python3
"""
Create a side-by-side compare image from base and preview.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create side-by-side compare image.")
    parser.add_argument("--base", required=True, help="Base image path")
    parser.add_argument("--preview", required=True, help="Preview image path")
    parser.add_argument("--output", required=True, help="Output compare image path")
    parser.add_argument("--height", type=int, default=960, help="Target output height")
    parser.add_argument("--gap", type=int, default=20, help="Gap between two images")
    parser.add_argument("--bg", default="#f7f5f1", help="Background color")
    return parser.parse_args()


def fit_height(im: Image.Image, target_h: int) -> Image.Image:
    w, h = im.size
    if h <= 0:
        return im
    new_w = max(1, int(round(w * target_h / h)))
    return im.resize((new_w, target_h), Image.Resampling.LANCZOS)


def main() -> None:
    args = parse_args()
    base_path = Path(args.base).expanduser().resolve()
    preview_path = Path(args.preview).expanduser().resolve()
    out_path = Path(args.output).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(base_path) as b:
        base = fit_height(ImageOps.exif_transpose(b).convert("RGB"), args.height)
    with Image.open(preview_path) as p:
        preview = fit_height(ImageOps.exif_transpose(p).convert("RGB"), args.height)

    width = base.width + args.gap + preview.width
    canvas = Image.new("RGB", (width, args.height), args.bg)
    canvas.paste(base, (0, 0))
    canvas.paste(preview, (base.width + args.gap, 0))
    canvas.save(out_path, format="JPEG", quality=90, optimize=True)
    print(f"compare: {out_path}")


if __name__ == "__main__":
    main()
