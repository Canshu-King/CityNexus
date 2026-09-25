from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

try:
    from scripts.hermes_r6_h11_model_probe import (
        PROFILE_NAME, _gateway_run, _provider_key, _read_profile, _read_trace,
        _save_json, clean_receipt, git, _seed,
    )
    from scripts.hermes_r7_human_approval_probe import (
        _configure_arm, _r7_state, _sanitize_guard, _stop_arm,
    )
    from scripts.hermes_r8_context_probe import BASELINE_INPUT, BASELINE_INSTRUCTIONS
    from scripts.hermes_r9_mcp_context_probe import (
        _authority_ok, _configure_r9_arm, _read_measurement,
    )
except ImportError:
    from hermes_r6_h11_model_probe import (
        PROFILE_NAME, _gateway_run, _provider_key, _read_profile, _read_trace,
        _save_json, clean_receipt, git, _seed,
    )
    from hermes_r7_human_approval_probe import (
        _configure_arm, _r7_state, _sanitize_guard, _stop_arm,
    )
    from hermes_r8_context_probe import BASELINE_INPUT, BASELINE_INSTRUCTIONS
    from hermes_r9_mcp_context_probe import (
        _authority_ok, _configure_r9_arm, _read_measurement,
    )


SCENARIO_ID = "hermes-r10-tool-planning-efficiency"
VARIANTS = ("baseline", "r10-guided")


def _canonical(value: Any) -> Any:
    volatile = {
        "id", "journey_id", "trigger_event_id", "base_plan_version_id",
        "proposed_plan_version_id", "request_id", "snapshot_id", "snapshot_at",
        "captured_at", "created_at", "updated_at", "timestamp", "event_id",
        "plan_version_id", "activity_id", "current_activity_id", "latest_event_id",
        "proposal_id",
    }
    if isinstance(value, dict):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in volatile
        }
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    return value


