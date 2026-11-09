import json
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

from tests.kodi_stubs import Addon, install

install()

from resources.lib.ebibliocat.Cache import Cache
from resources.lib.ebibliocat.EfilmAPI import EfilmSession
from resources.lib.ebibliocat.Errors import Cancelled, EfilmError
from resources.lib.ebibliocat.Storage import write_json
from tests.test_catalog import movie


class CacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.session = EfilmSession(Addon(self.tmp.name))

    def pages(self, method, path):
        page = int(parse_qs(urlsplit(path).query)["page"][0])
        return {"count": 3, "total_pages": 3, "results": [movie(page)], "next": None}

    def test_complete_download_then_cache_without_network(self):
        self.session._request = Mock(side_effect=self.pages)
        progress = Mock()
        self.assertEqual(len(self.session.movies(progress=progress)), 3)
        self.assertEqual(self.session._request.call_count, 3)
        self.assertEqual(len(self.session.movies()), 3)
        self.assertEqual(self.session._request.call_count, 3)
        self.assertEqual(progress.call_args.args, (3, 3))

    def test_failed_download_does_not_create_partial_cache(self):
        self.session._request = Mock(side_effect=EfilmError("network_error"))
        with self.assertRaises(EfilmError):
            self.session.movies()
        self.assertFalse(list(self.session.cache.directory.glob("*.json")))

    def test_cancelled_download_does_not_save_partial_data(self):
        self.session._request = Mock(side_effect=self.pages)
        with self.assertRaises(Cancelled):
            self.session.movies(cancelled=lambda: True)
        self.assertFalse(list(self.session.cache.directory.glob("*.json")))
        self.session._request.assert_not_called()

    def test_expired_cache_is_served_on_transient_failure(self):
        self.session._request = Mock(side_effect=self.pages)
        original = self.session.movies()
        path = self.session.cache.directory / "movies-ca.json"
        cache = json.loads(path.read_text())
        cache["updated"] = 0
        write_json(path, cache)
        self.session._request = Mock(side_effect=EfilmError("network_error"))
        self.assertEqual(self.session.movies(), original)
        self.assertTrue(self.session.cache.used_stale)

    def test_invalid_fresh_cache_is_not_trusted(self):
        path = self.session.cache.directory / "movies-ca.json"
        for bad in (
            None,
            [],
            {"schema": 1, "updated": time.time(), "data": "bad"},
            {"schema": 1, "updated": time.time(), "data": [{"id": []}]},
        ):
            write_json(path, bad)
            self.session._request = Mock(side_effect=self.pages)
            self.assertEqual(len(self.session.movies()), 3)
            self.assertEqual(self.session._request.call_count, 3)

    def test_refresh_replaces_cache_and_clear_preserves_session(self):
        self.session._save_session("refresh-placeholder")
        self.session._request = Mock(side_effect=self.pages)
        self.session.movies()
        self.session.movies(refresh=True)
        self.assertEqual(self.session._request.call_count, 6)
        self.session.cache.clear()
        self.assertTrue(self.session.has_session())
        self.assertEqual(list(self.session.cache.directory.glob("*.json")), [])

    def test_concurrent_cold_load_runs_one_builder(self):
        calls, errors = [], []

        def load():
            calls.append(True)
            time.sleep(0.02)
            return []

        def worker():
            try:
                Cache(self.tmp.name, "ca").get("test", load, lambda v: isinstance(v, list))
            except Exception as error:
                errors.append(error)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(calls), 1)
        self.assertFalse(errors)

    def test_page_bound_and_empty_catalog(self):
        self.session._request = Mock(return_value={"total_pages": 1000000, "results": []})
        with self.assertRaises(EfilmError):
            self.session.movies()
        self.session._request = Mock(return_value={"total_pages": 0, "count": 0, "results": []})
        self.assertEqual(self.session.movies(), [])

    def test_cancel_while_waiting_for_another_catalog_builder(self):
        from resources.lib.ebibliocat.Storage import file_lock

        with file_lock(self.session.cache.directory, "movies"):
            with self.assertRaises(Cancelled):
                self.session.movies(cancelled=lambda: True)

    def test_incomplete_or_duplicate_catalog_is_not_cached(self):
        for first in (
            {"count": 2, "total_pages": 1, "results": [movie()]},
            {"count": 2, "total_pages": 1, "results": [movie(), movie()]},
            {"count": 1, "total_pages": 1, "results": [None]},
        ):
            self.session._request = Mock(return_value=first)
            with self.assertRaises(EfilmError):
                self.session.movies()
            self.assertFalse(list(self.session.cache.directory.glob("*.json")))

    def test_cancellation_does_not_fall_back_to_stale_cache(self):
        cache = self.session.cache
        cache.get("test", lambda: [], lambda v: isinstance(v, list))
        with self.assertRaises(Cancelled):
            cache.get("test", lambda: [], lambda v: isinstance(v, list), force=True, cancelled=lambda: True)
