#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import shutil
from pathlib import Path

IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description='Persist the newest inbound image into a pic-to-pick run directory.'
    )
    p.add_argument('--out-dir', required=True, help='Run directory to copy the image into')
    p.add_argument('--source', help='Optional explicit source image path')
    p.add_argument('--dest-name', default='00-base-input', help='Destination basename without extension')
    p.add_argument('--print-json', action='store_true', help='Print result as JSON')
    return p.parse_args()


def candidate_roots() -> list[Path]:
    home = Path.home()
    roots = [
        Path.cwd() / 'media' / 'inbound',
        home / '.openclaw' / 'workspace' / 'media' / 'inbound',
        home / '.openclaw' / 'media' / 'inbound',
        Path('/tmp/openclaw'),
        Path('/private/tmp/openclaw'),
    ]
    seen = []
    for root in roots:
        if root not in seen:
            seen.append(root)
    return seen


def is_image(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.suffix.lower() in IMAGE_EXTS:
        return True
    mime, _ = mimetypes.guess_type(path.name)
    return bool(mime and mime.startswith('image/'))


def newest_image_under(root: Path) -> Path | None:
    if not root.exists():
        return None
    candidates: list[Path] = []
    if root.is_file() and is_image(root):
        candidates = [root]
    else:
        try:
            for path in root.rglob('*'):
                if is_image(path):
                    candidates.append(path)
        except Exception:
            return None
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def resolve_source(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not is_image(path):
            raise SystemExit(f'Explicit source is not a readable image: {path}')
        return path
    found: list[Path] = []
    for root in candidate_roots():
        hit = newest_image_under(root)
        if hit:
            found.append(hit)
    if not found:
        raise SystemExit('No inbound image found under known staging roots')
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found[0]


def main() -> None:
    args = parse_args()
    src = resolve_source(args.source)
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = src.suffix.lower() or '.png'
    dest = out_dir / f'{args.dest_name}{ext}'
    shutil.copy2(src, dest)
    result = {
        'source': str(src),
        'copied_to': str(dest),
        'bytes': dest.stat().st_size,
    }
    if args.print_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(dest)


if __name__ == '__main__':
    main()
