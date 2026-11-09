# Contributing

Use Python 3.8-compatible syntax for runtime code. Start with the development commands in README.md. Keep patches focused and include a regression test for changes to authentication, persistence, borrowing, provider-response parsing, or routing.

Tests must import the actual application using `tests/kodi_stubs.py`; do not extract methods with AST or mock away the behavior being tested. Use synthetic `.example.test` service responses and placeholder credentials. Never commit real tokens, production response dumps, personal logs, downloaded webpages, or bytecode. Live verification must not borrow a title without an explicit human confirmation.

The repository is GPL-2.0-or-later. Preserve upstream attribution and use only assets you have permission to redistribute. The current artwork is reproducible from basic geometry and does not use third-party imagery or fonts.

Keep UI messages in `EBiblioStrings.py` and all three PO catalogs (English, Catalan, Spanish). Keep the message IDs stable. The selected Kodi language controls both interface strings and content requests; unsupported languages fall back to English. Fallback-list names without translations use their service slugs.

Use typed `EfilmError` keys across boundaries. Do not log arbitrary exception strings, HTTP payloads, plugin arguments, credentials, cookies, or stream/license URLs. Keep loan POSTs distinct from safe catalog GETs; uncertain loan creation must be reconciled with a read, never blindly retried.

Before requesting review, run tests, lint, formatting, manifest/artwork validation, and the release builder. Describe the behavior change and the checks actually run, distinguishing unit tests from device/provider playback tests. See docs/RELEASE_CHECKLIST.md for publication requirements.
