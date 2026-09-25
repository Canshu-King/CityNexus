"""Independent validator for the Hermes R13 weather provenance package."""

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
FORBIDDEN = ("__pycache__/", ".pyc", ".sqlite", ".db-wal", ".db-shm", "/.env", "\\.env")
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


def _object_sha(kind: bytes, body: bytes) -> str:
    return hashlib.sha1(kind + b" " + str(len(body)).encode("ascii") + b"\0" + body).hexdigest()


def _payload(item: dict[str, Any]) -> dict[str, Any]:
    for key in ("response", "result"):
        if isinstance(item.get(key), dict):
            return item[key]
    return {}


def _proposal_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if not isinstance(value, dict):
        return found
    for field in ("proposal", "proposals", "proposal_views"):
        candidate = value.get(field)
        entries = [candidate] if isinstance(candidate, dict) else candidate if isinstance(candidate, list) else []
        for entry in entries:
            if isinstance(entry, dict) and (entry.get("id") or entry.get("proposal_id")):
                found.add(str(entry.get("id") or entry.get("proposal_id")))
    return found


def _authority(state: dict[str, Any]) -> dict[str, Any]:
    entities = state.get("entities", {})
    journey = entities.get("journey") or {}
    plans = entities.get("plans") or []
    return {
        "journey": {key: journey.get(key) for key in ("id", "status", "active_plan_version_id", "current_activity_id")},
        "active_plans": sorted(
            (str(row.get("id")), row.get("status"))
            for row in plans
            if isinstance(row, dict) and row.get("status") in {"ACTIVE", "SUPERSEDED"}
        ),
        "bookings": entities.get("bookings", []),
        "commitments": entities.get("commitments", []),
        "payments": entities.get("payments", []),
    }


def _persisted_proposals(state: dict[str, Any]) -> set[str]:
    return {
        str(row.get("id"))
        for row in state.get("entities", {}).get("proposals", [])
        if isinstance(row, dict) and row.get("id")
    }


def _validate_trial(source: Source, arm: str, number: int, errors: list[str]) -> None:
    prefix = f"evidence/R13-{arm}-trial-{number}"
    trial = source.json(prefix + ".json")
    label = f"{arm}-trial-{number}"
    if trial.get("status") != "completed":
        errors.append(f"{label}: run did not complete")
    if trial.get("actual_invocation_observed") is not True:
        errors.append(f"{label}: real model invocation missing")
    if int((trial.get("usage") or {}).get("total_tokens") or 0) <= 0:
        errors.append(f"{label}: provider usage missing")
    for key in (
        "real_model", "completed", "weather_fixture_truth", "native_event_stream_nonempty",
        "loopback_guard_installed", "no_non_loopback_connection_attempt",
        "journey_authority_unchanged", "no_booking_commitment_payment_mutation",
        "intent_and_truth_grounding", "no_mutation_tool",
    ):
        if (trial.get("assertions") or {}).get(key) is not True:
            errors.append(f"{label}: assertion {key} failed")
    event = ((trial.get("seed") or {}).get("event") or {})
    payload = event.get("payload") or {}
    if event.get("event_type") != "WEATHER":
        errors.append(f"{label}: event type is not WEATHER")
    if event.get("provenance") != "SIMULATED":
        errors.append(f"{label}: weather event is not SIMULATED")
    if event.get("provider_key") != "demo-simulator":
        errors.append(f"{label}: synthetic provider identity mismatch")
    if payload.get("kind") != "SYNTHETIC_WEATHER_FIXTURE":
        errors.append(f"{label}: synthetic weather marker missing")
    if (trial.get("seed") or {}).get("weather_provenance_contract", {}).get("live_provider_evidence") is not False:
        errors.append(f"{label}: live weather evidence was not explicitly false")
    chronology = source.json(prefix + "-chronology.json")
    if any(len(str(item.get("request_id") or "")) < 8 for item in chronology if item.get("kind") == "mcp.request"):
        errors.append(f"{label}: short request_id")
    if any(item.get("kind") == "mcp.error" for item in chronology):
        errors.append(f"{label}: MCP error recorded")
    requests = [item for item in chronology if item.get("kind") == "mcp.request"]
    if any(item.get("tool_name") not in TOOLS for item in requests):
        errors.append(f"{label}: tool outside allowlist")
    before = source.json(prefix + "-before.json")
    after = source.json(prefix + "-after.json")
    if _authority(before) != _authority(after):
        errors.append(f"{label}: authority projection changed")
    replan = [
        item for item in chronology
        if item.get("kind") == "mcp.response" and item.get("tool_name") == "request_replan"
    ]
    server_ids: set[str] = set()
    complete = False
    for item in replan:
        response = _payload(item)
        server_ids.update(_proposal_ids(response))
        complete = complete or (
            response.get("proposal_contract_version") == "hermes-replan-proposal-view.v1"
            and bool(response.get("proposal_views"))
            and bool(response.get("proposals"))
        )
    if server_ids and not server_ids <= _persisted_proposals(after):
        errors.append(f"{label}: returned proposal id is not persisted")
    mutation_requests = [item.get("tool_name") for item in requests if item.get("tool_name") in MUTATIONS]
    if arm == "weather-proposal":
        if not replan or not complete:
            errors.append(f"{label}: complete request_replan missing")
        if mutation_requests:
            errors.append(f"{label}: mutation request observed: {mutation_requests}")
    else:
        if replan:
            errors.append(f"{label}: read-only arm requested replan")
        if mutation_requests:
            errors.append(f"{label}: mutation request observed: {mutation_requests}")
        for entity in ("plans", "events", "proposals", "bookings", "commitments"):
            if before.get("entities", {}).get(entity, []) != after.get("entities", {}).get(entity, []):
                errors.append(f"{label}: read-only entity changed: {entity}")


