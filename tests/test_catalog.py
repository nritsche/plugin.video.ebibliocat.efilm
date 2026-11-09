import tempfile
import unittest
from unittest.mock import Mock

from tests.kodi_stubs import Addon, install

install()

from resources.lib.ebibliocat.Catalog import episode_product, movie_page, movie_selection, video_from_product
from resources.lib.ebibliocat.EBibliocat import EBibliocat
from resources.lib.ebibliocat.Errors import EfilmError


def movie(identifier=1, name="Title", **extra):
    return dict(id=identifier, name=name, slug="title-" + str(identifier), type="audiovisual", **extra)


class CatalogTest(unittest.TestCase):
    def test_global_accent_insensitive_order_and_no_page_overlap(self):
        products = [movie(i + 1, "Z%02d" % i) for i in range(30)] + [movie(40, "Àbac")]
        first, more = movie_page(list(reversed(products)))
        second, following = movie_page(products, 2)
        self.assertEqual(first[0]["name"], "Àbac")
        self.assertTrue(more)
        self.assertFalse(following)
        self.assertEqual(len({p["id"] for p in first + second}), 31)

    def test_genre_applied_before_pagination_and_series_excluded(self):
        products = [movie(i + 1, str(i), genres=[{"id": i % 2 + 1}]) for i in range(60)]
        products.append(dict(movie(90), type="serie", genres=[{"id": 1}]))
        first, more = movie_page(products, genre_id="1")
        second, _ = movie_page(products, 2, genre_id="1")
        self.assertTrue(more)
        self.assertEqual(len(first + second), 30)
        self.assertTrue(all(p["type"] == "audiovisual" for p in first + second))

    def test_search_letters_and_malformed_items(self):
        products = [
            movie(1, "Àbac"),
            movie(2, '"Bravo"'),
            movie(3, "2001"),
            None,
            {"id": "bad"},
            movie(4, "Another"),
        ]
        self.assertEqual([p["id"] for p in movie_selection(products, term="abac")], [1])
        self.assertEqual([p["id"] for p in movie_selection(products, letter="B")], [2])
        self.assertEqual([p["id"] for p in movie_selection(products, letter="#")], [3])

    def test_episode_tracks_are_scoped_and_deduplicated(self):
        track = {"audiovisual": 5, "language": {"id": 6}, "subtitle": {"id": 88}}
        value = episode_product(
            {
                "id": 870,
                "name": "Series",
                "seasons": [{"chapters": [{"id": 5, "name": "Episode"}]}],
                "languages": [track, dict(track, audiovisual=6), None, track],
            },
            "5",
        )
        self.assertEqual(value["id"], 5)
        self.assertEqual(value["name"], "Episode")
        self.assertEqual(value["languages"], [track])
        with self.assertRaises(EfilmError):
            episode_product({"seasons": []}, 99)

    def test_metadata_tolerates_bad_duration_and_genres(self):
        video = video_from_product(movie(duration="oops", year="2020", genres=[None, {"name": "Drama"}]))
        self.assertEqual(video.durada, 0)
        self.assertEqual(video.information["year"], 2020)
        self.assertEqual(video.information["genre"], ["Drama"])
        self.assertIsNone(video_from_product({"id": []}))

    def test_actual_application_seasons_and_episode_routes(self):
        with tempfile.TemporaryDirectory() as profile:
            browser = EBibliocat("", Addon(profile))
            episode = dict(movie(500, "Episode", duration=25), type="serie")
            browser.session.series_detail = Mock(
                return_value={
                    "id": 870,
                    "slug": "show",
                    "seasons": [{"season": 2, "chapters": [episode, None]}],
                }
            )
            season = browser.listSeasons("870")[0]
            self.assertEqual((season.mode, season.url), ("season:870", "2"))
            episodes, following = browser.listEpisodes("870", "2")
            self.assertEqual(episodes[0].url, "efilm://episode/870/show/500/title-500")
            self.assertEqual(episodes[0].information["episode"], 1)
            self.assertEqual(episodes[0].information["season"], 2)
            self.assertEqual(episodes[0].durada, 1500)
            self.assertIsNone(following)

    def test_bad_collection_item_does_not_discard_valid_siblings(self):
        with tempfile.TemporaryDirectory() as profile:
            browser = EBibliocat("", Addon(profile))
            browser.session.list_elements = Mock(
                return_value={
                    "results": [None, {"products": {"id": "bad"}}, {"products": movie()}],
                    "links": {"next": "next"},
                }
            )
            items, following = browser.listCollection(1)
            self.assertEqual(len(items), 1)
            self.assertEqual(following.url, "2")
