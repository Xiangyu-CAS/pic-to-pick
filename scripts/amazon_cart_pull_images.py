#!/usr/bin/env python3
"""
Pull real product images from an Amazon cart tab via openclaw browser,
then download higher-resolution media assets to local files.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path


CART_JS = r"""
() => {
  const normalizeMoney = (text) => {
    if (!text) return null;
    const raw = String(text).replace(/\s+/g, " ").trim();
    const m = raw.replace(/,/g, "").match(/([A-Za-z$€£¥]{0,4})\s*([0-9]+(?:\.[0-9]{1,2})?)/);
    if (!m) return null;
    return {
      text: raw,
      currency: (m[1] || "").trim() || null,
      value: Number(m[2]),
    };
  };

  const items = [];
  const rows = document.querySelectorAll(".sc-list-item-content");
  rows.forEach((row) => {
    const img = row.querySelector("img.sc-product-image, img");
    const link = row.querySelector("a.sc-product-link, a[href*='/dp/'], a[href*='/gp/product']");
    const titleEl = row.querySelector(".sc-product-title, .a-truncate-full, .a-truncate-cut");
    let title = (titleEl?.textContent || img?.alt || "").replace(/\s+/g, " ").trim();
    const src = img?.getAttribute("data-old-hires") || img?.getAttribute("src") || "";
    const href = link?.href || "";
    const priceEl = row.querySelector(".sc-price .a-offscreen, .sc-product-price .a-offscreen, .a-price .a-offscreen, .sc-price");
    const priceText = (priceEl?.textContent || "").replace(/\s+/g, " ").trim();
    const price = normalizeMoney(priceText);

    const qtyPrompt = row.querySelector("span.a-dropdown-prompt");
    const qtyRaw = (qtyPrompt?.textContent || "").trim();
    const qtyNum = Number((qtyRaw.match(/\d+/) || [])[0] || 1);
    const quantity = Number.isFinite(qtyNum) && qtyNum > 0 ? qtyNum : 1;

    const lineTotalValue = price?.value != null ? Number((price.value * quantity).toFixed(2)) : null;

    if (title && src) {
      items.push({
        title,
        src,
        href,
        price_text: price?.text || null,
        price_value: price?.value ?? null,
        currency: price?.currency || null,
        quantity,
        line_total_value: lineTotalValue,
      });
    }
  });
  const uniq = [];
  const seen = new Set();
  for (const it of items) {
    if (seen.has(it.src)) continue;
    seen.add(it.src);
    uniq.push(it);
  }
  const subtotalEl =
    document.querySelector("#sc-subtotal-amount-activecart") ||
    document.querySelector("#sc-subtotal-amount-buybox") ||
    document.querySelector(".sc-subtotal .a-color-price");
  const subtotalText = (subtotalEl?.textContent || "").replace(/\s+/g, " ").trim();
  const subtotal = normalizeMoney(subtotalText);
  const computedTotal = uniq.reduce((acc, it) => acc + (Number(it.line_total_value) || 0), 0);

  return {
    items: uniq,
    subtotal_text: subtotal?.text || null,
    subtotal_value: subtotal?.value ?? null,
    currency: subtotal?.currency || null,
    computed_items_total: Number(computedTotal.toFixed(2)),
  };
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract Amazon cart product image URLs and download local copies."
    )
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--browser-profile", default="user", help="openclaw browser profile")
    parser.add_argument("--target-id", help="Cart tab target id (optional, auto-detect if omitted)")
    parser.add_argument("--max-items", type=int, default=6, help="Max cart items to download")
    parser.add_argument(
        "--cdn-size",
        type=int,
        default=1500,
        help="Amazon CDN long-side hint for hi-res URL (default: 1500)",
    )
    return parser.parse_args()


def run_cmd(args: list[str]) -> str:
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(proc.stdout, end="")
        print(proc.stderr, end="", file=sys.stderr)
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(args)}")
    return proc.stdout


def first_json_blob(text: str):
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch not in "[{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
            return obj
        except json.JSONDecodeError:
            continue
    raise ValueError("No JSON payload found in command output")


