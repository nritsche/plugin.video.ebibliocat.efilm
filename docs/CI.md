# Automated checks

All third-party actions are pinned to verified commit SHAs, with Dependabot update proposals and a seven-day cooldown. Workflow permissions default to read-only. The code does not use pull_request_target, interpolate untrusted PR text into shell commands, or persist checkout credentials.

| Check | Purpose | Where it runs |
| --- | --- | --- |
| Ruff lint | Python errors, unused imports, invalid escapes | Push, PR, release |
| Ruff format | Consistent code style | Push, PR, release |
| unittest + coverage | Real application regression tests, branch coverage gate at 80%, XML artifacts | Python 3.8/3.12/3.14 on Linux and 3.12 on Windows |
| Gitleaks | Redacted scan of reachable Git history and intended source files | Push, PR, release |
| actionlint | Workflow syntax and expression checks | Push, PR, release |
| zizmor | Workflow/Dependabot security checks | Push, PR, release |
| CodeQL security-extended | Semantic Python security analysis | Public-repo push/PR, weekly, manual |
| Dependency review | Reject newly introduced moderate-or-higher dependency vulnerabilities | Public-repo pull requests |
| Manifest/artwork/package checks | Required dependencies/assets, clean/deterministic ZIP, import from extracted ZIP | Push, PR, release |
| Dependabot | Propose dependency/action updates | Monthly |

Coverage reports and release-build artifacts remain on GitHub Actions; no external coverage service/token is needed. `checks.yml` builds and uploads artifacts without publishing a release. `publish.yml` handles explicit tagged/manual publication separately.

CodeQL and dependency review are skipped while the source repository is private, avoiding an assumption that a paid GitHub security license is available. Enable the dependency graph and use the advanced CodeQL workflow when the repository becomes public; do not also enable a conflicting default CodeQL setup. Branch protection and private vulnerability reporting are GitHub repository settings, not changes that this commit can certify.

Run the same checks locally using README.md and DISTRIBUTION.md. A configured workflow is not a successful hosted run: inspect the Actions results after pushing. Automated tests do not substitute for clean Kodi installation and real device/provider playback acceptance.
