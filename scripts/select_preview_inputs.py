#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

HOME_PRIORITY = [
    'sofa', 'couch', 'loveseat', 'sectional',
    'armchair', 'accent chair', 'chair',
    'rug', 'carpet',
    'coffee table', 'center table',
    'curtain', 'drape', 'blind',
    'floor lamp', 'standing lamp', 'lamp',
    'side table', 'end table',
    'ottoman', 'stool',
    'pillow', 'throw', 'blanket',
    'plant', 'tree'
]
OOTD_PRIORITY = [
    'dress', 'top', 'shirt', 'tee', 't-shirt', 'blouse', 'hoodie', 'sweater',
    'bottom', 'pants', 'trousers', 'jeans', 'shorts', 'skirt', 'skort',
    'outerwear', 'jacket', 'cardigan',
    'shoes', 'sneaker', 'boots', 'sandals',
    'hat', 'cap',
    'bag', 'backpack', 'crossbody',
    'accessory', 'sunglasses', 'watch', 'bracelet',
    'socks'
]
BEAUTY_PRIORITY = [
    'foundation', 'concealer', 'primer', 'blush', 'lip', 'lipstick', 'gloss',
    'eyeshadow', 'eyeliner', 'mascara', 'brow', 'brush', 'sponge',
    'nail', 'polish', 'press-on', 'sticker'
]


def parse_args():
    p = argparse.ArgumentParser(description='Select base + cart product images for preview generation.')
    p.add_argument('--base-image', required=True)
    p.add_argument('--cart-items-json', required=True)
    p.add_argument('--scene', default='auto', choices=['auto', 'home', 'ootd', 'beauty-face', 'beauty-nail'])
    p.add_argument('--max-images', type=int, default=10)
    return p.parse_args()


def priority_list(scene: str):
    if scene == 'home':
        return HOME_PRIORITY
    if scene == 'ootd':
        return OOTD_PRIORITY
    return BEAUTY_PRIORITY


def score_item(title: str, priorities: list[str]) -> tuple[int, int]:
    t = (title or '').lower()
    for idx, pat in enumerate(priorities):
        if pat in t:
            return (0, idx)
    return (1, 999)


def main():
    args = parse_args()
    base = Path(args.base_image).resolve()
    items = json.loads(Path(args.cart_items_json).read_text(encoding='utf-8'))
    prios = priority_list(args.scene)
    usable = []
    for it in items:
        local_image = it.get('local_image')
        if not local_image:
            continue
        img = (Path(args.cart_items_json).resolve().parent / local_image).resolve()
        if not img.exists():
            continue
        usable.append((score_item(it.get('title', ''), prios), img, it.get('title', '')))
    usable.sort(key=lambda x: x[0])
    chosen = [str(base)]
    for _, img, _title in usable[: max(args.max_images - 1, 0)]:
        chosen.append(str(img))
    print(json.dumps(chosen, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
