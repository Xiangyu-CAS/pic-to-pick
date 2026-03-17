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
    # OOTD / outfit
    "top": ("t-shirt", "tee", "shirt", "blouse", "sweater", "hoodie", "top"),
    "bottom": ("pants", "trousers", "jeans", "skirt", "shorts", "bottom"),
    "outerwear": ("jacket", "coat", "cardigan", "windbreaker", "outerwear"),
    "dress": ("dress", "one-piece", "one piece"),
    "shoes": ("shoe", "sneaker", "boots", "sandals", "loafer"),
    "hat": ("hat", "cap", "beanie", "bucket hat"),
    "bag": ("bag", "backpack", "crossbody", "purse", "tote"),
    "socks": ("sock", "stocking", "hosiery"),
    "accessory": ("scarf", "belt", "watch", "glasses", "sunglasses", "bracelet", "necklace"),
    # Beauty / makeup
    "foundation": ("foundation", "bb cream", "cc cream", "concealer", "primer"),
    "blush": ("blush", "cheek"),
    "lip": ("lipstick", "lip gloss", "lip tint", "lip liner", "lip"),
    "eye makeup": ("eyeshadow", "eyeliner", "mascara", "brow pencil", "eyebrow", "eye makeup"),
    "makeup tool": ("brush", "beauty blender", "sponge", "makeup puff", "curler"),
    # Nail
    "nail polish": ("nail polish", "gel polish", "nail color", "polish"),
    "press-on nails": ("press on nails", "press-on nails", "fake nails", "acrylic nails", "nail tips"),
    "nail sticker": ("nail sticker", "nail decal", "nail art sticker"),
    "nail tool": ("nail file", "cuticle", "uv lamp", "nail drill", "dotting tool"),
}

