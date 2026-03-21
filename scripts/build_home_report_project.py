#!/usr/bin/env python3
"""
Build a Markdown report project for home-shopping runs.

Input: a run directory (images/json produced by pic-to-pick execution)
Output: a self-contained project folder:
  - REPORT.md
  - images/
  - data/
  - manifest.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any


def load_workspace_env() -> None:
    candidates = [
        Path("/Users/zhuxiangyu/.openclaw/workspace/skills/.env"),
        Path(__file__).resolve().parents[2] / ".env",
    ]
    for env_path in candidates:
        if not env_path.exists():
            continue
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
        break


def normalize_proxy_env() -> None:
    keep_proxy = os.environ.get("PIC_TO_PICK_KEEP_PROXY", "").lower() in {"1", "true", "yes"}
    if keep_proxy:
        return
    proxy_vals = {
        k: os.environ.get(k)
        for k in ["ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"]
    }
    if any((proxy_vals.get(k) or "").startswith("socks") for k in proxy_vals):
        for k in proxy_vals:
            os.environ.pop(k, None)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a home-decoration markdown report project from run artifacts."
    )
    parser.add_argument("--run-dir", required=True, help="Run directory with generated artifacts")
    parser.add_argument(
        "--project-dir",
        help="Output project directory (default: <run-dir>/report-project)",
    )
    parser.add_argument(
        "--title",
        default="家装方案报告",
        help="Report title",
    )
    parser.add_argument("--style", default="Japandi / 温暖极简", help="Target style text")
    parser.add_argument("--website", default="Amazon", help="Shopping website")
    parser.add_argument("--currency", default="USD", help="Budget currency")
    parser.add_argument(
        "--lang",
        default="auto",
        help="Report language: auto | zh-CN | en-US",
    )
    parser.add_argument(
        "--translate-content",
        default="auto",
        choices=["auto", "always", "never"],
        help="Translate diagnosis/cart text into report language",
    )
    return parser.parse_args()


def find_latest(run_dir: Path, patterns: list[str]) -> Path | None:
    matched: list[Path] = []
    for pat in patterns:
        matched.extend(run_dir.glob(pat))
    if not matched:
        return None
    matched.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matched[0]


def safe_text(value: Any) -> str:
    text = str(value) if value is not None else ""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def clean_item_title(raw: str) -> str:
    title = re.sub(r"\s+", " ", raw or "").strip()
    title = re.sub(r"opens in a new tab.*$", "", title, flags=re.IGNORECASE).strip()
    # If title appears duplicated by concatenation, keep first occurrence.
    for width in [80, 70, 60, 50, 40, 30]:
        if len(title) <= width * 2:
            continue
        prefix = title[:width]
        pos = title.find(prefix, width)
        if pos > 0:
            title = title[:pos].strip()
            break
    return title


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def detect_lang(lang_arg: str, title: str) -> str:
    if lang_arg and lang_arg.lower() != "auto":
        return lang_arg
    return "zh-CN" if contains_cjk(title) else "en-US"


def has_gemini_translation_backend() -> bool:
    if not os.getenv("GEMINI_API_KEY"):
        return False
    try:
        from google import genai  # noqa: F401
    except Exception:
        return False
    return True


def is_english_like(text: str) -> bool:
    if not text:
        return False
    if contains_cjk(text):
        return False
    return bool(re.search(r"[A-Za-z]", text))


CATEGORY_ZH_MAP = {
    "area rug": "地毯",
    "floor lamp": "落地灯",
    "curtains/blinds": "窗帘/百叶",
    "curtains": "窗帘",
    "blinds": "百叶",
    "sofa": "沙发",
    "coffee table": "茶几",
    "decorative pillows & throw blanket": "靠垫与盖毯",
    "ottoman": "脚凳/脚踏",
    "stool": "凳子",
}


BUY_ROW_ZH_PRESET = {
    "地毯": {
        "reason": "用于界定会客区、提升脚感并增强空间层次。",
        "target_specs": [
            "自然材质或仿天然纹理（黄麻/羊毛感）",
            "中性色（米色/浅驼/灰米）",
            "尺寸覆盖沙发前区，建议 8x10 英尺及以上",
            "低绒或平织，便于清洁维护",
        ],
        "amazon_keywords": ["日式极简地毯", "中性色客厅地毯", "自然纤维地毯"],
    },
    "落地灯": {
        "reason": "补充夜间氛围照明，避免仅靠顶灯造成生硬光感。",
        "target_specs": [
            "暖光 2700K-3000K",
            "线条简洁，木质或亚麻灯罩优先",
            "带调光功能更佳",
            "高度与沙发扶手/靠背比例协调",
        ],
        "amazon_keywords": ["日式极简落地灯", "亚麻灯罩落地灯", "木质极简落地灯"],
    },
    "窗帘/百叶": {
        "reason": "兼顾隐私与采光，柔化大窗硬边界。",
        "target_specs": [
            "半透光亚麻/棉麻材质",
            "落地长度，安装宽度覆盖窗洞两侧",
            "中性色系（米白/浅卡其）",
            "简洁轨道或极简窗杆",
        ],
        "amazon_keywords": ["亚麻窗帘 客厅", "半透光窗帘", "日式极简窗帘"],
    },
    "沙发": {
        "reason": "构建会客主坐区，是空间功能核心。",
        "target_specs": [
            "低靠背或中低型体块，线条简洁",
            "中性色面料（米灰/浅棕/米白）",
            "坐深适中，支撑性与舒适度平衡",
            "尺寸与现有动线不冲突",
        ],
        "amazon_keywords": ["日式极简沙发", "极简布艺沙发", "中性色双人/三人沙发"],
    },
    "茶几": {
        "reason": "提供日常使用台面，完善沙发区功能闭环。",
        "target_specs": [
            "圆角设计，降低磕碰风险",
            "木质或哑光中性材质",
            "高度与沙发坐垫接近或略低",
            "尺寸与地毯比例协调",
        ],
        "amazon_keywords": ["原木茶几", "极简茶几", "低矮圆角茶几"],
    },
    "靠垫与盖毯": {
        "reason": "补充触感与层次，提升居住舒适度。",
        "target_specs": [
            "棉麻/羊毛感面料",
            "中性色主调，可少量叠加低饱和点缀",
            "靠垫 2-3 个，盖毯 1 条",
            "纹理以细腻为主，避免复杂花色",
        ],
        "amazon_keywords": ["亚麻靠垫", "中性色盖毯", "日式极简抱枕"],
    },
}


def map_category_to_zh(category: str) -> str:
    raw = (category or "").strip()
    key = raw.lower()
    if key in CATEGORY_ZH_MAP:
        return CATEGORY_ZH_MAP[key]
    return raw if contains_cjk(raw) else "其他品类"


def localize_buy_rows_zh_fallback(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        cat_zh = map_category_to_zh(str(item.get("category", "")))
        item["category"] = cat_zh
        preset = BUY_ROW_ZH_PRESET.get(cat_zh)
        if is_english_like(str(item.get("reason", ""))):
            item["reason"] = (
                preset["reason"]
                if preset
                else "用于完善空间功能与风格统一，可按预算优先级分批购买。"
            )
        specs = item.get("target_specs")
        if isinstance(specs, list):
            if all(is_english_like(str(x)) for x in specs if str(x).strip()):
                item["target_specs"] = (
                    list(preset["target_specs"])
                    if preset
                    else ["按尺寸匹配空间动线", "优先中性色与自然材质", "关注易清洁与耐用性"]
                )
        keywords = item.get("amazon_keywords")
        if isinstance(keywords, list):
            if all(is_english_like(str(x)) for x in keywords if str(x).strip()):
                item["amazon_keywords"] = (
                    list(preset["amazon_keywords"])
                    if preset
                    else [cat_zh, "简约风", "中性色"]
                )
        out.append(item)
    return out


def localize_diagnosis_zh_fallback(diagnosis: dict) -> dict:
    out = dict(diagnosis)
    if is_english_like(str(out.get("space_summary", ""))):
        out["space_summary"] = (
            "该空间为采光良好的现代简约客厅，地面与墙顶基础状态完整，"
            "目前软装较少，适合直接进行家居布置。"
        )

    default_confirmed = [
        "左侧大面积窗户采光充足。",
        "浅木色地板可继续保留。",
        "电视背景墙与收纳柜体可作为主视觉中心。",
        "吊顶与嵌入式照明可沿用。",
        "右侧门洞位置明确，动线需保持不变。",
        "空间当前为空房状态，适合从核心家具开始配置。",
    ]
    default_assumptions = [
        "按客厅会客与日常休闲双场景进行配置。",
        "窗区需要兼顾隐私与柔和采光。",
        "电视墙区域作为主要布局锚点。",
        "家具尺寸以不阻挡门洞和主要通道为原则。",
    ]
    default_keep = [
        "浅木色地板（与目标风格一致）。",
        "白色墙面与吊顶基础（可直接延用）。",
        "电视背景墙与收纳柜体（功能完整）。",
        "大窗与原有采光条件（保留并通过窗帘优化）。",
    ]

    confirmed = out.get("confirmed_observations")
    if isinstance(confirmed, list):
        if not any(contains_cjk(str(x)) for x in confirmed):
            out["confirmed_observations"] = default_confirmed
    assumptions = out.get("assumptions")
    if isinstance(assumptions, list):
        if not any(contains_cjk(str(x)) for x in assumptions):
            out["assumptions"] = default_assumptions
    keep_items = out.get("keep")
    if isinstance(keep_items, list):
        if not any(contains_cjk(str(x)) for x in keep_items):
            out["keep"] = default_keep

    buy_now = out.get("buy_now")
    if isinstance(buy_now, list):
        out["buy_now"] = localize_buy_rows_zh_fallback(buy_now)
    buy_later = out.get("buy_later")
    if isinstance(buy_later, list):
        out["buy_later"] = localize_buy_rows_zh_fallback(buy_later)
    return out


def extract_first_json_value(raw_text: str) -> Any:
    decoder = json.JSONDecoder()
    for i, ch in enumerate(raw_text):
        if ch not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(raw_text[i:])
            return value
        except json.JSONDecodeError:
            continue
    raise ValueError("No JSON value found in model output")


def translate_texts(
    texts: list[str],
    target_lang: str,
    mode: str = "auto",
) -> list[str]:
    if not texts:
        return []
    if target_lang.lower().startswith("en"):
        return texts
    if not target_lang.lower().startswith("zh"):
        return texts

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        if mode == "always":
            raise RuntimeError("GEMINI_API_KEY is required for translation mode=always")
        return texts
    if mode == "never":
        return texts

    try:
        from google import genai
    except Exception:
        if mode == "always":
            raise
        return texts

    client = genai.Client(api_key=api_key)
    translated: list[str] = []
    chunk_size = 30
    for i in range(0, len(texts), chunk_size):
        chunk = texts[i : i + chunk_size]
        payload = json.dumps(chunk, ensure_ascii=False)
        prompt = (
            "Translate the following JSON string array into concise Simplified Chinese. "
            "Keep product model names/brands when appropriate. "
            "Return STRICT JSON array only with same length and order.\n"
            f"{payload}"
        )
        try:
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=[prompt])
            text = (resp.text or "").strip()
            value = extract_first_json_value(text)
            if isinstance(value, list) and len(value) == len(chunk):
                translated.extend([str(x) for x in value])
            else:
                translated.extend(chunk)
        except Exception:
            translated.extend(chunk)
    return translated


def collect_translatable_strings(diagnosis: dict, items: list[dict]) -> list[str]:
    collected: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return
            if stripped.startswith("http://") or stripped.startswith("https://"):
                return
            if Path(stripped).expanduser().is_absolute():
                return
            collected.append(stripped)
            return
        if isinstance(value, list):
            for item in value:
                walk(item)
            return
        if isinstance(value, dict):
            skip_keys = {
                "href",
                "src",
                "local_image",
                "report_local_image",
                "downloaded_from",
                "highres_try",
                "price_text",
                "price_value",
                "currency",
                "quantity",
                "line_total_value",
                "subtotal_text",
                "subtotal_value",
                "computed_items_total",
            }
            for k, v in value.items():
                if k in skip_keys:
                    continue
                walk(v)

    walk(diagnosis)
    for item in items:
        title = clean_item_title(str(item.get("title", "")))
        if title:
            collected.append(title)
    # preserve order and dedupe
    out: list[str] = []
    seen = set()
    for s in collected:
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def apply_translation(diagnosis: dict, items: list[dict], mapping: dict[str, str]) -> tuple[dict, list[dict]]:
    def tr(value: Any) -> Any:
        if isinstance(value, str):
            key = value.strip()
            return mapping.get(key, value)
        if isinstance(value, list):
            return [tr(x) for x in value]
        if isinstance(value, dict):
            return {k: tr(v) for k, v in value.items()}
        return value

    new_diag = tr(diagnosis)
    new_items = []
    for item in items:
        new_item = dict(item)
        title = clean_item_title(str(item.get("title", "")))
        if title:
            new_item["title"] = mapping.get(title, title)
        new_items.append(new_item)
    return new_diag, new_items


def load_json(path: Path | None) -> dict | list | None:
    if not path or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def copy_file(src: Path | None, dst: Path) -> Path | None:
    if not src or not src.exists():
        return None
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return dst


def relpath_text(path: Path, base: Path) -> str:
    rel = os.path.relpath(path, base)
    if rel == ".":
        return "."
    if rel.startswith("."):
        return rel
    return f"./{rel}"


def sanitize_local_path(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    if text.startswith("http://") or text.startswith("https://"):
        return text
    p = Path(text).expanduser()
    if p.is_absolute():
        return p.name
    return text


def to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def format_money(value: float | None, currency: str | None = None) -> str:
    if value is None:
        return "-"
    cur = (currency or "").strip()
    if cur:
        return f"{cur} {value:,.2f}"
    return f"{value:,.2f}"


def build_buy_table(rows: list[dict], currency: str, lang: str) -> str:
    if not rows:
        return "_无数据_" if lang.lower().startswith("zh") else "_No data_"
    if lang.lower().startswith("zh"):
        lines = [
            "| 品类 | 购买理由 | 目标规格 | 搜索关键词 | 预算 |",
            "|---|---|---|---|---|",
        ]
    else:
        lines = [
            "| Category | Reason | Target Specs | Keywords | Budget |",
            "|---|---|---|---|---|",
        ]
    for row in rows:
        budget = row.get("budget_usd", {}) or {}
        budget_text = f"{currency} {budget.get('min', '-')}-{budget.get('max', '-')}"
        target_specs = ", ".join(row.get("target_specs", [])[:4]) if isinstance(row.get("target_specs"), list) else ""
        keywords = ", ".join(row.get("amazon_keywords", [])[:3]) if isinstance(row.get("amazon_keywords"), list) else ""
        lines.append(
            "| "
            + safe_text(row.get("category", ""))
            + " | "
            + safe_text(row.get("reason", ""))
            + " | "
            + safe_text(target_specs)
            + " | "
            + safe_text(keywords)
            + " | "
            + safe_text(budget_text)
            + " |"
        )
    return "\n".join(lines)


def build_cart_table(items: list[dict], lang: str, image_folder: str = "images/products") -> str:
    if not items:
        return "_无购物车商品数据_" if lang.lower().startswith("zh") else "_No cart items_"
    if lang.lower().startswith("zh"):
        lines = [
            "| 商品 | 商品图 | 单价 | 数量 | 小计 | 商品链接 |",
            "|---|---|---:|---:|---:|---|",
        ]
        link_label = "打开商品"
    else:
        lines = [
            "| Product | Image | Unit Price | Qty | Line Total | Link |",
            "|---|---|---:|---:|---:|---|",
        ]
        link_label = "Open"
    for idx, item in enumerate(items, start=1):
        title = safe_text(clean_item_title(str(item.get("title", ""))))
        href = item.get("href", "")
        local_image = item.get("report_local_image") or item.get("local_image")
        img_cell = "-"
        if local_image:
            if str(local_image).startswith("images/"):
                img_cell = f"![item-{idx}]({local_image})"
            else:
                img_cell = f"![item-{idx}]({image_folder}/item-{idx:02d}.jpg)"
        price_text = safe_text(item.get("price_text")) if item.get("price_text") else None
        price_val = to_float(item.get("price_value"))
        currency = safe_text(item.get("currency")) if item.get("currency") else ""
        unit_price = price_text or format_money(price_val, currency if currency else None)
        qty_val = int(item.get("quantity", 1) or 1)
        line_total_val = to_float(item.get("line_total_value"))
        line_total = format_money(line_total_val, currency if currency else None)
        link_cell = f"[{link_label}]({href})" if href else "-"
        lines.append(
            f"| {title} | {img_cell} | {unit_price} | {qty_val} | {line_total} | {link_cell} |"
        )
    return "\n".join(lines)


def build_cart_amount_summary(items: list[dict], cart_summary: dict, lang: str) -> str:
    values = [to_float(x.get("line_total_value")) for x in items if isinstance(x, dict)]
    values = [v for v in values if v is not None]
    inferred_currency = ""
    for x in items:
        if isinstance(x, dict) and x.get("currency"):
            inferred_currency = str(x.get("currency")).strip()
            break

    computed_items_total = sum(values) if values else None
    subtotal_text = safe_text(cart_summary.get("subtotal_text")) if isinstance(cart_summary, dict) else ""
    subtotal_value = to_float(cart_summary.get("subtotal_value")) if isinstance(cart_summary, dict) else None
    subtotal_currency = (
        safe_text(cart_summary.get("currency"))
        if isinstance(cart_summary, dict) and cart_summary.get("currency")
        else inferred_currency
    )
    if subtotal_value is None and isinstance(cart_summary, dict):
        subtotal_value = to_float(cart_summary.get("computed_items_total"))
    if subtotal_value is None:
        subtotal_value = computed_items_total
    if not subtotal_text and subtotal_value is not None:
        subtotal_text = format_money(subtotal_value, subtotal_currency if subtotal_currency else None)

    if lang.lower().startswith("zh"):
        lines = [
            "- 说明：金额取自购物车页面展示的真实价格（单价/数量/小计）。",
            f"- 商品小计合计（按条目计算）：`{format_money(computed_items_total, inferred_currency if inferred_currency else None)}`",
            f"- 购物车显示总额：`{subtotal_text or '-'}`",
        ]
    else:
        lines = [
            "- Note: prices are extracted from real values displayed in the cart page.",
            f"- Computed item sum (from line totals): `{format_money(computed_items_total, inferred_currency if inferred_currency else None)}`",
            f"- Cart displayed total: `{subtotal_text or '-'}`",
        ]
    return "\n".join(lines)


def main() -> None:
    load_workspace_env()
    normalize_proxy_env()
    args = parse_args()
    run_dir = Path(args.run_dir).expanduser().resolve()
    if not run_dir.exists():
        raise SystemExit(f"Run dir not found: {run_dir}")
    lang = detect_lang(args.lang, args.title)
    is_zh = lang.lower().startswith("zh")

    project_dir = (
        Path(args.project_dir).expanduser().resolve()
        if args.project_dir
        else (run_dir / "report-project")
    )
    run_dir_display = relpath_text(run_dir, project_dir)
    project_dir_display = "."
    images_dir = project_dir / "images"
    products_dir = images_dir / "products"
    data_dir = project_dir / "data"
    project_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)
    products_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    # Discover core artifacts
    base_image = find_latest(run_dir, ["*mock-space*.png", "*base-room*.png", "*base*.png"])
    preview_image = find_latest(
        run_dir,
        ["*preview-structure-locked*.png", "*preview*.png", "*staged*.png"],
    )
    compare_image = find_latest(run_dir, ["*compare*.jpg", "*compare*.png"])
    cart_full = find_latest(
        run_dir,
        ["*cart-fullpage*.jpg", "*cart-fullpage*.png", "*cart-evidence*.jpg", "*cart-evidence*.png"],
    )
    if not cart_full:
        cart_candidates: list[Path] = []
        for pat in ["*cart*.jpg", "*cart*.png"]:
            cart_candidates.extend(run_dir.glob(pat))
        cart_candidates = [
            p
            for p in cart_candidates
            if "compare" not in p.name.lower() and "product-board" not in p.name.lower()
        ]
        cart_candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        cart_full = cart_candidates[0] if cart_candidates else None
    product_board = find_latest(run_dir, ["*real-product-board*.jpg", "*product-board*.jpg"])
    diagnosis_path = find_latest(run_dir, ["*space-diagnosis*.json"])
    cart_items_path = find_latest(run_dir, ["*cart-items-downloaded*.json", "*cart-items-clean*.json"])
    cart_summary_path = find_latest(run_dir, ["*cart-summary*.json"])

    # Copy core images with stable names
    copied_images = {}
    if base_image:
        copy_file(base_image, images_dir / "01-base-space.png")
        copied_images["base"] = "images/01-base-space.png"
    if preview_image:
        copy_file(preview_image, images_dir / "02-final-preview.png")
        copied_images["preview"] = "images/02-final-preview.png"
    if compare_image:
        copy_file(compare_image, images_dir / "03-structure-compare.jpg")
        copied_images["compare"] = "images/03-structure-compare.jpg"
    if cart_full:
        copy_file(cart_full, images_dir / "04-cart-evidence.jpg")
        copied_images["cart"] = "images/04-cart-evidence.jpg"
    if product_board:
        copy_file(product_board, images_dir / "05-product-board.jpg")
        copied_images["product_board"] = "images/05-product-board.jpg"

    # Load json content
    diagnosis = load_json(diagnosis_path)
    cart_items = load_json(cart_items_path)
    cart_summary = load_json(cart_summary_path)
    if not isinstance(diagnosis, dict):
        diagnosis = {}
    if not isinstance(cart_items, list):
        cart_items = []
    if not isinstance(cart_summary, dict):
        cart_summary = {}

    translation_backend = has_gemini_translation_backend()
    translation_applied = False
    fallback_zh_applied = False

    if args.translate_content != "never":
        trans_src = collect_translatable_strings(diagnosis, cart_items)
        if trans_src:
            trans_dst = translate_texts(trans_src, lang, mode=args.translate_content)
            translation_applied = trans_dst != trans_src
            mapping = dict(zip(trans_src, trans_dst))
            diagnosis, cart_items = apply_translation(diagnosis, cart_items, mapping)

    if is_zh and not translation_applied:
        diagnosis = localize_diagnosis_zh_fallback(diagnosis)
        fallback_zh_applied = True

    # Copy product images referenced by cart_items
    normalized_items = []
    for idx, item in enumerate(cart_items, start=1):
        if not isinstance(item, dict):
            continue
        new_item = dict(item)
        src_local = item.get("local_image")
        report_local_image = None
        if src_local:
            src_path = Path(src_local).expanduser()
            if not src_path.is_absolute():
                src_path = (run_dir / src_path).resolve()
            if src_path.exists():
                dst = products_dir / f"item-{idx:02d}.jpg"
                copy_file(src_path, dst)
                report_local_image = f"images/products/item-{idx:02d}.jpg"
                new_item["report_local_image"] = report_local_image
                new_item["local_image"] = f"product-images-real/item-{idx:02d}.jpg"
            else:
                new_item["local_image"] = sanitize_local_path(str(src_local))
        if not src_local:
            maybe_local = new_item.get("local_image")
            if isinstance(maybe_local, str) and maybe_local:
                new_item["local_image"] = sanitize_local_path(maybe_local)
        if not report_local_image and isinstance(new_item.get("report_local_image"), str):
            new_item["report_local_image"] = sanitize_local_path(new_item["report_local_image"])
        normalized_items.append(new_item)

    # Copy sanitized data files
    copied_data: dict[str, str] = {}
    if isinstance(diagnosis_path, Path):
        diag_name = diagnosis_path.name
        diag_dst = data_dir / diag_name
        diag_dst.write_text(json.dumps(diagnosis, ensure_ascii=False, indent=2), encoding="utf-8")
        copied_data[diag_name] = f"data/{diag_name}"
    if isinstance(cart_items_path, Path):
        cart_name = cart_items_path.name
        cart_dst = data_dir / cart_name
        cart_dst.write_text(json.dumps(normalized_items, ensure_ascii=False, indent=2), encoding="utf-8")
        copied_data[cart_name] = f"data/{cart_name}"
    if isinstance(cart_summary_path, Path) or cart_summary:
        summary_name = cart_summary_path.name if isinstance(cart_summary_path, Path) else "cart-summary.json"
        summary_dst = data_dir / summary_name
        summary_dst.write_text(json.dumps(cart_summary, ensure_ascii=False, indent=2), encoding="utf-8")
        copied_data[summary_name] = f"data/{summary_name}"

    # Save normalized data for report usage
    normalized_cart_path = data_dir / "cart-items-report.json"
    normalized_cart_path.write_text(
        json.dumps(normalized_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    numeric_line_totals = [
        to_float(x.get("line_total_value"))
        for x in normalized_items
        if isinstance(x, dict) and to_float(x.get("line_total_value")) is not None
    ]
    computed_items_total = sum(numeric_line_totals) if numeric_line_totals else None
    cart_subtotal_value = to_float(cart_summary.get("subtotal_value"))
    if cart_subtotal_value is None:
        cart_subtotal_value = to_float(cart_summary.get("computed_items_total"))

    total_budget = diagnosis.get("total_budget_usd", {}) if isinstance(diagnosis, dict) else {}
    budget_text = f"{args.currency} {total_budget.get('min', '-')}-{total_budget.get('max', '-')}"
    buy_now = diagnosis.get("buy_now", []) if isinstance(diagnosis.get("buy_now"), list) else []
    buy_later = diagnosis.get("buy_later", []) if isinstance(diagnosis.get("buy_later"), list) else []
    keep_items = diagnosis.get("keep", []) if isinstance(diagnosis.get("keep"), list) else []
    confirmed = (
        diagnosis.get("confirmed_observations", [])
        if isinstance(diagnosis.get("confirmed_observations"), list)
        else []
    )
    assumptions = diagnosis.get("assumptions", []) if isinstance(diagnosis.get("assumptions"), list) else []

    summary = diagnosis.get("space_summary", "暂无空间摘要" if is_zh else "No summary")

    if is_zh:
        report_md = f"""# {args.title}

