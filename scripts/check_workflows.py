"""Check Actions syntax (actionlint) and security (zizmor), without a GitHub token."""

import argparse
import hashlib
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1.7.12"
CHECKSUM = "8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8"


def download(directory):
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
        raise SystemExit("Use --actionlint PATH outside Linux x86_64.")
    url = (
        "https://github.com/rhysd/actionlint/releases/download/v{0}/actionlint_{0}_linux_amd64.tar.gz".format(
            VERSION
        )
    )
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read(32 * 1024 * 1024)
    if hashlib.sha256(data).hexdigest() != CHECKSUM:
        raise SystemExit("actionlint checksum mismatch")
    archive = directory / "actionlint.tar.gz"
    archive.write_bytes(data)
    with tarfile.open(archive) as source:
        member = source.getmember("actionlint")
        if not member.isfile():
            raise SystemExit("Invalid actionlint archive")
        binary = directory / "actionlint"
        binary.write_bytes(source.extractfile(member).read())
        binary.chmod(0o755)
    return binary


def check(binary):
    workflows = sorted(str(path) for path in (ROOT / ".github/workflows").glob("*.yml"))
    subprocess.run([str(binary), "-shellcheck=", "-pyflakes=", *workflows], cwd=ROOT, check=True)
    name = "zizmor.exe" if sys.platform == "win32" else "zizmor"
    zizmor = shutil.which(name) or str(Path(sys.executable).parent / name)
    subprocess.run([zizmor, "--offline", "--format", "plain", ".github"], cwd=ROOT, check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--actionlint", type=Path)
    group.add_argument("--download", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="efilm-workflow-tools-") as directory:
        check(download(Path(directory)) if args.download else args.actionlint)
