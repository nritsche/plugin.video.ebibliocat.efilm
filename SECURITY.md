# Reporting sensitive issues

Do not include credentials or signed URLs in public issues. If an account token was exposed, sign out/revoke the affected service session and rotate affected credentials as appropriate.

Use this repository's **Security → Report a vulnerability** private-reporting feature if the maintainer has enabled it. If unavailable, open a public issue containing only a request for a private reporting channel; do not include exploit details or account data until a private channel is arranged. Maintainers should enable private vulnerability reporting before public launch.

Refresh tokens reside only in the Kodi profile's session.json, not in the source or release ZIP. Treat the entire profile backup as private. The add-on never saves the reader password. Local OS permissions and atomic writes reduce accidental exposure but do not protect an account from other software running as the same OS user.

For maintainers: run the maintained history scanner before publication and after handling any suspected exposure. A clean scan is not proof that arbitrary data is safe to disclose. Preserve upstream author attribution; do not rewrite unrelated history merely to remove public contributor metadata.
