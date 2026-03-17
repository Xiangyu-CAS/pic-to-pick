# Amazon Home-Space Focused Flow

This is the only retained production flow.

## 1) Open Amazon cart in logged-in profile

Use:

```bash
openclaw browser --browser-profile user tabs --json
```

Find the cart tab target id (`/cart`).

## 2) Pull real cart product images

```bash
python scripts/amazon_cart_pull_images.py \
  --browser-profile user \
  --target-id <cart_target_id> \
  --out-dir <run_dir> \
  --max-items 12
```

Artifacts:

- `<run_dir>/cart-items-clean.json`
- `<run_dir>/cart-items-downloaded.json`
- `<run_dir>/cart-summary.json`
- `<run_dir>/product-images-real/item-*.jpg`

## 3) Generate strict preview

```bash
uv run scripts/nano_banana_generate_image.py \
  -i <run_dir>/base-room.png \
  -i <run_dir>/product-images-real/item-01.jpg \
  -i <run_dir>/product-images-real/item-02.jpg \
  --cart-items-json <run_dir>/cart-items-downloaded.json \
  --enforce-cart-only \
  --must-have-category sofa \
  --must-have-category stool/ottoman \
  --must-have-category "coffee table" \
  --must-have-category armchair \
  --must-have-category "side table" \
  --must-have-category curtain \
  --must-have-category rug \
  --must-have-category "floor lamp" \
  --enforce-structure-lock \
  --aspect-ratio auto \
  -p "Use only cart products and keep room structure unchanged. Avoid sparse layout and stage a complete living-room composition." \
  -f <run_dir>/preview.png \
  -r 1K
```

## 4) Build report project

```bash
python scripts/build_home_report_project.py \
  --run-dir <run_dir> \
  --title "家装方案报告" \
  --lang zh-CN \
  --website Amazon
```

## 5) Verify before handoff

- Preview ratio close to base image ratio.
- Door/window/wall/built-ins/viewpoint unchanged.
- No purchasable objects outside cart items.
- Report language consistent with user language.
- Report includes real cart amounts: unit price, quantity, line total, and cart total.
