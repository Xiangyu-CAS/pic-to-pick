#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
WIDTH = 4724
HEIGHT = 11811
DPI = 150
MARGIN = 220
CARD_RADIUS = 42

BG_TOP = (249, 244, 235)
BG_BOTTOM = (243, 237, 229)
INK = (27, 27, 27)
MUTED = (96, 88, 80)
ORANGE = (233, 148, 92)
ORANGE_SOFT = (249, 224, 204)
TEAL = (107, 149, 149)
TEAL_SOFT = (214, 232, 231)
BLUE = (104, 138, 196)
BLUE_SOFT = (216, 227, 247)
ROSE = (214, 117, 112)
ROSE_SOFT = (247, 223, 220)
GOLD = (171, 140, 84)
GOLD_SOFT = (241, 233, 212)
CARD = (255, 252, 247)
OUTLINE = (223, 214, 201)
DARK = (34, 37, 41)


def font_candidates(bold: bool) -> list[str]:
    if bold:
        return [
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/HelveticaNeue.ttc",
        ]
    return [
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
    ]


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for candidate in font_candidates(bold):
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def lerp_color(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    ascii_buffer = ""
    for ch in text:
        if ch == "\n":
            if ascii_buffer:
                tokens.append(ascii_buffer)
                ascii_buffer = ""
            tokens.append("\n")
            continue
        if ch == " ":
            if ascii_buffer:
                tokens.append(ascii_buffer)
                ascii_buffer = ""
            tokens.append(" ")
            continue
        if ord(ch) < 128 and ch not in "，。；：！？（）【】《》、":
            ascii_buffer += ch
            continue
        if ascii_buffer:
            tokens.append(ascii_buffer)
            ascii_buffer = ""
        tokens.append(ch)
    if ascii_buffer:
        tokens.append(ascii_buffer)
    return tokens


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for token in tokenize(text):
        if token == "\n":
            lines.append(current.rstrip())
            current = ""
            continue
        proposal = token if not current else f"{current}{token}"
        if token == " " and not current:
            continue
        if current and draw.textlength(proposal, font=font) > max_width:
            lines.append(current.rstrip())
            current = token.lstrip()
        else:
            current = proposal
    if current:
        lines.append(current.rstrip())
    return [line for line in lines if line]


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    max_width: int,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    line_gap: int,
) -> int:
    lines = wrap_text(draw, text, font, max_width)
    line_h = font.size + line_gap
    for index, line in enumerate(lines):
        draw.text((x, y + index * line_h), line, font=font, fill=fill)
    return y + len(lines) * line_h


def rounded_card(
    base: Image.Image,
    box: tuple[int, int, int, int],
    fill: tuple[int, int, int] | tuple[int, int, int, int],
    outline: tuple[int, int, int] = OUTLINE,
    radius: int = CARD_RADIUS,
    shadow_alpha: int = 40,
    shadow_offset: tuple[int, int] = (0, 18),
) -> None:
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1
    shadow = Image.new("RGBA", (w + 120, h + 120), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((60, 50, 60 + w, 50 + h), radius=radius, fill=(23, 27, 30, shadow_alpha))
    shadow = shadow.filter(ImageFilter.GaussianBlur(22))
    base.alpha_composite(shadow, (x1 - 60 + shadow_offset[0], y1 - 50 + shadow_offset[1]))

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=3)
    base.alpha_composite(overlay)


def pill(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    text_fill: tuple[int, int, int] = INK,
    outline: tuple[int, int, int] | None = None,
    padding: tuple[int, int] = (28, 18),
) -> tuple[int, int, int, int]:
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    rect = (x, y, x + tw + padding[0] * 2, y + th + padding[1] * 2)
    draw.rounded_rectangle(rect, radius=(rect[3] - rect[1]) // 2, fill=fill, outline=outline, width=2 if outline else 0)
    draw.text((x + padding[0], y + padding[1] - 3), text, font=font, fill=text_fill)
    return rect


def cover_image(path: Path, size: tuple[int, int], corner: int = 28) -> Image.Image:
    image = Image.open(path).convert("RGB")
    fitted = ImageOps.fit(image, size, method=Image.Resampling.LANCZOS)
    if corner <= 0:
        return fitted
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=corner, fill=255)
    fitted.putalpha(mask)
    return fitted


