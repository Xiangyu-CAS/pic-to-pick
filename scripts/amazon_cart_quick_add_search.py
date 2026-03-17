#!/usr/bin/env python3
"""
Quick-add Amazon products from search result pages.

This workflow is intentionally lightweight and robust:
- clear current cart tab
- for each keyword: open search page and click first visible add-to-cart button
- refresh cart and save screenshot + summary
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote_plus


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quick add cart items from Amazon search pages.")
    parser.add_argument("--out-dir", required=True, help="Output run directory")
    parser.add_argument("--browser-profile", default="user", help="openclaw browser profile")
    parser.add_argument("--cart-target-id", required=True, help="Amazon cart target id")
    parser.add_argument("--work-target-id", required=True, help="Amazon search/work target id")
    parser.add_argument("--keyword", action="append", default=[], help="Keyword to search and quick-add")
    parser.add_argument("--wait-ms", type=int, default=1800, help="Delay after each add click")
    return parser.parse_args()


def run_cmd(args: list[str]) -> str:
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(args)}\n{proc.stdout}\n{proc.stderr}"
        )
    return proc.stdout


def browser(profile: str, subcmd: list[str]) -> str:
    return run_cmd(["openclaw", "browser", "--browser-profile", profile, *subcmd])


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
    raise ValueError("No JSON payload found")


def media_path_from_output(text: str) -> str | None:
    for line in text.splitlines():
        m = re.search(r"MEDIA:(\S+)", line.strip())
        if m:
            return m.group(1)
    return None


CLEAR_JS = r"""
() => {
  const btns = Array.from(
    document.querySelectorAll("input[name^='submit.delete'], input[value='Delete'], .sc-action-delete input")
  );
  btns.forEach((b) => { try { b.click(); } catch (e) {} });
  return { rows: document.querySelectorAll(".sc-list-item-content").length, clicked: btns.length };
}
"""


QUICK_ADD_JS = r"""
() => {
  const btn = document.querySelector(
    "button[name='submit.addToCart'], input[name='submit.addToCart'], button[aria-label*='Add to Cart' i]"
  );
  if (!btn) return { clicked: false };
  try {
    btn.click();
    return { clicked: true, label: (btn.innerText || btn.value || "").trim() || "add" };
  } catch (e) {
    return { clicked: false };
  }
}
"""


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.keyword:
        raise SystemExit("No keywords provided")

    # Open cart page and clear old items
    browser(
        args.browser_profile,
        ["navigate", "--target-id", args.cart_target_id, "https://www.amazon.com/gp/cart/view.html?ref_=nav_cart"],
    )
    browser(args.browser_profile, ["wait", "--target-id", args.cart_target_id, "--load", "domcontentloaded"])
    clear_logs: list[dict] = []
    for _ in range(12):
        state = first_json_blob(
            browser(args.browser_profile, ["evaluate", "--target-id", args.cart_target_id, "--fn", CLEAR_JS])
        )
        clear_logs.append(state if isinstance(state, dict) else {"raw": state})
        browser(args.browser_profile, ["wait", "--target-id", args.cart_target_id, "--time", "1200"])
        if isinstance(state, dict) and int(state.get("rows", 0)) <= 0:
            break

    # Quick add from search results
    results = []
    added_count = 0
    for kw in args.keyword:
        url = f"https://www.amazon.com/s?k={quote_plus(kw)}"
        browser(args.browser_profile, ["navigate", "--target-id", args.work_target_id, url])
        browser(args.browser_profile, ["wait", "--target-id", args.work_target_id, "--load", "domcontentloaded"])
        add_res = first_json_blob(
            browser(args.browser_profile, ["evaluate", "--target-id", args.work_target_id, "--fn", QUICK_ADD_JS])
        )
        ok = isinstance(add_res, dict) and bool(add_res.get("clicked"))
        if ok:
            added_count += 1
        results.append({"keyword": kw, "ok": ok, "result": add_res})
        browser(args.browser_profile, ["wait", "--target-id", args.work_target_id, "--time", str(args.wait_ms)])

    # Refresh cart and capture summary + screenshot
    browser(
        args.browser_profile,
        ["navigate", "--target-id", args.cart_target_id, "https://www.amazon.com/gp/cart/view.html?ref_=nav_cart"],
    )
    browser(args.browser_profile, ["wait", "--target-id", args.cart_target_id, "--load", "domcontentloaded"])
    cart_state = first_json_blob(
        browser(
            args.browser_profile,
            [
                "evaluate",
                "--target-id",
                args.cart_target_id,
                "--fn",
                "() => ({rows: document.querySelectorAll('.sc-list-item-content').length, subtotal:(document.querySelector('#sc-subtotal-amount-activecart')?.textContent||'').trim()})",
            ],
        )
    )
    shot_raw = browser(args.browser_profile, ["screenshot", args.cart_target_id, "--full-page"])
    media = media_path_from_output(shot_raw)
    copied_shot = None
    if media:
        src = Path(media).expanduser().resolve()
        if src.exists():
            copied_shot = out_dir / "2026-03-17-cart-fullpage.jpg"
            copied_shot.write_bytes(src.read_bytes())

    summary = {
        "keywords": args.keyword,
        "added_count": added_count,
        "quick_results": results,
        "clear_logs": clear_logs,
        "cart_state": cart_state,
        "cart_screenshot": str(copied_shot) if copied_shot else None,
    }
    summary_path = out_dir / "cart-quick-add-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"added_count: {added_count}")
    print(f"cart_state: {json.dumps(cart_state, ensure_ascii=False)}")
    print(f"summary_json: {summary_path}")
    if copied_shot:
        print(f"cart_screenshot: {copied_shot}")


if __name__ == "__main__":
    main()
