"""Run pinned Gitleaks on reachable history and intended source files.

Pass --download on Linux x86_64 to fetch the official checksum-pinned binary,
or --binary PATH to use an already installed matching version. No findings or
report files are retained in the repository; scanner output is fully redacted.
"""

import argparse
import hashlib
import platform
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "8.30.1"
CHECKSUM = "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"


def download(directory):
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
        raise SystemExit("Automatic scanner download supports Linux x86_64; use --binary elsewhere.")
    url = "https://github.com/gitleaks/gitleaks/releases/download/v{0}/gitleaks_{0}_linux_x64.tar.gz".format(
        VERSION
    )
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read(32 * 1024 * 1024)
    if hashlib.sha256(data).hexdigest() != CHECKSUM:
        raise SystemExit("Gitleaks checksum mismatch")
    archive_path = directory / "scanner.tar.gz"
    archive_path.write_bytes(data)
    with tarfile.open(archive_path) as archive:
        member = archive.getmember("gitleaks")
        if not member.isfile():
            raise SystemExit("Invalid scanner archive")
        binary = directory / "gitleaks"
        binary.write_bytes(archive.extractfile(member).read())
        binary.chmod(0o755)
    return binary


def check(binary, root=ROOT):
    version = subprocess.check_output([str(binary), "version"], text=True).strip()
    if version.lstrip("v") != VERSION:
        raise SystemExit("Use Gitleaks " + VERSION + " for the reproducible release check.")
    subprocess.run([str(binary), "git", "--redact=100", "--log-opts=--all", str(root)], check=True)
    with tempfile.TemporaryDirectory(prefix="efilm-source-scan-") as temporary:
        snapshot = Path(temporary)
        files = (
            subprocess.check_output(
                [
                    "git",
                    "-C",
                    str(root),
                    "ls-files",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                    "-z",
                ]
            )
            .decode()
            .split("\0")
        )
        root_names = {
            "addon.py",
            "addon.xml",
            "README.md",
            "LICENSE.txt",
            "changelog.txt",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "RELEASE_AUDIT.md",
            "requirements-dev.txt",
            "requirements-security.txt",
            "pyproject.toml",
        }
        for name in set(files):
            relative = Path(name)
            if not name or (
                relative.parts[0] not in ("resources", "tests", "scripts", "docs", ".github")
                and name not in root_names
            ):
                continue
            path = root / relative
            if "__pycache__" in relative.parts or path.suffix == ".pyc" or not path.is_file():
                continue
            if path.is_symlink():
                raise SystemExit("Source snapshot may not contain symlinks")
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        subprocess.run([str(binary), "dir", "--redact=100", str(snapshot)], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--binary", type=Path)
    group.add_argument("--download", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="efilm-scanner-") as directory:
        check(download(Path(directory)) if args.download else args.binary)