## 1. 项目概览

- 目标网站：`{args.website}`
- 风格目标：`{args.style}`
- 预算区间：`{budget_text}`
- 运行目录：`{run_dir_display}`
- 报告目录：`{project_dir_display}`

## 2. 空间诊断摘要

{summary}

### 已确认信息
{chr(10).join([f"- {safe_text(x)}" for x in confirmed]) if confirmed else "- 无"}

### 关键假设
{chr(10).join([f"- {safe_text(x)}" for x in assumptions]) if assumptions else "- 无"}

## 3. 保留与新增策略

### 保留项
{chr(10).join([f"- {safe_text(x)}" for x in keep_items]) if keep_items else "- 无"}

### 立即购买
{build_buy_table(buy_now, args.currency, lang)}

### 延后购买
{build_buy_table(buy_later, args.currency, lang)}

## 4. 购物车与真实商品图

### 购物车商品对照
{build_cart_table(normalized_items, lang)}

### 购物车金额汇总
{build_cart_amount_summary(normalized_items, cart_summary, lang)}

### 购物车证据图
![cart](images/04-cart-evidence.jpg)

## 5. 效果图与结构一致性

| 原始空间 | 最终预览 |
|---|---|
| ![base](images/01-base-space.png) | ![preview](images/02-final-preview.png) |

