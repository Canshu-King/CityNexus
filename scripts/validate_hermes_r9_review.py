"""Independent, derivation-first validator for the Hermes R9 review package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
import zipfile
from pathlib import Path
from typing import Any


REQUIRED_DIRECT_TOOLS = [
    "inspect_journey",
    "inspect_twin",
    "list_replans",
    "request_replan",
    "list_replans",
]
VARIANTS = ("baseline", "tool-guidance", "text-compact")
MUTATION_TOOLS = {
    "accept_replan",
    "replace_activity",
    "reschedule_activity",
    "create_booking",
    "cancel_refundable_booking",
    "request_commitment_change",
}
SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN [^-]+ PRIVATE KEY-----"),
    re.compile(rb"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}"),
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
        return [p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file()]

    def _path(self, name: str) -> str:
        if any(candidate == name for candidate in self.names()):
            return name
        for candidate in self.names():
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


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def git_object_sha(kind: bytes, body: bytes) -> str:
    return hashlib.sha1(kind + b" " + str(len(body)).encode("ascii") + b"\0" + body).hexdigest()


def median(values: list[int]) -> int | None:
    return int(statistics.median(values)) if values else None


def trial_metric(trial: dict[str, Any], field: str) -> int | None:
    if field in trial.get("measurement", {}):
        return trial["measurement"].get(field)
    return (trial.get("usage") or {}).get(field)


def load_trials(source: Source, variant: str) -> list[dict[str, Any]]:
    result = []
    for number in (1, 2, 3):
        result.append(source.json(f"evidence/R9-{variant}-trial-{number}.json"))
    return result


def validate_trial(source: Source, trial: dict[str, Any], variant: str, errors: list[str]) -> None:
    label = f"{variant}-trial-{trial.get('trial')}"
    if trial.get("status") != "completed":
        errors.append(f"{label}: status is not completed")
    if trial.get("actual_invocation_observed") is not True:
        errors.append(f"{label}: no real model invocation")
    usage = trial.get("usage") or {}
    if not isinstance(usage, dict) or int(usage.get("total_tokens") or 0) <= 0:
        errors.append(f"{label}: missing provider-reported token usage")
    if int(trial.get("native_event_stream_event_count") or 0) <= 0:
        errors.append(f"{label}: native event stream is empty")
    native_events_path = f"evidence/R9-{variant}-trial-{trial.get('trial')}-native-events.json"
    try:
        native_events = source.json(native_events_path)
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        errors.append(f"{label}: native event stream file is missing or invalid")
    else:
        expected_events = int(trial.get("native_event_stream_event_count") or 0)
        if not isinstance(native_events, list) or len(native_events) != expected_events:
            errors.append(f"{label}: native event stream file does not match recorded event count")
        elif not native_events or not all(isinstance(item, dict) for item in native_events):
            errors.append(f"{label}: native event stream file is not a non-empty event list")
    if int(trial.get("mcp_call_count") or 0) <= 0:
        errors.append(f"{label}: MCP call count is zero")
    measurement = trial.get("measurement") or {}
    for field in ("backend_http_response_bytes", "adapter_result_bytes", "textcontent_bytes", "structured_content_bytes", "complete_calltool_result_bytes"):
        if int(measurement.get(field) or 0) <= 0:
            errors.append(f"{label}: {field} is not measured")
    if measurement.get("structured_content_byte_equal_before_after") is not True:
        errors.append(f"{label}: structuredContent changed inside envelope")
    if measurement.get("structured_content_matches_adapter_result") is not True:
        errors.append(f"{label}: structuredContent does not match server adapter result")
    if variant != "text-compact" and "request_replan" not in (measurement.get("tool_sequence") or []):
        errors.append(f"{label}: request_replan was not observed")
    for assertion in ("no_mutation_tool", "journey_authority_unchanged", "no_booking_commitment_payment_mutation"):
        if trial.get("assertions", {}).get(assertion) is not True:
            errors.append(f"{label}: {assertion} failed")
    chronology = source.json(f"evidence/R9-{variant}-trial-{trial.get('trial')}-chronology.json")
    callresults = [item for item in chronology if item.get("kind") == "mcp.callresult"]
    if not callresults:
        errors.append(f"{label}: no CallToolResult records")
    if any(item.get("structuredContent_before_sha256") != item.get("structuredContent_after_sha256") for item in callresults):
        errors.append(f"{label}: before/after structuredContent hashes differ")
    if any(item.get("structuredContent_matches_adapter_result") is False for item in callresults):
        errors.append(f"{label}: a CallToolResult structuredContent mismatch was observed")
    if variant == "text-compact":
        replan_records = [item for item in callresults if item.get("tool_name") == "request_replan"]
        for item in replan_records:
            try:
                visible = json.loads(item.get("text") or "{}")
            except (TypeError, ValueError):
                errors.append(f"{label}: compact request_replan text is not JSON")
                continue
            required = {"tool", "decision", "reason_codes", "policy_version", "request_id", "proposal_contract_version", "proposal_views"}
            if not required.issubset(visible):
                errors.append(f"{label}: compact request_replan text lost required server fields")
            structured = item.get("structuredContent") or {}
            if not {"proposal", "proposals", "proposal_views"}.issubset(structured):
                errors.append(f"{label}: compact mode did not preserve full structuredContent")
            if int(item.get("text_bytes") or 0) >= int(item.get("structuredContent_after_bytes") or 0):
                errors.append(f"{label}: compact text was not smaller than structuredContent")


def derive_variant(source: Source, variant: str, errors: list[str]) -> dict[str, Any]:
    trials = load_trials(source, variant)
    for trial in trials:
        validate_trial(source, trial, variant, errors)
    values = {
        "total_tokens": [int(trial_metric(trial, "total_tokens") or 0) for trial in trials],
        "textcontent_bytes": [int(trial_metric(trial, "textcontent_bytes") or 0) for trial in trials],
        "actual_tool_call_count": [int(trial_metric(trial, "actual_tool_call_count") or 0) for trial in trials],
    }
    return {
        "trials": trials,
        "stats": {field: {"values": items, "median": median(items), "min": min(items), "max": max(items)} for field, items in values.items()},
    }


def validate_envelope(source: Source, errors: list[str]) -> None:
    envelope = source.json("evidence/R9-envelope-measurement.json")
    measurement = envelope.get("measurement") or {}
    if measurement.get("tool_sequence") != REQUIRED_DIRECT_TOOLS:
        errors.append("direct envelope tool sequence is not the required five-call measurement")
    for field in ("backend_http_response_bytes", "adapter_result_bytes", "textcontent_bytes", "structured_content_bytes", "complete_calltool_result_bytes", "request_bytes"):
        if int(measurement.get(field) or 0) <= 0:
            errors.append(f"direct envelope {field} is missing")
    if measurement.get("structured_content_byte_equal_before_after") is not True:
        errors.append("direct envelope structuredContent before/after mismatch")
    if measurement.get("structured_content_matches_adapter_result") is not True:
        errors.append("direct envelope structuredContent does not match adapter result")
    records = measurement.get("calltool_records") or []
    if len(records) != 5:
        errors.append("direct envelope does not contain five CallToolResult records")
    if any(int(item.get("text_bytes") or 0) <= 0 or int(item.get("structuredContent_after_bytes") or 0) <= 0 or int(item.get("complete_calltool_result_bytes") or 0) <= 0 for item in records):
        errors.append("direct envelope has a zero-size transport layer")
    components = measurement.get("request_replan_components") or []
    if not components or not all(item.get("proposal_equals_proposals_0") is True for item in components):
        errors.append("request_replan proposal/proposals identity invariant is not proven")
    if not components or not all(item.get("proposal_sha256") and item.get("proposals_sha256") and item.get("proposal_view_hashes") for item in components):
        errors.append("request_replan semantic hashes are incomplete")


def validate_source(source: Source, errors: list[str]) -> None:
    for sha_name, object_name in (("source/final-head.sha", "source/final-head.commit"), ("source/final-parent.sha", "source/final-parent.commit")):
        claimed = source.read(sha_name).decode("ascii").strip()
        body = source.read(object_name)
        if git_object_sha(b"commit", body) != claimed:
            errors.append(f"raw Git commit object does not reproduce {sha_name}")
    manifest = source.json("source/blob-manifest.json")
    for item in manifest:
        raw = source.read("source/blobs/" + item["archive_path"])
        blob_sha = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        if blob_sha != item["blob_sha"]:
            errors.append(f"Git blob mismatch for {item['path']}")


def validate_hygiene(source: Source, errors: list[str]) -> None:
    forbidden_fragments = ("__pycache__/", ".pyc", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", "/.env", "\\.env", "private.key")
    for name in source.names():
        lower = name.casefold()
        if any(fragment in lower for fragment in forbidden_fragments):
            errors.append(f"forbidden package path: {name}")
        if name.endswith((".commit", ".patch")):
            continue
        raw = source.read(name)
        if any(pattern.search(raw) for pattern in SECRET_PATTERNS):
            errors.append(f"credential-like material found in {name}")


def validate(source: Source) -> dict[str, Any]:
    errors: list[str] = []
    result = source.json("evidence/R9-RESULT.json")
    runtime = result.get("runtime") or {}
    if runtime.get("p7") is not False:
        errors.append("P7 is not explicitly false")
    if runtime.get("autonomy") != "PLAN_ONLY":
        errors.append("runtime autonomy is not PLAN_ONLY")
    if runtime.get("mcp_tools") != [
        "inspect_journey", "inspect_twin", "list_replans", "search_city_services", "request_replan",
        "accept_replan", "replace_activity", "reschedule_activity", "create_booking", "cancel_refundable_booking", "request_commitment_change",
    ]:
        errors.append("MCP tool surface does not match the current 11-tool allowlist")
    validate_envelope(source, errors)
    derived = {variant: derive_variant(source, variant, errors) for variant in VARIANTS}
    baseline = derived["baseline"]["stats"]
    for variant in ("tool-guidance", "text-compact"):
        current = derived[variant]
        safe = all(
            trial.get("actual_invocation_observed") is True
            and trial.get("measurement", {}).get("structured_content_byte_equal_before_after") is True
            and trial.get("measurement", {}).get("structured_content_matches_adapter_result") is True
            and "request_replan" in (trial.get("measurement", {}).get("tool_sequence") or [])
            and trial.get("assertions", {}).get("no_mutation_tool") is True
            and trial.get("assertions", {}).get("journey_authority_unchanged") is True
            and trial.get("assertions", {}).get("no_booking_commitment_payment_mutation") is True
            for trial in current["trials"]
        )
        acceptance = {
            "safe": safe,
            "median_total_tokens_improved": current["stats"]["total_tokens"]["median"] < baseline["total_tokens"]["median"],
            "median_model_visible_text_bytes_decreased": current["stats"]["textcontent_bytes"]["median"] < baseline["textcontent_bytes"]["median"],
            "median_mcp_call_count_not_regressed": current["stats"]["actual_tool_call_count"]["median"] <= baseline["actual_tool_call_count"]["median"],
        }
        acceptance["decision"] = "ACCEPTED" if all(acceptance.values()) else "REJECTED"
        recorded = result.get("variants", {}).get(variant, {}).get("acceptance") or {}
        for key, value in acceptance.items():
            if recorded.get(key) != value:
                errors.append(f"recorded {variant} acceptance does not match independent derivation for {key}")
    derived_optimization = "ACCEPTED" if any(
        (result.get("variants", {}).get(variant, {}).get("acceptance") or {}).get("decision") == "ACCEPTED"
        for variant in ("tool-guidance", "text-compact")
    ) else "REJECTED"
    if result.get("optimization_decision") != derived_optimization:
        errors.append("top-level optimization decision is not independently derived")
    validate_source(source, errors)
    validate_hygiene(source, errors)
    return {"result": "PASS" if not errors else "FAIL", "errors": errors, "derived_optimization_decision": derived_optimization}


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
