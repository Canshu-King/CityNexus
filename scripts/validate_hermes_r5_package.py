from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


FORBIDDEN_NAMES = re.compile(r"(?:^|/)(?:\.env(?:\.|$)|[^/]+\.sqlite(?:3)?(?:-wal|-shm)?$|[^/]+\.db(?:-wal|-shm)?$|__pycache__|[^/]+\.pyc$)", re.I)
SECRET_PATTERNS = [
    re.compile(rb"-----BEGIN (?:OPENSSH|RSA|EC|DSA) PRIVATE KEY-----"),
    re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(rb"(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*['\"]?[A-Za-z0-9_./+-]{24,}"),
]


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def git_commit_sha(data: bytes) -> str:
    return hashlib.sha1(b"commit " + str(len(data)).encode() + b"\0" + data).hexdigest()


def validate(path: Path) -> list[str]:
    failures: list[str] = []
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            failures.append(f"ZIP CRC failed: {bad_member}")
        infos = archive.infolist()
        names = [info.filename for info in infos]
        required = {
            "REVIEW_MANIFEST.md", "REVIEW_MANIFEST.json", "EXTERNAL_REVIEW.md", "HERMES_R5_SCENARIO.md",
            "evidence/hermes-r5-request-replan-original.json",
            "evidence/hermes-r5-legacy-cache-retry.json",
            "evidence/hermes-r5-missing-proposal.json",
            "evidence/r4-regression-receipt.json", "evidence/os-stdout.txt",
            "evidence/os-stderr.txt", "evidence/exit-code.txt",
            "evidence/focused-tests.txt", "source/source.commit-object.txt",
            "source/parent.commit-object.txt", "source/parent-to-source.patch",
            "source/changed-files.txt", "validation/validate_hermes_r5_package.py",
        }
        failures.extend(f"required file missing: {name}" for name in sorted(required - set(names)))
        for name in names:
            member = PurePosixPath(name)
            if member.is_absolute() or ".." in member.parts or "\\" in name:
                failures.append(f"unsafe archive path: {name}")
            if FORBIDDEN_NAMES.search(name):
                failures.append(f"forbidden payload: {name}")
            data = archive.read(name)
            if data.startswith(b"SQLite format 3\0"):
                failures.append(f"SQLite payload: {name}")
            if name != "REVIEW_MANIFEST.json":
                for pattern in SECRET_PATTERNS:
                    if pattern.search(data):
                        failures.append(f"credential pattern in {name}")
                        break
        if "REVIEW_MANIFEST.json" in names:
            manifest = json.loads(archive.read("REVIEW_MANIFEST.json"))
            for name, entry in manifest["files"].items():
                if name not in names:
                    failures.append(f"manifest file missing: {name}")
                    continue
                data = archive.read(name)
                if len(data) != entry["size"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                    failures.append(f"manifest mismatch: {name}")
            commit = archive.read("source/source.commit-object.txt")
            parent = archive.read("source/parent.commit-object.txt")
            if git_commit_sha(commit) != manifest["source_commit"]:
                failures.append("source commit object SHA mismatch")
            if git_commit_sha(parent) != manifest["direct_parent"]:
                failures.append("direct parent commit object SHA mismatch")
            headers = commit.split(b"\n\n", 1)[0].splitlines()
            parent_headers = [line.split(b" ", 1)[1].decode() for line in headers if line.startswith(b"parent ")]
            if manifest["direct_parent"] not in parent_headers:
                failures.append("source commit does not name packaged direct parent")
            if archive.read("evidence/exit-code.txt").strip() != b"0":
                failures.append("scenario process exit code is not zero")
            try:
                receipt = json.loads(archive.read("evidence/hermes-r5-request-replan-original.json"))
                stdout_bytes = archive.read("evidence/os-stdout.txt")
                stdout_receipt = json.loads(stdout_bytes)
                if (receipt != stdout_receipt or receipt.get("result") != "PASS"
                        or archive.read("evidence/hermes-r5-request-replan-original.json") != stdout_bytes):
                    failures.append("machine receipt and OS stdout disagree or scenario is not PASS")
                if receipt.get("source_binding_before", {}).get("status_porcelain_v1"):
                    failures.append("source worktree was dirty before runtime")
                if receipt.get("source_binding_after", {}).get("status_porcelain_v1"):
                    failures.append("source worktree was dirty after runtime")
            except (ValueError, KeyError) as exc:
                failures.append(f"receipt validation failed: {exc}")

        patch_name = "source/parent-to-source.patch"
        parent_tree_prefix = "source/parent-tree/"
        final_tree_prefix = "source/final-tree/"
        if patch_name in names:
            changed = [name for name in names if name.startswith(parent_tree_prefix)]
            if not changed:
                failures.append("patch reconstruction source trees are absent")
            else:
                with tempfile.TemporaryDirectory(prefix="hermes-r5-validator-") as temp_name:
                    work = Path(temp_name)
                    for name in names:
                        if name.startswith(final_tree_prefix):
                            relative = name[len(final_tree_prefix):]
                            target = work / relative
                            target.parent.mkdir(parents=True, exist_ok=True)
                            target.write_bytes(archive.read(name))
                    patch = work / "source.patch"
                    patch.write_bytes(archive.read(patch_name))
                    reverse = subprocess.run(["git", "-c", "core.autocrlf=false", "apply", "--reverse", str(patch)], cwd=work, capture_output=True)
                    if reverse.returncode:
                        failures.append("parent-to-source patch cannot reverse-apply: " + reverse.stderr.decode(errors="replace"))
                    else:
                        for name in names:
                            if name.startswith(parent_tree_prefix):
                                relative = name[len(parent_tree_prefix):]
                                if (work / relative).read_bytes() != archive.read(name):
                                    failures.append(f"reverse patch differs from parent file: {relative}")
                        forward = subprocess.run(["git", "-c", "core.autocrlf=false", "apply", str(patch)], cwd=work, capture_output=True)
                        if forward.returncode:
                            failures.append("parent-to-source patch cannot forward-apply: " + forward.stderr.decode(errors="replace"))
                        else:
                            for name in names:
                                if name.startswith(final_tree_prefix):
                                    relative = name[len(final_tree_prefix):]
                                    if (work / relative).read_bytes() != archive.read(name):
                                        failures.append(f"forward patch differs from final file: {relative}")
    return failures


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    problems = validate(args.archive)
    print(json.dumps({"result": "FAIL" if problems else "PASS", "failures": problems}, indent=2))
    raise SystemExit(1 if problems else 0)
