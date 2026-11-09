import io
import json
import socket
import unittest
import urllib.error
from unittest.mock import Mock, patch

from resources.lib.ebibliocat import HTTP
from resources.lib.ebibliocat.Errors import EfilmError


class HTTPTest(unittest.TestCase):
    def test_loan_limit_code_is_localized_without_exposing_server_message(self):
        for body, expected in (
            ({"code": "0010", "msg": "PRIVATE ACCOUNT DETAILS"}, "loan_limit"),
            ({"code": "unknown", "msg": "PRIVATE ACCOUNT DETAILS"}, "service_error"),
            (["0010"], "service_error"),
        ):
            failure = urllib.error.HTTPError(
                "https://api.example.test/", 406, "private", {}, io.BytesIO(json.dumps(body).encode())
            )
            with patch.object(HTTP.urllib.request, "urlopen", side_effect=failure):
                with self.assertRaises(EfilmError) as caught:
                    HTTP.request("https://api.example.test/", "POST", {})
            self.assertEqual(caught.exception.message, expected)
            self.assertEqual(caught.exception.status, 406)
            self.assertFalse(caught.exception.uncertain)
            self.assertNotIn("PRIVATE ACCOUNT DETAILS", str(caught.exception))

    def test_timeout_and_json(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'{"results": []}'
        with patch.object(HTTP.urllib.request, "urlopen", return_value=response) as open_url:
            self.assertEqual(HTTP.request("https://api.example.test/"), {"results": []})
        self.assertEqual(open_url.call_args.kwargs["timeout"], 20)

    def test_network_and_decode_errors_are_typed_and_post_is_uncertain(self):
        for failure in (socket.timeout(), ConnectionResetError(), urllib.error.URLError("offline")):
            with patch.object(HTTP.urllib.request, "urlopen", side_effect=failure):
                with self.assertRaises(EfilmError) as caught:
                    HTTP.request("https://api.example.test/", "POST", {})
                self.assertEqual(caught.exception.message, "network_error")
                self.assertTrue(caught.exception.uncertain)

    def test_backend_error_body_is_not_displayed(self):
        failure = urllib.error.HTTPError(
            "https://api.example.test/",
            403,
            "private",
            {},
            io.BytesIO(json.dumps({"detail": "DO NOT DISPLAY"}).encode()),
        )
        with patch.object(HTTP.urllib.request, "urlopen", side_effect=failure):
            with self.assertRaises(EfilmError) as caught:
                HTTP.request("https://api.example.test/")
        self.assertEqual(caught.exception.message, "access_denied")
        self.assertNotIn("DO NOT DISPLAY", str(caught.exception))
