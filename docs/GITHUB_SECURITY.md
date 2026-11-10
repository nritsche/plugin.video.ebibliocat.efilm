# GitHub security settings

These are repository-owner settings; the local workflow files do not enable them. Git-over-SSH access does not let this task inspect or change administrator settings. Their current enablement state has not been verified.

In the repository's **Settings**, open the security sections (GitHub may show separate **Code security** and **Secret Protection** pages):

- Enable **Secret Protection / secret scanning**, including **push protection**. Push protection blocks supported credential patterns before a push reaches the repository; Gitleaks Actions checks run after a push and before release publication. Neither detects every possible secret.
- Enable the **dependency graph**, **Dependabot alerts**, and **Dependabot security updates**. Dependabot version-update configuration is already committed.
- Enable **private vulnerability reporting**, so researchers can report privately through the repository Security tab.
- Keep the existing workflow-based **CodeQL** setup; it already runs security-extended Python queries. A second default CodeQL setup is unnecessary.

Under **Settings → Rules → Rulesets**, protect `master`: require pull requests and passing test, secret-scanning, and workflow-validation checks; block force pushes and branch deletion. For a solo-maintained repository, do not require another person's approval unless another reviewer is available. Select exact check names from the latest successful workflow run. Review how the rule applies to administrators before enforcing it.

Repository settings: https://github.com/nritsche/plugin.video.ebibliocat.efilm/settings

GitHub guidance checked 2026-11-10:

- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-security-and-analysis-settings-for-your-repository
- https://docs.github.com/en/code-security/concepts/secret-security/push-protection
- https://docs.github.com/en/code-security/getting-started/quickstart-for-securing-your-repository