def validate(source: Source) -> dict[str, Any]:
    errors: list[str] = []
    result = source.json("evidence/R13-RESULT.json")
    runtime = result.get("runtime") or {}
    if result.get("result") != "PASS":
        errors.append("runner result is not PASS")
    if result.get("exact_blockers") != []:
        errors.append("runner recorded blockers")
    if runtime.get("p7") is not False:
        errors.append("P7 is not false")
    if runtime.get("autonomy") != "PLAN_ONLY":
        errors.append("runtime is not PLAN_ONLY")
    if runtime.get("weather_provenance") != "SIMULATED demo-simulator event; no LIVE/provider weather evidence":
        errors.append("weather provenance contract is not explicit")
    if runtime.get("tool_allowlist") != TOOLS:
        errors.append("tool allowlist mismatch")
    for arm in ("weather-proposal", "weather-read-only"):
        for number in (1, 2):
            _validate_trial(source, arm, number, errors)
    if source.has("source/final-head.sha"):
        for sha_name, object_name in (
            ("source/final-head.sha", "source/final-head.commit"),
            ("source/final-parent.sha", "source/final-parent.commit"),
        ):
            claimed = source.read(sha_name).decode("ascii").strip()
            if _object_sha(b"commit", source.read(object_name)) != claimed:
                errors.append(f"{sha_name}: raw commit mismatch")
        for entry in source.json("source/blob-manifest.json"):
            raw = source.read("source/blobs/" + entry["archive_path"])
            if _object_sha(b"blob", raw) != entry["blob_sha"]:
                errors.append(f"blob mismatch: {entry['path']}")
    else:
        errors.append("source bindings missing")
    for name in source.names():
        lower = name.casefold()
        if any(fragment in lower for fragment in FORBIDDEN):
            errors.append(f"forbidden package path: {name}")
        if name.endswith((".commit", ".patch")):
            continue
        raw = source.read(name)
        if any(pattern.search(raw) for pattern in SECRET_PATTERNS):
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
