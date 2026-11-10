# [plugin.video.ebibliocat.efilm] 0.2.2

Draft submission of an unofficial eBiblioCat eFilm video add-on. Users browse the service's movie catalog, genres, curated lists, and series, then sign in with an eligible library account. New loans require confirmation; existing active loans are reused. The service controls account eligibility, regional availability, loan limits, and stream availability.

Source: https://github.com/nritsche/plugin.video.ebibliocat.efilm/tree/v0.2.2
License: GPL-2.0-or-later for code; recovered library branding is attributed separately.
Minimum declared Kodi version: 19 / Python 3.

Validation: 85 unit tests pass, 83% coverage, Ruff lint/format, workflow checks, Gitleaks history/source scan, deterministic packaging, and verified public release checksums/feed. The user confirmed movie playback and icon display on a Raspberry Pi running Kodi 20. Episode playback, a fresh-profile installer/upgrade test, and broader provider/device checks are pending.

This draft is not ready to merge: Kodi's checker reports two icon errors (transparency and 300×364 dimensions), plus warnings about a website redirect, entry-point length, and the packaged artwork SVG. These must be resolved and the final package rechecked before requesting approval. Existing mixed-case Python module filenames also need review against the submission guidelines.

The candidate contains only the video add-on; it does not install a third-party repository. No user credentials, session files, or captured authenticated responses are included. The third-party release is currently a prerelease; this draft does not claim official catalog acceptance or stable certification.
