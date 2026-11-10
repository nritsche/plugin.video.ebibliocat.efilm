# Official Kodi catalog submission preparation

Prepared 2026-11-10 for **v0.2.2**. This is preparation, not an opened or accepted upstream pull request.

## Submission target and package

- Upstream: https://github.com/xbmc/repo-plugins, branch `matrix`.
- Kodi's combined repositories use the lowest supported Python 3 branch; this add-on declares Kodi 19+ compatibility.
- Source tag: https://github.com/nritsche/plugin.video.ebibliocat.efilm/tree/v0.2.2
- Published package: https://github.com/nritsche/plugin.video.ebibliocat.efilm/releases/tag/v0.2.2
- Submit the video add-on only, without the third-party repository installer or update feed.
- Single commit title: `[plugin.video.ebibliocat.efilm] 0.2.2`.
- A local candidate patch is prepared in `dist/kodi-submission-v0.2.2.patch`; it is not included in release packages. The temporary submission repository is `/tmp/efilm-kodi-submission-repo`, branch `efilm-v0.2.2`.

## Official checker result

Ran `kodi-addon-checker 0.0.36 --branch matrix` against a clean extraction of the published v0.2.2 package. Result: **2 errors, 3 warnings**.

Blocking errors:

- The recovered library logo has transparency.
- Its size is 300×364; Kodi requires an opaque 256×256 or 512×512 icon.

Warnings:

- The service website redirects to `/landing`.
- The entry point is 16 counted lines; the checker recommends at most 15.
- `resources/artwork/fanart.svg` is outside the checker's file-extension allowlist. Keep editable artwork in the source repository and omit unneeded source assets from an official submission package.

The checker accepted the manifest XML, add-on ID, translations, fanart size/file size, and declared dependency checks. Automated acceptance does not certify every device/provider or substitute for Team Kodi review. Review the remaining manual checks in [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md), including episode playback and fresh-profile installation. Review the guideline on lower-case filenames; existing Python module filenames include upper-case letters.

Keep the restored logo recognizable when preparing a square opaque variant. Do not modify an already published v0.2.2 ZIP or move its tag; publish a later version if the package changes. The current third-party release remains a prerelease while manual acceptance is pending.

## Opening the pull request

A GitHub fork/API login is still needed. This machine has a working Git SSH key, but no GitHub CLI/API login; SSH authentication cannot create a fork or open a pull request. The public API returned 404 for `nritsche/repo-plugins` during preparation.

1. Create a fork at https://github.com/xbmc/repo-plugins/fork and include the `matrix` branch (disable “Copy the master branch only” if offered).
2. Resolve the checker errors, rerun the checker against the final exported package, and update the package version/source tag if it changes.
3. Push the single-commit submission branch to that fork.
4. Open a draft pull request against `xbmc/repo-plugins:matrix` using [KODI_PULL_REQUEST.md](KODI_PULL_REQUEST.md). Record the actual PR URL here once opened.

References checked during preparation:

- https://kodi.wiki/view/Submitting_Add-ons
- https://kodi.wiki/view/Add-on_rules
- https://github.com/xbmc/repo-plugins/blob/master/CONTRIBUTING.md
- https://github.com/xbmc/addon-check