def pick_cart_target(browser_profile: str) -> str:
    out = run_cmd(["openclaw", "browser", "--browser-profile", browser_profile, "tabs", "--json"])
    payload = first_json_blob(out)
    tabs = payload.get("tabs", [])
    for tab in tabs:
        title = (tab.get("title") or "").lower()
        url = (tab.get("url") or "").lower()
        if "shopping cart" in title or "/cart" in url:
            return tab["targetId"]
    raise RuntimeError("No Amazon cart tab found. Open cart page first.")


def sanitize_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    title = re.sub(r"opens in a new tab.*$", "", title, flags=re.IGNORECASE).strip()
    half = len(title) // 2
    if half > 20 and title[:half] == title[half:]:
        title = title[:half]
    return title


def to_hires_url(src: str, size: int) -> str:
    repl = f"._AC_SL{size}_."
    out = re.sub(r"\._AC_[A-Z0-9]+_\.", repl, src)
    if out == src:
        out = re.sub(r"\._[A-Z0-9,]+_\.", repl, src)
    return out


def download(url: str, out_path: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        if len(data) < 10_000:
            return False
        out_path.write_bytes(data)
        return True
    except Exception:  # noqa: BLE001
        return False


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    image_dir = out_dir / "product-images-real"
    image_dir.mkdir(parents=True, exist_ok=True)

    target_id = args.target_id or pick_cart_target(args.browser_profile)
    raw = run_cmd(
        [
            "openclaw",
            "browser",
            "evaluate",
            "--browser-profile",
            args.browser_profile,
            "--target-id",
            target_id,
            "--fn",
            CART_JS,
        ]
    )
    payload = first_json_blob(raw)
    if isinstance(payload, list):
        items = payload
        summary = {}
    elif isinstance(payload, dict):
        items = payload.get("items", [])
        summary = payload
    else:
        raise RuntimeError("Unexpected evaluate payload, expected JSON object or array")
    if not isinstance(items, list):
        raise RuntimeError("Unexpected evaluate payload, expected items list")

    items = items[: args.max_items]
    clean_items = []
    downloaded_items = []

    for idx, item in enumerate(items, start=1):
        title = sanitize_title(item.get("title", ""))
        src = item.get("src", "")
        href = item.get("href", "")
        if not title or not src:
            continue

        quantity = int(item.get("quantity", 1) or 1)
        if quantity < 1:
            quantity = 1
        price_text = item.get("price_text")
        price_value = item.get("price_value")
        line_total_value = item.get("line_total_value")
        currency = item.get("currency")

        clean = {
            "title": title,
            "src": src,
            "href": href,
            "price_text": price_text,
            "price_value": price_value,
            "currency": currency,
            "quantity": quantity,
            "line_total_value": line_total_value,
        }
        clean_items.append(clean)

        hi = to_hires_url(src, args.cdn_size)
        output = image_dir / f"item-{idx:02d}.jpg"
        used_url = None
        for candidate in [hi, src]:
            if download(candidate, output):
                used_url = candidate
                break
        downloaded_items.append(
            {
                **clean,
                "highres_try": hi,
                "downloaded_from": used_url,
                "local_image": f"product-images-real/item-{idx:02d}.jpg" if used_url else None,
            }
        )

    cart_summary = {
        "subtotal_text": summary.get("subtotal_text"),
        "subtotal_value": summary.get("subtotal_value"),
        "currency": summary.get("currency"),
        "computed_items_total": summary.get("computed_items_total"),
        "items_count": len(downloaded_items),
    }

    (out_dir / "cart-items-clean.json").write_text(
        json.dumps(clean_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "cart-items-downloaded.json").write_text(
        json.dumps(downloaded_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "cart-summary.json").write_text(
        json.dumps(cart_summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"target_id: {target_id}")
    print(f"clean_json: {(out_dir / 'cart-items-clean.json')}")
    print(f"downloaded_json: {(out_dir / 'cart-items-downloaded.json')}")
    print(f"summary_json: {(out_dir / 'cart-summary.json')}")
    print(f"image_dir: {image_dir}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
