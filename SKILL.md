---
name: pic-to-pick
description: "Amazon cart-constrained visual shopping flow for home-space, OOTD, and beauty (face/nail): mock/base image -> cart items -> cart-only AI preview -> report project. Trigger when users ask for 家居布置 / home-space styling, 穿搭推荐 / OOTD outfit recommendations, or 美妆推荐 (face makeup / nail look), including close synonyms."
---

# Pic to Pick (Focused)

This skill supports three reliable Amazon flows:

- Home space image (renovation done, furniture missing)
- OOTD full-body outfit (e.g., kids 9:16)
- Beauty close-up (face makeup / nail design)

## Scope

Supported:

- `home-space -> Amazon -> cart -> preview -> report-project`
- `ootd -> Amazon -> cart -> preview -> report-project`
- `beauty-face / beauty-nail -> Amazon -> cart -> preview -> report-project`

Not supported:

- multi-site shopping orchestration
- Taobao/Tmall flow

## Hard Constraints

- Preserve room structure: door/window/wall/built-ins/camera viewpoint unchanged.
- Preview must be cart-only for purchasable objects.
- If a must-have object category should appear (for example `sofa`, `stool/ottoman`), ensure it is already in cart.
- Report language must match user language.
- Report must include real cart amounts:
  - per-item unit price
  - quantity
  - line total
  - cart total summary

## Workflow

1. Persist the inbound image first
- Never rely on the chat surface's temporary/model-only image handle as the long-lived base input for the workflow.
- Before any diagnosis or shopping step, copy the user image into the current run directory under `skills/pic-to-pick/output/<run>/` as a stable file, preferably `00-base-input.<ext>`.
- First try the staged inbound-media locations that OpenClaw uses (for example `media/inbound/*` in the active workspace, or other true inbound staging roots).
- Use `scripts/persist_inbound_image.py --out-dir <run_dir>` to copy the newest staged inbound image into the run directory.
- If a direct file path is already available, call `scripts/persist_inbound_image.py --out-dir <run_dir> --source <path>` instead of guessing.
- Do **not** scan the whole workspace and guess from old skill outputs; that can silently pick the wrong image.
- If no staged inbound image can be found, then and only then ask the user to resend the image.

2. Prepare room image
- Use the persisted `skills/pic-to-pick/output/<run>/00-base-input.<ext>` as the base image for all later steps.
- If the user did not provide a suitable room/base image, generate a mock room image first.

3. Space diagnosis
- Output: keep / buy-now / buy-later and category budgets.
- For `ootd`, diagnose the **visible crop first** before choosing shoppable categories.
- For `ootd`, infer the likely wearer **gender presentation / target rack** from the image and the user's wording before searching products.
- Do **not** default to `boys/men` or `girls/women` just because the subject is a child or because one catalog is easier to search.
- If the image strongly reads as girl-coded, search `girls` items first; if it strongly reads as boy-coded, search `boys` items first.
- If gender presentation is ambiguous, ask the user before building the cart, or use gender-neutral kids keywords explicitly and say that you are doing so.
- Do not default to a full-body outfit template when the image is a portrait or half-body shot.
- Category selection must follow what the image can actually support:
  - **half-body / portrait:** prioritize visible or near-visible categories such as `top`, `outerwear`, neckline/layering upgrades, and low-noise accessories like `watch` only when they materially help.
  - **full-body:** then consider `bottom`, `shoes`, and full silhouette composition.
- Never add a category just because it is common in OOTD flows. If the crop does not meaningfully show it, do not force it into the cart unless the user explicitly asks for a full look.

4. Amazon cart execution
- Use `openclaw browser --browser-profile user`.
- Amazon login is preferred but not strictly required for adding items to cart; if the signed-in cart is unavailable, a guest cart is still acceptable for demo execution as long as items can be added and verified on cart/cart-like pages.
- Add target categories to cart and verify on cart page.
- **Default cart cap: 6 items maximum.** Do not exceed 6 unless the user explicitly asks for a denser or more decorative setup.
- **Prioritize major visible items first.** Add the minimum set that makes the scene believable before adding small accessories.
- Use this priority rule:
  1. hero/anchor items that define the scene
  2. functional support items needed to complete the composition
  3. only then a small number of finish/detail items if budget and slot count still allow
- Recommended cart composition by scene:
  - **home-space:** usually 4-6 items total. Prioritize `sofa / rug / coffee table / curtains / floor lamp / accent chair`. Treat side table, ottoman, pillows, throw, plant as lower-priority fillers.
  - **ootd:** usually 2-6 items total, but let the image crop decide.
    - **half-body / portrait:** usually 2-4 items. Prioritize `top / outerwear / visible accessory`. Do **not** default to `bottom` or `shoes` unless the user explicitly wants a full look or those areas are actually visible enough to matter.
    - **full-body:** prioritize the visually dominant wearable pieces first: `top / bottom or dress / shoes / outerwear`. Add bag/hat/jewelry only if they materially improve the look.
  - **beauty-face:** usually 2-3 items total. Prioritize the products most visible in the requested look, for example `lip + eye` or `base + lip + eye`.
  - **beauty-nail:** usually 1 item total, optionally 2 if one is the core polish/press-on and one is a clearly necessary support item.
- Avoid spending cart slots on low-impact accessories before the main composition is already satisfied.

