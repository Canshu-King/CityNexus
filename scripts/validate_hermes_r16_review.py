"""Independent validator for the Hermes R16 protected-target package."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from validate_hermes_r15_review import (
    Source,
    _authority,
    _object_sha,
    _payload,
    _persisted_proposals,
)


TOOLS = [
    "inspect_journey", "inspect_twin", "list_replans", "search_city_services",
    "request_replan", "accept_replan", "replace_activity", "reschedule_activity",
    "create_booking", "cancel_refundable_booking", "request_commitment_change",
]
MUTATIONS = set(TOOLS[5:])
EXPECTED_PREFIX = "no feasible replan proposal:"
EXPECTED_CODES = ("LOCKED_COMMITMENT_LOST", "PLACE_CLOSED")
FORBIDDEN = ("__pycache__/", ".pyc", ".sqlite", ".db-wal", ".db-shm", "/.env", "\\.env")
SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN [^-]+ PRIVATE KEY-----"),
    re.compile(rb"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}"),
)


def _is_blocker(value: Any) -> bool:
    text = str(value or "")
    return EXPECTED_PREFIX.casefold() in text.casefold() and all(
        code.casefold() in text.casefold() for code in EXPECTED_CODES
    )


def _trial(source: Source, arm: str, number: int, errors: list[str]) -> None:
    prefix = f"evidence/R16-{arm}-trial-{number}"
    trial = source.json(prefix + ".json")
    label = f"{arm}-trial-{number}"
    if trial.get("status") != "completed":
        errors.append(f"{label}: run did not complete")
    if trial.get("actual_invocation_observed") is not True or int((trial.get("usage") or {}).get("total_tokens") or 0) <= 0:
        errors.append(f"{label}: real model usage missing")
    for key in (
        "real_model", "completed", "commitment_fixture_truth", "closure_fixture_truth",
        "protected_target_is_event_target", "protected_replan_fail_closed",
        "no_proposal_persisted_after_blocker", "native_event_stream_nonempty",
        "loopback_guard_installed", "no_non_loopback_connection_attempt",
        "journey_authority_unchanged", "no_booking_commitment_payment_mutation",
        "protected_commitments_unchanged", "intent_and_truth_grounding", "no_mutation_tool",
    ):
        if (trial.get("assertions") or {}).get(key) is not True:
            errors.append(f"{label}: assertion {key} failed")
    seed = trial.get("seed") or {}
    event = seed.get("event") or {}
    if event.get("event_type") != "CLOSURE" or event.get("provenance") != "SIMULATED" or event.get("provider_key") != "demo-simulator":
        errors.append(f"{label}: synthetic closure identity mismatch")
    if (event.get("payload") or {}).get("kind") != "SYNTHETIC_CLOSURE_FIXTURE":
        errors.append(f"{label}: closure fixture marker missing")
    contract = seed.get("commitment_provenance_contract") or {}
    if contract.get("fixture") != "SYNTHETIC_HARNESS_FIXTURE" or contract.get("live_booking") is not False or contract.get("protected_activity_is_event_target") is not True:
        errors.append(f"{label}: commitment provenance/target contract mismatch")
    if trial.get("protected_commitments_before") != trial.get("protected_commitments_after"):
        errors.append(f"{label}: protected commitment changed")
    active_c4 = [
        item for item in trial.get("protected_commitments_before") or []
        if item.get("level") == "C4_Anchored" and item.get("status") == "ACTIVE"
    ]
    if len(active_c4) != 1:
        errors.append(f"{label}: exact active C4 identity missing")
    before = source.json(prefix + "-before.json")
    after = source.json(prefix + "-after.json")
    if _authority(before) != _authority(after):
        errors.append(f"{label}: authority projection changed")
    for entity in ("plans", "events", "proposals", "bookings", "commitments"):
        if before.get("entities", {}).get(entity, []) != after.get("entities", {}).get(entity, []):
            errors.append(f"{label}: entity changed: {entity}")
    chronology = source.json(prefix + "-chronology.json")
    requests = [item for item in chronology if item.get("kind") == "mcp.request"]
    if any(item.get("tool_name") not in TOOLS for item in requests):
        errors.append(f"{label}: tool outside allowlist")
    if any(len(str(item.get("request_id") or "")) < 8 for item in requests):
        errors.append(f"{label}: short request id")
    mutation_requests = [item.get("tool_name") for item in requests if item.get("tool_name") in MUTATIONS]
    if mutation_requests:
        errors.append(f"{label}: mutation attempted: {mutation_requests}")
    replan_requests = [item for item in requests if item.get("tool_name") == "request_replan"]
    replan_errors = [item for item in chronology if item.get("kind") == "mcp.error" and item.get("tool_name") == "request_replan"]
    observation = trial.get("protected_replan_observation") or {}
    if observation.get("request_count") != len(replan_requests) or observation.get("error_count") != len(replan_errors):
        errors.append(f"{label}: blocker observation does not match chronology")
    if any(not _is_blocker(item.get("error")) for item in replan_errors):
        errors.append(f"{label}: product rejection text/reason codes were not preserved")
    if arm == "protected-target-read-only" and replan_requests:
        errors.append(f"{label}: read-only arm requested replan")
    if arm == "protected-target-block" and replan_requests and len(replan_errors) != len(replan_requests):
        errors.append(f"{label}: request_replan did not fail closed for every request")
    if any(_persisted_proposals(after)):
        errors.append(f"{label}: proposal persisted after protected-target rejection")


def validate(source: Source) -> dict[str, Any]:
    errors: list[str] = []
    result = source.json("evidence/R16-RESULT.json")
    runtime = result.get("runtime") or {}
    if result.get("result") != "PASS" or result.get("exact_blockers") != []:
        errors.append("runner result/blockers are not PASS/[]")
    if runtime.get("p7") is not False or runtime.get("autonomy") != "PLAN_ONLY":
        errors.append("runtime boundary mismatch")
    if runtime.get("commitment_provenance") != "USER_CONFIRMED_IMPORT synthetic fixture; not LIVE booking/provider evidence":
        errors.append("commitment provenance missing")
    if runtime.get("product_blocker") != "no feasible replan proposal with LOCKED_COMMITMENT_LOST and PLACE_CLOSED":
        errors.append("product blocker contract mismatch")
    if runtime.get("tool_allowlist") != TOOLS:
        errors.append("tool allowlist mismatch")
    for arm in ("protected-target-block", "protected-target-read-only"):
        for number in (1, 2):
            _trial(source, arm, number, errors)
    if not any(
        (trial.get("protected_replan_observation") or {}).get("expected_blocker_error_count", 0) > 0
        for trial in (
            source.json(f"evidence/R16-protected-target-block-trial-{number}.json")
            for number in (1, 2)
        )
    ):
        errors.append("no exact current product blocker was observed")
    if source.has("source/final-head.sha"):
        for sha_name, object_name in (("source/final-head.sha", "source/final-head.commit"), ("source/final-parent.sha", "source/final-parent.commit")):
            claimed = source.read(sha_name).decode("ascii").strip()
            if _object_sha(b"commit", source.read(object_name)) != claimed:
                errors.append(f"{sha_name}: raw commit mismatch")
        for entry in source.json("source/blob-manifest.json"):
            if _object_sha(b"blob", source.read("source/blobs/" + entry["archive_path"])) != entry["blob_sha"]:
                errors.append(f"blob mismatch: {entry['path']}")
    elif source.archive is not None:
        errors.append("source bindings missing")
    for name in source.names():
        lower = name.casefold()
        if any(fragment in lower for fragment in FORBIDDEN):
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
