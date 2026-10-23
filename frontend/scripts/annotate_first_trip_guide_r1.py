# -*- coding: utf-8 -*-
"""把教程原图变成"圈出来 + 编号 + 图下说明"的标注版（Issue #31 C 返工）。

为什么要有这个脚本而不是手 P：用户否决的第一条就是"人工猜坐标导致偏移"。坐标全部来自
`e2e/qoder31-first-trip-guide.spec.ts` 现取的 `locator.boundingBox()`，缩放比来自
`PNG 实际宽 / 记录时的视口宽`，所以设备像素比一变也不会画歪。

版式上做了两处取舍，都是被上一版的现场截图逼出来的：
1. 编号写在贴着按钮的**圆形角标**里，不再写悬浮黑条——黑条会盖住按钮旁边的正文
   （④ 两张实测盖住了"动态"两个字和"住宿搜索失败"那一行）；
2. 每一屏的动作话写进图片**下方的说明带**（同一张 PNG 里，不是网页文字），
   所以屏幕内容一个像素都没被遮，读者缩放、转发、打印都还带着说明。

原图留在 docs/assets/raw/，标注版写到 docs/assets/——教程引用的是标注版。

用法：python scripts/annotate_first_trip_guide_r1.py [--frontend-dir DIR]
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyhbd.ttc",   # 微软雅黑 Bold：中文标注不发虚
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\NotoSansCJK-Bold.ttc",
]
INK = (226, 59, 43)        # 高对比红：亮档暗档都看得见
HALO = (255, 255, 255)     # 描一圈白，压住深色底也能辨
BADGE_BG = (17, 17, 19)
BADGE_FG = (255, 255, 255)
NOTE_BG = (255, 243, 199)
NOTE_INK = (74, 44, 8)
CAPTION_BG = (255, 255, 255)
CAPTION_INK = (28, 28, 30)
CAPTION_RULE = (226, 59, 43)
CIRCLED = "①②③④⑤⑥⑦⑧⑨"


def font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def text_width(draw, text, face):
    box = draw.textbbox((0, 0), text, font=face)
    return box[2] - box[0], box[3] - box[1]


def wrap(draw, text, face, max_width):
    """按画布宽度折行。

    第 ⑨ 张逼出来的：那张的标题比屏幕宽，画出来右半边被裁掉了（"从这一格回" 后面没了）。
    原先只有 8 张靠"标题写短一点"躲过这件事，那不是机制。折行按字符走，中文没有词间空格，
    所以不假装会分词——只保证一行放得下。
    """
    lines = []
    current = ""
    for char in text:
        trial = current + char
        if current and text_width(draw, trial, face)[0] > max_width:
            lines.append(current)
            current = char
        else:
            current = trial
    if current:
        lines.append(current)
    return lines or [""]


def badge_spot(frame, canvas, radius, wide):
    """角标落在哪儿：宽框（输入格、整条按钮）放框内右端，那里本来就是空的；
    窄框（文字按钮）放框外右下角，往下优先——上面往往还压着一行正文。
    """
    x0, y0, x1, y1 = frame
    mid_y = (y0 + y1) / 2
    candidates = []
    if wide:
        candidates.append((x1 - radius * 1.35, mid_y))          # 框内右端，垂直居中
    candidates += [
        (x1 - radius * 0.35, y1 + radius * 0.65),               # 右下，往外
        (x0 + radius * 0.35, y1 + radius * 0.65),               # 左下，往外
        (x1 - radius * 0.35, y0 - radius * 0.65),               # 右上，往外
        (x0 + radius * 0.35, y0 - radius * 0.65),               # 左上，往外
        (x1 - radius * 1.2, y1 - radius * 1.2),                 # 压进框内的右下角
        (x1 - radius * 1.2, y0 + radius * 1.2),
    ]
    for cx, cy in candidates:
        if cx - radius < 4 or cy - radius < 4:
            continue
        if cx + radius > canvas[0] - 4 or cy + radius > canvas[1] - 4:
            continue
        return cx, cy
    return candidates[-1]


def annotate(frontend):
    manifest_path = os.path.join(frontend, "docs", "assets", "manifest.json")
    with open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)

    written = []
    shots = manifest["shots"]
    for shot in shots:
        raw = os.path.join(frontend, "docs", "assets", "raw", shot["file"])
        out = os.path.join(frontend, "docs", "assets", shot["file"])
        if not os.path.exists(raw):
            print("MISSING-RAW %s" % raw, file=sys.stderr)
            return 1
        screen = Image.open(raw).convert("RGB")
        scale = screen.width / float(shot.get("viewportWidth") or screen.width)
        number = CIRCLED[int(shot["id"]) - 1]

        # 说明带的高度先量出来，画布一次开够：屏幕本身一个像素都不遮。
        head_font = font(max(17, int(23 * scale)))
        line_font = font(max(15, int(19 * scale)))
        note_font = font(max(15, int(18 * scale)))
        stroke = max(4, int(5 * scale))
        probe = ImageDraw.Draw(screen)

        boxed = [target for target in shot["targets"] if target.get("box")]
        # 一屏上可能圈 2~3 处：角标写成 ①a / ①b，说明带逐行对上，读者不会认错哪个圈对应哪句话。
        glyphs = [
            number if len(boxed) == 1 else "%s%s" % (number, "abcdefgh"[index])
            for index in range(len(boxed))
        ]
        lines = ["%s %s" % (glyph, target["action"])
                 for glyph, target in zip(glyphs, boxed)]
        headline = "%s %s" % (number, shot["headline"].split(" ", 1)[-1])
        # 只有一个圈、且圈上写的话就是这屏的标题时，不必再重复一行（④ 两张就是这样）
        if len(lines) == 1 and lines[0].split(" ", 1)[-1] == headline.split(" ", 1)[-1]:
            lines = []  # 角标照画，只是说明带不再重复同一句话
        head_w, head_h = text_width(probe, headline, head_font)
        pad_x = int(16 * scale)
        max_text = screen.width - 2 * pad_x
        # 标题与逐行说明都按画布宽度折行：第 ⑨ 张的标题比屏幕长，右半边直接被裁掉过。
        head_lines = wrap(probe, headline, head_font, max_text)
        wrapped_lines = []
        for line in lines:
            wrapped_lines += wrap(probe, line, line_font, max_text - int(6 * scale))
        line_height = int(24 * scale)
        widest = max([text_width(probe, item, head_font)[0] for item in head_lines] +
                     [text_width(probe, item, line_font)[0] for item in wrapped_lines] + [0])
        caption_height = (
            int(14 * scale)
            + len(head_lines) * (head_h + int(4 * scale))
            + int(6 * scale)
            + len(wrapped_lines) * line_height
            + int(14 * scale)
        )
        canvas = Image.new("RGB", (screen.width, screen.height + caption_height), CAPTION_BG)
        canvas.paste(screen, (0, 0))

        note = shot.get("note")
        note_height = 0
        if note:
            note_lines = wrap(probe, note, note_font, screen.width - 2 * int(10 * scale))
            note_height = int(14 * scale) + len(note_lines) * int(26 * scale)
            band = ImageDraw.Draw(canvas)
            band.rectangle([0, 0, canvas.width, note_height], fill=NOTE_BG)
            for index, note_line in enumerate(note_lines):
                band.text(
                    (int(10 * scale), int(7 * scale) + index * int(26 * scale)),
                    note_line, font=note_font, fill=NOTE_INK,
                )

        draw = ImageDraw.Draw(canvas)
        radius = max(11, int(15 * scale))
        badge_font = font(max(15, int(20 * scale)))
        for glyph, target in zip(glyphs, boxed):
            box = target["box"]
            x = box["x"] * scale
            y = box["y"] * scale
            w = box["width"] * scale
            h = box["height"] * scale
            pad = int(7 * scale)
            frame = (x - pad, max(note_height + 2, y - pad), x + w + pad, y + h + pad)
            radius_box = max(6, int(10 * scale))
            # 先白后红两道框：暗档截图上只画红会糊进背景
            draw.rounded_rectangle(
                frame, radius=radius_box, outline=HALO, width=stroke + max(2, int(3 * scale))
            )
            draw.rounded_rectangle(frame, radius=radius_box, outline=INK, width=stroke)

            # 框够宽（放得下角标又不压字）就把角标放进框内右端：那里通常是留白。
            # 阈值按角标直径算，不按像素写死——第 ⑥ 张那颗小入口曾被外置角标压住下面那行
            # 「行程」标签。
            cx, cy = badge_spot(frame, canvas.size, radius, w > radius * 6)
            glyph_w, glyph_h = text_width(draw, glyph, badge_font)
            if len(glyph) == 1:
                draw.ellipse(
                    [cx - radius, cy - radius, cx + radius, cy + radius],
                    fill=BADGE_BG, outline=HALO, width=max(2, int(3 * scale)),
                )
            else:
                # 两个字符（①a）塞进圆里会顶出去，就把它拉成一枚胶囊，字号不变
                half_w = max(radius, glyph_w / 2 + radius * 0.55)
                draw.rounded_rectangle(
                    [cx - half_w, cy - radius, cx + half_w, cy + radius],
                    radius=radius, fill=BADGE_BG, outline=HALO, width=max(2, int(3 * scale)),
                )
            draw.text(
                (cx - glyph_w / 2, cy - glyph_h / 2 - int(2 * scale)),
                glyph, font=badge_font, fill=BADGE_FG,
            )

        top = screen.height + int(14 * scale)
        draw.line([(0, screen.height), (canvas.width, screen.height)], fill=CAPTION_RULE,
                  width=max(3, int(4 * scale)))
        for index, head_line in enumerate(head_lines):
            draw.text((pad_x, top), head_line, font=head_font, fill=CAPTION_INK)
            top += head_h + int(4 * scale)
        top += int(4 * scale)
        for line in wrapped_lines:
            draw.text((pad_x + int(6 * scale), top), line, font=line_font, fill=CAPTION_INK)
            top += line_height

        canvas.save(out)
        written.append((shot["file"], len(boxed), bool(note), widest + 2 * pad_x <= canvas.width))
    for name, count, has_note, fits in written:
        print("annotated %s | 圈了 %d 处 | 顶部说明=%s | 文字没超出画布=%s"
              % (name, count, "有" if has_note else "无", "是" if fits else "否"))
        if not fits:
            print("WARN %s 的说明文字比画布还宽，会被裁掉" % name, file=sys.stderr)
    return 0


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    default_frontend = os.path.dirname(here)
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend-dir", default=default_frontend)
    args = parser.parse_args()
    return annotate(args.frontend_dir)


if __name__ == "__main__":
    raise SystemExit(main())