5. Pull real cart product images
- Run `scripts/amazon_cart_pull_images.py`.
- Keep `cart-summary.json` for report pricing totals.
- After pulling images, output step (2) before generation:
  - `02-selected-products.md`
  - selected product board image
  - cart evidence image

6. Generate AI preview (strict)
- Before generation, output step (3):
  - `03-nano-banana-input.md`
  - exact final prompt text
  - exact reference image list in order
- Use `scripts/nano_banana_generate_image.py` with:
  - `--scene home|ootd|beauty-face|beauty-nail` (or `auto`)
  - `--cart-items-json`
  - `--enforce-cart-only`
  - `--must-have-category ...` (if needed)
  - `--enforce-structure-lock`
  - `--aspect-ratio auto`
  - `--quality-gate auto|on|off` and `--max-attempts` for auto-regeneration when change is too weak
- For preview generation, do not send only the base image. Send `base + real product images` together.
- Use `scripts/select_preview_inputs.py` to choose the reference image pack by default.
- Nano Banana can accept up to 10 input images total, but do not treat that as a reason to fill the cart.
- Default packing rule:
  - 1 slot for the base image
  - up to 6 slots for real cart product images by default, matching the cart cap
  - prioritize hero categories first (home: sofa/rug/coffee table/curtain/lamp/accent chair; ootd: top/bottom-or-dress/shoes/outerwear; beauty: only the main visible products)
- If the cart has fewer than 6 items, that is preferred over adding weak accessories just to use more reference slots.
- `must-have-category` must match categories actually present in the cart; never require a category that is absent from the current cart.
- Default resolution is `1K` unless explicitly overridden.

7. Build report project
- Run `scripts/build_home_report_project.py`.

## Bundled Scripts

- `scripts/persist_inbound_image.py`
- `scripts/amazon_cart_pull_images.py`
- `scripts/select_preview_inputs.py`
- `scripts/nano_banana_generate_image.py`
- `scripts/build_home_report_project.py`

## Reference

- `references/amazon-real-image-preview-flow.md`

## Output Standard

Do not make the user wait for only one final artifact when the flow is long. Prefer progressive outputs in this order.

Important: do both.
- Write the step artifacts to files.
- Also send a short in-chat progress reply after each step so the user sees the result during the conversation instead of waiting silently.

**Mandatory confirmation gate before preview generation**
- After product selection/cart build, always show the user the **product board image** plus a **product table/summary with prices** first.
- Then pause for confirmation before generating the preview image.
- Do not proceed to Nano Banana preview generation until the user explicitly confirms, even if the selected cart looks reasonable.
- If the user requests changes after seeing the board/table, update the cart first and re-show the revised board/table before any preview step.

Recommended chat cadence:
1. After recommendation/diagnosis:
   - Send a brief text summary of the proposed layout / outfit direction.
2. After product selection/cart build:
   - Send a brief summary with item count, notable categories, and cart total.
   - Explicitly explain why each selected item made the cut if the cart is small or heavily prioritized.
   - Send or surface the **product board image**.
   - Include a concise **product table/summary with unit price, quantity, and line total**.
   - Ask for confirmation to continue.
3. Only after user confirmation, before Nano Banana generation:
   - Send a brief summary of the final prompt intent and how many reference images will be sent.
4. After preview generation:
   - Send a brief summary that preview is ready and mention any obvious quality/structure caveat if already noticed.
5. After final report build:
   - Send a brief completion summary pointing to the final project/report.

Run naming:
- Do not use generic run names like `run-2026-03-21-home-user` when repeated runs are likely.
- Default to a high-distinguishability run id:
  - `run-YYYYMMDD-HHMMSS-<scene>-<space-tag>-<style-tag>-<shortid>`
- Requirements:
  - include timestamp to seconds
  - include scene: `home` / `ootd` / `beauty-face` / `beauty-nail`
  - include a short space tag based on the image or request, for example `livingroom`, `bedroom`, `dining`, `bigwindow`, `tvwall`, `vanity`
  - include a short style tag when known, for example `japandi`, `warmminimal`, `modern`, `cozy`, `clean`
  - include a short random/hash suffix (4-6 chars) to avoid collisions
- Example run ids:
  - `run-20260321-115842-home-livingroom-japandi-8f3a`
  - `run-20260321-120731-home-tvwall-warmminimal-c2d1`
  - `run-20260321-121455-ootd-kids-casual-a91e`
- If the scene/style is uncertain, still keep the timestamp + scene + shortid and use a neutral tag like `space`, `room`, `look`, or `style`.

File outputs:
1. `skills/pic-to-pick/output/<run>/00-base-input.<ext>`
   - Persisted inbound/base image copied into the run directory before any later step; this is the canonical base image path for the run.
2. `01-recommendation.md`
   - Text-only diagnosis + buy-now/buy-later or outfit recommendation.
3. `02-selected-products.md`
   - Chosen products summary after shopping/cart selection.
   - Include links, prices, and a product board / cart evidence image when available.
4. `03-nano-banana-input.md`
   - Exact Nano Banana input package used for preview generation.
   - Include the final prompt text and the exact reference image paths/order.
5. Preview image output
   - e.g. `preview.png` or `preview-with-products.png`
6. Final project folder
   - `REPORT.md`
   - `images/`
   - `data/`
   - `manifest.json`
   - `REPORT.md` includes pricing table and total amount summary.

For an included successful sample, see:

- `showcase/example1-success/report-project/`
