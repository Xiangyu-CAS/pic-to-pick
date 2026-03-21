#!/usr/bin/env python3
"""
Build an Amazon cart from keyword searches using openclaw browser automation.

Flow:
- Open/focus Amazon cart tab
- Clear existing cart items
- For each keyword, search and try top product pages until one can be added
- Save cart evidence screenshot and run summary json
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Amazon cart from keyword list via openclaw browser profile."
    )
    parser.add_argument("--out-dir", required=True, help="Run output directory")
    parser.add_argument("--browser-profile", default="user", help="openclaw browser profile")
    parser.add_argument(
        "--keyword",
        action="append",
        default=[],
        help="Keyword to search and add (repeatable)",
    )
    parser.add_argument(
        "--keywords-file",
        help="Optional txt/json file for keywords (txt: one per line; json: array of strings)",
    )
    parser.add_argument("--max-links-per-keyword", type=int, default=8, help="Max candidate links per keyword")
    parser.add_argument("--max-items", type=int, default=6, help="Maximum cart items to add from the keyword list")
    parser.add_argument("--cmd-timeout-sec", type=int, default=60, help="Timeout for each openclaw command")
    parser.add_argument("--cart-url", default="https://www.amazon.com/cart?ref_=nav_cart")
    return parser.parse_args()


def run_cmd(args: list[str], timeout_sec: int = 60) -> str:
    attempts = 2
    last_err = None
    for attempt in range(1, attempts + 1):
        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Command timeout ({timeout_sec}s): {' '.join(args)}") from exc
        if proc.returncode == 0:
            return proc.stdout
        combined = f"{proc.stdout}\n{proc.stderr}"
        last_err = (proc.returncode, combined)
        retryable = "node disconnected (browser.proxy)" in combined.lower()
        if retryable and attempt < attempts:
            subprocess.run(
                ["openclaw", "browser", "--browser-profile", "user", "start", "--json"],
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_sec,
            )
            time.sleep(2.0)
            continue
        print(proc.stdout, end="")
        print(proc.stderr, end="", file=sys.stderr)
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(args)}")
    raise RuntimeError(f"Command failed after retries: {' '.join(args)} :: {last_err}")


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


def media_path_from_output(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("MEDIA:"):
            return line.replace("MEDIA:", "", 1).strip()
    return None


def browser(args: argparse.Namespace, subcmd: list[str]) -> str:
    return run_cmd(
        ["openclaw", "browser", "--browser-profile", args.browser_profile, *subcmd],
        timeout_sec=args.cmd_timeout_sec,
    )


def list_tabs(args: argparse.Namespace) -> list[dict]:
    out = browser(args, ["tabs", "--json"])
    payload = first_json_blob(out)
    tabs = payload.get("tabs", []) if isinstance(payload, dict) else []
    return tabs if isinstance(tabs, list) else []


def pick_tab(args: argparse.Namespace, *, contains_url: str | None = None, type_page_only: bool = True) -> str | None:
    tabs = list_tabs(args)
    for tab in tabs:
        if not isinstance(tab, dict):
            continue
        if type_page_only and tab.get("type") != "page":
            continue
        url = str(tab.get("url") or "")
        if contains_url and contains_url not in url:
            continue
        tid = tab.get("targetId")
        if isinstance(tid, str) and tid:
            return tid
    return None


def open_tab(args: argparse.Namespace, url: str) -> str:
    out = browser(args, ["open", url, "--json"])
    payload = first_json_blob(out)
    target_id = payload.get("targetId")
    if not target_id:
        raise RuntimeError("open did not return targetId")
    return target_id


def wait_load(args: argparse.Namespace, target_id: str, state: str = "domcontentloaded") -> None:
    browser(args, ["wait", "--target-id", target_id, "--load", state, "--timeout-ms", "30000"])


def wait_time(args: argparse.Namespace, target_id: str, ms: int) -> None:
    browser(args, ["wait", "--target-id", target_id, "--time", str(ms)])


def evaluate(args: argparse.Namespace, target_id: str, fn: str):
    out = browser(args, ["evaluate", "--target-id", target_id, "--fn", fn])
    return first_json_blob(out)


def load_keywords(args: argparse.Namespace) -> list[str]:
    out = list(args.keyword)
    if args.keywords_file:
        p = Path(args.keywords_file).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"keywords file not found: {p}")
        text = p.read_text(encoding="utf-8").strip()
        if not text:
            return out
        if p.suffix.lower() == ".json":
            data = json.loads(text)
            if not isinstance(data, list):
                raise ValueError("keywords json must be an array of strings")
            out.extend([str(x).strip() for x in data if str(x).strip()])
        else:
            out.extend([line.strip() for line in text.splitlines() if line.strip()])
    dedup: list[str] = []
    seen = set()
    for kw in out:
        if kw in seen:
            continue
        seen.add(kw)
        dedup.append(kw)
    if args.max_items > 0:
        dedup = dedup[: args.max_items]
    return dedup


CLEAR_CART_JS = r"""
() => {
  const rows = Array.from(document.querySelectorAll(".sc-list-item-content"));
  const btns = Array.from(
    document.querySelectorAll(
      "input[name^='submit.delete'], input[value='Delete'], .sc-action-delete input, [data-feature-id='item-delete-button'] input, [aria-label='Delete']"
    )
  );
  let clicked = 0;
  btns.forEach((b) => {
    try {
      b.click();
      clicked += 1;
    } catch (e) {}
  });
  const subtotal = (document.querySelector("#sc-subtotal-amount-activecart")?.textContent || "").trim();
  return { rows: rows.length, clicked, subtotal };
}
"""


SEARCH_LINKS_JS = r"""
() => {
  const links = [];
  const candidates = Array.from(
    document.querySelectorAll(
      "div[data-component-type='s-search-result'] a.s-no-outline[href], div[data-component-type='s-search-result'] h2 a[href], a.s-no-outline[href*='/dp/'], a.a-link-normal[href*='/dp/']"
    )
  );
  candidates.forEach((a) => {
    const href = (a.getAttribute("href") || a.href || "").trim();
    if (!href) return;
    if (!href.includes("/dp/") && !href.includes("/gp/product/")) return;
    const full = href.startsWith("http") ? href : ("https://www.amazon.com" + href);
    links.push(full);
  });
  return Array.from(new Set(links));
}
"""


ADD_FROM_PRODUCT_JS = r"""
() => {
  const pickSelectFirst = (sel) => {
    const el = document.querySelector(sel);
    if (!el || !el.options) return false;
    const options = Array.from(el.options || []);
    const opt = options.find(
      (o) =>
        o &&
        o.value &&
        !o.disabled &&
        !/select|choose|unavailable/i.test((o.textContent || "").trim())
    );
    if (!opt) return false;
    el.value = opt.value;
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  };

  const clickFirst = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return false;
    try {
      el.click();
      return true;
    } catch (e) {
      return false;
    }
  };

  pickSelectFirst("#native_dropdown_selected_size_name");
  pickSelectFirst("#native_dropdown_selected_style_name");
  clickFirst("#inline-twister-expander-content-color_name li:not(.swatchUnavailable) input");
  clickFirst("#inline-twister-expander-content-size_name li:not(.swatchUnavailable) input");
  clickFirst("#twister .a-button-toggle input");

  const clicked =
    clickFirst("#add-to-cart-button") ||
    clickFirst("input[name='submit.add-to-cart']") ||
    clickFirst("#a-autoid-1-announce");

  return {
    clicked,
    title: document.title,
    url: location.href,
  };
}
"""


CHECK_ADDED_JS = r"""
() => {
  const text = (document.body?.innerText || "").slice(0, 20000);
  const lowered = text.toLowerCase();
  const ok =
    lowered.includes("added to cart") ||
    lowered.includes("added to basket") ||
    location.href.includes("/cart");
  const count = (document.querySelector("#nav-cart-count")?.textContent || "").trim();
  return { ok, cart_count: count || null, url: location.href, title: document.title };
}
"""


def clear_cart(args: argparse.Namespace, cart_target: str) -> list[dict]:
    logs: list[dict] = []
    browser(args, ["navigate", "--target-id", cart_target, args.cart_url])
    wait_load(args, cart_target)
    for _ in range(10):
        state = evaluate(args, cart_target, CLEAR_CART_JS)
        logs.append(state)
        if (state.get("rows") or 0) <= 0:
            break
        if (state.get("clicked") or 0) <= 0:
            break
        wait_time(args, cart_target, 2500)
    browser(args, ["navigate", "--target-id", cart_target, args.cart_url])
    wait_load(args, cart_target)
    return logs


def add_keyword_once(
    args: argparse.Namespace,
    work_target: str,
    keyword: str,
    max_links: int,
) -> dict:
    search_url = f"https://www.amazon.com/s?k={quote_plus(keyword)}"
    browser(args, ["navigate", "--target-id", work_target, search_url])
    wait_load(args, work_target)
    links = evaluate(args, work_target, SEARCH_LINKS_JS)
    if not isinstance(links, list):
        links = []
    links = [str(x) for x in links if isinstance(x, str) and x.strip()][:max_links]

    tried: list[dict] = []
    for link in links:
        browser(args, ["navigate", "--target-id", work_target, link])
        wait_load(args, work_target)
        add_state = evaluate(args, work_target, ADD_FROM_PRODUCT_JS)
        wait_time(args, work_target, 2200)
        check = evaluate(args, work_target, CHECK_ADDED_JS)
        row = {"link": link, "add_state": add_state, "check": check}
        tried.append(row)
        if bool(check.get("ok")):
            return {"ok": True, "keyword": keyword, "selected": row, "tried": tried}
    return {"ok": False, "keyword": keyword, "selected": None, "tried": tried}


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    started_at_epoch = time.time()
    started_at_iso = time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(started_at_epoch))
    keywords = load_keywords(args)
    if not keywords:
        raise SystemExit("No keywords provided")

    cart_target = pick_tab(args, contains_url="/cart")
    if not cart_target:
        cart_target = open_tab(args, args.cart_url)
        time.sleep(1.0)
        cart_target = pick_tab(args, contains_url="/cart") or cart_target

    work_target = pick_tab(args, contains_url="amazon.com")
    if not work_target:
        work_target = open_tab(args, "https://www.amazon.com/")
        time.sleep(1.0)
        work_target = pick_tab(args, contains_url="amazon.com") or work_target

    clear_logs = clear_cart(args, cart_target)
    added: list[dict] = []
    failed: list[dict] = []

    for kw in keywords:
        result = add_keyword_once(args, work_target, kw, args.max_links_per_keyword)
        if result.get("ok"):
            added.append(result)
        else:
            failed.append(result)
        # give Amazon time to settle requests before next keyword
        time.sleep(1.2)

    browser(args, ["navigate", "--target-id", cart_target, args.cart_url])
    wait_load(args, cart_target)

    shot_raw = browser(args, ["screenshot", cart_target, "--full-page"])
    media_path = media_path_from_output(shot_raw)
    copied_shot = None
    if media_path:
        src = Path(media_path).expanduser().resolve()
        if src.exists():
            copied_shot = out_dir / f"{time.strftime('%Y-%m-%d')}-cart-fullpage.jpg"
            copied_shot.write_bytes(src.read_bytes())

    finished_at_epoch = time.time()
    finished_at_iso = time.strftime('%Y-%m-%dT%H:%M:%S%z', time.localtime(finished_at_epoch))

    run_meta = {
        "source": "live_browser_run",
        "script": str(Path(__file__).resolve()),
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started_at_iso": started_at_iso,
        "finished_at_iso": finished_at_iso,
        "duration_sec": round(finished_at_epoch - started_at_epoch, 2),
        "browser_profile": args.browser_profile,
        "out_dir": str(out_dir),
        "keywords_count": len(keywords),
        "max_items": args.max_items,
    }
    run_meta_path = out_dir / "cart-build-run-meta.json"
    run_meta_path.write_text(json.dumps(run_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "run_meta": run_meta,
        "keywords": keywords,
        "added_count": len(added),
        "failed_count": len(failed),
        "added": added,
        "failed": failed,
        "clear_logs": clear_logs,
        "cart_target_id": cart_target,
        "work_target_id": work_target,
        "cart_screenshot": str(copied_shot) if copied_shot else None,
    }
    summary_path = out_dir / "cart-build-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"run_meta_json: {run_meta_path}")
    print(f"added_count: {len(added)}")
    print(f"failed_count: {len(failed)}")
    print(f"summary_json: {summary_path}")
    if copied_shot:
        print(f"cart_screenshot: {copied_shot}")


if __name__ == "__main__":
    main()
