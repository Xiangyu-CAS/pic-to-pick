#!/usr/bin/env python3
"""
Build a compact product reference board image from downloaded product pictures.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageOps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a product board from local images.")
    parser.add_argument("--images-dir", required=True, help="Directory containing item-*.jpg files")
    parser.add_argument(
        "--cart-items-json",
        help="Optional cart-items json; when set, board uses only current cart item local_image entries",
    )
    parser.add_argument(
        "--allow-extra-images",
        action="store_true",
        help="Allow extra item-*.jpg files not referenced by cart-items-json (default: false)",
    )
    parser.add_argument("--output", required=True, help="Output board image path")
    parser.add_argument("--thumb", type=int, default=360, help="Thumbnail size (square)")
    parser.add_argument("--padding", type=int, default=20, help="Outer/cell padding")
    parser.add_argument("--bg", default="#f7f5f1", help="Background color")
    return parser.parse_args()


def files_from_cart_items(src_dir: Path, cart_json: Path, allow_extra_images: bool = False) -> list[Path]:
    try:
        data = json.loads(cart_json.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"Invalid cart items json: {cart_json} ({exc})") from exc
    if not isinstance(data, list):
        raise SystemExit(f"cart items json must be a list: {cart_json}")

    out: list[Path] = []
    seen = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        local_image = str(item.get("local_image") or "").strip()
        if not local_image:
            continue
        p = Path(local_image)
        if not p.is_absolute():
            p = (src_dir.parent / p).resolve()
        if not p.exists():
            continue
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)

    all_item_files = sorted([p.resolve() for p in src_dir.glob("item-*.jpg") if p.is_file()])
    selected_set = {p.resolve() for p in out}
    extra = [p for p in all_item_files if p not in selected_set]
    if extra and not allow_extra_images:
        extra_names = ", ".join(p.name for p in extra[:8])
        raise SystemExit(
            "Found stale product images not referenced by current cart-items-json: "
            + extra_names
            + ". Clean product-images-real or pass --allow-extra-images."
        )
    return out


def main() -> None:
    args = parse_args()
    src_dir = Path(args.images_dir).expanduser().resolve()
    out_path = Path(args.output).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.cart_items_json:
        cart_json = Path(args.cart_items_json).expanduser().resolve()
        files = files_from_cart_items(
            src_dir,
            cart_json,
            allow_extra_images=args.allow_extra_images,
        )
    else:
        files = sorted([p for p in src_dir.glob("item-*.jpg") if p.is_file()])
    if not files:
        raise SystemExit(f"No item-*.jpg found in {src_dir}")

    n = len(files)
    cols = min(4, max(2, math.ceil(math.sqrt(n))))
    rows = math.ceil(n / cols)
    cell = args.thumb
    pad = args.padding

    width = cols * cell + (cols + 1) * pad
    height = rows * cell + (rows + 1) * pad
    canvas = Image.new("RGB", (width, height), args.bg)

    for idx, path in enumerate(files):
        with Image.open(path) as im:
            tile = ImageOps.fit(im.convert("RGB"), (cell, cell), method=Image.Resampling.LANCZOS)
        r = idx // cols
        c = idx % cols
        x = pad + c * (cell + pad)
        y = pad + r * (cell + pad)
        canvas.paste(tile, (x, y))

    canvas.save(out_path, format="JPEG", quality=88, optimize=True)
    print(f"board: {out_path}")
    print(f"items_used: {len(files)}")


if __name__ == "__main__":
    main()