def _semantic_replan(trace: list[dict[str, Any]]) -> dict[str, Any] | None:
    results = [
        item.get("result") for item in trace
        if item.get("kind") == "adapter.result"
        and item.get("tool_name") == "request_replan"
        and isinstance(item.get("result"), dict)
    ]
    if not results:
        return None
    result = results[-1]
    projection = {
        "decision": result.get("decision"),
        "proposal_contract_version": result.get("proposal_contract_version"),
        "reason_codes": result.get("reason_codes"),
        "proposal_views": result.get("proposal_views"),
        "proposals": result.get("proposals"),
    }
    canonical = _canonical(projection)
    return {
        "projection": canonical,
        "sha256": hashlib.sha256(
            json.dumps(canonical, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest(),
        "proposal_count": len(result.get("proposal_views") or []),
        "proposal_contract_version": result.get("proposal_contract_version"),
        "hard_constraint_results": [
            item.get("hard_constraints_passed")
            for item in result.get("proposal_views", [])
            if isinstance(item, dict)
        ],
    }


def _post_success_reads(trace: list[dict[str, Any]]) -> dict[str, Any]:
    def _proposal_ids(response: dict[str, Any]) -> set[str]:
        ids: set[str] = set()
        for field in ("proposal_views", "proposals"):
            values = response.get(field)
            if not isinstance(values, list):
                continue
            for value in values:
                if not isinstance(value, dict):
                    continue
                proposal_id = value.get("id") or value.get("proposal_id")
                if proposal_id is not None:
                    ids.add(str(proposal_id))
        return ids

    responses = [item for item in trace if item.get("kind") == "mcp.response"]
    generated_ids: set[str] = set()
    windows: list[dict[str, Any]] = []
    for index, item in enumerate(responses):
        if item.get("tool_name") != "request_replan":
            continue
        response = item.get("response") if isinstance(item.get("response"), dict) else {}
        if not _proposal_ids(response):
            continue
        generated_ids = _proposal_ids(response)
        reads = []
        for later in responses[index + 1:]:
            if later.get("tool_name") == "request_replan":
                break
            if later.get("tool_name") != "list_replans":
                continue
            listed = later.get("response") if isinstance(later.get("response"), dict) else {}
            listed_ids = _proposal_ids(listed)
            reads.append({
                "request_id": later.get("request_id"),
                "listed_ids": sorted(listed_ids),
                "same_generated_ids": bool(generated_ids and generated_ids <= listed_ids),
                "response_sha256": hashlib.sha256(
                    json.dumps(listed, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), default=str).encode("utf-8")
                ).hexdigest(),
            })
        windows.append({
            "request_id": item.get("request_id"),
            "generated_ids": sorted(generated_ids),
            "list_replans_after_success": len(reads),
            "redundant_list_replans_after_success": sum(
                bool(read.get("same_generated_ids")) for read in reads
            ),
            "reads": reads,
        })
    return {
        "successful_request_replan_count": len(windows),
        "list_replans_after_success": sum(
            int(window["list_replans_after_success"]) for window in windows
        ),
        "redundant_list_replans_after_success": sum(
            int(window["redundant_list_replans_after_success"]) for window in windows
        ),
        "windows": windows,
    }


def _run_trial(temp_root: Path, hermes_bin: Path, hermes_python: Path,
               profile: dict[str, Any], provider_key: str, variant: str,
               trial: int, output: Path) -> dict[str, Any]:
    arm = None
    try:
        description_mode = "baseline" if variant == "baseline" else "r10-guided"
        arm = _configure_r9_arm(
            temp_root, f"r10-{variant}-{trial}", hermes_bin, hermes_python,
            profile, provider_key, "full", description_mode,
        )
        seed = _seed(arm["backend"], arm["runtime"])
        before = _r7_state(arm["database"], seed["journey_id"])
        mission = str(uuid.uuid4())
        session = f"citynexus-{seed['journey_id']}-r10-{variant}-{trial}-{mission}"
        run = _gateway_run(
            gateway=arm["gateway"], backend=arm["backend"],
            journey_id=seed["journey_id"], session_id=session, mission_id=mission,
            run_key=f"r10-{variant}-{trial}-{mission}",
            user_input=BASELINE_INPUT + " Journey ID: " + seed["journey_id"],
            instructions=BASELINE_INSTRUCTIONS + " Journey ID: " + seed["journey_id"],
            trace_path=arm["trace_path"], tee=arm["tee"], api_headers=arm["headers"],
            timeout_seconds=300,
        )
        after = _r7_state(arm["database"], seed["journey_id"])
        trace = _read_trace(arm["trace_path"])
        measurement = _read_measurement(trace, run)
        post_success = _post_success_reads(trace)
        semantic = _semantic_replan(trace)
        authority = _authority_ok(before, after, measurement["tool_sequence"])
        guard = _sanitize_guard(
            arm["guard"], [provider_key, arm.get("agent_token", ""), arm.get("gateway_key", "")]
        )
        errors = [item for item in trace if item.get("kind") == "mcp.error"]
        item = {
            "scenario_id": SCENARIO_ID,
            "variant": variant,
            "trial": trial,
            "run_id": run.get("run_id"),
            "mission_id": mission,
            "session_id": session,
            "status": run.get("status"),
            "run_status": run.get("run_status"),
            "submission_http_status": run.get("submission_http_status"),
            "submission_response": run.get("submission_response"),
            "stream_error": run.get("stream_error"),
            "exact_blocker": run.get("exact_blocker"),
            "model_reported_by_gateway": run.get("model_reported_by_gateway"),
            "actual_invocation_observed": bool(run.get("actual_invocation_observed")),
            "native_event_stream_event_count": len(run.get("native_event_stream") or []),
            "mcp_call_count": len(run.get("mcp_calls") or []),
            "usage": run.get("usage"),
            "output": run.get("output"),
            "tool_sequence": measurement["tool_sequence"],
            "measurement": {key: value for key, value in measurement.items()
                            if key != "calltool_records"},
            "post_success_reads": post_success,
            "semantic_replan": semantic,
            "mcp_error_count": len(errors),
            "network_guard": guard,
            "authority": authority,
            "seed": seed,
            "assertions": {
                "real_model": bool(run.get("actual_invocation_observed")),
                "completed": run.get("status") == "completed",
                "request_replan_observed": "request_replan" in measurement["tool_sequence"],
                "proposal_contract_present": bool(
                    semantic and semantic.get("proposal_contract_version")
                    == "hermes-replan-proposal-view.v1"
                ),
                "semantic_replan_present": semantic is not None,
                "native_event_stream_nonempty": bool(run.get("native_event_stream")),
                "loopback_guard_installed": any(
                    entry.get("event") == "guard_installed" for entry in guard
                ),
                "no_non_loopback_connection_attempt": not any(
                    entry.get("event") == "blocked_non_loopback" for entry in guard
                ),
                "no_mcp_errors": not errors,
                **authority,
            },
        }
        prefix = output / f"R10-{variant}-trial-{trial}"
        _save_json(prefix.with_suffix(".json"), item)
        _save_json(prefix.with_name(prefix.name + "-measurement.json"), measurement)
        _save_json(prefix.with_name(prefix.name + "-post-success-reads.json"), post_success)
        _save_json(prefix.with_name(prefix.name + "-semantic.json"), semantic or {})
        _save_json(prefix.with_name(prefix.name + "-network-guard.json"), guard)
        _save_json(prefix.with_name(prefix.name + "-native-events.json"), run.get("native_event_stream") or [])
        prefix.with_name(prefix.name + "-chronology.json").write_text(
            json.dumps(trace, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        return item
    finally:
        if arm:
            _stop_arm(arm)


def _stats(trials: list[dict[str, Any]]) -> dict[str, Any]:
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
        result[name] = {
            "values": values,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "median": values[len(values) // 2] if values else None,
        }
    return result


def _acceptance(baseline: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    bm, vm = baseline["stats"], variant["stats"]
    safe = all(
        all(item.get("assertions", {}).get(name) for name in (
            "real_model", "completed", "request_replan_observed",
            "proposal_contract_present", "semantic_replan_present",
            "native_event_stream_nonempty", "loopback_guard_installed",
            "no_non_loopback_connection_attempt", "no_mcp_errors",
            "no_mutation_tool", "journey_authority_unchanged",
            "no_booking_commitment_payment_mutation",
        ))
        for item in variant["trials"]
    )
    lower = lambda field: (
        vm[field]["median"] is not None and bm[field]["median"] is not None
        and vm[field]["median"] < bm[field]["median"]
    )
    non_regressed = (
        vm["mcp_call_count"]["median"] is not None
        and bm["mcp_call_count"]["median"] is not None
        and vm["mcp_call_count"]["median"] <= bm["mcp_call_count"]["median"]
    )
    semantic_match = all(
        item.get("semantic_replan", {}).get("proposal_contract_version")
        == "hermes-replan-proposal-view.v1"
        for item in variant["trials"]
    )
    result = {
        "safe": safe,
        "semantic_invariants_present": semantic_match,
        "median_total_tokens_improved": lower("total_tokens"),
        "median_mcp_response_bytes_decreased": lower("mcp_response_bytes"),
        "median_mcp_call_count_not_regressed": non_regressed,
        "median_post_success_list_replans_decreased": lower("post_success_list_replans"),
        "median_redundant_post_success_list_replans_decreased": lower("redundant_post_success_list_replans"),
    }
    result["decision"] = "ACCEPTED" if all(result.values()) else "REJECTED"
    return result


def run(output: Path, trials: int = 3) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    source = clean_receipt()
    hermes_home = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
    hermes_bin = hermes_home / "hermes-agent" / ".venv" / "Scripts" / "hermes.exe"
    hermes_python = hermes_home / "hermes-agent" / ".venv" / "Scripts" / "python.exe"
    profile_config = hermes_home / "profiles" / PROFILE_NAME / "config.yaml"
    profile = _read_profile(hermes_python, profile_config)
    provider_key = _provider_key()
    if not provider_key:
        result = {
            "result": "BLOCKED", "scenario_id": SCENARIO_ID,
            "exact_blockers": ["MODEL_NOT_CONFIGURED"], "source": source,
        }
        _save_json(output / "R10-RESULT.json", result)
        return result
    temp_root = Path(tempfile.mkdtemp(prefix="citynexus-hermes-r10-"))
    try:
        variants: dict[str, dict[str, Any]] = {}
        for variant in VARIANTS:
            trial_rows = [
                _run_trial(temp_root, hermes_bin, hermes_python, profile, provider_key,
                           variant, number, output)
                for number in range(1, trials + 1)
            ]
            variants[variant] = {"trials": trial_rows, "stats": _stats(trial_rows)}
            _save_json(output / f"R10-{variant}-trials.json", variants[variant])
        variants["r10-guided"]["acceptance"] = _acceptance(
            variants["baseline"], variants["r10-guided"]
        )
        baseline_failures = []
        for item in variants["baseline"]["trials"]:
            failed = [name for name, passed in item.get("assertions", {}).items() if not passed]
            if failed:
                baseline_failures.append(f"baseline-trial-{item.get('trial')}:" + ",".join(failed))
        result = {
            "result": "PASS" if not baseline_failures else "BLOCKED",
            "scenario_id": SCENARIO_ID,
            "source": {
                "pre": source, "post": clean_receipt(),
                "head": git("rev-parse", "HEAD"), "parent": git("rev-parse", "HEAD^"),
            },
            "runtime": {
                "profile": PROFILE_NAME, "provider": profile["provider"],
                "model": profile["model"], "mcp_tools": profile["tool_allowlist"],
                "autonomy": "PLAN_ONLY", "p7": False,
            },
            "variants": {
                name: {
                    "stats": value["stats"],
                    "acceptance": value.get("acceptance"),
                    "trials": len(value["trials"]),
                }
                for name, value in variants.items()
            },
            "exact_blockers": baseline_failures,
            "optimization_decision": variants["r10-guided"]["acceptance"]["decision"],
            "variant_rejection_reasons": {
                name: [
                    f"trial-{item.get('trial')}:" + ",".join(
                        key for key, passed in item.get("assertions", {}).items() if not passed
                    )
                    for item in value["trials"]
                    if any(not passed for passed in item.get("assertions", {}).values())
                ]
                for name, value in variants.items() if name != "baseline"
            },
            "model_runs": [
                {
                    "variant": name, "trial": item.get("trial"), "run_id": item.get("run_id"),
                    "mission_id": item.get("mission_id"), "session_id": item.get("session_id"),
                    "status": item.get("status"), "usage": item.get("usage"),
                    "mcp_call_count": item.get("mcp_call_count"),
                    "native_event_stream_event_count": item.get("native_event_stream_event_count"),
                }
                for name, value in variants.items() for item in value["trials"]
            ],
        }
        _save_json(output / "R10-RESULT.json", result)
        _save_json(output / "R10-profile-contract.json", {
            "profile": PROFILE_NAME, "provider": profile["provider"],
            "model": profile["model"], "tool_allowlist": profile["tool_allowlist"],
            "disabled_toolsets": profile["disabled_toolsets"], "resources": profile["resources"],
            "prompts": profile["prompts"], "p7": False,
        })
        (output / "R10-reproduction.md").write_text(
            "# Hermes R10 reproduction\n\n"
            "    $env:PYTHONPATH='.'\n"
            "    uv run --project backend python scripts/hermes_r10_tool_planning_probe.py --evidence-dir C:/path/to/R10-evidence --trials 3\n\n"
            "The baseline and R10-guided arms use the same natural-language task and fresh disposable SQLite state. The experimental change is limited to server-owned MCP tool descriptions. The runner records native Hermes events, MCP chronology, provider usage, semantic proposal invariants, post-success list_replans reads, and PLAN_ONLY authority state.\n",
            encoding="utf-8",
        )
        return result
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=3, choices=range(3, 6))
    args = parser.parse_args()
    result = run(args.evidence_dir, args.trials)
    print(json.dumps({
        "result": result.get("result"),
        "evidence_dir": str(args.evidence_dir),
        "optimization_decision": result.get("optimization_decision"),
        "exact_blockers": result.get("exact_blockers", []),
    }, ensure_ascii=False))
    return 0 if result.get("result") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
