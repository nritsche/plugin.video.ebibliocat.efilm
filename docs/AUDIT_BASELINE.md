# Public release audit

Reviewed: 2026-11-09. Baseline: `de7002d`.

This is a cleanup backlog, not a statement that every item must be finished before sharing experimental source. Finish the public-repository preparation first; address the reliability items before calling the add-on a stable public release. Official Kodi repository submission has additional requirements, listed separately.

## Scope and evidence

- Reviewed all 48 tracked files, including 23 Python source files, manifest, translations, artwork metadata, documentation, and tests; inspected the inherited TV3 implementation and current eFilm routes.
- Enumerated 59 reachable commits and 230 reachable Git blobs. Applied common private-key, GitHub-token, AWS-key, JWT, credential-literal, email, and private-address patterns to text blobs; separately checked current tracked bytecode for selected credential signatures. No private keys or common authentication-token signatures matched. This is a best-effort scan, not a complete secret-scanner certification; remote-only branches, unreachable objects, and account settings were not audited.
- The committed HTML capture contains eFilm support email addresses and public page data; the inspected patterns did not identify a user's credentials. It is still an unnecessary captured webpage and should be removed.
- Ran `python3 -m unittest discover -s tests -v`: all 10 tests pass. Parsed tracked Python source: four invalid-escape warnings remain in legacy code. `git diff --check` passes.
- Reproduced malformed-session failure, fallback byte labels, and disappearing next-page navigation locally without network access or borrowing titles.
- Earlier Pi verification established that movie, genre, list, series, season, and episode directories render in Kodi. It did not establish successful episode playback, every provider/DRM variant, or a clean installation from a release ZIP.
- This audit did not change application code, deploy anything, publish anything, or rewrite Git history.

## Before making the repository public

### PUBLIC-01 — Remove development artifacts and add ignore rules

**Confirmed.** Git tracks 11 `.pyc` files under `resources/lib/ebibliocat/__pycache__/` and `resources/lib/video/__pycache__/`, plus a roughly 388 KiB captured webpage at `resources/lib/ebibliocat/tmp`. There is no `.gitignore`. The working tree also contains an approximately 23 MiB virtual environment and 22 MiB of downloaded website files.

- [ ] Remove tracked bytecode and the webpage capture from the repository's current tree.
- [ ] Ignore virtual environments, `__pycache__`, bytecode, downloaded `tmp/` content, logs, session files, local credentials/configuration, and generated release archives.
- [ ] Build releases from an explicit file allowlist; a generic recursive ZIP of this working directory is unsuitable.

**Done when:** a clean checkout and release ZIP contain source and required assets only, and running tests does not dirty tracked files.

### PUBLIC-02 — Complete the publication privacy check

**Review task; no secret leak confirmed.** The history contains nine distinct author email identities and eight committer email identities, including inherited upstream contributions. Deleting files in a new commit does not remove older content from published history.

- [ ] Run a maintained secret scanner against the complete history intended for publication and inspect its findings privately.
- [ ] Review the maintainer's own commit identity and any development captures included in historical commits. Preserve upstream attribution.
- [ ] If a real credential is found, rotate it and decide on targeted history cleanup before publication. Do not rewrite history merely because the best-effort scan found email addresses.

**Done when:** the intended public history and release contents have been checked, and any actual sensitive material has been handled.

### PUBLIC-03 — Settle the release identity and correct metadata

**Confirmed.** `addon.xml:2` still uses `plugin.video.ebibliocat.efilm.pitest`; `UI.py:50` hardcodes that ID. `addon.xml:22` advertises a different GitHub repository path from the configured Git remote. The English description still advertises TV3 live channels, and the changelog only describes `0.0.1` while the manifest is `0.1.0`.

- [ ] Choose the permanent add-on ID before external users install it; derive internal plugin links from the active add-on/base URL.
- [ ] Plan how the test installation's settings/session data and saved URLs migrate if the ID changes.
- [ ] Correct the source URL, descriptions, version/changelog, provider identity, and translation headers/issue URLs.

**Done when:** the manifest, installed folder, documentation, links, and release archive all agree on the identity and supported features.

### PUBLIC-04 — Document provenance and asset ownership

**Review task.** The project has a GPL license and inherited TV3 history, code, translations, and artwork. The README does not explain that lineage or distinguish this community add-on from the service itself.

- [ ] Add upstream acknowledgments and retain applicable copyright/license notices.
- [ ] Verify provenance and redistribution terms for retained artwork; replace TV3-specific assets that no longer belong in this product.
- [ ] State that this is an unofficial eBiblioCat-specific integration, describe account eligibility, and identify the external service dependency.

**Done when:** users and contributors can identify the maintainers, upstream project, code license, asset provenance, and service scope.

