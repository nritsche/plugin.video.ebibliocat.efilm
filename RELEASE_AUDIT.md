# Release audit resolution

Updated: 2026-11-09 for version 0.2.1. The original findings against `de7002d` are retained in [docs/AUDIT_BASELINE.md](docs/AUDIT_BASELINE.md). This resolution records code/documentation work and its verification; it does not certify untested devices or a public release.

| Issue | Resolution | Evidence |
| --- | --- | --- |
| PUBLIC-01 Repository hygiene | Fixed | Tracked bytecode/web capture removed; `.gitignore`; allowlisted deterministic ZIP builder. |
| PUBLIC-02 History/privacy scan | Checked | Checksum-pinned Gitleaks 8.30.1 reports no history/source findings; existing author/committer attribution retained. |
| PUBLIC-03 Identity/metadata | Fixed | Permanent ID, correct source URL, version/changelog, dynamic plugin URLs, and standard sign-in/sign-out. |
| PUBLIC-04 Provenance/assets | Fixed | GPL/upstream credits retained; recovered library icon attributed separately from GPL geometric fanart. |
| PUBLIC-05 User documentation | Added | Installation, dependency setup, eligibility, privacy, known limits, development and support instructions. |
| STABLE-01 Expired loans | Fixed | Service-side reconciliation, expiry checks, separate reborrow confirmation, regression tests. |
| STABLE-02 Ambiguous/duplicate borrowing | Fixed in client | Per-title lock; existing website loans reused; uncertain POST reconciled once by GET and never blindly repeated. Actual service duplicate-POST behavior is not claimed/tested by consuming credits. |
| STABLE-03 Session persistence | Fixed | Validated atomic JSON, restrictive permissions, thread/process locks, token rotation, truthful deletion errors; concurrency/failure tests. |
| STABLE-04 Password whitespace | Fixed | Password passed unchanged; controller/UI tests. |
| STABLE-05 Network failures | Fixed | One bounded HTTP layer, typed sanitized errors, safe failure resolution, no unsafe loan retry. |
| STABLE-06 Legacy routes | Fixed | TV3 implementation/modules/assets removed; explicit validated dispatch and unknown-route handling. |
| STABLE-07 Empty-page navigation | Fixed | Pagination rendered independently; actual UI regression test. |
| STABLE-08 Unicode | Fixed | Real localized strings remain Unicode, including fallback menus. |
| STABLE-09 Playback prerequisites | Implemented | Helper/ISA check before borrowing; known DRM checked early and actual stream checked before resolution. Providers revealing DRM only after borrowing remain an explicit service limitation. |
| STABLE-10 Kodi/DRM contract | Implemented; device acceptance pending | Kodi 19–22 property tests; separate headers; reject unknown DRM; current Android-only PlayReady. See manual matrix in release checklist. |
| STABLE-11 Schema validation | Fixed | Typed boundary checks, per-item catalog filtering, versioned validated cache, count/duplicate checks, fail-closed malformed active loans. |
| STABLE-12 Application tests | Added | Real modules/initialization/routes with explicit Kodi doubles, auth/loan/playback tests, synthetic fixtures; no AST extraction or real credentials. |
| STABLE-13 Release process | Implemented; real installer acceptance pending | Deterministic ZIP, extracted-install import, isolated Pi tests, CI matrix/coverage; manual fresh Kodi installer/upgrade checks remain distinct. |
| QUALITY-01 Cache/loading | Fixed | Progress/cancellation, cancellable rebuild locks, stale fallback, refresh/clear, short directory caches, bounded/count-checked catalog. API scope documented. |
| QUALITY-02 Catalog navigation | Added | Search, letter selector, previous/next paging, counts, filter-preserving links; refresh starts a new view. |
| QUALITY-03 Localization | Added | Current UI translated into English/Catalan/Spanish; selected language drives API/page requests; fallback policy documented. |
| QUALITY-04 Logging | Fixed | No raw args, credentials, arbitrary backend errors, or stream/license URLs logged. |
| QUALITY-05 Python cleanup | Fixed | Removed Python 2 shims/future, unused legacy code/imports, invalid escapes; split storage/HTTP/cache/validation/playback/UI; Ruff lint/format. |
| QUALITY-06 Kodi metadata | Fixed | Version-aware information tags, movies/TV shows/seasons/episodes content types, year/duration/genres/episode metadata. |
| QUALITY-07 Contributor/support conventions | Added | CONTRIBUTING.md, SECURITY.md, issue template, architecture/CI/distribution/release documents. |
| KODI-01 Official submission packaging | Assets/package prepared | Recovered original library icon (300×364 with transparency), 1280×720 JPEG fanart, artwork attribution, no compiled artifacts. Official submission/review remains separate. |

Additional requested automation: pinned GitHub Actions for Ruff style/static checking, cross-version/Windows regression tests, branch coverage/XML artifacts, Gitleaks, actionlint, zizmor, CodeQL, dependency review, Dependabot, deterministic artifact builds, and an **opt-in** tagged/manual workflow publishing a Kodi repository feed and prerelease assets. Ordinary source pushes do not publish releases or change repository visibility.

The regression suite passed on Python 3.8 and 3.14 and in an isolated ZIP extraction on the Pi. Current coverage is approximately 83%, above the enforced 80% branch gate. Local actionlint/zizmor and Gitleaks scans passed. Hosted Actions results must be checked after the commit is pushed; they are not implied by local success.

Remaining real-world release gates are listed explicitly in [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md): actual Kodi installation/upgrade, human-confirmed movie/episode/provider/DRM playback, other device coverage, website catalog comparison, and GitHub settings/hosted checks. No new service loan was created, source history was not rewritten, and the installed working Pi add-on was not replaced during this cleanup.
