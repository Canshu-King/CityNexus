"""Independent validator for the Hermes R25 external-review package."""

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
    result = json.loads((evidence / "R25-RESULT.json").read_text(encoding="utf-8"))
    if result.get("result") != "PASS":
        errors.append("R25 result is not PASS")
    if result.get("scenario_id") != "hermes-r25-concurrent-request-replan-signature-conflict":
        errors.append("scenario id mismatch")
    runtime = result.get("runtime") or {}
    if runtime.get("autonomy") != "PLAN_ONLY" or runtime.get("p7") is not False:
        errors.append("runtime boundary mismatch")
    trial_files = sorted(evidence.glob("R25-trial-*.json"))
    if len(trial_files) != int(result.get("trial_count") or 0):
        errors.append("trial count mismatch")
    for path in trial_files:
        row = json.loads(path.read_text(encoding="utf-8"))
        for name, passed in (row.get("assertions") or {}).items():
            if passed is not True:
                errors.append(f"trial assertion failed: {path.name}:{name}")
        if len(row.get("calls") or []) != 2:
            errors.append(f"two concurrent call records missing: {path.name}")
        calls = row.get("calls") or []
        successes = [
            call for call in calls
            if call.get("ok")
            and call.get("backend_http_status") == 200
            and not call.get("trace_error")
        ]
        conflicts = [
            call for call in calls
            if call.get("ok")
            and call.get("backend_http_status") == 409
            and bool(call.get("trace_error"))
        ]
        if len(successes) != 1:
            errors.append(f"winning MCP response count mismatch: {path.name}")
        if len(conflicts) != 1:
            errors.append(f"conflict MCP response count mismatch: {path.name}")
        if conflicts:
            conflict = conflicts[0]
            text = str(conflict.get("trace_error") or "")
            if conflict.get("backend_http_status") != 409:
                errors.append(f"conflict HTTP status mismatch: {path.name}")
            if not any(
                phrase in text
                for phrase in (
                    "same agent request id used for a different request",
                    "same idempotency key used for a different request",
                )
            ):
                errors.append(f"conflict message mismatch: {path.name}")
        if successes:
            response = successes[0].get("json") or {}
            response_ids = sorted(
                str(item.get("id"))
                for item in response.get("proposals", [])
                if isinstance(item, dict) and item.get("id") is not None
            )
            response_plan_ids = sorted(
                str(item.get("proposed_plan_version_id"))
                for item in response.get("proposals", [])
                if isinstance(item, dict)
                and item.get("proposed_plan_version_id") is not None
            )
            before = row.get("before") or {}
            after = row.get("after") or {}
            identities = row.get("new_identity_sets") or {}
            before_proposals = set(before.get("proposal_ids") or [])
            before_plans = set(before.get("plan_ids") or [])
            after_proposals = set(after.get("proposal_ids") or [])
            after_plans = set(after.get("plan_ids") or [])
            if not set(response_ids).issubset(after_proposals):
                errors.append(f"proposal response identity not persisted: {path.name}")
            if not set(response_plan_ids).issubset(after_plans):
                errors.append(f"plan response identity not persisted: {path.name}")
            if sorted(set(response_ids) - before_proposals) != sorted(
                identities.get("proposals") or []
            ):
                errors.append(f"new proposal identity mismatch: {path.name}")
            if sorted(set(response_plan_ids) - before_plans) != sorted(
                identities.get("plans") or []
            ):
                errors.append(f"new plan identity mismatch: {path.name}")
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
        with TemporaryDirectory(prefix="hermes-r25-validate-") as temp:
            with zipfile.ZipFile(args.package) as archive:
                archive.extractall(temp)
            report = validate(Path(temp))
    else:
        report = validate(args.evidence_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
