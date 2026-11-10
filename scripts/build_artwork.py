"""Build release artwork from the square icon master and geometric fanart.

Copyright 2026 Rick Nitsche and contributors. GPL-2.0-or-later.
Requires Pillow (developer tool only). See resources/artwork/LICENSE.txt.
"""

from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def artwork(width, height):
    image = Image.new("RGB", (width, height), "#101d31")
    draw = ImageDraw.Draw(image)
    scale = min(width, height) / 512
    cx, cy = width / 2, height / 2

    def box(coords):
        return tuple(int((cx if i % 2 == 0 else cy) + v * scale) for i, v in enumerate(coords))

    draw.rounded_rectangle(box((-184, -136, 184, 136)), radius=int(28 * scale), fill="#31c7b7")
    draw.rounded_rectangle(box((-134, -105, 134, 105)), radius=int(12 * scale), fill="#101d31")
    for x in (-168, 146):
        for y in (-104, -48, 8, 64):
            draw.rectangle(box((x, y, x + 22, y + 32)), fill="#101d31")
    draw.polygon([box((-32, -64))[:2], box((-32, 64))[:2], box((72, 0))[:2]], fill="#f4f8fc")
    return image


def main():
    with Image.open(ROOT / "resources/artwork/library-icon-master.png") as icon:
        icon.convert("RGB").resize((512, 512), Image.Resampling.LANCZOS).save(ROOT / "resources/icon.png")
    artwork(1280, 720).save(ROOT / "resources/fanart.jpg", quality=92)
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
<rect width="512" height="512" fill="#101d31"/>
<rect x="72" y="120" width="368" height="272" rx="28" fill="#31c7b7"/>
<rect x="122" y="151" width="268" height="210" rx="12" fill="#101d31"/>
<g fill="#101d31">"""
    for x in (88, 402):
        for y in (152, 208, 264, 320):
            svg += '<rect x="{}" y="{}" width="22" height="32"/>'.format(x, y)
    svg += '</g><path d="M224 192 L224 320 L328 256 Z" fill="#f4f8fc"/></svg>\n'
    (ROOT / "resources/artwork/fanart.svg").write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