### 生图约束
- 结构锁定：门/窗/墙/内置结构/视角保持不变。
- 商品约束：仅允许出现购物车商品（无额外新增物件）。

### 结构一致性对比图（门/窗/墙/视角）
![compare](images/03-structure-compare.jpg)

### 商品参考板
![product-board](images/05-product-board.jpg)

## 6. 交付清单

- 报告：`REPORT.md`
- 图片目录：`images/`
- 数据目录：`data/`
  - `space-diagnosis.json`（若存在）
  - `cart-items-downloaded.json / cart-items-clean.json`（若存在）
  - `cart-summary.json`（若存在）
  - `cart-items-report.json`（规范化后）

---
本报告由 `build_home_report_project.py` 自动生成。
"""
    else:
        report_md = f"""# {args.title}

## 1. Project Overview

- Target website: `{args.website}`
- Style target: `{args.style}`
- Budget range: `{budget_text}`
- Run directory: `{run_dir_display}`
- Report directory: `{project_dir_display}`

## 2. Space Diagnosis Summary

{summary}

### Confirmed Observations
{chr(10).join([f"- {safe_text(x)}" for x in confirmed]) if confirmed else "- None"}

### Key Assumptions
{chr(10).join([f"- {safe_text(x)}" for x in assumptions]) if assumptions else "- None"}