def contain_image(path: Path, size: tuple[int, int], bg: tuple[int, int, int], corner: int = 28) -> Image.Image:
    image = Image.open(path).convert("RGB")
    fitted = ImageOps.contain(image, size, method=Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, bg)
    x = (size[0] - fitted.size[0]) // 2
    y = (size[1] - fitted.size[1]) // 2
    canvas.paste(fitted, (x, y))
    if corner <= 0:
        return canvas
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=corner, fill=255)
    canvas.putalpha(mask)
    return canvas


def image_frame(
    base: Image.Image,
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    image_path: Path,
    mode: str = "cover",
    tint: tuple[int, int, int] = (248, 244, 238),
) -> None:
    rounded_card(base, box, fill=(255, 255, 255, 245), outline=OUTLINE, radius=32, shadow_alpha=24, shadow_offset=(0, 10))
    x1, y1, x2, y2 = box
    title_font = get_font(66, bold=True)
    draw.text((x1 + 30, y1 + 24), label, font=title_font, fill=INK)
    inner = (x1 + 26, y1 + 96, x2 - 26, y2 - 26)
    inner_size = (inner[2] - inner[0], inner[3] - inner[1])
    if mode == "contain":
        image = contain_image(image_path, inner_size, tint)
    else:
        image = cover_image(image_path, inner_size)
    base.alpha_composite(image, (inner[0], inner[1]))


def draw_background(base: Image.Image) -> None:
    bg = ImageDraw.Draw(base)
    for y in range(HEIGHT):
        color = lerp_color(BG_TOP, BG_BOTTOM, y / (HEIGHT - 1))
        bg.line((0, y, WIDTH, y), fill=color)

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse((-420, -180, 2200, 1650), fill=(255, 255, 255, 120))
    od.ellipse((3000, 160, 5200, 2200), fill=(255, 220, 189, 96))
    od.ellipse((2600, 4150, 5200, 6050), fill=(214, 232, 231, 78))
    od.ellipse((-300, 7200, 1700, 9200), fill=(216, 227, 247, 72))
    od.ellipse((2600, 9300, 5200, 11700), fill=(249, 224, 204, 80))
    overlay = overlay.filter(ImageFilter.GaussianBlur(70))
    base.alpha_composite(overlay)


def section_heading(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    eyebrow: str,
    title: str,
    subtitle: str,
    accent_fill: tuple[int, int, int],
) -> int:
    pill_font = get_font(56, bold=True)
    title_font = get_font(144, bold=True)
    subtitle_font = get_font(74)
    pill(draw, (x, y), eyebrow, pill_font, accent_fill)
    y += 144
    draw.text((x, y), title, font=title_font, fill=INK)
    y += 166
    return draw_wrapped_text(draw, subtitle, x, y, WIDTH - x - MARGIN, subtitle_font, MUTED, 22)


def hero_stack(base: Image.Image, draw: ImageDraw.ImageDraw) -> None:
    main_box = (2890, 280, 4490, 1320)
    left_box = (2570, 910, 3440, 1800)
    right_box = (3480, 1010, 4380, 1890)

    image_frame(
        base,
        draw,
        main_box,
        "家居改造",
        ROOT / "showcase/example1-success/report-project/images/02-final-preview.jpg",
        mode="cover",
    )
    image_frame(
        base,
        draw,
        left_box,
        "OOTD",
        ROOT / "showcase/example2-ootd/report-project/images/02-final-preview.jpg",
        mode="cover",
    )
    image_frame(
        base,
        draw,
        right_box,
        "Beauty",
        ROOT / "showcase/example3-beauty-face/report-project/images/02-final-preview.jpg",
        mode="cover",
    )

    badge_font = get_font(42, bold=True)
    pill(draw, (3230, 204), "真实购物车绑定", badge_font, ORANGE_SOFT, text_fill=(114, 63, 22), outline=(228, 169, 122))
    pill(draw, (2590, 1940), "先预览，再决策，再购买", badge_font, TEAL_SOFT, text_fill=(37, 89, 87), outline=(123, 171, 170))


