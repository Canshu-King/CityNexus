"""Independent derivation-first validator for the Hermes R10 review package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import zipfile
from pathlib import Path
from typing import Any


TOOLS = [
    "inspect_journey", "inspect_twin", "list_replans", "search_city_services",
    "request_replan", "accept_replan", "replace_activity", "reschedule_activity",
    "create_booking", "cancel_refundable_booking", "request_commitment_change",
]
MUTATION_TOOLS = set(TOOLS[5:])
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


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def git_object_sha(kind: bytes, body: bytes) -> str:
    return hashlib.sha1(kind + b" " + str(len(body)).encode("ascii") + b"\0" + body).hexdigest()


def median(values: list[int]) -> int | None:
    return int(statistics.median(values)) if values else None


def proposal_ids(value: Any) -> set[str]:
    result: set[str] = set()
    if not isinstance(value, dict):
        return result
    for field in ("proposal_views", "proposals"):
        entries = value.get(field)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            identity = entry.get("id") or entry.get("proposal_id")
            if identity is not None:
                result.add(str(identity))
    return result


def post_success_reads(chronology: list[dict[str, Any]]) -> dict[str, Any]:
    responses = [item for item in chronology if item.get("kind") == "mcp.response"]
    windows: list[dict[str, Any]] = []
    for index, item in enumerate(responses):
        if item.get("tool_name") != "request_replan":
            continue
        response = item.get("response") if isinstance(item.get("response"), dict) else {}
        generated = proposal_ids(response)
        if not generated:
            continue
        reads: list[dict[str, Any]] = []
        for later in responses[index + 1:]:
            if later.get("tool_name") == "request_replan":
                break
            if later.get("tool_name") != "list_replans":
                continue
            listed_response = later.get("response") if isinstance(later.get("response"), dict) else {}
            listed = proposal_ids(listed_response)
            reads.append({
                "request_id": later.get("request_id"),
                "listed_ids": sorted(listed),
                "same_generated_ids": bool(generated and generated <= listed),
                "response_sha256": hashlib.sha256(canonical(listed_response)).hexdigest(),
            })
        windows.append({
            "request_id": item.get("request_id"),
            "generated_ids": sorted(generated),
            "list_replans_after_success": len(reads),
            "redundant_list_replans_after_success": sum(bool(read["same_generated_ids"]) for read in reads),
            "reads": reads,
        })
    return {
        "successful_request_replan_count": len(windows),
        "list_replans_after_success": sum(window["list_replans_after_success"] for window in windows),
        "redundant_list_replans_after_success": sum(window["redundant_list_replans_after_success"] for window in windows),
        "windows": windows,
    }


def trial_stats(trials: list[dict[str, Any]]) -> dict[str, Any]:
    fields = {
        "total_tokens": lambda item: (item.get("usage") or {}).get("total_tokens"),
        "input_tokens": lambda item: (item.get("usage") or {}).get("input_tokens"),
        "output_tokens": lambda item: (item.get("usage") or {}).get("output_tokens"),
        "mcp_call_count": lambda item: item.get("mcp_call_count"),
        "mcp_response_bytes": lambda item: (item.get("measurement") or {}).get("cumulative_tool_response_bytes"),
        "post_success_list_replans": lambda item: (item.get("post_success_reads") or {}).get("list_replans_after_success"),
        "redundant_post_success_list_replans": lambda item: (item.get("post_success_reads") or {}).get("redundant_list_replans_after_success"),
    }
    result: dict[str, Any] = {}
    for name, getter in fields.items():
        values = sorted(int(value) for item in trials if (value := getter(item)) is not None)
        result[name] = {"values": values, "min": min(values) if values else None, "max": max(values) if values else None, "median": median(values)}
    return result


def validate_trial(source: Source, variant: str, number: int, errors: list[str]) -> dict[str, Any]:
    prefix = f"evidence/R10-{variant}-trial-{number}"
    trial = source.json(prefix + ".json")
    label = f"{variant}-trial-{number}"
    if trial.get("status") != "completed":
        errors.append(f"{label}: status is not completed")
    if trial.get("actual_invocation_observed") is not True:
        errors.append(f"{label}: real model invocation missing")
    if int((trial.get("usage") or {}).get("total_tokens") or 0) <= 0:
        errors.append(f"{label}: provider usage missing")
    native = source.json(prefix + "-native-events.json")
    if not isinstance(native, list) or not native:
        errors.append(f"{label}: native event stream missing")
    elif len(native) != int(trial.get("native_event_stream_event_count") or 0):
        errors.append(f"{label}: native event count mismatch")
    measurement = trial.get("measurement") or {}
    for field in ("backend_http_response_bytes", "adapter_result_bytes", "textcontent_bytes", "structured_content_bytes", "complete_calltool_result_bytes"):
        if int(measurement.get(field) or 0) <= 0:
            errors.append(f"{label}: {field} is not measured")
    if measurement.get("structured_content_byte_equal_before_after") is not True:
        errors.append(f"{label}: structuredContent changed")
    if measurement.get("structured_content_matches_adapter_result") is not True:
        errors.append(f"{label}: structuredContent differs from adapter result")
    chronology = source.json(prefix + "-chronology.json")
    if not isinstance(chronology, list):
        errors.append(f"{label}: chronology is not a list")
        chronology = []
    called = [item.get("tool_name") for item in chronology if item.get("kind") == "mcp.response"]
    if not called:
        errors.append(f"{label}: MCP response chronology is empty")
    if any(tool in MUTATION_TOOLS for tool in called):
        errors.append(f"{label}: mutation tool was called")
    if "request_replan" not in called:
        errors.append(f"{label}: request_replan was not observed")
    for field in ("no_mutation_tool", "journey_authority_unchanged", "no_booking_commitment_payment_mutation", "loopback_guard_installed", "no_non_loopback_connection_attempt"):
        if trial.get("assertions", {}).get(field) is not True:
            errors.append(f"{label}: assertion {field} failed")
    replan = [item for item in chronology if item.get("kind") == "mcp.response" and item.get("tool_name") == "request_replan"]
    if not replan:
        errors.append(f"{label}: no request_replan response")
    else:
        for item in replan:
            response = item.get("response") if isinstance(item.get("response"), dict) else {}
            required = {"decision", "reason_codes", "proposal_contract_version", "proposal_views", "proposals"}
            if not required.issubset(response):
                errors.append(f"{label}: request_replan response is not full fidelity")
            if response.get("proposal_contract_version") != "hermes-replan-proposal-view.v1":
                errors.append(f"{label}: proposal contract version missing")
            if not response.get("proposal_views"):
                errors.append(f"{label}: proposal_views empty")
            if proposal_ids(response) != {str(item.get("id")) for item in response.get("proposals", []) if isinstance(item, dict) and item.get("id") is not None}:
                errors.append(f"{label}: proposal identity sets differ")
    derived_reads = post_success_reads(chronology)
    if trial.get("post_success_reads") != derived_reads:
        errors.append(f"{label}: stored post-success metric differs from raw chronology")
    return trial


def acceptance(baseline: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    safe = all(
        all(trial.get("assertions", {}).get(name) is True for name in (
            "real_model", "completed", "request_replan_observed", "proposal_contract_present",
            "semantic_replan_present", "native_event_stream_nonempty", "loopback_guard_installed",
            "no_non_loopback_connection_attempt", "no_mcp_errors", "no_mutation_tool",
            "journey_authority_unchanged", "no_booking_commitment_payment_mutation",
        )) for trial in variant["trials"]
    )
    bm, vm = baseline["stats"], variant["stats"]
    lower = lambda field: vm[field]["median"] is not None and bm[field]["median"] is not None and vm[field]["median"] < bm[field]["median"]
    result = {
        "safe": safe,
        "semantic_invariants_present": all(trial.get("semantic_replan", {}).get("proposal_contract_version") == "hermes-replan-proposal-view.v1" for trial in variant["trials"]),
        "median_total_tokens_improved": lower("total_tokens"),
        "median_mcp_response_bytes_decreased": lower("mcp_response_bytes"),
        "median_mcp_call_count_not_regressed": vm["mcp_call_count"]["median"] is not None and bm["mcp_call_count"]["median"] is not None and vm["mcp_call_count"]["median"] <= bm["mcp_call_count"]["median"],
        "median_post_success_list_replans_decreased": lower("post_success_list_replans"),
        "median_redundant_post_success_list_replans_decreased": lower("redundant_post_success_list_replans"),
    }
    result["decision"] = "ACCEPTED" if all(result.values()) else "REJECTED"
    return result


def validate_source(source: Source, errors: list[str]) -> None:
    for sha_name, object_name in (("source/final-head.sha", "source/final-head.commit"), ("source/final-parent.sha", "source/final-parent.commit")):
        claimed = source.read(sha_name).decode("ascii").strip()
        if git_object_sha(b"commit", source.read(object_name)) != claimed:
            errors.append(f"{sha_name}: raw Git object hash mismatch")
    for entry in source.json("source/blob-manifest.json"):
        raw = source.read("source/blobs/" + entry["archive_path"])
        actual = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        if actual != entry["blob_sha"]:
            errors.append(f"source blob mismatch: {entry['path']}")


def validate_hygiene(source: Source, errors: list[str]) -> None:
    forbidden = ("__pycache__/", ".pyc", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", "/.env", "\\.env", "private.key")
    for name in source.names():
        lower = name.casefold()
        if any(fragment in lower for fragment in forbidden):
            errors.append(f"forbidden package path: {name}")
        if name.endswith((".commit", ".patch")):
            continue
        raw = source.read(name)
        if any(pattern.search(raw) for pattern in SECRET_PATTERNS):
            errors.append(f"credential-like material found in {name}")


def validate(source: Source) -> dict[str, Any]:
    errors: list[str] = []
    result = source.json("evidence/R10-RESULT.json")
    runtime = result.get("runtime") or {}
    if runtime.get("p7") is not False:
        errors.append("P7 is not explicitly false")
    if runtime.get("autonomy") != "PLAN_ONLY":
        errors.append("runtime is not PLAN_ONLY")
    if runtime.get("mcp_tools") != TOOLS:
        errors.append("MCP tool surface differs from the 11-tool allowlist")
    variants: dict[str, dict[str, Any]] = {}
    for variant in ("baseline", "r10-guided"):
        trials = [validate_trial(source, variant, number, errors) for number in (1, 2, 3)]
        variants[variant] = {"trials": trials, "stats": trial_stats(trials)}
    derived_acceptance = acceptance(variants["baseline"], variants["r10-guided"])
    recorded_acceptance = (result.get("variants", {}).get("r10-guided", {}).get("acceptance") or {})
    for key, value in derived_acceptance.items():
        if recorded_acceptance.get(key) != value:
            errors.append(f"recorded acceptance mismatch: {key}")
    for variant, value in variants.items():
        recorded_stats = result.get("variants", {}).get(variant, {}).get("stats") or {}
        if recorded_stats != value["stats"]:
            errors.append(f"recorded stats mismatch: {variant}")
    baseline_failures = [
        f"baseline-trial-{trial.get('trial')}:" + ",".join(name for name, passed in trial.get("assertions", {}).items() if not passed)
        for trial in variants["baseline"]["trials"]
        if any(not passed for passed in trial.get("assertions", {}).values())
    ]
    if result.get("result") != ("PASS" if not baseline_failures else "BLOCKED"):
        errors.append("top-level result does not match derived baseline safety")
    if result.get("optimization_decision") != derived_acceptance["decision"]:
        errors.append("top-level optimization decision is not derived from trial data")
    if source.has("source/final-head.sha"):
        validate_source(source, errors)
    elif source.archive:
        errors.append("package source bindings are missing")
    validate_hygiene(source, errors)
    return {
        "result": "PASS" if not errors else "FAIL",
        "errors": errors,
        "derived": {variant: {"stats": value["stats"]} for variant, value in variants.items()},
        "derived_acceptance": derived_acceptance,
    }


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
