#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SIZES = [16, 24, 32, 48, 64, 128, 256]


def scale(points: list[tuple[int, int]], factor: int) -> list[tuple[int, int]]:
    return [(x * factor, y * factor) for x, y in points]


def draw_icon(size: int) -> Image.Image:
    factor = 4
    canvas = 256 * factor
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def xy(box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        return tuple(v * factor for v in box)

    # Background tile.
    d.rounded_rectangle(xy((16, 16, 240, 240)), radius=52 * factor, fill=(15, 22, 19, 255))
    d.rounded_rectangle(xy((22, 22, 234, 234)), radius=46 * factor, outline=(126, 226, 147, 78), width=3 * factor)
    d.ellipse(xy((30, 8, 226, 196)), fill=(126, 226, 147, 30))

    # Terminal panel.
    d.rounded_rectangle(xy((48, 96, 212, 208)), radius=24 * factor, fill=(10, 15, 13, 255), outline=(142, 232, 159, 255), width=5 * factor)
    d.rounded_rectangle(xy((66, 118, 194, 185)), radius=14 * factor, fill=(7, 16, 12, 255))
    for cx, color in [(81, (126, 226, 147, 255)), (96, (247, 245, 239, 220)), (111, (126, 226, 147, 160))]:
        d.ellipse(xy((cx - 4, 109 - 4, cx + 4, 109 + 4)), fill=color)
    d.line(scale([(84, 142), (96, 133), (100, 138), (91, 144), (100, 150), (96, 155), (84, 146)], factor), fill=(126, 226, 147, 255), width=5 * factor, joint="curve")
    d.rounded_rectangle(xy((112, 137, 160, 145)), radius=4 * factor, fill=(126, 226, 147, 255))
    d.rounded_rectangle(xy((112, 154, 180, 162)), radius=4 * factor, fill=(126, 226, 147, 190))
    d.rounded_rectangle(xy((112, 171, 150, 179)), radius=4 * factor, fill=(126, 226, 147, 130))

    # Pika-inspired original bird mark.
    d.polygon(
        scale(
            [
                (71, 93),
                (83, 62),
                (109, 45),
                (139, 45),
                (166, 62),
                (184, 89),
                (211, 85),
                (181, 105),
                (169, 130),
                (143, 154),
                (108, 157),
                (82, 139),
                (68, 113),
            ],
            factor,
        ),
        fill=(121, 208, 138, 255),
    )
    d.polygon(scale([(84, 62), (98, 30), (123, 47), (101, 53)], factor), fill=(178, 245, 188, 255))
    d.polygon(scale([(138, 47), (205, 43), (177, 78), (163, 61)], factor), fill=(111, 208, 132, 255))
    d.polygon(scale([(102, 96), (145, 116), (121, 139), (91, 131)], factor), fill=(224, 255, 228, 235))
    d.polygon(scale([(98, 123), (145, 115), (122, 139), (92, 132)], factor), fill=(47, 143, 86, 105))
    d.ellipse(xy((142, 70, 158, 86)), fill=(6, 12, 10, 255))
    d.ellipse(xy((150, 73, 156, 79)), fill=(247, 245, 239, 255))
    d.polygon(scale([(170, 86), (210, 82), (180, 103), (164, 97)], factor), fill=(241, 200, 75, 255))
    d.polygon(scale([(172, 95), (199, 91), (178, 103), (164, 98)], factor), fill=(219, 159, 47, 255))

    # Stand.
    d.line(scale([(80, 198), (176, 198)], factor), fill=(142, 232, 159, 230), width=10 * factor)
    d.line(scale([(105, 185), (151, 185)], factor), fill=(142, 232, 159, 230), width=14 * factor)

    return img.resize((size, size), Image.Resampling.LANCZOS)


def main() -> int:
    for size in SIZES:
        out = ROOT / "data" / "icons" / "hicolor" / f"{size}x{size}" / "apps" / "pika-fastfetch-gui.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        draw_icon(size).save(out)
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
