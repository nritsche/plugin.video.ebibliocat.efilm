import json
import multiprocessing
import os
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tests.kodi_stubs import Addon, install

install()

from resources.lib.ebibliocat.EfilmAPI import EfilmSession
from resources.lib.ebibliocat.Errors import EfilmError
from resources.lib.ebibliocat.Storage import file_lock, write_json


def increment_profile_counter(profile):
    from resources.lib.ebibliocat.Storage import read_json

    for _ in range(3):
        with file_lock(profile, "counter"):
            path = Path(profile, "counter.json")
            value = read_json(path, 0)
            write_json(path, value + 1)


class SessionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.session = EfilmSession(Addon(self.tmp.name))

    def signed_in(self):
        self.session._save_session("test-refresh-placeholder", {})
        self.session.access_token = "test-access-placeholder"
        self.session._refresh_marker = "test-refresh-placeholder"

    def test_corrupt_and_wrong_shape_session_do_not_crash_home(self):
        for raw in ("[]", "null", '"oops"', "{", '{"refresh": 123}', "{}"):
            Path(self.session.session_path).write_text(raw, encoding="utf-8")
            self.assertFalse(self.session.has_session())

    def test_password_preserved_and_only_refresh_persisted(self):
        self.session._request = Mock(
            return_value={"access": "test-access-placeholder", "refresh": "test-refresh-placeholder"}
        )
        self.session.login("user", " password with spaces ")
        self.assertEqual(self.session._request.call_args.args[2]["password"], " password with spaces ")
        value = json.loads(Path(self.session.session_path).read_text(encoding="utf-8"))
        self.assertEqual(set(value), {"refresh", "loans"})
        self.assertNotIn("password", json.dumps(value))
        self.assertNotIn("test-access-placeholder", json.dumps(value))
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(Path(self.session.session_path).stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(Path(self.tmp.name).stat().st_mode), 0o700)

    def test_invalid_login_response_is_not_saved(self):
        for response in ([], None, {}, {"access": 1, "refresh": []}):
            self.session._request = Mock(return_value=response)
            with self.assertRaises(EfilmError):
                self.session.login("user", "password")
            self.assertFalse(self.session.has_session())

    def test_atomic_replace_failure_preserves_previous_session(self):
        self.signed_in()
        before = Path(self.session.session_path).read_bytes()
        with patch("resources.lib.ebibliocat.Storage.os.replace", side_effect=PermissionError):
            with self.assertRaises(EfilmError):
                self.session._save_session("replacement")
        self.assertEqual(Path(self.session.session_path).read_bytes(), before)
        self.assertEqual(list(Path(self.tmp.name).glob(".session.json-*")), [])

    def test_concurrent_loan_writes_do_not_lose_updates(self):
        self.signed_in()
        errors = []

        def save(identifier):
            try:
                EfilmSession(Addon(self.tmp.name)).save_loan(identifier, identifier + 100)
            except Exception as error:
                errors.append(error)

        threads = [threading.Thread(target=save, args=(i,)) for i in range(1, 15)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertFalse(errors)
        self.assertEqual(len(self.session._load_session()["loans"]), 14)

    def test_lock_timeout_is_typed(self):
        with file_lock(self.tmp.name, "operation"):
            with self.assertRaises(EfilmError):
                with file_lock(self.tmp.name, "operation", timeout=0.01):
                    self.fail("Lock acquired twice")

    def test_independent_processes_share_file_lock(self):
        context = multiprocessing.get_context("spawn")
        processes = [
            context.Process(target=increment_profile_counter, args=(self.tmp.name,)) for _ in range(3)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(15)
            if process.is_alive():
                process.terminate()
                self.fail("Profile lock did not complete")
            self.assertEqual(process.exitcode, 0)
        self.assertEqual(json.loads(Path(self.tmp.name, "counter.json").read_text(encoding="utf-8")), 9)

    def test_malformed_loan_map_is_sanitized(self):
        write_json(
            self.session.session_path,
            {
                "refresh": "placeholder",
                "loans": {"1": 2, "bad": [1], "3": None, "4": True},
            },
        )
        self.assertEqual(self.session._load_session()["loans"], {"1": 2})

    def test_signout_does_not_report_success_on_permission_failure(self):
        self.signed_in()
        with patch("resources.lib.ebibliocat.EfilmAPI.os.unlink", side_effect=PermissionError):
            with self.assertRaises(EfilmError):
                self.session.clear()
        self.assertTrue(self.session.has_session())
        self.session.clear()
        self.session.clear()  # Missing file is harmless.
        self.assertFalse(self.session.has_session())

    def test_refresh_rotates_token_preserves_loans_and_retries_401_once(self):
        self.signed_in()
        self.session.save_loan(1, 99)
        self.session._request = Mock(
            side_effect=[
                EfilmError("session_expired", 401),
                {"access": "new-access-placeholder", "refresh": "new-refresh-placeholder"},
                {"ok": True},
            ]
        )
        self.assertEqual(self.session._authorized_request("GET", "private/"), {"ok": True})
        self.assertEqual(self.session._load_session()["loans"], {"1": 99})
        self.assertEqual(self.session._load_refresh_token(), "new-refresh-placeholder")
        self.assertEqual(self.session._request.call_count, 3)

    def test_repeated_unauthorized_is_not_an_infinite_retry(self):
        self.signed_in()
        self.session._request = Mock(
            side_effect=[
                EfilmError("session_expired", 401),
                {"access": "new-access-placeholder"},
                EfilmError("session_expired", 401),
            ]
        )
        with self.assertRaises(EfilmError):
            self.session._authorized_request("POST", "loans/loans/", {})
        self.assertEqual(self.session._request.call_count, 3)

    def test_expired_refresh_clears_persisted_session(self):
        self.signed_in()
        self.session.access_token = None
        self.session._request = Mock(side_effect=EfilmError("session_expired", 401))
        with self.assertRaises(EfilmError):
            self.session._authorized_request("GET", "private/")
        self.assertFalse(self.session.has_session())

    def test_other_process_refresh_is_used_and_logout_is_respected(self):
        self.signed_in()
        self.session._save_session("rotated-elsewhere")
        self.session._request = Mock(side_effect=[{"access": "new-access-placeholder"}, {"ok": True}])
        self.session._authorized_request("GET", "private/")
        self.assertEqual(self.session._request.call_args_list[0].args[2], {"refresh": "rotated-elsewhere"})
        Path(self.session.session_path).unlink()
        with self.assertRaises(EfilmError):
            self.session._authorized_request("GET", "private/")

    def test_saved_loan_is_reconciled_against_server(self):
        self.signed_in()
        self.session.save_loan(1, 98)
        self.session._authorized_request = Mock(
            return_value=[
                {"id": 98, "product": 1, "enabled": True, "expire": "2000-01-01T00:00:00Z"},
                {"id": 99, "product": 1, "enabled": True, "expire": "2099-01-01T00:00:00Z"},
            ]
        )
        self.assertEqual(self.session.find_active_loan(1), 99)
        self.assertEqual(self.session._load_session()["loans"], {"1": 99})
        self.session._authorized_request.return_value = []
        self.assertIsNone(self.session.find_active_loan(1))
        self.assertEqual(self.session._load_session()["loans"], {})

    def test_malformed_active_loans_fail_closed_instead_of_allowing_a_new_borrow(self):
        self.signed_in()
        for response in ([None], [{"id": 1}], [{"id": 1, "product": 1, "expire": "broken"}]):
            self.session._authorized_request = Mock(return_value=response)
            with self.assertRaises(EfilmError):
                self.session.find_active_loan(1)

    def test_malformed_successful_borrow_response_is_reconciled_without_repost(self):
        self.signed_in()
        self.session._authorized_request = Mock(return_value=[])
        self.session.find_active_loan = Mock(return_value=99)
        self.assertEqual(self.session.make_loan(1), {"id": 99})
        self.session._authorized_request.assert_called_once()

    def test_uncertain_borrow_reconciles_once_and_never_repeats_post(self):
        self.signed_in()
        self.session._authorized_request = Mock(side_effect=EfilmError("network_error", uncertain=True))
        self.session.find_active_loan = Mock(return_value=99)
        self.assertEqual(self.session.make_loan(1), {"id": 99})
        self.assertEqual(self.session._authorized_request.call_count, 1)
        self.session.find_active_loan.return_value = None
        with self.assertRaises(EfilmError) as caught:
            self.session.make_loan(1)
        self.assertEqual(caught.exception.message, "borrow_uncertain")
        self.assertEqual(self.session._authorized_request.call_count, 2)

    def test_successful_borrow_then_disk_failure_is_not_reposted(self):
        self.signed_in()
        self.session._authorized_request = Mock(return_value={"loan": {"id": 99}})
        self.session.save_loan = Mock(side_effect=EfilmError("storage_error"))
        with self.assertRaises(EfilmError):
            self.session.make_loan(1)
        self.session._authorized_request.assert_called_once()
