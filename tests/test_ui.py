import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

from tests.kodi_stubs import Addon, install

install()

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
from resources.lib.ui.UI import UI
from resources.lib.video.FolderVideo import FolderVideo
from tests.test_catalog import movie

BASE = "plugin://plugin.video.ebibliocat.efilm/"


class UITest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.patch = patch.object(xbmcaddon, "Addon", side_effect=lambda: Addon(self.tmp.name))
        self.patch.start()
        self.addCleanup(self.patch.stop)
        xbmc.getInfoLabel.return_value = "21.2"
        xbmcgui.Dialog.return_value.input.reset_mock(side_effect=True)
        xbmcgui.Dialog.return_value.yesno.return_value = True
        for name in (
            "endOfDirectory",
            "setResolvedUrl",
            "addDirectoryItem",
            "setContent",
            "setPluginCategory",
        ):
            getattr(xbmcplugin, name).reset_mock()
        xbmc.executebuiltin.reset_mock()

    def ui(self, **args):
        return UI(BASE, 10, {k: [str(v)] for k, v in args.items()})

    def test_entry_point_parses_arguments_and_initializes_the_real_route_boundary(self):
        import addon

        with patch.object(addon, "UI") as ui:
            addon.main([BASE, "10", "?mode=series&url=2"])
            ui.assert_called_once_with(BASE, 10, {"mode": ["series"], "url": ["2"]})
            ui.return_value.run.assert_called_once()
        with self.assertRaises(ValueError):
            addon.main([])
        with patch.object(addon, "UI") as ui:
            addon.main([BASE, "10", "?" + "&".join("p{}=x".format(i) for i in range(30))])
            self.assertEqual(ui.call_args.args[2], {"mode": ["invalid"]})

    def test_home_and_actual_imports_initialize(self):
        ui = self.ui()
        ui.run()
        urls = [call.args[1] for call in xbmcplugin.addDirectoryItem.call_args_list]
        self.assertTrue(any("all_movies" in url for url in urls))
        self.assertTrue(any("search" in url for url in urls))
        self.assertTrue(any("login" in url for url in urls))
        xbmcplugin.endOfDirectory.assert_called_once()

    def test_home_never_exposes_legacy_import_even_when_old_data_exists(self):
        legacy = Path(self.tmp.name, "addon_data", "plugin.video.ebibliocat.efilm.pitest", "session.json")
        legacy.parent.mkdir(parents=True)
        legacy.write_text('{"refresh": "synthetic-old-session"}', encoding="utf-8")

        def translate(path):
            return path.replace("special://profile/", self.tmp.name + "/")

        with patch("resources.lib.ui.UI.xbmcvfs.translatePath", side_effect=translate):
            ui = self.ui()
            ui.run()
        modes = [
            parse_qs(urlsplit(call.args[1]).query)["mode"][0]
            for call in xbmcplugin.addDirectoryItem.call_args_list
        ]
        self.assertIn("login", modes)
        self.assertNotIn("import_session", modes)
        self.assertEqual(len(modes), 9)
        self.assertFalse(hasattr(ui.ebiblio.session, "import_session"))
        self.assertTrue(legacy.is_file())

    def test_removed_import_route_is_rejected(self):
        self.ui(mode="import_session").run()
        xbmcplugin.addDirectoryItem.assert_not_called()
        self.assertFalse(xbmcplugin.endOfDirectory.call_args.kwargs["succeeded"])

    def test_empty_filtered_page_keeps_next_page(self):
        ui = self.ui(mode="collection:1", url=1)
        ui.ebiblio.session.list_elements = Mock(
            return_value={"results": [{"products": dict(movie(), type="music")}], "links": {"next": "next"}}
        )
        ui.run()
        self.assertEqual(xbmcplugin.addDirectoryItem.call_count, 1)
        query = parse_qs(urlsplit(xbmcplugin.addDirectoryItem.call_args.args[1]).query)
        self.assertEqual(query["url"], ["2"])

    def test_login_preserves_password_and_refresh_uses_active_plugin_id(self):
        ui = self.ui(mode="login")
        xbmcgui.Dialog.return_value.input.side_effect = [" user ", " password "]
        ui.ebiblio.signIn = Mock()
        ui.run()
        ui.ebiblio.signIn.assert_called_once_with("user", " password ")
        xbmc.executebuiltin.assert_called_once_with("Container.Update({})".format(BASE))

    def test_unknown_legacy_and_invalid_parameters_end_directory_safely(self):
        for route, page in (
            ("directe", "1"),
            ("nonsense", "1"),
            ("collection:1", "oops"),
            ("collection:-1", "1"),
            ("all_movies", "0"),
        ):
            xbmcplugin.endOfDirectory.reset_mock()
            ui = self.ui(mode=route, url=page)
            ui.run()
            xbmcplugin.endOfDirectory.assert_called_once()
            self.assertFalse(xbmcplugin.endOfDirectory.call_args.kwargs.get("succeeded", True))
        self.assertFalse(hasattr(self.ui(), "tv3"))

    def test_malformed_playback_url_resolves_false_once(self):
        for url in (
            "https://stream.example.test/raw.mp4",
            "efilm://product/no/title",
            "efilm://episode/1/show/no/episode",
            "efilm://product/1/",
        ):
            xbmcplugin.setResolvedUrl.reset_mock()
            self.ui(mode="playVideo", url=url).run()
            xbmcplugin.setResolvedUrl.assert_called_once()
            self.assertFalse(xbmcplugin.setResolvedUrl.call_args.args[1])

    def test_episode_route_wires_parent_series_without_network(self):
        ui = self.ui(mode="playVideo", url="efilm://episode/10/show/1/episode")
        ui.ebiblio.playProduct = Mock()
        ui.run()
        ui.ebiblio.playProduct.assert_called_once_with(1, "episode", 10, 10, "show")

    def test_query_filters_survive_next_and_previous_page_links(self):
        ui = self.ui(mode="all_movies", url=2, term="café", letter="C")
        ui.ebiblio.session.movies = Mock(return_value=[movie(i + 1, "Café %02d" % i) for i in range(60)])
        ui.run()
        urls = [
            call.args[1] for call in xbmcplugin.addDirectoryItem.call_args_list if call.kwargs.get("isFolder")
        ]
        self.assertEqual(len(urls), 2)
        for url in urls:
            args = parse_qs(urlsplit(url).query)
            self.assertEqual(args["term"], ["café"])
            self.assertEqual(args["letter"], ["C"])
        self.assertEqual(xbmcplugin.setContent.call_args.args[1], "movies")

    def test_episode_directory_uses_episode_content_and_metadata_tags(self):
        ui = self.ui(mode="season:10", url=1)
        ui.ebiblio.session.series_detail = Mock(
            return_value={"id": 10, "slug": "show", "seasons": [{"season": 1, "chapters": [movie()]}]}
        )
        ui.run()
        item = xbmcplugin.addDirectoryItem.call_args.args[2]
        item.tag.setSeason.assert_called_once_with(1)
        item.tag.setEpisode.assert_called_once_with(1)
        self.assertEqual(xbmcplugin.setContent.call_args.args[1], "episodes")

    def test_kodi19_uses_compatible_metadata_boundary(self):
        xbmc.getInfoLabel.return_value = "19.5"
        ui = self.ui()
        ui.listFolder([FolderVideo("Unicode À", "1", "series")])
        self.assertEqual(xbmcplugin.addDirectoryItem.call_args.args[2].info["title"], "Unicode À")

    def test_route_values_with_multiple_entries_are_rejected(self):
        ui = self.ui()
        ui.args = {"mode": ["series", "movies"]}
        ui.run()
        xbmcplugin.addDirectoryItem.assert_not_called()
        self.assertFalse(xbmcplugin.endOfDirectory.call_args.kwargs["succeeded"])

    def test_no_raw_arguments_or_stream_urls_in_logs(self):
        xbmc.log.reset_mock()
        sentinel = "https://stream.example.test/private?token=PRIVATE-SENTINEL"
        self.ui(mode="playVideo", url=sentinel).run()
        self.assertNotIn("PRIVATE-SENTINEL", str(xbmc.log.call_args_list))
