import tempfile
import unittest
from unittest.mock import Mock

from tests.kodi_stubs import Addon, install

install()

from resources.lib.ebibliocat import home as Home
from resources.lib.ebibliocat.ebibliostrings import EBiblioStrings
from resources.lib.ebibliocat.efilmapi import EfilmSession
from resources.lib.ebibliocat.errors import EfilmError


class CollectionsTest(unittest.TestCase):
    def test_directory_follows_pages_and_caches(self):
        with tempfile.TemporaryDirectory() as profile:
            session = EfilmSession(Addon(profile))
            session._request = Mock(
                side_effect=[
                    {"results": [{"list": {"id": 1}}], "links": {"next": "page2"}},
                    {"results": [{"list": {"id": 2}}], "links": {"next": None}},
                ]
            )
            self.assertEqual(len(session.visible_lists()), 2)
            self.assertIn("page=2", session._request.call_args.args[1])
            self.assertEqual(len(session.visible_lists()), 2)
            self.assertEqual(session._request.call_count, 2)

    def test_menu_deduplicates_skips_invalid_and_uses_selected_language(self):
        entries = [
            None,
            {"list": {"id": 1, "name_ca": "Acció", "name_en": "Action"}, "count": 2},
            {"list": {"id": 1, "name": "Duplicate"}, "count": 2},
            {"list": {"id": 2, "name": "Empty"}, "count": 0},
        ]
        folders = Home.from_entries(entries, "en")
        self.assertEqual([(f.name, f.mode) for f in folders], [("Action", "collection:1")])

    def test_real_localization_fallback_is_unicode(self):
        folders = Home.getList(EBiblioStrings(Addon()))
        self.assertEqual(len(folders), 25)
        self.assertTrue(all(isinstance(f.name, str) for f in folders))

    def test_invalid_directory_response_is_typed(self):
        with tempfile.TemporaryDirectory() as profile:
            session = EfilmSession(Addon(profile))
            session._request = Mock(return_value={"results": None})
            with self.assertRaises(EfilmError):
                session.visible_lists()