### PUBLIC-05 — Provide usable installation and support instructions

**Confirmed documentation gap.** `README.md` describes menus but not how to install, authenticate, troubleshoot, or contribute.

- [ ] Document release-ZIP installation, supported Kodi/Python/platform versions, dependencies, sign-in/out, loan consumption, and regional/library eligibility.
- [ ] Explain that passwords are not persisted, refresh tokens are stored in the Kodi profile, and the catalog cache lasts six hours.
- [ ] Describe the slower first catalog load, known provider/DRM limits, and tested versus experimental features.
- [ ] Add a reproducible development/test command and an issue-report checklist that asks users to redact credentials and signed URLs.

**Done when:** a new user can install and diagnose the add-on without this conversation or manual SSH deployment.

## Fix before advertising a stable release

### STABLE-01 — Recover from expired or invalid saved loans

**Code-derived failure path.** `EfilmAPI.py:171` and `EBibliocat.py:97` trust saved loan IDs indefinitely. Once one is saved, the code always offers Resume; failed playback never clears or revalidates it. A title can remain stuck on an expired loan.

- [ ] Check validity/expiry against the service and invalidate rejected saved loans.
- [ ] Offer a new, explicit Borrow confirmation when a new loan is required; never silently consume another credit during recovery.
- [ ] Add tests for active, expired, revoked, and missing loans.

### STABLE-02 — Reconcile server-side loans and ambiguous borrow failures

**Code-derived risk.** `EBibliocat.py:118` creates a loan whenever the local map lacks one. A loan made on the website, a deleted local profile, or a successful server request followed by a local write/network failure leaves no reliable local record.

- [ ] Reconcile existing service loans before creating a new one where the API supports it.
- [ ] Handle uncertain POST outcomes without blindly retrying loan creation.
- [ ] Confirm the API's duplicate-loan behavior and test failure after server success but before local persistence.

### STABLE-03 — Harden session persistence and sign-out

**Confirmed bug plus persistence risks.** A session file containing valid JSON `[]` raises `AttributeError` in `_load_refresh_token()` (`EfilmAPI.py:48`), which can prevent even the home menu from opening. `_save_session()` truncates the live file in place; concurrent invocations can lose updates. `clear()` suppresses every deletion error, so the UI can announce sign-out even if the persisted token remains.

- [ ] Validate the session object, token types, and loan-map shape on read.
- [ ] Write atomically, coordinate concurrent session updates/refreshes, and handle disk/permission failures clearly.
- [ ] Treat a missing file as harmless; surface other sign-out deletion failures.
- [ ] Preserve the existing restrictive profile/file permissions and password non-persistence.

### STABLE-04 — Preserve passwords exactly as entered

**Confirmed.** `UI.py:273` calls `password.strip()`, changing valid credentials with leading or trailing spaces.

- [ ] Pass the password unchanged and add a regression test. Keep username normalization a separate decision.

### STABLE-05 — Bound HTML requests and normalize network failures

**Confirmed.** The API has a 30-second timeout, but playback's `getHtml()` calls `urlopen()` without a timeout (`Utils.py:15`). Socket timeouts, connection resets, some I/O failures, and filesystem errors are not consistently converted into user-facing errors or caught at route boundaries.

- [ ] Give every request a bounded timeout and use one consistent HTTP/error layer.
- [ ] Show useful, distinct messages for authentication, quota, unavailable content, network failure, and unexpected service responses.
- [ ] Ensure failed playback resolves the Kodi handle as unsuccessful; failed directories terminate cleanly.
- [ ] Limit retries to appropriate operations; loan creation needs the precautions in STABLE-02.

### STABLE-06 — Remove inherited TV3 routes and validate route inputs

**Confirmed.** `UI.py:93` through the inherited route block call `self.tv3`, which is never initialized. Unknown modes fall through to `listPopular()` and can raise `KeyError`; the `collection:` route parses its page number outside an error boundary. Roughly 500 lines of old TV3 browsing logic remain in `EBibliocat.py`, with corresponding modules, URLs, strings, and assets.

- [ ] Remove unused TV3 routes, methods, imports, constants, and assets as one coherent cleanup.
- [ ] Replace the catch-all legacy dispatch with an explicit route table and safe unknown-route behavior.
- [ ] Validate IDs, page bounds, URL structure, and required parameters before issuing requests.

### STABLE-07 — Keep Next page available when the current page is empty

**Reproduced.** `UI.py:243` only adds the next-page folder inside the branch for a nonempty result list. `listCollection()` filters unsupported content types, so a page with no supported items but a valid next page becomes a dead end.

- [ ] Render pagination independently of the current page's playable item count.
- [ ] Test an empty filtered page with a following page, plus malformed individual items.

### STABLE-08 — Return Unicode strings from localization

