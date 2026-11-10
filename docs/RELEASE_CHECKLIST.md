# Release procedure and verification record

Version under review: **0.2.3**, prepared 2026-11-10. This file distinguishes completed engineering checks from manual release acceptance. Do not turn a pending check into a claim of supported device/provider playback.

## Completed locally

- [x] Replace the test ID with `plugin.video.ebibliocat.efilm`.
- [x] Remove inherited TV3 routes/assets, tracked bytecode, and captured webpage; add ignore rules and explicit release allowlists.
- [x] Retain GPL license/upstream attribution; attribute the recovered library icon and original geometric fanart separately.
- [x] Add English/Catalan/Spanish messages, metadata, installation/privacy/support/contributor documentation.
- [x] Add atomic session persistence, thread/process locks, validation, truthful sign-out failures, and password whitespace preservation.
- [x] Reconcile active loans; validate expiration; require a distinct new borrow confirmation after expiry; never blindly repeat uncertain loan POSTs.
- [x] Bound HTTP requests, sanitize errors/logging, validate routes/responses/cache data, and retain next-page navigation on empty pages.
- [x] Add preflight checks, version-aware Kodi/DRM configuration, and separate manifest/segment/license headers.
- [x] Add search/A–Z, previous/next paging, progress/cancellation, cache refresh/clear, stale-cache recovery, and safe concurrent rebuilding.
- [x] Test actual application imports and routes, Kodi 19/20/21/22 boundary configuration, atomic-write failures, independent-process locks, auth refresh, cancellation, uncertain loans, provider parsing, and release packaging.
- [x] Run the regression suite on Python 3.8 and 3.14 and on the Pi's Python in a clean temporary extraction. The Pi run did not modify the installed add-on or account data.
- [x] Pass Ruff lint/format, artwork/manifest validation, deterministic ZIP checks, and clean import from an extracted ZIP.
- [x] Run public API smoke checks from the isolated Pi release: 3,603 catalog entries, 21 genres, 63 series, three seasons for the sample show, and the expected episode language track. No account or loan requests were made.
- [x] Run checksum-verified Gitleaks 8.30.1 against reachable history and intended source files: no findings. Existing contributor identities/history are retained; no real credential requiring rotation/history rewriting was found.
- [x] Pass actionlint 1.7.12 and zizmor 1.32.0 locally; pin external actions to verified commits and use restricted workflow permissions.
- [x] Add coverage reporting with an 80% branch-coverage gate, CodeQL, dependency review, Dependabot, and a tagged/manual Kodi repository publication workflow.
- [x] Build/test the repository installer ZIP, update-feed layout/digest, and matching manifest versions; verify published prereleases.

The current suite has 85 tests and approximately 83% branch coverage. Counts can increase as more regressions are added; the authoritative result is the test/coverage command output for the release commit. A CI workflow configured in the repository is not a successful hosted CI run.

## Live Pi verification

- [x] User confirmed movie playback works.
- [x] User confirmed the recovered library icon appears.
- [x] Confirmed HTTP 406 / code 0010 means loan allowance exhausted; localized the message.
- [x] Published v0.2.0/v0.2.1 prereleases and verified the public repository feed.

## Before a stable release

- [x] Inspect hosted GitHub Actions results for the initial release: all automated checks passed. Recheck the patch-release commit before publication. CodeQL and dependency review require a public repository or suitable GitHub security entitlement; the committed workflows skip private repositories by default.
- [ ] On a fresh **real Kodi profile**, install the generated ZIP through Kodi's add-on manager and verify dependency installation/enabling, including a device where InputStream Adaptive is absent. Clean archive/import tests and the isolated Pi suite do not exercise Kodi's installer UI.
- [ ] Verify same-ID upgrades through Kodi retain the normal account session.
- [ ] With a human confirming any loan consumption, verify movie **and episode** playback, existing/expired/website loans, audio/subtitles, and ambiguous network failures against the service.
- [ ] Exercise direct MP4, HLS, DASH/Widevine, and supported Android PlayReady on the specific Kodi/device/provider combinations being advertised. All combinations are not certified by unit tests.
- [ ] Compare a representative set of website-visible titles/genres/lists against the API-backed catalog. The builder verifies response counts/duplicates to avoid silent truncation, but does not claim that one service endpoint exposes every title across every eFilm client.
- [ ] Enable/check GitHub dependency graph/alerts, private vulnerability reporting, and desired branch rules; these are host settings, not local source changes.
- [x] Review current official Kodi repository submission checks and pass the official checker with zero errors/warnings. The package now uses a 512×512 opaque icon, lower-case Python modules, and excludes unused artwork sources. Official checker/reviewer acceptance is recorded in KODI_SUBMISSION.md.

These manual checks require a real Kodi UI, service-account actions, additional hardware/provider access, or GitHub account settings. They were not silently performed, and no new loan was created for this cleanup.

## Build and publish

1. Run tests with warnings as errors, coverage, lint, formatting, workflow syntax/security checks, secret scanning, metadata validation, and both builders (README.md / DISTRIBUTION.md).
2. Confirm the permanent ID, manifest version, changelog, source URL, generated artifact checksums, and clean Git status after committing.
3. Use a prerelease while the manual checks above remain open.
4. Publish only by an explicit matching release tag or manual release-workflow dispatch. See [DISTRIBUTION.md](DISTRIBUTION.md). A normal source push must not publish a repository feed or release.
5. For the first repository-feed release, verify public raw access and the repository installer in a clean Kodi profile. Users installing this development feed are opting into public testing.
6. Submit to Team Kodi separately if official built-in catalog inclusion is desired.
