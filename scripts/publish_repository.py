"""Opt-in release publishing, invoked only by the tagged/manual release workflow.

Requires GitHub's gh CLI and GH_TOKEN. This script is never called by tests,
ordinary push checks, or the local build commands.
"""

import argparse
import base64
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_release import ROOT  # noqa: E402
from scripts.build_repository import build_repository, feed_base  # noqa: E402


def publish(tag, repository, prerelease=True):
    feed_base(repository)  # Validate repository before constructing any command/URL.
    version = ET.parse(ROOT / "addon.xml").getroot().attrib["version"]
    if tag != "v" + version:
        raise ValueError("Release tag must exactly match addon.xml version")
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise ValueError("GH_TOKEN is required only for explicit publishing")
    with tempfile.TemporaryDirectory(prefix="efilm-publish-") as temporary:
        directory = Path(temporary)
        site = build_repository(directory / "site", repository)
        checkout = directory / "checkout"
        checkout.mkdir()
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
        encoded = base64.b64encode(("x-access-token:" + token).encode()).decode()
        env.update(
            GIT_CONFIG_COUNT="1",
            GIT_CONFIG_KEY_0="http.https://github.com/.extraheader",
            GIT_CONFIG_VALUE_0="AUTHORIZATION: basic " + encoded,
        )

        def git(*args, capture=False):
            return subprocess.run(
                ["git", *args], cwd=checkout, env=env, check=True, capture_output=capture, text=True
            )

        git("init", "-b", "kodi-repository")
        git("remote", "add", "origin", "https://github.com/" + repository + ".git")
        remote = git("ls-remote", "--heads", "origin", "kodi-repository", capture=True)
        if remote.stdout.strip():
            git("fetch", "--depth=1", "origin", "kodi-repository")
            git("checkout", "-B", "kodi-repository", "FETCH_HEAD")
        shutil.copytree(site, checkout, dirs_exist_ok=True)
        git("add", "-A")
        changes = git("diff", "--cached", "--name-only", capture=True)
        if changes.stdout.strip():
            git(
                "-c",
                "user.name=github-actions[bot]",
                "-c",
                "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                "commit",
                "-m",
                "Publish eBiblioCat eFilm " + version,
            )
            git("push", "origin", "HEAD:refs/heads/kodi-repository")
        assets = sorted(str(path) for path in site.glob("*/*.zip*"))
        view = subprocess.run(
            ["gh", "release", "view", tag, "--repo", repository], capture_output=True, check=False
        )
        if view.returncode == 0:
            command = ["gh", "release", "upload", tag, "--repo", repository, "--clobber", *assets]
        else:
            notes = (
                "Unofficial eBiblioCat eFilm for Kodi. Install the repository ZIP once, "
                "then install the video add-on from that repository. See README.md for "
                "eligibility, playback prerequisites and verification limits."
            )
            command = [
                "gh",
                "release",
                "create",
                tag,
                "--repo",
                repository,
                "--verify-tag",
                "--title",
                "eBiblioCat eFilm " + version,
                "--notes",
                notes,
                *assets,
            ]
            if prerelease:
                command.append("--prerelease")
        subprocess.run(command, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--github-repository", required=True)
    parser.add_argument(
        "--stable", action="store_true", help="Use only after completing device release checks"
    )
    args = parser.parse_args()
    publish(args.tag, args.github_repository, prerelease=not args.stable)