**Reproduced.** `EBiblioStrings.py:38` encodes translated strings to `bytes`. The live directory usually hides this, but `Home.getList()` uses these byte labels during fallback. Kodi's Python UI boundary should receive strings.

- [ ] Return `str`, remove legacy encode/decode workarounds, and test the real fallback labels rather than a generic mock.

### STABLE-09 — Check playback prerequisites before consuming a loan

**Confirmed gap.** `addon.xml:7` makes InputStream Adaptive optional; `_makePlaybackItem()` selects it without checking that it is installed/enabled. There is no DRM capability/Widevine availability check before borrowing. A configured Pi is not a clean-install test.

- [ ] Decide dependency installation policy and provide actionable missing-component messages.
- [ ] Check stream/DRM prerequisites as early as the service response permits, before borrowing where possible.
- [ ] Test a new Kodi profile with missing or disabled InputStream Adaptive and unavailable DRM support.

### STABLE-10 — Define and verify the Kodi/DRM compatibility contract

**Confirmed implementation gap; compatibility tests required.** `EBibliocat.py:227` always sets `manifest_type`, uses the old DRM properties, and forwards only stream headers. It does not separately configure manifest headers, and defaults an unrecognized license type to Widevine. `addon.xml` currently declares all platforms without documenting tested combinations.

- [ ] Choose supported Kodi/platform versions and use the matching InputStream Adaptive APIs.
- [ ] Validate required manifest, segment, and license headers independently; reject unsupported DRM with a useful message.
- [ ] Cover direct MP4, HLS, DASH, supported DRM, alternate audio/subtitles, and representative providers in the test matrix.
- [ ] Treat episode metadata/navigation verification separately from actual episode playback verification.

