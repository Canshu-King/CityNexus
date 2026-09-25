"""Independent validator for the Hermes R24 external-review package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory


FORBIDDEN = (
    ".sqlite",
    ".sqlite3",
    ".db-wal",
    ".db-shm",
    ".env",
    ".pyc",
    "__pycache__",
)
SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN [^-]+ PRIVATE KEY-----"),
    re.compile(rb"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}"),
)


def object_sha(kind: bytes, body: bytes) -> str:
    return hashlib.sha1(
        kind + b" " + str(len(body)).encode() + b"\0" + body
    ).hexdigest()


def validate(root: Path) -> dict[str, object]:
    errors: list[str] = []
    evidence = root / "evidence"
    result = json.loads((evidence / "R24-RESULT.json").read_text(encoding="utf-8"))
    if result.get("result") != "PASS":
        errors.append("R24 result is not PASS")
    if result.get("scenario_id") != "hermes-r24-concurrent-request-replan-idempotency":
        errors.append("scenario id mismatch")
    runtime = result.get("runtime") or {}
    if runtime.get("autonomy") != "PLAN_ONLY" or runtime.get("p7") is not False:
        errors.append("runtime boundary mismatch")
    trial_files = sorted(evidence.glob("R24-trial-*.json"))
    if len(trial_files) != int(result.get("trial_count") or 0):
        errors.append("trial count mismatch")
    for path in trial_files:
        row = json.loads(path.read_text(encoding="utf-8"))
        for name, passed in (row.get("assertions") or {}).items():
            if passed is not True:
                errors.append(f"trial assertion failed: {path.name}:{name}")
        if len(row.get("calls") or []) != 2:
            errors.append(f"two concurrent call records missing: {path.name}")
        for call in row.get("calls") or []:
            if call.get("ok") and call.get("result", {}).get("is_error"):
                errors.append(f"MCP error response: {path.name}")
    for relative in (
        "source/final-head.sha",
        "source/final-head.commit",
        "source/final-parent.sha",
        "source/final-parent.commit",
    ):
        if not (root / relative).exists():
            errors.append(f"missing source binding: {relative}")
    for sha_name, commit_name in (
        ("final-head.sha", "final-head.commit"),
        ("final-parent.sha", "final-parent.commit"),
    ):
        sha_path = root / "source" / sha_name
        commit_path = root / "source" / commit_name
        if (
            sha_path.exists()
            and commit_path.exists()
            and sha_path.read_text(encoding="ascii").strip()
            != object_sha(b"commit", commit_path.read_bytes())
        ):
            errors.append(f"raw commit mismatch: {sha_name}")
    manifest = root / "source" / "blob-manifest.json"
    if not manifest.exists():
        errors.append("blob manifest missing")
    else:
        for item in json.loads(manifest.read_text(encoding="utf-8")):
            blob = root / "source" / "blobs" / item["archive_path"]
            if (
                not blob.exists()
                or object_sha(b"blob", blob.read_bytes()) != item["blob_sha"]
            ):
                errors.append(f"blob mismatch: {item['path']}")
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        lowered = path.as_posix().casefold()
        if any(fragment in lowered for fragment in FORBIDDEN):
            errors.append(f"forbidden package path: {path.relative_to(root)}")
        if path.suffix not in {".commit", ".patch"} and any(
            pattern.search(path.read_bytes()) for pattern in SECRET_PATTERNS
        ):
            errors.append(f"credential-like bytes found: {path.relative_to(root)}")
    return {"result": "PASS" if not errors else "FAIL", "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--package", type=Path)
    group.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    if args.package:
        with TemporaryDirectory(prefix="hermes-r24-validate-") as temp:
            with zipfile.ZipFile(args.package) as archive:
                archive.extractall(temp)
            report = validate(Path(temp))
    else:
        report = validate(args.evidence_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