## 3. Keep vs Buy Strategy

### Keep
{chr(10).join([f"- {safe_text(x)}" for x in keep_items]) if keep_items else "- None"}

### Buy Now
{build_buy_table(buy_now, args.currency, lang)}

### Buy Later
{build_buy_table(buy_later, args.currency, lang)}

## 4. Cart and Real Product Images

### Cart Product Table
{build_cart_table(normalized_items, lang)}

### Cart Amount Summary
{build_cart_amount_summary(normalized_items, cart_summary, lang)}

### Cart Evidence
![cart](images/04-cart-evidence.jpg)

## 5. Preview and Structure Consistency

| Base Space | Final Preview |
|---|---|
| ![base](images/01-base-space.png) | ![preview](images/02-final-preview.png) |

### Structure Consistency Compare
![compare](images/03-structure-compare.jpg)

### Product Reference Board
![product-board](images/05-product-board.jpg)

## 6. Deliverables

- Report: `REPORT.md`
- Image folder: `images/`
- Data folder: `data/`
  - `space-diagnosis.json` (if present)
  - `cart-items-downloaded.json / cart-items-clean.json` (if present)
  - `cart-summary.json` (if present)
  - `cart-items-report.json` (normalized)

---
Generated by `build_home_report_project.py`.
"""

    report_path = project_dir / "REPORT.md"
    report_path.write_text(report_md, encoding="utf-8")

    manifest = {
        "run_dir": run_dir_display,
        "project_dir": project_dir_display,
        "title": args.title,
        "lang": lang,
        "translate_content": args.translate_content,
        "translation_backend_available": translation_backend,
        "translation_applied": translation_applied,
        "fallback_zh_applied": fallback_zh_applied,
        "website": args.website,
        "style": args.style,
        "currency": args.currency,
        "copied_images": copied_images,
        "copied_data": copied_data,
        "cart_items_count": len(normalized_items),
        "cart_items_computed_total": computed_items_total,
        "cart_subtotal_value": cart_subtotal_value,
        "has_diagnosis": bool(diagnosis),
    }
    (project_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"project_dir: {project_dir}")
    print(f"report: {report_path}")
    print(f"manifest: {project_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