def flow_cards(base: Image.Image, draw: ImageDraw.ImageDraw, top: int) -> int:
    card_w = 1316
    card_h = 720
    gap_x = 36
    gap_y = 40
    items = [
        ("01", "上传参考图", "支持空房、穿搭 mock、脸部、美甲等输入。", ORANGE_SOFT, ORANGE),
        ("02", "理解场景与风格", "识别空间结构、人物部位、风格线索和约束条件。", BLUE_SOFT, BLUE),
        ("03", "电商检索并真实加购", "连接 Amazon，把候选商品加入真实购物车。", TEAL_SOFT, TEAL),
        ("04", "生成商品约束板", "把真实商品图整理成可直接驱动 AI 的参考板。", GOLD_SOFT, GOLD),
        ("05", "受约束 AI 预览", "只围绕购物车中的类目与风格出图，尽量不漂移。", ROSE_SOFT, ROSE),
        ("06", "报告与证据输出", "输出预览图、购物车截图、金额明细和项目报告。", TEAL_SOFT, TEAL),
    ]
    small_font = get_font(44)
    number_font = get_font(54, bold=True)
    title_font = get_font(58, bold=True)
    desc_font = get_font(44)

    for idx, (num, title, desc, tint, accent) in enumerate(items):
        row = idx // 3
        col = idx % 3
        x = MARGIN + col * (card_w + gap_x)
        y = top + row * (card_h + gap_y)
        rounded_card(base, (x, y, x + card_w, y + card_h), fill=(255, 254, 251, 240), outline=OUTLINE)
        draw.rounded_rectangle((x + 40, y + 38, x + 180, y + 118), radius=40, fill=tint, outline=accent, width=3)
        draw.text((x + 67, y + 54), num, font=number_font, fill=accent)
        draw.text((x + 40, y + 168), title, font=title_font, fill=INK)
        draw_wrapped_text(draw, desc, x + 40, y + 258, card_w - 80, desc_font, MUTED, 14)
        draw.rounded_rectangle((x + 40, y + card_h - 84, x + card_w - 40, y + card_h - 50), radius=18, fill=tint)
        draw.text((x + 58, y + card_h - 84), "从图像理解走到真实购买闭环", font=small_font, fill=accent)
    return top + card_h * 2 + gap_y


def scenario_card(
    base: Image.Image,
    draw: ImageDraw.ImageDraw,
    y: int,
    title: str,
    subtitle: str,
    chips: Iterable[tuple[str, tuple[int, int, int], tuple[int, int, int]]],
    accent: tuple[int, int, int],
    tint: tuple[int, int, int],
    labels_and_paths: list[tuple[str, Path, str]],
) -> int:
    x1 = MARGIN
    x2 = WIDTH - MARGIN
    height = 1180
    rounded_card(base, (x1, y, x2, y + height), fill=(255, 253, 249, 245), outline=OUTLINE, radius=48)

    left_w = 1020
    left_box = (x1 + 34, y + 34, x1 + 34 + left_w, y + height - 34)
    draw.rounded_rectangle(left_box, radius=36, fill=tint, outline=accent, width=3)

    title_font = get_font(104, bold=True)
    subtitle_font = get_font(60)
    chip_font = get_font(54, bold=True)

    draw.text((left_box[0] + 48, left_box[1] + 50), title, font=title_font, fill=INK)
    body_bottom = draw_wrapped_text(
        draw,
        subtitle,
        left_box[0] + 48,
        left_box[1] + 194,
        left_w - 96,
        subtitle_font,
        MUTED,
        16,
    )
    chip_y = body_bottom + 30
    for text, fill, text_fill in chips:
        rect = pill(draw, (left_box[0] + 48, chip_y), text, chip_font, fill, text_fill=text_fill)
        chip_y = rect[3] + 24

    right_x = left_box[2] + 40
    slot_gap = 28
    slot_w = 950
    slot_h = 1030
    for idx, (label, path, mode) in enumerate(labels_and_paths):
        box = (
            right_x + idx * (slot_w + slot_gap),
            y + 70,
            right_x + idx * (slot_w + slot_gap) + slot_w,
            y + 70 + slot_h,
        )
        image_frame(base, draw, box, label, path, mode=mode)
    return y + height


