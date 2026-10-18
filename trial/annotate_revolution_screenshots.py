"""Render Issue #33 callouts from recorded live DOM bounding boxes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


RED = (210, 36, 52, 255)
WHITE = (255, 255, 255, 255)
INK = (21, 45, 36, 255)
FOOTER = (250, 253, 251, 255)
RULE = (205, 222, 213, 255)


def load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [Path(r"C:\Windows\Fonts\msyhbd.ttc"), Path(r"C:\Windows\Fonts\msyh.ttc")]
        if bold
        else [Path(r"C:\Windows\Fonts\msyh.ttc"), Path(r"C:\Windows\Fonts\msyhbd.ttc")]
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def badge_center(box: dict[str, float], placement: str, width: int, height: int) -> tuple[int, int]:
    x = box["x"]
    y = box["y"]
    right = x + box["width"]
    bottom = y + box["height"]
    anchors = {
        "top-left": (x, y),
        "top-right": (right, y),
        "bottom-left": (x, bottom),
        "bottom-right": (right, bottom),
    }
    if placement not in anchors:
        raise ValueError(f"unsupported badge placement: {placement}")
    ax, ay = anchors[placement]
    radius = 14
    return (
        max(radius + 2, min(width - radius - 2, round(ax))),
        max(radius + 2, min(height - radius - 2, round(ay))),
    )


def annotate(source: Path, destination: Path, callouts: list[dict[str, Any]], viewport: dict[str, int]) -> None:
    with Image.open(source) as opened:
        image = opened.convert("RGBA")
    expected = (viewport["width"], viewport["height"])
    if image.size != expected:
        raise ValueError(f"{source.name}: expected exact {expected}, got {image.size}")

    draw = ImageDraw.Draw(image, "RGBA")
    line_width = 3
    font = load_font(14)
    for item in callouts:
        box = item["bbox_css"]
        x1 = round(box["x"])
        y1 = round(box["y"])
        x2 = round(box["x"] + box["width"])
        y2 = round(box["y"] + box["height"])
        if x1 < 0 or y1 < 0 or x2 > image.width or y2 > image.height:
            raise ValueError(f"{source.name}: bounding box outside viewport: {item['element']}")

        draw.rounded_rectangle((x1, y1, x2, y2), radius=7, outline=RED, width=line_width)
        cx, cy = badge_center(box, item["badge_placement"], image.width, image.height)
        # Short leader links the numbered badge to the measured DOM rectangle.
        draw.line((cx, cy, x1 if cx < (x1 + x2) / 2 else x2, y1 if cy < (y1 + y2) / 2 else y2), fill=RED, width=3)
        radius = 14
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=RED, outline=WHITE, width=2)
        number_text = str(item["number"])
        number_box = draw.textbbox((0, 0), number_text, font=load_font(13, bold=True))
        draw.text((cx - (number_box[2] - number_box[0]) / 2, cy - (number_box[3] - number_box[1]) / 2 - 1), number_text, font=load_font(13, bold=True), fill=WHITE)

    footer_height = 34 + max(1, len(callouts)) * 27
    canvas = Image.new("RGBA", (image.width, image.height + footer_height), FOOTER)
    canvas.alpha_composite(image, (0, 0))
    overlay = ImageDraw.Draw(canvas, "RGBA")
    overlay.line((0, image.height, image.width, image.height), fill=RULE, width=1)
    label_font = load_font(14, bold=True)
    row_y = image.height + 8
    for item in callouts:
        cx = 22
        cy = row_y + 10
        radius = 10
        overlay.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=RED)
        number_text = str(item["number"])
        number_box = overlay.textbbox((0, 0), number_text, font=load_font(11, bold=True))
        overlay.text((cx - (number_box[2] - number_box[0]) / 2, cy - (number_box[3] - number_box[1]) / 2 - 1), number_text, font=load_font(11, bold=True), fill=WHITE)
        overlay.text((40, row_y), item["label"], font=label_font, fill=INK)
        row_y += 27

    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(destination, format="PNG", optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).parent / "results" / "assets" / "illustrated-revolution-first-trip" / "annotations.json",
    )
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = manifest_path.parent
    viewport = manifest["viewport_css_px"]
    for screenshot in manifest["screenshots"]:
        source = root / screenshot["raw"]
        destination = root / screenshot["annotated"]
        annotate(source, destination, screenshot["callouts"], viewport)
        with Image.open(destination) as rendered:
            print(f"{destination.relative_to(root)} {rendered.width}x{rendered.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