HOME_SCENE_CATEGORIES = {
    "sofa",
    "stool/ottoman",
    "rug",
    "curtain",
    "floor lamp",
    "coffee table",
    "armchair",
    "side table",
}
OOTD_SCENE_CATEGORIES = {
    "top",
    "bottom",
    "outerwear",
    "dress",
    "shoes",
    "hat",
    "bag",
    "socks",
    "accessory",
}
BEAUTY_FACE_SCENE_CATEGORIES = {"foundation", "blush", "lip", "eye makeup", "makeup tool"}
BEAUTY_NAIL_SCENE_CATEGORIES = {"nail polish", "press-on nails", "nail sticker", "nail tool"}


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
    parser.add_argument(
        "--scene",
        default="auto",
        choices=["auto", "home", "ootd", "beauty-face", "beauty-nail"],
        help="Scene template for stronger constraints (default: auto).",
    )
    parser.add_argument(
        "--quality-gate",
        default="auto",
        choices=["auto", "on", "off"],
        help="Quality gate mode; auto enables scene-specific checks for beauty/ootd.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Max generation attempts when quality gate is enabled.",
    )
    parser.add_argument(
        "--keep-attempts",
        action="store_true",
        help="Keep intermediate attempt files (default: false).",
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


def extract_first_image_part(response):
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
            return rgb
        elif image.mode == "RGB":
            return image
        else:
            return image.convert("RGB")
    return None


def save_image(image, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(str(output_path), "PNG")


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


def infer_scene(scene_arg: str, base_prompt: str, cart_items: list[dict] | None) -> str:
    if scene_arg != "auto":
        return scene_arg

    categories: set[str] = set()
    if cart_items:
        for item in cart_items:
            if isinstance(item, dict):
                categories |= infer_categories_from_title(str(item.get("title", "")))

    if categories & BEAUTY_FACE_SCENE_CATEGORIES:
        return "beauty-face"
    if categories & BEAUTY_NAIL_SCENE_CATEGORIES:
        return "beauty-nail"
    if categories & OOTD_SCENE_CATEGORIES:
        return "ootd"
    if categories & HOME_SCENE_CATEGORIES:
        return "home"

    text = base_prompt.lower()
    if any(x in text for x in ["lipstick", "eyeshadow", "makeup", "face makeup", "blush"]):
        return "beauty-face"
    if any(x in text for x in ["press-on", "press on", "nail", "manicure", "rhinestone"]):
        return "beauty-nail"
    if any(x in text for x in ["outfit", "ootd", "wear", "fashion look", "full-body", "full body"]):
        return "ootd"
    return "home"


def build_scene_constraints(scene: str) -> list[str]:
    if scene == "beauty-face":
        return [
            "Scene template: beauty-face.",
            "Keep face identity, facial geometry, head pose, and camera framing unchanged.",
            "Apply visible makeup changes only from cart items.",
            "If cart includes lipstick, lip color must visibly match lipstick shade.",
            "If cart includes eyeshadow/eye makeup, eyelid color must visibly match that shade family.",
            "No non-cart cosmetics, jewelry, props, or text overlays.",
        ]
    if scene == "beauty-nail":
        return [
            "Scene template: beauty-nail.",
            "Keep hand pose, finger geometry, skin texture, and camera framing unchanged.",
            "Apply nail style/color/shape strictly from cart items.",
            "For press-on/rhinestone products, preserve obvious style cues (shape/decor/shine).",
            "Difference from base should be clearly visible on nails only.",
            "No rings, extra hands, tools, or non-cart decorations.",
        ]
    if scene == "ootd":
        return [
            "Scene template: ootd.",
            "Keep person identity, body pose, face, background, and camera framing unchanged.",
            "Update outfit/accessories only with categories present in cart items.",
            "No non-cart wearable objects or unrelated props.",
        ]
    return [
        "Scene template: home interior.",
        "Keep room geometry and camera framing fixed.",
        "Only render purchasable decor/furniture from cart items.",
    ]


def build_guardrail_prompt(
    base_prompt: str,
    cart_items: list[dict] | None,
    enforce_cart_only: bool,
    must_have_categories: list[str],
    enforce_structure_lock: bool,
    scene: str,
) -> str:
    constraints: list[str] = []

    constraints.extend(build_scene_constraints(scene))

    if enforce_structure_lock:
        constraints.extend(
            [
                "Composition and viewpoint lock: keep subject pose, framing, and camera perspective unchanged.",
                "Preserve key background geometry and relative object positions from Image-1.",
                "Keep output framing/aspect ratio consistent with Image-1.",
                "If this is an interior scene, keep doors/windows/walls/built-ins unchanged.",
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


def should_enable_quality_gate(mode: str, scene: str) -> bool:
    if mode == "on":
        return True
    if mode == "off":
        return False
    return scene in {"beauty-face", "beauty-nail", "ootd"}


def _roi_box(w: int, h: int, x1: float, y1: float, x2: float, y2: float) -> tuple[int, int, int, int]:
    return (int(w * x1), int(h * y1), int(w * x2), int(h * y2))


def mean_abs_diff(base_img, cand_img, box=None) -> float:
    from PIL import ImageChops, ImageStat

    if cand_img.size != base_img.size:
        cand_img = cand_img.resize(base_img.size)
    if box is not None:
        base_crop = base_img.crop(box)
        cand_crop = cand_img.crop(box)
    else:
        base_crop = base_img
        cand_crop = cand_img
    diff = ImageChops.difference(base_crop, cand_crop)
    st = ImageStat.Stat(diff)
    return float(sum(st.mean) / max(len(st.mean), 1))


def evaluate_quality(scene: str, base_img, cand_img) -> tuple[bool, float, str]:
    w, h = base_img.size
    global_diff = mean_abs_diff(base_img, cand_img)

    if scene == "beauty-face":
        mouth_box = _roi_box(w, h, 0.30, 0.58, 0.70, 0.84)
        left_eye_box = _roi_box(w, h, 0.12, 0.26, 0.42, 0.50)
        right_eye_box = _roi_box(w, h, 0.58, 0.26, 0.88, 0.50)
        mouth_diff = mean_abs_diff(base_img, cand_img, mouth_box)
        eye_diff = (mean_abs_diff(base_img, cand_img, left_eye_box) + mean_abs_diff(base_img, cand_img, right_eye_box)) / 2.0
        score = min(mouth_diff, eye_diff)
        passed = mouth_diff >= 4.0 and eye_diff >= 3.6 and global_diff >= 2.0
        msg = f"global={global_diff:.2f}, mouth={mouth_diff:.2f}, eyes={eye_diff:.2f}"
        return passed, score, msg

    if scene == "beauty-nail":
        nail_box = _roi_box(w, h, 0.16, 0.16, 0.90, 0.78)
        nail_diff = mean_abs_diff(base_img, cand_img, nail_box)
        score = nail_diff
        passed = nail_diff >= 4.8 and global_diff >= 2.0
        msg = f"global={global_diff:.2f}, nails={nail_diff:.2f}"
        return passed, score, msg

    if scene == "ootd":
        body_box = _roi_box(w, h, 0.20, 0.18, 0.82, 0.92)
        body_diff = mean_abs_diff(base_img, cand_img, body_box)
        score = body_diff
        passed = body_diff >= 4.5 and global_diff >= 2.0
        msg = f"global={global_diff:.2f}, body={body_diff:.2f}"
        return passed, score, msg

    score = global_diff
    passed = global_diff >= 1.8
    msg = f"global={global_diff:.2f}"
    return passed, score, msg


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

    scene = infer_scene(args.scene, args.prompt, cart_items)
    print(f"Scene inferred: {scene}")

    try:
        final_prompt = build_guardrail_prompt(
            base_prompt=args.prompt,
            cart_items=cart_items,
            enforce_cart_only=args.enforce_cart_only,
            must_have_categories=args.must_have_category,
            enforce_structure_lock=args.enforce_structure_lock,
            scene=scene,
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
    quality_gate_enabled = should_enable_quality_gate(args.quality_gate, scene) and bool(images)
    max_attempts = max(int(args.max_attempts), 1)
    if not quality_gate_enabled:
        max_attempts = 1
    print(f"Quality gate: {'on' if quality_gate_enabled else 'off'} (attempts={max_attempts})")

    best_score = -1.0
    best_path: Path | None = None
    passed_path: Path | None = None
    created_attempts: list[Path] = []

    base_img = images[0].convert("RGB") if images else None

    for attempt in range(1, max_attempts + 1):
        attempt_path = output_path.with_name(f"{output_path.stem}.attempt-{attempt}.png")
        created_attempts.append(attempt_path)
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
            print(f"Error generating image (attempt {attempt}): {exc}", file=sys.stderr)
            continue

        image = extract_first_image_part(response)
        if image is None:
            print(f"No image returned by model (attempt {attempt}).", file=sys.stderr)
            continue
        save_image(image, attempt_path)

        if not quality_gate_enabled or base_img is None:
            passed_path = attempt_path
            break

        passed, score, metrics_msg = evaluate_quality(scene, base_img, image.convert("RGB"))
        print(f"Attempt {attempt} quality: {metrics_msg} -> {'PASS' if passed else 'FAIL'}")
        if score > best_score:
            best_score = score
            best_path = attempt_path
        if passed:
            passed_path = attempt_path
            break

    chosen = passed_path or best_path
    if chosen is None or not chosen.exists():
        print("Error: No image returned by model.", file=sys.stderr)
        sys.exit(1)

    if chosen != output_path:
        output_path.write_bytes(chosen.read_bytes())

    if not args.keep_attempts:
        for p in created_attempts:
            if p == chosen:
                continue
            if p.exists():
                p.unlink()
    if chosen.exists() and chosen != output_path and not args.keep_attempts:
        chosen.unlink(missing_ok=True)

    if quality_gate_enabled and passed_path is None:
        print("Quality gate fallback: no attempt passed; selected best attempt by score.")

    print(f"Image saved: {output_path.resolve()}")


if __name__ == "__main__":
    main()
