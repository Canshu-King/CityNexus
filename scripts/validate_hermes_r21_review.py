"""Independent validator for the Hermes R21 request_replan retry package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory


FORBIDDEN = (".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".env", ".pyc", "__pycache__")
SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN [^-]+ PRIVATE KEY-----"),
    re.compile(rb"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}"),
)


def object_sha(kind: bytes, body: bytes) -> str:
    return hashlib.sha1(kind + b" " + str(len(body)).encode() + b"\0" + body).hexdigest()


def _json(root: Path, name: str) -> dict:
    return json.loads((root / "evidence" / name).read_text(encoding="utf-8"))


def validate(root: Path) -> dict[str, object]:
    errors: list[str] = []
    result = _json(root, "R21-RESULT.json")
    if result.get("result") != "PASS":
        errors.append("R21 result is not PASS")
    runtime = result.get("runtime") or {}
    if result.get("scenario_id") != "hermes-r21-request-replan-retry-reliability":
        errors.append("scenario id mismatch")
    if runtime.get("autonomy") != "PLAN_ONLY" or runtime.get("p7") is not False:
        errors.append("runtime boundary mismatch")
    if not runtime.get("provider") or not runtime.get("model"):
        errors.append("provider/model identity missing")
    boundary = result.get("retry_boundary") or {}
    for field in (
        "same_request_id_required",
        "same_canonical_arguments_required",
        "same_agent_identity_required",
        "same_disposable_database_required",
        "new_proposal_forbidden",
        "new_plan_forbidden",
        "new_event_forbidden",
        "new_idempotency_key_forbidden",
        "backend_api_unchanged",
        "proposal_authority_unchanged",
    ):
        if boundary.get(field) is not True:
            errors.append(f"retry boundary missing: {field}")
    trial_files = sorted((root / "evidence").glob("R21-real-model-exact-request-retry-trial-*.json"))
    trial_files = [
        path
        for path in trial_files
        if re.fullmatch(r"R21-real-model-exact-request-retry-trial-\d+\.json", path.name)
    ]
    if not trial_files:
        errors.append("trial receipts missing")
    for path in trial_files:
        row = json.loads(path.read_text(encoding="utf-8"))
        if not row.get("actual_invocation_observed"):
            errors.append(f"model invocation missing: {path.name}")
        assertions = row.get("assertions") or {}
        for name, passed in assertions.items():
            if passed is not True:
                errors.append(f"trial assertion failed: {path.name}:{name}")
        if row.get("retry_error"):
            errors.append(f"retry error present: {path.name}")
        request = row.get("model_request") or {}
        payload = request.get("request") or {}
        retry = row.get("retry_response") or {}
        if retry.get("request_id") != payload.get("request_id"):
            errors.append(f"request id mismatch: {path.name}")
        if (row.get("identity_sets") or {}).get("retry_new_proposal_ids") != []:
            errors.append(f"duplicate proposal ids: {path.name}")
        chronology = path.with_name(path.stem + "-chronology.json")
        if not chronology.exists():
            errors.append(f"chronology missing: {path.name}")
    for relative in (
        "source/final-head.sha",
        "source/final-head.commit",
        "source/final-parent.sha",
        "source/final-parent.commit",
    ):
        if not (root / relative).exists():
            errors.append(f"missing source binding: {relative}")
    for sha_name, commit_name in (("final-head.sha", "final-head.commit"), ("final-parent.sha", "final-parent.commit")):
        sha_path = root / "source" / sha_name
        commit_path = root / "source" / commit_name
        if sha_path.exists() and commit_path.exists():
            expected = sha_path.read_text(encoding="ascii").strip()
            actual = object_sha(b"commit", commit_path.read_bytes())
            if expected != actual:
                errors.append(f"raw commit mismatch: {sha_name}")
    manifest_path = root / "source" / "blob-manifest.json"
    if manifest_path.exists():
        for item in json.loads(manifest_path.read_text(encoding="utf-8")):
            blob = root / "source" / "blobs" / item["archive_path"]
            if not blob.exists() or object_sha(b"blob", blob.read_bytes()) != item["blob_sha"]:
                errors.append(f"blob mismatch: {item['path']}")
    else:
        errors.append("blob manifest missing")
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        name = path.as_posix().casefold()
        if any(fragment in name for fragment in FORBIDDEN):
            errors.append(f"forbidden package path: {path.relative_to(root)}")
        if path.suffix not in {".commit", ".patch"}:
            raw = path.read_bytes()
            if any(pattern.search(raw) for pattern in SECRET_PATTERNS):
                errors.append(f"credential-like bytes found: {path.relative_to(root)}")
    return {"result": "PASS" if not errors else "FAIL", "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--package", type=Path)
    group.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    if args.package:
        with TemporaryDirectory(prefix="hermes-r21-validate-") as temp:
            with zipfile.ZipFile(args.package) as archive:
                archive.extractall(temp)
            report = validate(Path(temp))
    else:
        report = validate(args.evidence_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
