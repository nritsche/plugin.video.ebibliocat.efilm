import contextlib
import json
import tempfile
import unittest
from unittest.mock import Mock, patch

from tests.kodi_stubs import Addon, install

install()

import inputstreamhelper
import xbmc
import xbmcgui
import xbmcplugin
from resources.lib.ebibliocat import Playback
from resources.lib.ebibliocat.EBibliocat import EBibliocat
from resources.lib.ebibliocat.Errors import EfilmError

TRACK = {"language": {"id": 6, "name_en": "English"}, "subtitle": {"id": 88, "name_en": "None"}}
PRODUCT = {"id": 1, "name": "Synthetic title", "slug": "synthetic", "languages": [TRACK]}


def response(url="https://stream.example.test/film.m3u8", **source):
    return {"player": {"source": dict(src=url, **source)}}


class PlaybackTest(unittest.TestCase):
    def setUp(self):
        xbmc.getInfoLabel.return_value = "21.2"
        xbmc.getCondVisibility.return_value = False
        inputstreamhelper.Helper.reset_mock()
        inputstreamhelper.Helper.return_value.check_inputstream.return_value = True
        xbmcgui.Dialog.reset_mock()
        xbmcgui.Dialog.return_value.yesno.return_value = True
        xbmcgui.Dialog.return_value.select.return_value = 0
        xbmcplugin.setResolvedUrl.reset_mock()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.browser = EBibliocat("", Addon(self.tmp.name))
        self.browser._product_detail = Mock(return_value=PRODUCT)
        self.browser.session.has_session = Mock(return_value=True)
        self.browser.session.loan_guard = Mock(side_effect=lambda p: contextlib.nullcontext())
        self.browser.session.find_active_loan = Mock(return_value=None)
        self.browser.session.make_loan = Mock(return_value={"id": 99})
        self.browser.session.get_playback = Mock(return_value=response())

    def test_provider_string_nested_list_dash_and_mp4_shapes(self):
        values = [
            response(),
            json.dumps(response()),
            [response()],
            {"data": response()},
            {"player": json.dumps({"source": json.dumps({"src": "https://stream.example.test/a.m3u8"})})},
        ]
        for value in values:
            self.assertEqual(Playback.parse_stream(value).manifest, "hls")
        self.assertEqual(Playback.parse_stream(response("https://stream.example.test/a.mpd")).manifest, "mpd")
        self.assertEqual(
            Playback.parse_stream(response("https://stream.example.test/a.mp4")).mime, "video/mp4"
        )
        self.assertEqual(
            Playback.parse_stream(
                {"player": {"source": {"data_streaming": [{"DASHURL": "https://stream.example.test/a.mpd"}]}}}
            ).manifest,
            "mpd",
        )

    def test_iframe_unknown_drm_and_header_injection_rejected(self):
        bad = [
            response("https://stream.example.test/player"),
            response("file:///etc/passwd"),
            response(license_url="https://license.example.test/", license_type="fairplay"),
            response(license_url="https://license.example.test/"),
            response(headers={"Header": "value\r\nInjected: true"}),
        ]
        for value in bad:
            with self.assertRaises(EfilmError):
                Playback.parse_stream(value)

    def test_headers_and_version_specific_drm_properties(self):
        parsed = Playback.parse_stream(
            response(
                "https://stream.example.test/a.mpd",
                license_type="widevine",
                license_url="https://license.example.test/request",
                manifest_headers={"X-Manifest": "one"},
                stream_headers={"X-Segment": "two"},
                license_headers={"Content-Type": "application/octet-stream"},
            )
        )
        for version in (19, 20, 21, 22):
            xbmc.getInfoLabel.return_value = str(version) + ".0"
            item = Playback.make_item(parsed, "Title")
            props = item.properties
            self.assertEqual("inputstream.adaptive.manifest_type" in props, version < 21)
            self.assertEqual(props["inputstream.adaptive.manifest_headers"], "X-Manifest=one")
            self.assertEqual(props["inputstream.adaptive.stream_headers"], "X-Segment=two")
            if version >= 22:
                self.assertIn("com.widevine.alpha", json.loads(props["inputstream.adaptive.drm"]))
                self.assertNotIn("inputstream.adaptive.license_key", props)
            elif version == 21:
                self.assertTrue(props["inputstream.adaptive.drm_legacy"].startswith("com.widevine.alpha|"))
            else:
                self.assertIn("R{SSM}", props["inputstream.adaptive.license_key"])

    def test_direct_mp4_does_not_require_adaptive(self):
        item = Playback.make_item(
            Playback.parse_stream(response("https://stream.example.test/a.mp4")), "Title"
        )
        self.assertNotIn("inputstream", item.properties)
        inputstreamhelper.Helper.assert_not_called()
        self.assertFalse(item.lookup)

    def test_playready_rejected_on_non_android(self):
        with self.assertRaises(EfilmError):
            Playback.check_dependencies("mpd", "com.microsoft.playready")
        inputstreamhelper.Helper.assert_not_called()

    def test_playready_on_current_android_checks_isa_without_installing_widevine(self):
        xbmc.getCondVisibility.return_value = True
        Playback.check_dependencies("mpd", "com.microsoft.playready")
        inputstreamhelper.Helper.assert_called_once_with("mpd", drm=None)
        xbmc.getInfoLabel.return_value = "20.5"
        with self.assertRaises(EfilmError):
            Playback.check_dependencies("mpd", "com.microsoft.playready")

    def test_helper_failures_are_normalized(self):
        inputstreamhelper.Helper.side_effect = RuntimeError("Do not log arbitrary helper output")
        try:
            with self.assertRaises(EfilmError):
                Playback.check_dependencies()
        finally:
            inputstreamhelper.Helper.side_effect = None

    def test_missing_helper_is_actionable(self):
        with patch.dict("sys.modules", {"inputstreamhelper": None}):
            with self.assertRaises(EfilmError) as caught:
                Playback.check_dependencies()
        self.assertEqual(caught.exception.message, "helper_missing")

    def test_prerequisites_fail_before_loan_confirmation_or_creation(self):
        inputstreamhelper.Helper.return_value.check_inputstream.return_value = False
        self.browser.playProduct(1, "synthetic", 10)
        self.browser.session.make_loan.assert_not_called()
        self.browser.session.find_active_loan.assert_not_called()
        xbmcgui.Dialog.return_value.yesno.assert_not_called()
        self.assertFalse(xbmcplugin.setResolvedUrl.call_args.args[1])

    def test_cancelled_borrow_never_creates_loan(self):
        xbmcgui.Dialog.return_value.yesno.return_value = False
        self.browser.playProduct(1, "synthetic", 10)
        self.browser.session.make_loan.assert_not_called()
        self.assertFalse(xbmcplugin.setResolvedUrl.call_args.args[1])

    def test_existing_website_loan_resumed_without_post(self):
        self.browser.session.find_active_loan.return_value = 88
        self.browser.playProduct(1, "synthetic", 10)
        self.browser.session.make_loan.assert_not_called()
        self.browser.session.get_playback.assert_called_once_with(88, 6, 88)
        self.assertTrue(xbmcplugin.setResolvedUrl.call_args.args[1])

    def test_new_loan_has_confirmation_and_successful_resolution(self):
        self.browser.playProduct(1, "synthetic", 10)
        xbmcgui.Dialog.return_value.yesno.assert_called_once()
        self.browser.session.make_loan.assert_called_once_with(1)
        self.assertTrue(xbmcplugin.setResolvedUrl.call_args.args[1])
        self.assertEqual(xbmcplugin.setResolvedUrl.call_count, 1)

    def test_expired_resume_requires_separate_new_borrow_confirmation(self):
        self.browser.session.find_active_loan.side_effect = [88, None]
        self.browser.session.get_playback.side_effect = [EfilmError("unavailable", 404), response()]
        self.browser.playProduct(1, "synthetic", 10)
        self.assertEqual(xbmcgui.Dialog.return_value.yesno.call_count, 2)
        self.browser.session.make_loan.assert_called_once_with(1)
        self.assertTrue(xbmcplugin.setResolvedUrl.call_args.args[1])

    def test_refusing_reborrow_does_not_consume_credit(self):
        self.browser.session.find_active_loan.side_effect = [88, None]
        self.browser.session.get_playback.side_effect = EfilmError("unavailable", 404)
        xbmcgui.Dialog.return_value.yesno.side_effect = [True, False]
        try:
            self.browser.playProduct(1, "synthetic", 10)
            self.browser.session.make_loan.assert_not_called()
            self.assertFalse(xbmcplugin.setResolvedUrl.call_args.args[1])
        finally:
            xbmcgui.Dialog.return_value.yesno.side_effect = None

    def test_still_active_but_unplayable_loan_does_not_trigger_reborrow(self):
        self.browser.session.find_active_loan.return_value = 88
        self.browser.session.get_playback.side_effect = EfilmError("unavailable", 404)
        self.browser.playProduct(1, "synthetic", 10)
        self.browser.session.make_loan.assert_not_called()
        self.assertEqual(xbmcgui.Dialog.return_value.yesno.call_count, 1)

    def test_borrow_network_failure_is_not_retried_by_player(self):
        self.browser.session.make_loan.side_effect = EfilmError("borrow_uncertain", uncertain=True)
        self.browser.playProduct(1, "synthetic", 10)
        self.browser.session.make_loan.assert_called_once()
        self.assertFalse(xbmcplugin.setResolvedUrl.call_args.args[1])

    def test_detail_parser_uses_episode_collection_and_language_route(self):
        props = {
            "collectionProp": {
                "id": 10,
                "seasons": [{"chapters": [dict(PRODUCT)]}],
                "languages": [dict(TRACK, audiovisual=1)],
            }
        }
        html = (
            '<script id="__NEXT_DATA__" type="application/json">'
            + json.dumps({"props": {"pageProps": props}})
            + "</script>"
        ).encode()
        with patch("resources.lib.ebibliocat.HTTP.request", return_value=html) as request:
            browser = EBibliocat("", Addon(self.tmp.name))
            product = browser._product_detail(1, "synthetic", 10, "show")
            self.assertEqual(product["id"], 1)
            self.assertEqual(len(product["languages"]), 1)
            self.assertIn("/en/series-detail/10/show", request.call_args.args[0])

    def test_missing_tracks_and_signed_out_do_not_borrow(self):
        for signed_in, product in ((False, PRODUCT), (True, dict(PRODUCT, languages=None))):
            self.browser.session.has_session.return_value = signed_in
            self.browser._product_detail.return_value = product
            self.browser.playProduct(1, "synthetic", 10)
        self.browser.session.make_loan.assert_not_called()