def feature_grid(base: Image.Image, draw: ImageDraw.ImageDraw, top: int) -> int:
    card_w = 1320
    card_h = 520
    gap_x = 32
    gap_y = 32
    features = [
        ("真实商品绑定", "不是靠想象凑概念图，而是把电商真实商品拉进闭环。", ORANGE_SOFT, (120, 72, 32)),
        ("购物车约束", "预览只围绕已加购类目和风格出图，减少幻觉和漂移。", TEAL_SOFT, (42, 92, 91)),
        ("结构锁定", "家居场景尽量保留空间结构、视角和动线，不随意改房。", BLUE_SOFT, (56, 80, 125)),
        ("金额可核对", "单价、数量、小计、总额都能在报告中落下来。", GOLD_SOFT, (104, 81, 41)),
        ("多场景迁移", "从空间、OOTD 到美妆/美甲，一套工作流跨品类复用。", ROSE_SOFT, (119, 57, 54)),
        ("开源可扩展", "兼容 OpenClaw、Claude Code、Codex，方便继续改造成产品。", (232, 238, 228), (67, 98, 58)),
    ]

    title_font = get_font(78, bold=True)
    desc_font = get_font(56)
    for idx, (title, desc, tint, text_color) in enumerate(features):
        row = idx // 3
        col = idx % 3
        x = MARGIN + col * (card_w + gap_x)
        y = top + row * (card_h + gap_y)
        rounded_card(base, (x, y, x + card_w, y + card_h), fill=(255, 253, 249, 240), outline=OUTLINE, radius=36)
        draw.rounded_rectangle((x + 34, y + 34, x + 170, y + 112), radius=28, fill=tint)
        draw.text((x + 56, y + 42), f"{idx + 1}", font=get_font(58, bold=True), fill=text_color)
        draw.text((x + 34, y + 150), title, font=title_font, fill=INK)
        draw_wrapped_text(draw, desc, x + 34, y + 256, card_w - 68, desc_font, MUTED, 16)
    return top + card_h * 2 + gap_y


def metric_row(
    base: Image.Image,
    draw: ImageDraw.ImageDraw,
    top: int,
    items: list[tuple[str, str, tuple[int, int, int], tuple[int, int, int]]],
) -> int:
    card_w = 1010
    card_h = 360
    gap = 28
    value_font = get_font(126, bold=True)
    label_font = get_font(56)
    for idx, (value, label, tint, accent) in enumerate(items):
        x = MARGIN + idx * (card_w + gap)
        rounded_card(base, (x, top, x + card_w, top + card_h), fill=(255, 253, 248, 244), outline=OUTLINE, radius=34)
        draw.rounded_rectangle((x + 30, top + 26, x + 116, top + 112), radius=24, fill=tint, outline=accent, width=3)
        draw.text((x + 52, top + 38), str(idx + 1), font=get_font(54, bold=True), fill=accent)
        draw.text((x + 30, top + 126), value, font=value_font, fill=INK)
        draw.text((x + 34, top + 266), label, font=label_font, fill=MUTED)
    return top + card_h


def evidence_strip(base: Image.Image, draw: ImageDraw.ImageDraw, top: int) -> int:
    x1 = MARGIN
    x2 = WIDTH - MARGIN
    height = 900
    rounded_card(base, (x1, top, x2, top + height), fill=(255, 252, 247, 244), outline=OUTLINE, radius=44)
    draw.text((x1 + 48, top + 44), "证据链展示", font=get_font(108, bold=True), fill=INK)
    draw.text((x1 + 48, top + 176), "输入图、商品约束板、AI 预览和购物车证据会一起出现，减少“只是生成一张图”的质疑。", font=get_font(62), fill=MUTED)

    labels = [
        ("Base", ROOT / "showcase/example1-success/report-project/images/01-base-space.jpg", "cover"),
        ("Product Board", ROOT / "showcase/example1-success/report-project/images/05-product-board.jpg", "contain"),
        ("Preview", ROOT / "showcase/example1-success/report-project/images/02-final-preview.jpg", "cover"),
        ("Cart Evidence", ROOT / "showcase/example1-success/report-project/images/04-cart-evidence.jpg", "contain"),
    ]
    card_w = 980
    card_h = 580
    gap = 32
    start_x = x1 + 50
    y = top + 236
    arrow_font = get_font(122, bold=True)
    for idx, (label, path, mode) in enumerate(labels):
        box = (start_x + idx * (card_w + gap), y, start_x + idx * (card_w + gap) + card_w, y + card_h)
        image_frame(base, draw, box, label, path, mode=mode)
        if idx < len(labels) - 1:
            ax = box[2] + 8
            draw.text((ax, y + 220), "→", font=arrow_font, fill=(157, 141, 121))
    return top + height


