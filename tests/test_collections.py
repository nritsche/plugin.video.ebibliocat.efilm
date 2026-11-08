import ast
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.modules.setdefault('xbmcvfs', types.ModuleType('xbmcvfs'))
from resources.lib.ebibliocat.EfilmAPI import EfilmSession
from resources.lib.ebibliocat import Home
from resources.lib.video.FolderVideo import FolderVideo


class CollectionsTest(unittest.TestCase):
    def test_directory_follows_every_page(self):
        session = EfilmSession.__new__(EfilmSession)
        session._request = Mock(side_effect=[
            {'results': [{'list': {'id': 1}}], 'links': {'next': 'page2'}},
            {'results': [{'list': {'id': 2}}], 'links': {'next': None}},
        ])
        self.assertEqual(len(session.visible_lists()), 2)
        self.assertIn('page=2', session._request.call_args.args[1])

    def test_menu_deduplicates_and_skips_empty_lists(self):
        entries = [
            {'list': {'id': 1, 'name_ca': 'Acció', 'name': 'Action'}, 'count': 2},
            {'list': {'id': 1, 'name': 'Duplicate'}, 'count': 2},
            {'list': {'id': 2, 'name': 'Empty'}, 'count': 0},
        ]
        folders = Home.from_entries(entries)
        self.assertEqual([(f.name, f.mode, f.url) for f in folders],
                         [('Acció', 'collection:1', '1')])

    def test_fallback_exposes_all_known_collections(self):
        folders = Home.getList(Mock())
        self.assertEqual(len(folders), 25)
        self.assertEqual(len({f.mode for f in folders}), 25)

    def test_collection_pagination_and_playback_product(self):
        # Load this method without requiring the Kodi runtime.
        tree = ast.parse(Path('resources/lib/ebibliocat/EBibliocat.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef)
                      and n.name == 'listCollection')
        namespace = {'FolderVideo': FolderVideo}
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<collection>', 'exec'), namespace)
        addon = Mock()
        addon.session.list_elements.return_value = {
            'results': [{'products': {'id': 9, 'type': 'audiovisual'}},
                        {'products': {'id': 10, 'type': 'music'}}],
            'links': {'next': 'page2'},
        }
        videos, following = namespace['listCollection'](addon, '1922', 1)
        self.assertEqual(len(videos), 1)
        self.assertEqual(addon.getVideo.call_args.args[0]['languages'], [])
        self.assertEqual((following.mode, following.url), ('collection:1922', '2'))
        addon.session.list_elements.return_value['links']['next'] = None
        self.assertIsNone(namespace['listCollection'](addon, '1922', 2)[1])


if __name__ == '__main__':
    unittest.main()