The official [InputStream Adaptive integration documentation](https://github.com/xbmc/inputstream.adaptive/wiki/Integration) says `manifest_type` is deprecated in Kodi 21 and removed in Kodi 22. Its [DRM documentation](https://github.com/xbmc/inputstream.adaptive/wiki/Integration-DRM) describes the current configuration interfaces. An ignored deprecated property alone is not proof that every stream fails; the whole configured flow needs version-specific tests.

### STABLE-11 — Validate external JSON and cache schemas

**Confirmed assumptions.** Readers frequently assume a dictionary/list with particular nested keys. Directory handlers do not consistently catch `AttributeError`, and playback's exception boundary excludes some storage/network errors. `movies()` accepts fresh cache payloads without checking the product list or its elements. One malformed title can abort a whole page.

- [ ] Validate endpoint responses and cached objects at their boundaries; reject unsupported shapes with an `EfilmError` or equivalent typed error.
- [ ] Skip/report malformed individual catalog entries without discarding valid siblings.
- [ ] Test `null`, arrays where objects are expected, missing keys, nonnumeric IDs/durations, corrupt cache data, and empty valid results.

### STABLE-12 — Test the actual authentication and playback paths

**Confirmed test gap.** The ten tests cover catalog behavior, but none covers login, refresh/retry, loan creation, actual `playProduct()` orchestration, or `_makePlaybackItem()`. Some tests extract selected methods with AST, bypassing real imports, class initialization, and UI routing (`tests/test_catalog.py:17`, `tests/test_collections.py:39`).

- [ ] Add focused tests for successful/failed login, expiration, one refresh retry, malformed responses, secure session writes, cancellation, and loan recovery.
- [ ] Test all supported stream-response variants and Kodi item properties with explicit Kodi stubs.
- [ ] Import/initialize the actual application with stubs and exercise route-to-service wiring, instead of relying only on extracted methods.
- [ ] Make sanitized service-response fixtures small and synthetic; do not use the captured website or real session tokens.

### STABLE-13 — Build and test a real release artifact

**Confirmed release-process gap.** There is no packaging script, CI workflow, or clean-install validation. Deployment so far copied files over an existing Pi installation, which can mask missing files/dependencies and retain obsolete files.

- [ ] Add CI for tests, supported Python versions, manifest validation, and release-content checks.
- [ ] Produce a versioned ZIP with exactly one top-level directory matching the add-on ID.
- [ ] Check that every required module/asset is included and development files are excluded.
- [ ] Install that ZIP on a fresh Kodi profile, then test an upgrade from the preceding version.

## Quality and maintainability improvements

### QUALITY-01 — Improve catalog loading and cache recovery

**Confirmed limitations.** `EfilmAPI.py:140` refetches the whole catalog after six hours using four workers, offers no cancellation/progress or stale-cache fallback, and has no user-facing refresh action. Lists, genres, and series details have no comparable cache. Seasons and episode browsing refetch the same detail. Concurrent cold starts can duplicate the complete catalog download.

- [ ] Show progress/cancellation, reuse expired cache on suitable transient errors, and add Refresh catalog/Clear cache actions.
- [ ] Coordinate concurrent rebuilds, clean up abandoned temporary files, bound pagination, and consider short-lived caches for other directories.
- [ ] Confirm catalog completeness against the service's visible movie catalog; the endpoint name `relevant` and a matching count alone are not a permanent completeness guarantee.

### QUALITY-02 — Make a large catalog practical to navigate

**Confirmed UX limitation.** The movie view has 24 items per page and only Next page. Reaching a title near the end can require about 150 page transitions at the current catalog size.

- [ ] Add search and/or an A–Z letter selector, with clear current-page/total feedback.
- [ ] Keep genre selection and paging stable when cached content refreshes.

### QUALITY-03 — Localize the actual product UI consistently

**Confirmed.** New menus, dialogs, errors, season labels, and pagination are hardcoded in English; API requests and list titles prefer Catalan, and playback metadata uses English web routes. Existing PO files still identify TV3 and upstream issue URLs.

- [ ] Move current UI text into Kodi localization resources and update the translation catalog.
- [ ] Choose a deliberate UI/content-language policy and apply it to titles, language names, subtitles, and errors.

### QUALITY-04 — Replace debug prints with structured, redacted logging

**Confirmed.** `addon.py:15` prints/logs raw arguments repeatedly; `UI.py:193` logs generated plugin URLs and `UI.py:225` logs video URLs. Current internal eFilm routes generally contain IDs rather than tokens, but the direct-URL fallback can include query parameters.

- [ ] Remove development prints and duplicated messages; use useful log levels and consistent add-on names.
- [ ] Redact query tokens, cookies, authorization headers, credentials, and signed stream/license URLs from diagnostic output.

### QUALITY-05 — Simplify the Python code after the legacy removal

**Confirmed.** Python 2 compatibility shims and `future` remain despite the Python 3 Kodi dependency, along with wildcard/duplicate imports, large commented blocks, inconsistent names, unused variables/imports, and four invalid-regex-escape warnings in inherited code.

- [ ] Remove obsolete compatibility code/dependencies where supported by the chosen minimum version.
- [ ] Separate HTTP/session storage, catalog parsing, playback, and Kodi presentation into directly testable units.
- [ ] Introduce modest formatting/lint checks; make regex strings explicit raw strings for any retained patterns.

### QUALITY-06 — Complete metadata and content presentation

**Confirmed.** `getVideo()` receives year/duration/genres but omits useful fields; season/episode metadata is not carried into Kodi information tags. `addon.py:24` sets every directory's content to movies, including series and episodes. `setInfo()`/`addStreamInfo()` are used throughout; prior Pi logs reported deprecation warnings.

- [ ] Set directory content and supported information tags appropriately for movies, TV shows, seasons, and episodes.
- [ ] Preserve year, numeric duration, episode/season numbers, genres, and artwork consistently.
- [ ] Adopt current Kodi information-tag APIs while honoring the selected minimum Kodi version.

### QUALITY-07 — Add lightweight contributor and support conventions

**Confirmed project gap.** No contribution guide, issue template, security-reporting instructions, or release procedure is present.

- [ ] Document test setup, architecture, fixture sanitization, and the release checklist.
- [ ] Add a concise bug template requesting Kodi/platform/add-on versions and redacted logs; document where sensitive reports should go.
- [ ] Explain that upstream website/API changes can require add-on updates and how to report provider-specific failures.

## Only if submitting to the official Kodi repository

### KODI-01 — Align assets and submission packaging with repository rules

**Confirmed mismatch; not a GitHub-publication requirement.** `resources/icon.png` is 300×364 with an alpha channel; `resources/fanart.png` is 1784×300. The official repository's published rules specify square 256×256 or 512×512 opaque icons, specified widescreen fanart sizes, and no compiled/unneeded files.

- [ ] Prepare compliant artwork and check it against the current submission checker/rules.
- [ ] Recheck metadata, dependency declarations, licensing/provenance, and package contents for the target Kodi branch.

Source: [Official Kodi add-on submission rules](https://kodi.wiki/view/Add-on_rules). These extra submission conditions should not be confused with permission to host experimental source on GitHub.

## Suggested implementation order

1. Public repository hygiene, identity, provenance, and installation documentation: PUBLIC-01 through PUBLIC-05.
2. Remove inherited routes, normalize Unicode, and fix pagination: STABLE-06 through STABLE-08.
3. Session/authentication and loan recovery: STABLE-01 through STABLE-05.
4. Playback prerequisites, service validation, and supported-version tests: STABLE-09 through STABLE-12.
5. Reproducible ZIP/CI and clean-profile acceptance: STABLE-13.
6. Quality improvements; official-repository requirements if that becomes a distribution goal.
