"""Independent validator for the Hermes R10 request-id schema package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any


TOOLS = [
    "inspect_journey", "inspect_twin", "list_replans", "search_city_services",
    "request_replan", "accept_replan", "replace_activity", "reschedule_activity",
    "create_booking", "cancel_refundable_booking", "request_commitment_change",
]
MUTATIONS = set(TOOLS[5:])
SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN [^-]+ PRIVATE KEY-----"),
    re.compile(rb"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}"),
)


class Source:
    def __init__(self, root: Path | None = None, package: Path | None = None):
        self.root = root
        self.archive = zipfile.ZipFile(package) if package else None

    def close(self) -> None:
        if self.archive:
            self.archive.close()

    def names(self) -> list[str]:
        if self.archive:
            return self.archive.namelist()
        assert self.root is not None
        return [item.relative_to(self.root).as_posix() for item in self.root.rglob("*") if item.is_file()]

    def _path(self, name: str) -> str:
        names = self.names()
        if name in names:
            return name
        if name.startswith("evidence/") and name[9:] in names:
            return name[9:]
        for candidate in names:
            if candidate.endswith("/" + name):
                return candidate
        raise FileNotFoundError(name)

    def read(self, name: str) -> bytes:
        path = self._path(name)
        if self.archive:
            return self.archive.read(path)
        assert self.root is not None
        return (self.root / path).read_bytes()

    def json(self, name: str) -> Any:
        return json.loads(self.read(name).decode("utf-8"))

    def has(self, name: str) -> bool:
        try:
            self._path(name)
        except FileNotFoundError:
            return False
        return True


def git_object_sha(kind: bytes, body: bytes) -> str:
    return hashlib.sha1(kind + b" " + str(len(body)).encode("ascii") + b"\0" + body).hexdigest()


def validate(source: Source) -> dict[str, Any]:
    errors: list[str] = []
    result = source.json("evidence/R10-REQUEST-ID-RESULT.json")
    runtime = result.get("runtime") or {}
    if result.get("result") != "PASS" or result.get("exact_blockers") != []:
        errors.append("probe result is not a clean PASS")
    if runtime.get("p7") is not False:
        errors.append("P7 is not false")
    if runtime.get("autonomy") != "PLAN_ONLY":
        errors.append("runtime is not PLAN_ONLY")
    if runtime.get("mcp_tools") != TOOLS:
        errors.append("tool surface does not match the 11-tool allowlist")

    for number in (1, 2, 3):
        prefix = f"evidence/R10-request-id-schema-trial-{number}"
        trial = source.json(prefix + ".json")
        label = f"trial-{number}"
        if trial.get("status") != "completed":
            errors.append(f"{label}: run did not complete")
        if trial.get("actual_invocation_observed") is not True:
            errors.append(f"{label}: no real model invocation")
        if int((trial.get("usage") or {}).get("total_tokens") or 0) <= 0:
            errors.append(f"{label}: provider usage missing")
        if trial.get("mcp_error_count") != 0:
            errors.append(f"{label}: MCP errors recorded")
        observation = trial.get("request_id_observation") or {}
        if observation.get("all_adapter_request_ids_valid_length") is not True or observation.get("short_request_ids"):
            errors.append(f"{label}: invalid adapter request_id observed")
        for assertion in (
            "request_replan_observed", "proposal_contract_present", "semantic_replan_present",
            "native_event_stream_nonempty", "loopback_guard_installed",
            "no_non_loopback_connection_attempt", "no_mcp_errors", "no_mutation_tool",
            "journey_authority_unchanged", "no_booking_commitment_payment_mutation",
        ):
            if trial.get("assertions", {}).get(assertion) is not True:
                errors.append(f"{label}: {assertion} failed")
        native = source.json(prefix + "-native-events.json")
        if not isinstance(native, list) or len(native) != int(trial.get("native_event_stream_event_count") or 0) or not native:
            errors.append(f"{label}: native event stream mismatch")
        chronology = source.json(prefix + "-chronology.json")
        requests = [item for item in chronology if item.get("kind") == "mcp.request"]
        if any(len(str(item.get("request_id") or "")) < 8 for item in requests):
            errors.append(f"{label}: raw chronology contains a short adapter request_id")
        if any(item.get("kind") == "mcp.error" for item in chronology):
            errors.append(f"{label}: raw chronology contains mcp.error")
        replan = [item for item in chronology if item.get("kind") == "mcp.response" and item.get("tool_name") == "request_replan"]
        if not replan:
            errors.append(f"{label}: no request_replan response")
        for item in replan:
            response = item.get("response") if isinstance(item.get("response"), dict) else {}
            if response.get("proposal_contract_version") != "hermes-replan-proposal-view.v1":
                errors.append(f"{label}: proposal contract missing")
            if not response.get("proposal_views") or not response.get("proposals"):
                errors.append(f"{label}: proposal projection incomplete")
        if any(item.get("tool_name") in MUTATIONS for item in requests):
            errors.append(f"{label}: mutation tool request observed")

    if source.has("source/final-head.sha"):
        for sha_name, object_name in (("source/final-head.sha", "source/final-head.commit"), ("source/final-parent.sha", "source/final-parent.commit")):
            claimed = source.read(sha_name).decode("ascii").strip()
            if git_object_sha(b"commit", source.read(object_name)) != claimed:
                errors.append(f"{sha_name}: raw Git commit hash mismatch")
        for sha_name, object_name in (("source/request-id-repair-head.sha", "source/request-id-repair-head.commit"), ("source/request-id-repair-parent.sha", "source/request-id-repair-parent.commit")):
            claimed = source.read(sha_name).decode("ascii").strip()
            if git_object_sha(b"commit", source.read(object_name)) != claimed:
                errors.append(f"{sha_name}: raw Git commit hash mismatch")
        for entry in source.json("source/blob-manifest.json"):
            raw = source.read("source/blobs/" + entry["archive_path"])
            actual = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
            if actual != entry["blob_sha"]:
                errors.append(f"source blob mismatch: {entry['path']}")
    elif source.archive:
        errors.append("package source bindings are missing")

    for name in source.names():
        lower = name.casefold()
        if any(fragment in lower for fragment in ("__pycache__/", ".pyc", ".sqlite", ".db-wal", ".db-shm", "/.env", "\\.env", "private.key")):
            errors.append(f"forbidden package path: {name}")
        if name.endswith((".commit", ".patch")):
            continue
        raw = source.read(name)
        if any(pattern.search(raw) for pattern in SECRET_PATTERNS):
            errors.append(f"credential-like material found in {name}")
    return {"result": "PASS" if not errors else "FAIL", "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--package", type=Path)
    group.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    source = Source(root=args.evidence_dir, package=args.package)
    try:
        report = validate(source)
    finally:
        source.close()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
