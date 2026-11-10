# Publish releases and a Kodi update repository

The ordinary push/PR checks never publish software. `Publish Kodi repository` is a separate, opt-in workflow. It runs only when a maintainer pushes a `v*` tag or manually dispatches it with an existing tag. Pushing the cleanup commit to `master` does not trigger publication.

## What gets published

- A GitHub prerelease containing the video add-on ZIP, repository-installer ZIP, and SHA-256 checksums.
- A dedicated `kodi-repository` branch containing `addons.xml`, Kodi's required MD5 manifest digest, and versioned add-on packages. The feed is served directly by GitHub's public raw-file URLs; GitHub Pages is not required.
- Older packages remain in the branch for rollback. The feed advertises the current versions.

Users download `repository.ebibliocat.efilm-1.0.0.zip` from the release and install it with **Add-ons → Install from zip file**. Then they choose **Install from repository → eBiblioCat eFilm repository → Video add-ons → eBiblioCat eFilm**. Later releases can be found through Kodi's repository updates, subject to each user's update preferences. Include that installer link in the public README/release notes so new users can discover the source.

This is a third-party repository. Inclusion in Kodi's built-in official catalog remains a separate submission/review process; a GitHub workflow cannot grant that listing.

## First publication

1. Complete `RELEASE_CHECKLIST.md`, especially clean Kodi installation, account/loan verification, and device/provider playback. Keep the release a prerelease while those checks remain incomplete.
2. Make the GitHub source repository public when ready. Kodi needs unauthenticated access to the feed; the publishing workflow intentionally skips private repositories. Check that GitHub Actions is enabled and the repository permits the workflow's narrowly scoped write permission. Enable private vulnerability reporting, dependency graph/alerts, and require the check workflows in your branch rules as appropriate.
3. Ensure `addon.xml` has the intended permanent ID/version and the changelog describes it. This repository's workflow uses `github.repository`, so a fork can publish its own feed without hardcoding another owner's token or URL.
4. Commit/push the reviewed source, create the exact matching tag (for example `v0.2.0` for version `0.2.0`), and push that tag. Alternatively dispatch `Publish Kodi repository` with that existing tag. This is the explicit publication action.
5. Confirm the workflow succeeds, the feed is public, both ZIPs download, and the repository installer finds the video add-on in a clean Kodi profile.

All actions are pinned to reviewed commits. The release job reruns tests, coverage, lint/format, workflow security/syntax checks, history/source secret scanning, and metadata/artwork validation before it receives the publishing token in the final step. It pushes the generated branch without force and verifies that the release tag matches the manifest. It does not modify source history, make the source repository public, or change account settings. Re-running a tag updates its release assets idempotently.

The workflow defaults to GitHub **prereleases**. Stable publishing is deliberately a separate maintainer decision after the device checks; `scripts/publish_repository.py --stable` is available for a reviewed release procedure. A prerelease's packages are still served by this development repository feed, so users who install that feed are opting into public testing. Create separate stable/beta feeds before promising a stable channel.

## Build locally without publishing

```sh
python scripts/build_release.py
python scripts/build_repository.py
```

The resulting feed is in `dist/repository/`. The builder performs no network requests or GitHub writes. Run `python scripts/check_workflows.py --download` after installing `requirements-security.txt` to check workflow syntax and security; this downloads a checksum-pinned Linux x86_64 actionlint binary. On other systems pass `--actionlint PATH`. `scripts/check_secrets.py` similarly accepts `--download` or a pinned local `--binary`.

## Official catalog preparation

See [KODI_SUBMISSION.md](KODI_SUBMISSION.md) for the v0.2.3 submission candidate, successful official checker result, and upstream review status. Repository-owner settings are described in [GITHUB_SECURITY.md](GITHUB_SECURITY.md).
