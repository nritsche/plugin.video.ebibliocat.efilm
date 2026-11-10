# Official Kodi catalog submission

Prepared 2026-11-11 for **v0.2.3**. Team Kodi review and acceptance remain separate from automated checks.

## Submission target

- Upstream: https://github.com/xbmc/repo-plugins, branch `matrix`.
- Fork: https://github.com/nritsche/repo-plugins (created and verified as a fork of the official repository).
- Kodi's combined repositories use the lowest supported Python 3 branch; this add-on declares Kodi 19+ compatibility.
- Source tag: https://github.com/nritsche/plugin.video.ebibliocat.efilm/tree/v0.2.3
- Release: https://github.com/nritsche/plugin.video.ebibliocat.efilm/releases/tag/v0.2.3
- Submit only the video add-on; the third-party repository installer/update feed are excluded.
- Single commit: `[plugin.video.ebibliocat.efilm] 0.2.3`, branch `efilm-v0.2.3`.
- Draft PR: https://github.com/xbmc/repo-plugins/pull/4892
- Submission commit: `08c49fa71cf388151f98c92126dd3f8a0c975484` (one commit against the official Matrix branch).

## Official checker result

`kodi-addon-checker 0.0.36`, target `matrix`, against a clean extraction of v0.2.3: **0 errors, 0 warnings**.

The checker initially stalled on unreachable Kodi mirrors. Official gzip/XML repository manifests for all branches from Gotham through Piers were downloaded successfully from `mirrors.kodi.tv` and its Host Europe mirror using IPv4. The checker used those fresh manifests through a local HTTP-response cache; dependency and cross-branch checks remained enabled. Non-repository URL checks remained live. No empty/fabricated dependency manifest or skipped dependency checks were used.

Resolved findings:

- Library icon is now 512×512 opaque RGB. Its original transparent logo and square icon master remain in the source tree; attribution is separate from the code license.
- Runtime Python module filenames are lower-case, with imports and clean-install tests updated.
- The entry point is below the checker's complexity threshold, with argument parsing still tested.
- Website metadata points directly to `/landing`.
- Editable SVG artwork remains in the source repository and is excluded from runtime packages.
- Runtime diagnostics use Kodi's debug logging level.

Other validation: 85 tests on Python 3.8 and 3.14, approximately 83% coverage, Ruff lint/format, actionlint/zizmor, Gitleaks history/source scan, deterministic packaging, and clean-extraction imports. The user confirmed movie playback and library-logo display on a Raspberry Pi running Kodi 20.

## Review status

Submitted as a draft for initial review on 2026-11-11. Episode playback, fresh-profile dependency installation, and broader device/provider checks remain open in [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md). No test loans are consumed automatically. The third-party feed remains a prerelease channel; neither these checks nor the draft PR claim stable certification or official catalog acceptance.

The previous v0.2.2 candidate had two icon errors and three warnings; it is superseded. Published tags/ZIPs are not rewritten. Local submission patches under `dist/` are not release inputs.

## References

- https://kodi.wiki/view/Submitting_Add-ons
- https://kodi.wiki/view/Add-on_rules
- https://github.com/xbmc/repo-plugins/blob/master/CONTRIBUTING.md
- https://github.com/xbmc/addon-check
