"""Independent validator for the Hermes R19 runtime fallback package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from validate_hermes_r15_review import Source, _authority, _object_sha, _persisted_proposals

TOOLS = ["inspect_journey", "inspect_twin", "list_replans", "search_city_services", "request_replan", "accept_replan", "replace_activity", "reschedule_activity", "create_booking", "cancel_refundable_booking", "request_commitment_change"]
MUTATIONS = set(TOOLS[5:])
FORBIDDEN = ("__pycache__/", ".pyc", ".sqlite", ".db-wal", ".db-shm", "/.env", "\\.env")
SECRET_PATTERNS = (re.compile(rb"-----BEGIN [^-]+ PRIVATE KEY-----"), re.compile(rb"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}"), re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}"))


def _payload(item: dict[str, Any]) -> dict[str, Any]:
    return item.get("response") if isinstance(item.get("response"), dict) else item.get("result") if isinstance(item.get("result"), dict) else {}


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _fallback(chronology: list[dict[str, Any]]) -> tuple[bool, bool, bool]:
    degraded = synthetic = live = False
    for item in chronology:
        if item.get("kind") != "mcp.response":
            continue
        for node in _walk(_payload(item)):
            degraded = degraded or (node.get("degraded") is True and isinstance(node.get("facts"), list))
            synthetic = synthetic or node.get("route_provenance") == "SYNTHETIC_FIXTURE"
            live = live or any(node.get(field) in {"LIVE_PROVIDER_CAPTURE", "PROVIDER_VERIFIED"} for field in ("provenance", "provider_provenance", "route_provenance", "capture_provenance"))
    return degraded, synthetic, live


def _trial(source: Source, arm: str, number: int, errors: list[str]) -> None:
    prefix = f"evidence/R19-{arm}-trial-{number}"
    trial = source.json(prefix + ".json")
    label = f"{arm}-trial-{number}"
    assertions = trial.get("assertions") or {}
    for key in ("real_model", "completed", "runtime_provider_fallback_observed", "synthetic_fallback_route_observed", "no_live_provider_claim", "unavailable_proposal_boundary", "journey_authority_unchanged", "no_booking_commitment_payment_mutation", "no_mutation_tool", "intent_and_truth_grounding"):
        if assertions.get(key) is not True:
            errors.append(f"{label}: assertion {key} failed")
    if int((trial.get("usage") or {}).get("total_tokens") or 0) <= 0:
        errors.append(f"{label}: model usage missing")
    if (trial.get("seed", {}).get("provider_state_contract") or {}).get("provider_state") != "UNAVAILABLE":
        errors.append(f"{label}: provider state mismatch")
    chronology = source.json(prefix + "-chronology.json")
    requests = [item for item in chronology if item.get("kind") == "mcp.request"]
    if any(item.get("tool_name") not in TOOLS for item in requests):
        errors.append(f"{label}: tool outside allowlist")
    if any(item.get("tool_name") in MUTATIONS for item in requests):
        errors.append(f"{label}: mutation tool attempted")
    degraded, synthetic, live = _fallback(chronology)
    if live:
        errors.append(f"{label}: LIVE/provider claim observed")
    before = source.json(prefix + "-before.json")
    after = source.json(prefix + "-after.json")
    if _authority(before) != _authority(after):
        errors.append(f"{label}: Journey authority changed")
    for entity in ("events", "bookings", "commitments", "payments"):
        if before.get("entities", {}).get(entity, []) != after.get("entities", {}).get(entity, []):
            errors.append(f"{label}: entity changed: {entity}")
    replans = [item for item in requests if item.get("tool_name") == "request_replan"]
    responses = [item for item in chronology if item.get("kind") == "mcp.response" and item.get("tool_name") == "request_replan"]
    if arm == "provider-unavailable-proposal":
        boundary = trial.get("proposal_boundary_observation") or {}
        if (
            not replans
            or not degraded
            or not synthetic
            or not _persisted_proposals(after)
            or boundary.get("server_proposal_contract_observed") is not True
        ):
            errors.append(f"{label}: runtime fallback/proposal evidence missing")
        if boundary.get("request_replan_response_count") == 0 and not boundary.get(
            "request_replan_transport_gap"
        ):
            errors.append(f"{label}: missing direct response or recorded transport gap")
        if boundary.get("finding") not in {
            None,
            "REQUEST_REPLAN_RESPONSE_TIMEOUT_WITH_PERSISTED_PROPOSALS",
        }:
            errors.append(f"{label}: unknown proposal transport finding")
    elif replans:
        errors.append(f"{label}: read-only arm requested replan")


def validate(source: Source) -> dict[str, Any]:
    errors: list[str] = []
    result = source.json("evidence/R19-RESULT.json")
    runtime = result.get("runtime") or {}
    if result.get("result") != "PASS" or result.get("exact_blockers") != []:
        errors.append("runner result/blockers are not PASS/[]")
    if runtime.get("p7") is not False or runtime.get("autonomy") != "PLAN_ONLY":
        errors.append("runtime boundary mismatch")
    if runtime.get("valhalla_url") != "http://127.0.0.1:1" or runtime.get("tool_allowlist") != TOOLS:
        errors.append("runtime contract mismatch")
    for arm in ("provider-unavailable-proposal", "provider-unavailable-read-only"):
        for number in (1, 2):
            _trial(source, arm, number, errors)
    for sha_name, object_name in (("source/final-head.sha", "source/final-head.commit"), ("source/final-parent.sha", "source/final-parent.commit")):
        if source.has(sha_name) and _object_sha(b"commit", source.read(object_name)) != source.read(sha_name).decode("ascii").strip():
            errors.append(f"{sha_name}: raw commit mismatch")
    if source.has("source/blob-manifest.json"):
        for entry in source.json("source/blob-manifest.json"):
            if _object_sha(b"blob", source.read("source/blobs/" + entry["archive_path"])) != entry["blob_sha"]:
                errors.append(f"blob mismatch: {entry['path']}")
    for name in source.names():
        if any(fragment in name.casefold() for fragment in FORBIDDEN):
            errors.append(f"forbidden package path: {name}")
        if name.endswith((".commit", ".patch")):
            continue
        if any(pattern.search(source.read(name)) for pattern in SECRET_PATTERNS):
            errors.append(f"credential-like bytes found in {name}")
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
