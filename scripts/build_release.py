"""Build a deterministic Kodi ZIP from an explicit runtime file allowlist."""

import argparse
import hashlib
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def release_files(root=ROOT):
    required = [
        "addon.py",
        "addon.xml",
        "LICENSE.txt",
        "README.md",
        "changelog.txt",
        "resources/__init__.py",
        "resources/icon.png",
        "resources/fanart.jpg",
        "resources/artwork/fanart.svg",
        "resources/artwork/LICENSE.txt",
    ]
    files = [root / name for name in required]
    files += sorted((root / "resources/lib").rglob("*.py"))
    files += sorted((root / "resources/language").glob("resource.language.*/strings.po"))
    if any(not path.is_file() or path.is_symlink() for path in files):
        raise ValueError("Missing or symlinked release input")
    return sorted(set(files))


def build(output_dir, root=ROOT):
    manifest = ET.parse(root / "addon.xml").getroot()
    addon_id, version = manifest.attrib["id"], manifest.attrib["version"]
    if not re.fullmatch(r"plugin\.video\.[a-z0-9.]+", addon_id) or not re.fullmatch(
        r"\d+\.\d+\.\d+", version
    ):
        raise ValueError("Invalid release ID/version")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "{}-{}.zip".format(addon_id, version)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in release_files(root):
            name = addon_id + "/" + path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(digest + "  " + target.name + "\n", encoding="ascii")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "dist"))
    print(build(parser.parse_args().output_dir))
