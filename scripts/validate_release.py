"""Validate runtime metadata and PNG/JPEG dimensions without image dependencies."""

import ast
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jpeg_size(path):
    with open(path, "rb") as source:
        if source.read(2) != b"\xff\xd8":
            raise ValueError("Not JPEG")
        while True:
            marker = source.read(2)
            if len(marker) != 2 or marker[0] != 255:
                raise ValueError("Invalid JPEG header")
            size = struct.unpack(">H", source.read(2))[0]
            if marker[1] in (192, 193, 194):
                _, height, width = struct.unpack(">BHH", source.read(5))
                return width, height
            source.seek(size - 2, 1)


def validate(root=ROOT):
    errors = []
    addon = ET.parse(root / "addon.xml").getroot()
    if addon.attrib["id"] != "plugin.video.ebibliocat.efilm":
        errors.append("Unexpected add-on ID")
    metadata = addon.find("extension[@point='xbmc.addon.metadata']")
    if metadata.findtext("license") != "GPL-2.0-or-later":
        errors.append("Missing license")
    if metadata.findtext("source") != "https://github.com/nritsche/plugin.video.ebibliocat.efilm":
        errors.append("Incorrect source URL")
    for child in metadata.find("assets"):
        if not (root / child.text).is_file():
            errors.append("Missing asset: " + child.text)
    png = (root / "resources/icon.png").read_bytes()
    width, height, _, color = struct.unpack(">IIBB", png[16:26])
    square_icon = width == height and width in (256, 512) and color == 2
    if not square_icon:
        errors.append("Icon must be a square opaque 256/512 RGB PNG")
    if jpeg_size(root / "resources/fanart.jpg") not in ((1280, 720), (1920, 1080), (3840, 2160)):
        errors.append("Invalid fanart size")
    files = [root / "addon.py"] + list((root / "resources/lib").rglob("*.py"))
    for path in files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    if not (root / "LICENSE.txt").is_file():
        errors.append("Missing license text")
    return errors


if __name__ == "__main__":
    issues = validate()
    for issue in issues:
        print(issue)
    if issues:
        raise SystemExit(1)
    print("Manifest, source, and artwork checks passed")