def flow_board(base: Image.Image, draw: ImageDraw.ImageDraw, top: int) -> int:
    x1 = MARGIN
    x2 = WIDTH - MARGIN
    height = 900
    rounded_card(base, (x1, top, x2, top + height), fill=(255, 253, 249, 245), outline=OUTLINE, radius=44)
    draw.text((x1 + 48, top + 44), "工作流闭环", font=get_font(96, bold=True), fill=INK)
    draw.text((x1 + 48, top + 168), "从上传参考图到输出证据报告，核心是让每一步都能被下一步消费，而不是停在单点能力。", font=get_font(56), fill=MUTED)

    items = [
        ("01", "上传图片", "空房、穿搭、脸部、美甲"),
        ("02", "理解需求", "提取结构、风格、部位"),
        ("03", "真实加购", "Amazon 检索并加入购物车"),
        ("04", "商品约束板", "整理真实商品图与类目"),
        ("05", "AI 预览", "只围绕已加购商品生成"),
        ("06", "报告输出", "证据图、金额、结论"),
    ]
    card_w = 635
    card_h = 470
    gap = 38
    start_x = x1 + 60
    y = top + 268
    num_font = get_font(56, bold=True)
    title_font = get_font(70, bold=True)
    desc_font = get_font(50)
    arrow_font = get_font(108, bold=True)
    tints = [ORANGE_SOFT, BLUE_SOFT, TEAL_SOFT, GOLD_SOFT, ROSE_SOFT, TEAL_SOFT]
    accents = [ORANGE, BLUE, TEAL, GOLD, ROSE, TEAL]

    for idx, (num, title, desc) in enumerate(items):
        x = start_x + idx * (card_w + gap)
        rounded_card(base, (x, y, x + card_w, y + card_h), fill=(255, 255, 255, 242), outline=OUTLINE, radius=30, shadow_alpha=24, shadow_offset=(0, 10))
        draw.rounded_rectangle((x + 24, y + 20, x + 124, y + 88), radius=24, fill=tints[idx], outline=accents[idx], width=3)
        draw.text((x + 48, y + 34), num, font=num_font, fill=accents[idx])
        draw.text((x + 24, y + 132), title, font=title_font, fill=INK)
        draw_wrapped_text(draw, desc, x + 24, y + 220, card_w - 48, desc_font, MUTED, 10)
        draw.rounded_rectangle((x + 24, y + 376, x + card_w - 24, y + 424), radius=18, fill=tints[idx])
        draw.text((x + 30, y + 382), "可被下一步直接消费", font=get_font(40, bold=True), fill=accents[idx])
        if idx < len(items) - 1:
            draw.text((x + card_w + 2, y + 148), "→", font=arrow_font, fill=(157, 141, 121))
    return top + height


def summary_footer(base: Image.Image, draw: ImageDraw.ImageDraw, top: int) -> int:
    bottom = HEIGHT - 180
    rounded_card(base, (MARGIN, top, WIDTH - MARGIN, bottom), fill=DARK + (245,), outline=(53, 58, 63), radius=48, shadow_alpha=26)
    draw.text((MARGIN + 70, top + 56), "从“喜欢一张图”到“真的可以买什么”", font=get_font(136, bold=True), fill=(251, 246, 239))
    draw_wrapped_text(
        draw,
        "pic-to-pick 让输入图、真实商品、AI 预览和报告证据彼此对齐，把生成式 AI 往“可核对、可执行、可下单”再推进一步。",
        MARGIN + 70,
        top + 240,
        WIDTH - MARGIN * 2 - 140,
        get_font(66),
        (224, 218, 210),
        18,
    )

    box_y = top + 420
    box_h = 380
    box_w = 1320
    gap = 28
    boxes = [
        ("对用户", "降低选品与搭配试错\n先预览，再决策", ORANGE),
        ("对业务", "连接种草、预览、加购、下单\n让转化链路更完整", TEAL),
        ("对团队", "沉淀可复用的端到端模板\n便于继续产品化", BLUE),
    ]
    for idx, (title, body, accent) in enumerate(boxes):
        x = MARGIN + 70 + idx * (box_w + gap)
        draw.rounded_rectangle((x, box_y, x + box_w, box_y + box_h), radius=34, fill=(52, 57, 62), outline=(78, 84, 90), width=3)
        draw.rounded_rectangle((x + 28, box_y + 26, x + 184, box_y + 92), radius=24, fill=accent)
        draw.text((x + 48, box_y + 32), title, font=get_font(52, bold=True), fill=(253, 248, 242))
        draw_wrapped_text(draw, body, x + 28, box_y + 132, box_w - 56, get_font(58), (231, 225, 217), 18)

    key_y = box_y + box_h + 48
    draw.text((MARGIN + 70, key_y), "项目关键词", font=get_font(76, bold=True), fill=(251, 246, 239))
    key_font = get_font(52, bold=True)
    pill(draw, (MARGIN + 70, key_y + 86), "真实购物车", key_font, ORANGE, text_fill=(255, 249, 241))
    pill(draw, (MARGIN + 360, key_y + 86), "商品约束生图", key_font, TEAL, text_fill=(255, 249, 241))
    pill(draw, (MARGIN + 730, key_y + 86), "证据化报告", key_font, BLUE, text_fill=(255, 249, 241))
    pill(draw, (MARGIN + 1040, key_y + 86), "多场景迁移", key_font, ROSE, text_fill=(255, 249, 241))
    pill(draw, (MARGIN + 1360, key_y + 86), "OpenClaw / Claude Code / Codex", key_font, GOLD, text_fill=(255, 249, 241))
    draw.text((WIDTH - MARGIN - 930, bottom - 100), "Repository: pic-to-pick", font=get_font(48), fill=(196, 189, 181))
    return bottom


