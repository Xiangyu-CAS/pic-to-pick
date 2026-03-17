#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "google-genai>=1.0.0",
#   "pillow>=10.0.0",
# ]
# ///
"""
Generate or edit images with Nano Banana Pro (Gemini image model).

This is a local copy for pic-to-pick so the skill is self-contained.
Supports both single-image and multi-image edit prompts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from io import BytesIO
from pathlib import Path

SUPPORTED_ASPECT_RATIOS: dict[str, float] = {
    "1:1": 1.0,
    "2:3": 2 / 3,
    "3:2": 3 / 2,
    "3:4": 3 / 4,
    "4:3": 4 / 3,
    "9:16": 9 / 16,
    "16:9": 16 / 9,
    "21:9": 21 / 9,
}

CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "sofa": ("sofa", "couch", "loveseat", "sectional"),
    "stool/ottoman": ("stool", "ottoman", "footstool", "foot stool", "bench"),
    "rug": ("rug", "carpet", "mat"),
    "curtain": ("curtain", "drape", "drapes", "blind", "window panel"),
    "floor lamp": ("floor lamp", "standing lamp", "lamp"),
    "coffee table": ("coffee table", "tea table", "center table"),
    "armchair": ("armchair", "accent chair", "single chair"),
    "side table": ("side table", "end table", "nightstand"),
}


def get_api_key(provided_key: str | None) -> str | None:
    if provided_key:
        return provided_key
    return os.environ.get("GEMINI_API_KEY")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate images using Nano Banana Pro (Gemini image model)."
    )
    parser.add_argument("--prompt", "-p", required=True, help="Image prompt/instructions")
    parser.add_argument("--filename", "-f", required=True, help="Output filename")
    parser.add_argument(
        "--input-image",
        "-i",
        action="append",
        default=[],
        help="Input image path for editing (repeatable)",
    )
    parser.add_argument(
        "--resolution",
        "-r",
        choices=["1K", "2K", "4K"],
        default="1K",
        help="Output resolution (default: 1K)",
    )
    parser.add_argument(
        "--model",
        default="gemini-3.1-flash-image-preview",
        help="Gemini image model name",
    )
    parser.add_argument(
        "--aspect-ratio",
        default="auto",
        choices=["auto", "1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9", "21:9"],
        help="Output aspect ratio. 'auto' maps to nearest supported ratio from first input image.",
    )
    parser.add_argument(
        "--cart-items-json",
        help="Path to cart-items-downloaded.json or cart-items-clean.json",
    )
    parser.add_argument(
        "--enforce-cart-only",
        action="store_true",
        help="Append hard constraints so render includes only cart item categories.",
    )
    parser.add_argument(
        "--must-have-category",
        action="append",
        default=[],
        help="Required object category (repeatable), e.g. sofa, stool/ottoman, rug.",
    )
    parser.add_argument(
        "--enforce-structure-lock",
        action="store_true",
        help="Append hard constraints to preserve architecture and camera geometry.",
    )
    parser.add_argument("--api-key", "-k", help="Gemini API key override")
    return parser.parse_args()


def load_images(paths: list[str]):
    from PIL import Image as PILImage

    images = []
    for p in paths:
        try:
            images.append(PILImage.open(p))
        except Exception as exc:  # noqa: BLE001
            print(f"Error loading input image '{p}': {exc}", file=sys.stderr)
            sys.exit(1)
    return images


def choose_resolution(default_res: str, images) -> str:
    # Keep default behavior deterministic: no implicit upscaling.
    # If higher resolution is needed, pass -r 2K or -r 4K explicitly.
    return default_res


def choose_aspect_ratio(aspect_ratio_arg: str, images) -> str | None:
    if aspect_ratio_arg != "auto":
        return aspect_ratio_arg
    if not images:
        return None
    w, h = images[0].size
    if h == 0:
        return None
    source_ratio = w / h
    nearest = min(
        SUPPORTED_ASPECT_RATIOS.items(),
        key=lambda x: abs(x[1] - source_ratio),
    )[0]
    print(
        f"Auto aspect ratio from first input: {w}x{h} ({source_ratio:.3f}) -> {nearest}"
    )
    return nearest


def save_first_image_part(response, output_path: Path) -> bool:
    from PIL import Image as PILImage

    for part in response.parts:
        if getattr(part, "inline_data", None) is None:
            continue
        image_data = part.inline_data.data
        if isinstance(image_data, str):
            import base64

            image_data = base64.b64decode(image_data)
        image = PILImage.open(BytesIO(image_data))
        if image.mode == "RGBA":
            rgb = PILImage.new("RGB", image.size, (255, 255, 255))
            rgb.paste(image, mask=image.split()[3])
            rgb.save(str(output_path), "PNG")
        elif image.mode == "RGB":
            image.save(str(output_path), "PNG")
        else:
            image.convert("RGB").save(str(output_path), "PNG")
        return True
    return False


def load_cart_items(cart_items_json: str) -> list[dict]:
    path = Path(cart_items_json).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"cart items json not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("cart items json must be a list")
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        out.append(item)
    if not out:
        raise ValueError("cart items json has no valid items")
    return out


def infer_categories_from_title(title: str) -> set[str]:
    text = re.sub(r"\s+", " ", title).strip().lower()
    hit: set[str] = set()
    for category, patterns in CATEGORY_PATTERNS.items():
        if any(p in text for p in patterns):
            hit.add(category)
    return hit


def build_guardrail_prompt(
    base_prompt: str,
    cart_items: list[dict] | None,
    enforce_cart_only: bool,
    must_have_categories: list[str],
    enforce_structure_lock: bool,
) -> str:
    constraints: list[str] = []

    if enforce_structure_lock:
        constraints.extend(
            [
                "Architecture and camera lock: keep door/window/wall positions unchanged.",
                "Keep built-ins, ceiling lines, floor perspective, and camera viewpoint unchanged.",
                "Preserve framing and composition ratio consistent with Image-1.",
                "Only add soft furnishings; do not alter room layout or structural geometry.",
            ]
        )

    if enforce_cart_only:
        if not cart_items:
            raise ValueError("--enforce-cart-only requires --cart-items-json")
        allowed_titles = [str(x.get("title", "")).strip() for x in cart_items if x.get("title")]
        allowed_categories: set[str] = set()
        for title in allowed_titles:
            allowed_categories |= infer_categories_from_title(title)
        if not allowed_categories:
            raise ValueError(
                "Unable to infer any categories from cart titles; add clearer titles or disable --enforce-cart-only"
            )

        must_have_normalized = [x.strip().lower() for x in must_have_categories if x.strip()]
        missing = [x for x in must_have_normalized if x not in allowed_categories]
        if missing:
            raise ValueError(
                "Missing required category in cart: "
                + ", ".join(missing)
                + ". Add these products to cart first, then regenerate."
            )

        constraints.append(
            "Cart-only object rule: only render purchasable objects that exist in the provided cart items."
        )
        constraints.append(
            "Do not add any non-cart furniture/decor objects, even if stylistically plausible."
        )
        constraints.append(
            "Allowed object categories: " + ", ".join(sorted(allowed_categories)) + "."
        )
        constraints.append("Cart item titles:")
        constraints.extend([f"- {t}" for t in allowed_titles])

    if not constraints:
        return base_prompt

    hard_block = "\n".join([f"- {x}" if not x.startswith("- ") else x for x in constraints])
    return (
        base_prompt.strip()
        + "\n\nHard constraints (must follow):\n"
        + hard_block
    )


def main() -> None:
    args = parse_args()
    api_key = get_api_key(args.api_key)
    if not api_key:
        print("Error: No API key provided.", file=sys.stderr)
        print("Set GEMINI_API_KEY or pass --api-key.", file=sys.stderr)
        sys.exit(1)

    from google import genai
    from google.genai import types

    output_path = Path(args.filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cart_items = None
    if args.cart_items_json:
        try:
            cart_items = load_cart_items(args.cart_items_json)
        except Exception as exc:  # noqa: BLE001
            print(f"Error loading cart items: {exc}", file=sys.stderr)
            sys.exit(1)

    try:
        final_prompt = build_guardrail_prompt(
            base_prompt=args.prompt,
            cart_items=cart_items,
            enforce_cart_only=args.enforce_cart_only,
            must_have_categories=args.must_have_category,
            enforce_structure_lock=args.enforce_structure_lock,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Error building constrained prompt: {exc}", file=sys.stderr)
        sys.exit(1)

    images = load_images(args.input_image)
    resolution = choose_resolution(args.resolution, images)
    aspect_ratio = choose_aspect_ratio(args.aspect_ratio, images)
    if images:
        print(f"Loaded {len(images)} input image(s)")
        contents = [*images, final_prompt]
        ratio_msg = f", aspect ratio {aspect_ratio}" if aspect_ratio else ""
        print(f"Editing image(s) with resolution {resolution}{ratio_msg}...")
    else:
        contents = final_prompt
        ratio_msg = f", aspect ratio {aspect_ratio}" if aspect_ratio else ""
        print(f"Generating image with resolution {resolution}{ratio_msg}...")

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=args.model,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(
                    image_size=resolution,
                    aspect_ratio=aspect_ratio,
                ),
            ),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Error generating image: {exc}", file=sys.stderr)
        sys.exit(1)

    saved = save_first_image_part(response, output_path)
    if not saved:
        print("Error: No image returned by model.", file=sys.stderr)
        sys.exit(1)

    print(f"Image saved: {output_path.resolve()}")


if __name__ == "__main__":
    main()
