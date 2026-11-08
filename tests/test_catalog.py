import ast
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.modules.setdefault('xbmcvfs', types.ModuleType('xbmcvfs'))
from resources.lib.ebibliocat.Catalog import movie_page, episode_product
from resources.lib.ebibliocat.EfilmAPI import EfilmSession, EfilmError
from resources.lib.video.FolderVideo import FolderVideo
from resources.lib.video.Video import Video


def browser_class():
    tree = ast.parse(Path('resources/lib/ebibliocat/EBibliocat.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in (
        'listHome', 'listMovies', 'listSeries', 'listSeasons', 'listEpisodes', 'getVideo',
    )]
    namespace = dict(FolderVideo=FolderVideo, Video=Video, movie_page=movie_page)
    exec(compile(ast.Module(body=[cls], type_ignores=[]), '<browser>', 'exec'), namespace)
    return namespace['EBibliocat']


class CatalogTest(unittest.TestCase):
    def test_alphabetical_order_is_global_and_accent_insensitive(self):
        products = [dict(id=i, name='Z%02d' % i, type='audiovisual') for i in range(30)]
        products.append(dict(id=40, name='Àbac', type='audiovisual'))
        first, more = movie_page(list(reversed(products)))
        second, more_second = movie_page(products, 2)
        self.assertEqual(first[0]['name'], 'Àbac')
        self.assertTrue(more)
        self.assertFalse(more_second)
        self.assertEqual(len({p['id'] for p in first + second}), 31)

    def test_genre_filter_precedes_pagination(self):
        products = [dict(id=i, name=str(i), type='audiovisual',
                         genres=[{'id': i % 2}]) for i in range(60)]
        products.append(dict(id=90, name='Series', type='serie', genres=[{'id': 1}]))
        first, more = movie_page(products, genre_id='1')
        second, _ = movie_page(products, 2, genre_id='1')
        self.assertTrue(more)
        self.assertEqual(len(first + second), 30)
        self.assertTrue(all(p['id'] % 2 for p in first + second))

    def test_cache_collects_all_pages_then_avoids_network(self):
        with tempfile.TemporaryDirectory() as profile:
            session = EfilmSession.__new__(EfilmSession)
            session.profile = profile
            def request(method, path):
                page = int(path.rsplit('page=', 1)[1])
                return {'total_pages': 3, 'results': [{'id': page}]}
            session._request = Mock(side_effect=request)
            self.assertEqual(len(session.movies()), 3)
            self.assertEqual(session._request.call_count, 3)
            session._request.reset_mock()
            self.assertEqual(len(session.movies()), 3)
            session._request.assert_not_called()

    def test_failed_download_does_not_create_partial_cache(self):
        with tempfile.TemporaryDirectory() as profile:
            session = EfilmSession.__new__(EfilmSession)
            session.profile = profile
            session._request = Mock(side_effect=[
                {'total_pages': 2, 'results': [{'id': 1}]}, EfilmError('offline'),
            ])
            with self.assertRaises(EfilmError):
                session.movies()
            self.assertFalse(Path(profile, 'movie-catalog.json').exists())

    def test_episode_languages_exclude_other_episodes_and_deduplicate(self):
        track = {'audiovisual': 5, 'language': {'id': 6}, 'subtitle': {'id': 88}}
        other = dict(track, audiovisual=6)
        product = episode_product({
            'id': 870, 'name': 'Series',
            'seasons': [{'chapters': [{'id': 5, 'name': 'Episode'}]}],
            'languages': [track, other, track],
        }, '5')
        self.assertEqual(product['id'], 5)
        self.assertEqual(product['name'], 'Episode')
        self.assertEqual(product['languages'], [track])
        with self.assertRaises(ValueError):
            episode_product({'seasons': []}, 99)

    def test_seasons_episodes_and_playback_routes(self):
        browser = browser_class()()
        browser.session = Mock()
        browser.session.series_detail.return_value = {
            'slug': 'show', 'seasons': [{'season': 2, 'chapters': [
                dict(id=500, name='Episode', slug='episode', type='serie', duration=25),
            ]}],
        }
        season = browser.listSeasons('870')[0]
        self.assertEqual((season.mode, season.url), ('season:870', '2'))
        episodes, following = browser.listEpisodes('870', '2')
        self.assertEqual(episodes[0].url, 'efilm://episode/870/show/500/episode')
        self.assertEqual(episodes[0].durada, 1500)
        self.assertIsNone(following)
        self.assertEqual([f.mode for f in browser.listHome()],
                         ['movies', 'genres', 'lists', 'series'])
        browser.session.series.return_value = {
            'results': [{'id': 870, 'name': 'Show'}], 'links': {'next': 'next'},
        }
        folders = browser.listSeries(1)
        self.assertEqual([(f.mode, f.url) for f in folders],
                         [('series:870', '1'), ('series', '2')])


if __name__ == '__main__':
    unittest.main()
