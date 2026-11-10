# [plugin.video.ebibliocat.efilm] 0.2.3

Initial submission of an unofficial eBiblioCat eFilm video add-on. Users browse movies, genres, curated lists, and series, then sign in with an eligible library account. New loans require confirmation; existing active loans are reused. The service controls account eligibility, regional availability, loan limits, and stream availability. The add-on does not bypass these restrictions.

Source: https://github.com/nritsche/plugin.video.ebibliocat.efilm/tree/v0.2.3
Code license: GPL-2.0-or-later. Library branding is attributed separately in resources/artwork/LICENSE.txt.
Minimum declared Kodi version: 19 / Python 3. Runtime modules use lower-case filenames; only the video add-on is included, without a third-party repository installer.

Validation:

- Official kodi-addon-checker 0.0.36 against Matrix: zero errors and zero warnings, including dependency and cross-branch checks. Fresh official repository manifests were cached locally to avoid an unreachable mirror; dependency checks were not skipped.
- 85 unit tests pass on Python 3.8 and 3.14; approximately 83% coverage. Ruff, actionlint/zizmor, and Gitleaks history/source scanning pass.
- Deterministic ZIP builds and clean-extraction application imports pass. The user confirmed movie playback and logo display on a Raspberry Pi running Kodi 20.

This is a draft for initial review. Episode playback, fresh-profile dependency installation, and broader device/provider checks remain pending; the independent GitHub release is a prerelease. An eligible eBiblioCat library account is required for authenticated testing. No credentials or captured authenticated responses are included in this submission.
