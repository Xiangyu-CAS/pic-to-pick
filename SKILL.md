---
name: pic-to-pick
description: Focused flow for home-space shopping on Amazon: room image -> cart items -> cart-only AI preview -> report project.
---

# Pic to Pick (Focused)

This skill is intentionally narrowed to **one reliable flow**:

- Home space image (renovation done, furniture missing)
- Diagnose and build a shopping plan
- Add products to Amazon cart
- Pull real cart product images
- Generate structure-locked, cart-only preview image
- Package a report project (`REPORT.md + images + data + manifest`)

## Scope

Supported: `home-space -> Amazon -> cart -> preview -> report-project`

Not supported in this focused version:

- outfit planning
- multi-site shopping orchestration
- Taobao/Tmall flow

## Hard Constraints

- Preserve room structure: door/window/wall/built-ins/camera viewpoint unchanged.
- Preview must be cart-only for purchasable objects.
- If a must-have object category should appear (for example `sofa`, `stool/ottoman`), ensure it is already in cart.
- Report language must match user language.

## Workflow

1. Prepare room image
- If missing, generate a mock room image first.

2. Space diagnosis
- Output: keep / buy-now / buy-later and category budgets.

3. Amazon cart execution
- Use `openclaw browser --browser-profile user`.
- Add target categories to cart and verify on cart page.

4. Pull real cart product images
- Run `scripts/amazon_cart_pull_images.py`.

5. Generate AI preview (strict)
- Use `scripts/nano_banana_generate_image.py` with:
  - `--cart-items-json`
  - `--enforce-cart-only`
  - `--must-have-category ...` (if needed)
  - `--enforce-structure-lock`
  - `--aspect-ratio auto`

6. Build report project
- Run `scripts/build_home_report_project.py`.

## Bundled Scripts

- `scripts/amazon_cart_pull_images.py`
- `scripts/nano_banana_generate_image.py`
- `scripts/build_home_report_project.py`

## Reference

- `references/amazon-real-image-preview-flow.md`

## Output Standard

A final project folder with:

- `REPORT.md`
- `images/`
- `data/`
- `manifest.json`

For an included successful sample, see:

- `showcase/example1-success/report-project/`
