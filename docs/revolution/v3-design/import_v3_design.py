#!/usr/bin/env python3
"""Import the exact original CityNexus V3 design bundle into the Codex product branch."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

ARCHIVE_NAME = "CityNexus_Revolution_V3_UI_Design_and_Flow.zip"
ARCHIVE_SHA256 = "af084281d7b3f05cee235650c57e9708a759da21f2a7316ddbc62571681c4543"
PRODUCT_BRANCH = "design/revolution-mobile-first-v1"
SCREENS = (
    "探索首页", "Agent主动研究", "地图探索", "地点详情", "三方案对比",
    "每日行程", "出发准备", "旅行中", "Guardian应变", "多人决策",
)
PNG_NAMES = [f"{i:02}_{label}.png" for i, label in enumerate(SCREENS, 1)]
HTML_NAMES = [f"{i:02}_{label}.html" for i, label in enumerate(SCREENS, 1)]
EXTRAS = {"index.html", "CityNexus_V3_交互与实现规格.md", "README_先看这里.txt", "MANIFEST_SHA256.txt"}
ASSETS = {
    "chosen_photos.jpg", "contact.jpg", "guanzhai.jpg", "hero.jpg",
    "lake.jpg", "lakeview.jpg", "mountain.jpg", "mountains.jpg",
    "old_contacts.jpg", "peak.jpg", "peitian.jpg", "secondlake.jpg",
    "spring.jpg", "temple.jpg", "tianyi.jpg", "village.jpg", "villageview.jpg",
}
EXPECTED = set(PNG_NAMES + HTML_NAMES) | EXTRAS | {f"assets/{name}" for name in ASSETS}


def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_zip(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Archive not found: {path}")
        return path
    roots = [Path.home(), Path.home() / "Downloads", Path.home() / "Desktop", Path.cwd()]
    for env in ("USERPROFILE", "OneDrive", "ONEDRIVE"):
        if os.environ.get(env):
            base = Path(os.environ[env])
            roots.extend((base / "Downloads", base / "Desktop", base))
    found: list[Path] = []
    for folder in dict.fromkeys(roots):
        if folder.is_dir():
            found.extend(sorted(folder.glob("CityNexus_Revolution_V3_UI_Design_and_Flow*.zip")))
    for candidate in dict.fromkeys(found):
        if checksum(candidate.read_bytes()) == ARCHIVE_SHA256:
            return candidate
    raise FileNotFoundError(
        f"Original {ARCHIVE_NAME} (SHA256 {ARCHIVE_SHA256}) was not found "
        "in common Downloads/Desktop locations. Pass --archive with the full local path."
    )


def verify_zip(path: Path) -> dict[str, bytes]:
    if checksum(path.read_bytes()) != ARCHIVE_SHA256:
        raise ValueError("Archive SHA256 mismatch; refusing non-original or modified ZIP")
    with zipfile.ZipFile(path) as z:
        names = [item.filename for item in z.infolist()]
        if len(names) != 41 or set(names) != EXPECTED or len(set(names)) != len(names):
            raise ValueError(f"Expected exactly 41 original entries; got {len(names)} (or unexpected paths)")
        for name in names:
            pure = PurePosixPath(name)
            if name.startswith("/") or "\\" in name or ".." in pure.parts or not pure.parts:
                raise ValueError(f"Unsafe archive path: {name!r}")
        bad = z.testzip()
        if bad is not None:
            raise ValueError(f"ZIP CRC error in {bad}")
        files = {name: z.read(name) for name in names}
    manifest: dict[str, str] = {}
    for line in files["MANIFEST_SHA256.txt"].decode("utf-8-sig").splitlines():
        if "  " not in line:
            continue
        digest, name = line.split("  ", 1)
        manifest[name] = digest.lower()
    if set(manifest) != set(PNG_NAMES):
        raise ValueError("PNG manifest names do not match original ten pages")
    for name in PNG_NAMES:
        if checksum(files[name]) != manifest[name]:
            raise ValueError(f"PNG manifest SHA256 mismatch: {name}")
    return files


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", help="Exact local path to the complete ZIP; otherwise search Downloads/Desktop")
    parser.add_argument("--verify-only", action="store_true", help="Verify original SHA/manifest without writing")
    parser.add_argument("--commit-and-push", action="store_true", help="Commit and safely push design files on Codex branch")
    args = parser.parse_args()
    archive = find_zip(args.archive)
    files = verify_zip(archive)
    print(f"VERIFIED: {archive} | {len(files)} files | 10 PNG, 10 HTML, 17 JPG, index/spec/manifests")
    if args.verify_only:
        return 0
    repo = Path(__file__).resolve().parents[3]
    branch = git(repo, "branch", "--show-current")
    if branch != PRODUCT_BRANCH:
        raise RuntimeError(f"Wrong Git branch {branch!r}; expected {PRODUCT_BRANCH!r}. No files changed.")
    if args.commit_and_push and git(repo, "diff", "--cached", "--name-only"):
        raise RuntimeError("Other changes are staged. Unstage them before an automated commit/push.")
    target = repo / "docs" / "revolution" / "v3-design"
    target.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        destination = target.joinpath(*PurePosixPath(name).parts)
        if destination.exists() and checksum(destination.read_bytes()) != checksum(data):
            raise RuntimeError(f"Existing file differs; refusing to overwrite: {destination}")
    for name, data in files.items():
        destination = target.joinpath(*PurePosixPath(name).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        if checksum(destination.read_bytes()) != checksum(data):
            raise IOError(f"Post-copy hash mismatch: {destination}")
    print(f"IMPORTED: all {len(files)} exact ZIP members into {target}")
    if args.commit_and_push:
        paths = ["docs/revolution/v3-design/" + name for name in sorted(files)]
        git(repo, "add", "--", *paths)
        git(repo, "commit", "-m", "docs(revolution): import exact original V3 ten-screen design reference")
        git(repo, "push", "origin", "HEAD:refs/heads/" + PRODUCT_BRANCH)
        print(f"PUSHED: {git(repo, 'rev-parse', 'HEAD')} | branch {PRODUCT_BRANCH}")
    else:
        print("Not pushed; review git status and commit these 41 imported files when ready.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        print(f"V3_IMPORT_BLOCKED: {exc}", file=sys.stderr)
        sys.exit(2)
