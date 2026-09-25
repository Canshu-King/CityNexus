"""Independent validator for the Hermes R20 transport package."""

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


def validate(root: Path) -> dict[str, object]:
    errors: list[str] = []
    result = json.loads((root / "evidence" / "R20-RESULT.json").read_text(encoding="utf-8"))
    if result.get("result") not in {"PASS", "PASS_WITH_EVIDENCE_CLEANUP_BLOCKER"}:
        errors.append("R20 result is not PASS or core-pass/cleanup-blocker state")
    if result.get("result") == "PASS" and result.get("cleanup_blockers") != []:
        errors.append("R20 reports PASS while retaining cleanup blockers")
    if result.get("unexpected_blockers") != []:
        errors.append("unexpected blockers are present")
    if result.get("p7") is not False or result.get("autonomy") != "PLAN_ONLY / NOT_USED":
        errors.append("runtime boundary mismatch")
    transport = result.get("transport_fix") or {}
    if transport.get("client_timeout_seconds") != 120.0 or transport.get("other_tool_timeout_seconds") != 15.0:
        errors.append("transport timeout contract mismatch")
    if transport.get("backend_api_unchanged") is not True or transport.get("proposal_authority_unchanged") is not True:
        errors.append("authority/API boundary mismatch")
    core = result.get("core_assertions") or {}
    for name, passed in core.items():
        if passed is not True:
            errors.append(f"core assertion failed: {name}")
    if len(core) != 8:
        errors.append("core assertion set is incomplete")
    if result.get("mcp_contract_observed") is not True or result.get("direct_stdio_semantic_match") is not True:
        errors.append("stdio MCP contract/parity evidence missing")
    mcp = json.loads((root / "evidence" / "hermes-r4-mcp-stdio.json").read_text(encoding="utf-8"))
    response = mcp.get("response") or {}
    if response.get("proposal_contract_version") != "hermes-replan-proposal-view.v1":
        errors.append("proposal contract version missing")
    if not isinstance(response.get("proposal_views"), list) or not response["proposal_views"]:
        errors.append("proposal views missing")
    if not (root / "evidence" / "hermes-r4-direct-planner.json").exists():
        errors.append("direct planner receipt missing")
    for relative in ("source/final-head.sha", "source/final-head.commit", "source/final-parent.sha", "source/final-parent.commit"):
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
            if object_sha(b"blob", blob.read_bytes()) != item["blob_sha"]:
                errors.append(f"blob mismatch: {item['path']}")
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
        with TemporaryDirectory(prefix="hermes-r20-validate-") as temp:
            with zipfile.ZipFile(args.package) as archive:
                archive.extractall(temp)
            report = validate(Path(temp))
    else:
        report = validate(args.evidence_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
