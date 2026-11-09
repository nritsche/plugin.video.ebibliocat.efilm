import hashlib
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import patch
import subprocess

from scripts.build_repository import REPOSITORY_ID, build_repository, feed_base
from scripts.publish_repository import publish


class RepositoryTest(unittest.TestCase):
    def test_feed_manifest_digest_and_installable_repository(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = build_repository(temporary)
            data = (site / "addons.xml").read_bytes()
            self.assertEqual(hashlib.md5(data).hexdigest(), (site / "addons.xml.md5").read_text())
            feed = ET.fromstring(data)
            self.assertEqual(
                {node.attrib["id"] for node in feed}, {"plugin.video.ebibliocat.efilm", REPOSITORY_ID}
            )
            repo = feed.find("addon[@id='repository.ebibliocat.efilm']")
            directory = repo.find("extension[@point='xbmc.addon.repository']/dir")
            self.assertEqual(
                directory.findtext("info"), feed_base("nritsche/plugin.video.ebibliocat.efilm") + "addons.xml"
            )
            path = next((site / REPOSITORY_ID).glob("*.zip"))
            with zipfile.ZipFile(path) as archive:
                root = ET.fromstring(archive.read(REPOSITORY_ID + "/addon.xml"))
                self.assertEqual(root.attrib["id"], REPOSITORY_ID)
                self.assertIn(REPOSITORY_ID + "/resources/icon.png", archive.namelist())
            plugin = next((site / "plugin.video.ebibliocat.efilm").glob("*.zip"))
            self.assertTrue(plugin.with_suffix(".zip.sha256").is_file())

    def test_repository_zip_is_deterministic(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = build_repository(Path(temporary, "one"))
            second = build_repository(Path(temporary, "two"))
            self.assertEqual(
                next((first / REPOSITORY_ID).glob("*.zip")).read_bytes(),
                next((second / REPOSITORY_ID).glob("*.zip")).read_bytes(),
            )

    def test_no_shell_or_url_injection_in_repository_name(self):
        for name in ("bad/repo;whoami", "../repo", "owner/repo/extra", "owner/repo\n"):
            with self.assertRaises(ValueError):
                feed_base(name)

    def test_explicit_publisher_creates_branch_and_prerelease_with_mocked_network(self):
        calls = []

        def command(args, **kwargs):
            calls.append((args, kwargs))
            output = "addons.xml" if args[:4] == ["git", "diff", "--cached", "--name-only"] else ""
            code = 1 if args[:3] == ["gh", "release", "view"] else 0
            return subprocess.CompletedProcess(args, code, stdout=output)

        with patch.dict("os.environ", {"GH_TOKEN": "synthetic-placeholder"}), patch(
            "scripts.publish_repository.subprocess.run", side_effect=command
        ):
            publish("v0.2.0", "nritsche/plugin.video.ebibliocat.efilm")
        commands = [args for args, _ in calls]
        self.assertIn(["git", "push", "origin", "HEAD:refs/heads/kodi-repository"], commands)
        release = next(args for args in commands if args[:3] == ["gh", "release", "create"])
        self.assertIn("--prerelease", release)
        self.assertIn("--verify-tag", release)
        self.assertTrue(all("synthetic-placeholder" not in " ".join(args) for args in commands))

    def test_publishing_rejects_mismatched_tag_before_using_credentials_or_network(self):
        with patch("scripts.publish_repository.subprocess.run") as run:
            with self.assertRaises(ValueError):
                publish("v99.0.0", "nritsche/plugin.video.ebibliocat.efilm")
            run.assert_not_called()