def build_poster() -> tuple[Path, Path, Path]:
    poster = Image.new("RGBA", (WIDTH, HEIGHT), BG_TOP + (255,))
    draw_background(poster)
    draw = ImageDraw.Draw(poster)

    huge = get_font(540, bold=True)
    big = get_font(200, bold=True)
    body = get_font(76)
    chip_font = get_font(52, bold=True)
    small = get_font(48)

    pill(draw, (MARGIN, 138), "兼容 OpenClaw / Claude Code / Codex", chip_font, TEAL_SOFT, text_fill=(39, 87, 87), outline=(139, 182, 181))
    pill(draw, (WIDTH - MARGIN - 470, 138), "生活龙虾 / 看图成单", chip_font, ORANGE_SOFT, text_fill=(114, 63, 22), outline=(228, 169, 122))
    draw.text((MARGIN, 212), "看图成单虾", font=huge, fill=INK)
    draw.text((MARGIN + 6, 770), "（pic-to-pick）", font=big, fill=INK)
    draw.text((MARGIN, 1010), "把参考图直接推进到可购买方案", font=body, fill=MUTED)

    pill(draw, (MARGIN, 1140), "真实商品加购", chip_font, ORANGE_SOFT, text_fill=(114, 63, 22), outline=(228, 169, 122))
    pill(draw, (MARGIN + 390, 1140), "商品约束 AI 预览", chip_font, BLUE_SOFT, text_fill=(55, 80, 121), outline=(133, 160, 214))
    pill(draw, (MARGIN + 960, 1140), "购物车证据", chip_font, GOLD_SOFT, text_fill=(101, 77, 31), outline=(194, 175, 128))

    draw.rounded_rectangle((MARGIN, 1328, MARGIN + 1860, 1468), radius=34, fill=(255, 255, 255, 170))
    draw.text((MARGIN + 34, 1366), "从灵感图到下单闭环。", font=small, fill=DARK)

    hero_stack(poster, draw)

    strip_bottom = evidence_strip(poster, draw, 2060)
    metric_bottom = metric_row(
        poster,
        draw,
        strip_bottom + 38,
        [
            ("3 大场景", "家居 / OOTD / Beauty", ORANGE_SOFT, ORANGE),
            ("22 件", "累计真实加购商品", TEAL_SOFT, TEAL),
            ("4 份", "报告与证据链已产出", BLUE_SOFT, BLUE),
            ("S$3,951.75", "示例累计购物车金额", GOLD_SOFT, GOLD),
        ],
    )

    section_y = metric_bottom + 120
    section_y = section_heading(
        draw,
        MARGIN,
        section_y,
        "闭环流程",
        "6 步把灵感图落进购物车",
        "项目的核心不是生成一张好看的图，而是让“输入图、商品、预览、证据、金额”连成一条可执行链路。",
        ORANGE_SOFT,
    )
    flow_bottom = flow_board(poster, draw, section_y + 36)

    scenario_top = flow_bottom + 120
    scenario_top = section_heading(
        draw,
        MARGIN,
        scenario_top,
        "案例展示",
        "三类场景，已经跑通",
        "每个案例都来自项目中的真实素材与真实报告，适合直接向评审或合作方展示“这不是概念 demo”。",
        TEAL_SOFT,
    ) + 42

    y = scenario_top
    y = scenario_card(
        poster,
        draw,
        y,
        "家居空间改造",
        "空房客厅输入，先在 Amazon 真实加购，再基于购物车商品做受约束软装预览。",
        [
            ("11 件真实商品", ORANGE_SOFT, (114, 63, 22)),
            ("S$3,726.55", GOLD_SOFT, (101, 77, 31)),
            ("结构与视角保持", BLUE_SOFT, (55, 80, 121)),
        ],
        GOLD,
        (250, 245, 236),
        [
            ("输入空间", ROOT / "showcase/example1-success/report-project/images/01-base-space.jpg", "cover"),
            ("商品约束板", ROOT / "showcase/example1-success/report-project/images/05-product-board.jpg", "contain"),
            ("最终预览", ROOT / "showcase/example1-success/report-project/images/02-final-preview.jpg", "cover"),
        ],
    ) + 54

    y = scenario_card(
        poster,
        draw,
        y,
        "每日穿搭 OOTD",
        "从 9:16 儿童 mock 图出发，把穿搭灵感落到真实购物车，再回到受约束 try-on 预览。",
        [
            ("7 件真实商品", ORANGE_SOFT, (114, 63, 22)),
            ("S$179.41", GOLD_SOFT, (101, 77, 31)),
            ("支持人物与服饰类目", BLUE_SOFT, (55, 80, 121)),
        ],
        BLUE,
        (242, 246, 254),
        [
            ("原始图", ROOT / "showcase/example2-ootd/report-project/images/01-base-space.jpg", "cover"),
            ("商品约束板", ROOT / "showcase/example2-ootd/report-project/images/05-product-board.jpg", "contain"),
            ("最终预览", ROOT / "showcase/example2-ootd/report-project/images/02-final-preview.jpg", "cover"),
        ],
    ) + 54

    y = scenario_card(
        poster,
        draw,
        y,
        "Beauty: 脸部美妆",
        "从素颜脸部输入出发，结合真实加购的彩妆商品，输出与购物车一致的脸部上妆预览和证据报告。",
        [
            ("3 件真实商品", ORANGE_SOFT, (114, 63, 22)),
            ("S$35.80", GOLD_SOFT, (101, 77, 31)),
            ("支持细颗粒编辑任务", ROSE_SOFT, (119, 57, 54)),
        ],
        ROSE,
        (252, 244, 244),
        [
            ("脸部输入", ROOT / "showcase/example3-beauty-face/report-project/images/01-base-space.jpg", "cover"),
            ("商品约束板", ROOT / "showcase/example3-beauty-face/report-project/images/05-product-board.jpg", "contain"),
            ("脸部预览", ROOT / "showcase/example3-beauty-face/report-project/images/02-final-preview.jpg", "cover"),
        ],
    ) + 160

    feature_top = section_heading(
        draw,
        MARGIN,
        y,
        "核心价值",
        "让 AI 效果图从“好看”升级为“可买”",
        "这张海报想传达的重点是：项目把生成式 AI 的效果，推进成可验证、可核对、可执行的购买闭环。",
        ROSE_SOFT,
    ) + 44
    feature_bottom = feature_grid(poster, draw, feature_top)

    footer_y = feature_bottom + 90
    summary_footer(poster, draw, footer_y)

    assets_dir = ROOT / "assets"
    assets_dir.mkdir(exist_ok=True)
    png_path = assets_dir / "poster-rollup-v2-0.8x2m-150dpi.png"
    jpg_path = assets_dir / "poster-rollup-v2-0.8x2m-150dpi.jpg"
    preview_path = assets_dir / "poster-rollup-v2-preview.jpg"

    rgb = poster.convert("RGB")
    rgb.save(png_path, dpi=(DPI, DPI))
    rgb.save(jpg_path, quality=95, dpi=(DPI, DPI), optimize=True)
    preview = rgb.resize((1181, round(HEIGHT * 1181 / WIDTH)), Image.Resampling.LANCZOS)
    preview.save(preview_path, quality=90)
    return png_path, jpg_path, preview_path


if __name__ == "__main__":
    paths = build_poster()
    for path in paths:
        print(path)
