"""Catalog ordering shared by movie and genre browsing."""
import unicodedata

PAGE_SIZE = 24


def name_key(product):
    name = unicodedata.normalize('NFKD', (product.get('name') or '').strip())
    return (''.join(c for c in name if not unicodedata.combining(c)).casefold(),
            int(product['id']))


def movie_page(products, page=1, genre_id=None):
    movies = [p for p in products if p.get('type') == 'audiovisual']
    if genre_id is not None:
        movies = [p for p in movies if any(
            str(g.get('id')) == str(genre_id) for g in (p.get('genres') or [])
        )]
    movies.sort(key=name_key)
    start = (max(1, int(page)) - 1) * PAGE_SIZE
    return movies[start:start + PAGE_SIZE], start + PAGE_SIZE < len(movies)


def episode_product(collection, product_id):
    """Select an episode and its own language tracks from series page metadata."""
    episode = next((p for season in collection.get('seasons', [])
                    for p in season.get('chapters', [])
                    if str(p.get('id')) == str(product_id)), None)
    if episode is None:
        raise ValueError('Episode not found in series')
    tracks = []
    seen = set()
    for track in collection.get('languages') or []:
        if track.get('audiovisual') is not None and str(track['audiovisual']) != str(product_id):
            continue
        pair = ((track.get('language') or {}).get('id'),
                (track.get('subtitle') or {}).get('id'))
        if pair not in seen:
            tracks.append(track)
            seen.add(pair)
    product = dict(collection)
    product.update(episode)
    product['id'] = int(product_id)
    product['languages'] = tracks
    return product
