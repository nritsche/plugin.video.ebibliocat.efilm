import ast
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from tests.kodi_stubs import install

install()

from scripts.build_release import ROOT, build


class ReleaseTest(unittest.TestCase):
    def test_archive_allowlist_determinism_and_clean_install_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = build(Path(temporary, "one"))
            second = build(Path(temporary, "two"))
            self.assertEqual(target.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(target) as archive:
                names = archive.namelist()
                self.assertTrue(all(name.startswith("plugin.video.ebibliocat.efilm/") for name in names))
                self.assertFalse(any("__pycache__" in name or name.endswith(".pyc") for name in names))
                self.assertFalse(
                    any("/tests/" in name or "/tmp/" in name or "/.github/" in name for name in names)
                )
                self.assertIn("plugin.video.ebibliocat.efilm/resources/lib/ebibliocat/Playback.py", names)
                archive.extractall(Path(temporary, "install"))
            # A separate process imports only the extracted application and explicit Kodi doubles.
            installed = Path(temporary, "install", "plugin.video.ebibliocat.efilm")
            code = (
                "import sys; sys.path.insert(0, " + repr(str(ROOT)) + ");"
                "from tests.kodi_stubs import install; install();"
                "sys.path.remove(" + repr(str(ROOT)) + "); sys.path.insert(0, " + repr(str(installed)) + ");"
                "from resources.lib.ui.UI import UI; import addon;"
                'assert UI.__module__ == "resources.lib.ui.UI";'
                "assert addon.__file__.startswith(" + repr(str(installed)) + ")"
            )
            subprocess.run([sys.executable, "-c", code], cwd=temporary, check=True, capture_output=True)

    def test_manifest_dependency_and_artwork_metadata(self):
        root = ET.parse(ROOT / "addon.xml").getroot()
        self.assertEqual(root.attrib["id"], "plugin.video.ebibliocat.efilm")
        imports = {node.attrib["addon"] for node in root.find("requires")}
        self.assertIn("script.module.inputstreamhelper", imports)
        self.assertNotIn("script.module.future", imports)
        from scripts.validate_release import validate

        self.assertEqual(validate(ROOT), [])

    def test_runtime_source_compiles_without_escape_warnings(self):
        for path in [ROOT / "addon.py"] + list((ROOT / "resources").rglob("*.py")):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_all_localization_keys_have_three_real_translations(self):
        from resources.lib.ebibliocat.EBiblioStrings import MESSAGES

        for locale in ("en_gb", "ca_es", "es_es"):
            text = (ROOT / ("resources/language/resource.language." + locale + "/strings.po")).read_text(
                encoding="utf-8"
            )
            for number, english in MESSAGES.values():
                self.assertIn('msgctxt "#{}"'.format(number), text)
                self.assertIn("msgid " + json.dumps(english, ensure_ascii=False), text)
            self.assertNotIn("plugin.video.tv3.cat", text)
