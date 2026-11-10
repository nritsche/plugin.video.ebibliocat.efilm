# Architecture

`addon.py` validates the Kodi entry arguments and constructs `UI`. `ui.py` owns the explicit route table, dialogs, filters, content types, and item rendering. It never accepts a raw external playback URL.

`ebibliocat.py` orchestrates catalog views and user-confirmed playback. It delegates schema checks and pure transformations to `validation.py`/`catalog.py`, provider stream normalization to `playback.py`, and service access to `efilmapi.py`. Movie and series website detail data currently come from Next.js `__NEXT_DATA__`; a website redesign can require an integration update. Full website dumps are not test fixtures.

`efilmapi.py` centralizes the eBiblioCat client ID and public/authenticated endpoints. All HTTP goes through bounded `http.py` requests and typed, sanitized errors. `storage.py` implements atomic JSON replacement and thread/process locks (POSIX flock / Windows locking). `cache.py` caches only public directory data and coordinates rebuilds. Auth refresh, session updates, catalog rebuilds, and per-title loan operations have separate locks.

Loan flow: require sign-in → fetch current title/episode metadata → choose tracks → check known playback prerequisites → lock this title → read active loans from eFilm → explicit Resume/Borrow confirmation → create at most one new loan → obtain playback response → verify actual stream/DRM prerequisites → resolve the Kodi player. An explicit 401 can refresh authentication once; an uncertain loan POST is never repeated. An authoritative active-loans read recovers website loans and ambiguous outcomes. Reborrowing after expiry requires a new confirmation.

The service may reveal provider/DRM requirements only after a loan is created. In that case the add-on cannot guarantee capability detection before a credit is consumed, and reports unsupported playback clearly. Do not describe metadata tests as successful provider playback tests.

Movie search and alphabet/genre filtering happen before pagination over the cached catalog. Cache refresh intentionally starts a new view at page one. Previous/next links retain filters; refreshing can change title positions because service content changes. Counts are those exposed by the catalog endpoint, not a guarantee that every title available through every eFilm client exists in eBiblioCat.

Tests run the real modules using explicit doubles for the Kodi boundary. They also extract a built ZIP into a clean temporary directory and import only its application files. CI adds Python-version/Windows checks; actual Kodi installation and DRM/provider playback remain separate device acceptance checks.
