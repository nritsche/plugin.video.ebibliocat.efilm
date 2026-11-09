"""Build an installable Kodi repository feed; no network or publishing occurs here."""

import argparse
import hashlib
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_release import ROOT, build  # noqa: E402

REPOSITORY_ID = "repository.ebibliocat.efilm"
REPOSITORY_VERSION = "1.0.0"
DEFAULT_REPOSITORY = "nritsche/plugin.video.ebibliocat.efilm"


def feed_base(repository):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]+", repository) or repository.split(
        "/", 1
    )[1] in (".", ".."):
        raise ValueError("Invalid GitHub repository")
    return "https://raw.githubusercontent.com/" + repository + "/kodi-repository/"


def repository_manifest(repository):
    base = feed_base(repository)
    addon = ET.Element(
        "addon",
        id=REPOSITORY_ID,
        name="eBiblioCat eFilm repository",
        version=REPOSITORY_VERSION,
        **{"provider-name": "Rick Nitsche"},
    )
    requires = ET.SubElement(addon, "requires")
    ET.SubElement(requires, "import", addon="xbmc.addon", version="14.0.0")
    extension = ET.SubElement(
        addon, "extension", point="xbmc.addon.repository", name="eBiblioCat eFilm repository"
    )
    directory = ET.SubElement(extension, "dir")
    ET.SubElement(directory, "info", compressed="false").text = base + "addons.xml"
    ET.SubElement(directory, "checksum").text = base + "addons.xml.md5"
    ET.SubElement(directory, "datadir", zip="true").text = base
    metadata = ET.SubElement(addon, "extension", point="xbmc.addon.metadata")
    ET.SubElement(
        metadata, "summary", lang="en_GB"
    ).text = "Updates for the unofficial eBiblioCat eFilm add-on"
    ET.SubElement(
        metadata, "description", lang="en_GB"
    ).text = "Install this repository to discover and update the eBiblioCat eFilm video add-on."
    ET.SubElement(metadata, "platform").text = "all"
    ET.SubElement(metadata, "license").text = "GPL-2.0-or-later"
    ET.SubElement(metadata, "source").text = "https://github.com/" + repository
    assets = ET.SubElement(metadata, "assets")
    ET.SubElement(assets, "icon").text = "resources/icon.png"
    ET.SubElement(assets, "fanart").text = "resources/fanart.jpg"
    return addon


def write_repository_zip(path, manifest, root):
    files = {
        "addon.xml": ET.tostring(manifest, encoding="utf-8", xml_declaration=True),
        "LICENSE.txt": (root / "LICENSE.txt").read_bytes(),
        "resources/icon.png": (root / "resources/icon.png").read_bytes(),
        "resources/fanart.jpg": (root / "resources/fanart.jpg").read_bytes(),
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(REPOSITORY_ID + "/" + name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compresslevel=9)


def build_repository(output, repository=DEFAULT_REPOSITORY, root=ROOT):
    site = Path(output)
    site.mkdir(parents=True, exist_ok=True)
    manifest = ET.parse(root / "addon.xml").getroot()
    addon_id, version = manifest.attrib["id"], manifest.attrib["version"]
    addon_dir = site / addon_id
    addon_dir.mkdir(exist_ok=True)
    plugin_zip = build(addon_dir, root)
    shutil.copyfile(root / "addon.xml", addon_dir / "addon.xml")
    repo = repository_manifest(repository)
    repo_dir = site / REPOSITORY_ID
    repo_dir.mkdir(exist_ok=True)
    repo_zip = repo_dir / "{}-{}.zip".format(REPOSITORY_ID, REPOSITORY_VERSION)
    write_repository_zip(repo_zip, repo, root)
    (repo_dir / "addon.xml").write_bytes(ET.tostring(repo, encoding="utf-8", xml_declaration=True))
    for identifier in (addon_id, REPOSITORY_ID):
        assets = site / identifier / "resources"
        assets.mkdir(exist_ok=True)
        for name in ("icon.png", "fanart.jpg"):
            shutil.copyfile(root / "resources" / name, assets / name)
    # Kodi's repository protocol uses MD5 for this manifest, not for credential/security hashing.
    feed = ET.Element("addons")
    feed.extend((manifest, repo))
    data = ET.tostring(feed, encoding="utf-8", xml_declaration=True)
    (site / "addons.xml").write_bytes(data)
    try:
        digest = hashlib.md5(data, usedforsecurity=False).hexdigest()
    except TypeError:  # Python 3.8 does not expose the non-security flag.
        digest = hashlib.md5(data).hexdigest()
    (site / "addons.xml.md5").write_text(digest, encoding="ascii")
    for path in (plugin_zip, repo_zip):
        path.with_suffix(".zip.sha256").write_text(
            hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name + "\n", encoding="ascii"
        )
    (site / "README.md").write_text(
        "# eBiblioCat eFilm Kodi repository\n\nInstall `"
        + repo_zip.relative_to(site).as_posix()
        + "` in Kodi, then use **Install from repository → eBiblioCat eFilm repository → Video add-ons**.\n\n"
        "Source and support: https://github.com/" + repository + "\n"
        "Current video add-on: " + version + "\n",
        encoding="utf-8",
    )
    return site


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "dist/repository"))
    parser.add_argument("--github-repository", default=DEFAULT_REPOSITORY)
    args = parser.parse_args()
    print(build_repository(args.output_dir, args.github_repository))
