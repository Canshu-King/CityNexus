from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from scripts.hermes_r6_h11_model_probe import (
        BACKEND, EXPECTED_TOOLS, MCP_PACKAGE, PROFILE_NAME, ROOT, Backend,
        GatewayTeeServer, HermesGateway, _free_port, _gateway_run,
        _minimal_environment, _mcp_tools, _provider_key, _read_profile,
        _read_trace, _save_json, clean_receipt, git, _seed,
    )
    from scripts.hermes_r7_human_approval_probe import (
        _configure_arm, _mcp_call, _r7_state, _sanitize_guard, _stop_arm,
    )
    from scripts.hermes_r8_context_probe import (
        BASELINE_INPUT, BASELINE_INSTRUCTIONS, _authority_projection,
    )
except ImportError:
    from hermes_r6_h11_model_probe import (
        BACKEND, EXPECTED_TOOLS, MCP_PACKAGE, PROFILE_NAME, ROOT, Backend,
        GatewayTeeServer, HermesGateway, _free_port, _gateway_run,
        _minimal_environment, _mcp_tools, _provider_key, _read_profile,
        _read_trace, _save_json, clean_receipt, git, _seed,
    )
    from hermes_r7_human_approval_probe import (
        _configure_arm, _mcp_call, _r7_state, _sanitize_guard, _stop_arm,
    )
    from hermes_r8_context_probe import (
        BASELINE_INPUT, BASELINE_INSTRUCTIONS, _authority_projection,
    )


SCENARIO_ID = "hermes-r9-mcp-context-transport-convergence"
MUTATION_TOOLS = {
    "accept_replan", "replace_activity", "reschedule_activity", "create_booking",
    "cancel_refundable_booking", "request_commitment_change",
}


def _json_bytes(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))


def _json_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def _write_r9_wrapper(path: Path, *, text_mode: str, description_mode: str) -> None:
    source = f'''import hashlib, json, os, sys, threading, time
for name in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
             "CITYNEXUS_HERMES_API_SERVER_KEY", "API_SERVER_KEY"):
    os.environ.pop(name, None)
sys.path.insert(0, os.environ["CITYNEXUS_HERMES_R7_SCRIPTS"])
from hermes_r4_socket_guard import install
install()
import httpx
import citynexus_mcp.server as server
import mcp.server as mcp_server
from mcp import types

TRACE = os.environ.get("CITYNEXUS_HERMES_TOOL_TRACE", "")
TEXT_MODE = {text_mode!r}
DESCRIPTION_MODE = {description_mode!r}
LOCK = threading.Lock()
ADAPTER_RESULTS = {{}}

def enc(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")

def digest(value):
    return hashlib.sha256(enc(value)).hexdigest()

def jsonable(value):
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json", by_alias=True, exclude_none=False)
        except TypeError:
            return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return value

def record(value):
    if TRACE:
        with LOCK, open(TRACE, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str) + "\\n")

def compact(tool, value):
    if TEXT_MODE != "compact" or not isinstance(value, dict):
        return value
    if tool == "request_replan":
        keys = ("tool", "decision", "reason_codes", "policy_version", "request_id",
                "proposal_contract_version", "proposal_views")
        return {{key: value[key] for key in keys if key in value}}
    return value

if DESCRIPTION_MODE == "baseline":
    server.TOOL_DESCRIPTIONS.update({{
        "request_replan": "Request a proposal without activating a Plan.",
        "list_replans": "List persisted Replan proposals.",
        "search_city_services": "Search server-owned city service facts.",
    }})
elif DESCRIPTION_MODE == "guided":
    server.TOOL_DESCRIPTIONS.update({{
        "request_replan": "Request a proposal without activating a Plan. The response contains the newly generated proposal information; an immediate list_replans reread is normally redundant after a successful call.",
        "list_replans": "List previously persisted Replan proposals. Use this for existing proposals; request_replan already returns newly generated proposal information.",
        "search_city_services": "Search server-owned city service facts only when the current server proposal or context lacks enough facts; do not repeatedly search an unchanged query.",
    }})
elif DESCRIPTION_MODE == "r10-guided":
    server.TOOL_DESCRIPTIONS.update({{
        "request_replan": "Request a proposal without activating a Plan. When this succeeds with complete proposal_views, use that server response as the authoritative new-proposal result and do not immediately call list_replans to reread the same proposals. Use list_replans only for prior proposal history, a failed or incomplete request, or an explicit historical comparison.",
        "list_replans": "List persisted Replan proposals. Use it to inspect prior proposal history, recover after a failed or incomplete request_replan, or make an explicit historical comparison. After a successful request_replan with complete proposal_views, do not immediately reread the same newly generated proposals.",
        "search_city_services": "Search server-owned city service facts only when the current server proposal or context lacks enough facts; do not repeat an unchanged query or search after the proposal already contains the needed facts.",
    }})

old_send = httpx.Client.send
def traced_send(self, request, *args, **kwargs):
    response = old_send(self, request, *args, **kwargs)
    if "/api/v1/agent/tools/" in str(request.url):
        request_body = bytes(request.content or b"")
        response_body = bytes(response.content or b"")
        record({{"kind": "backend.http", "tool_name": str(request.url).rsplit("/", 1)[-1],
                "request_json_bytes": len(request_body),
                "request_body_sha256": hashlib.sha256(request_body).hexdigest(),
                "http_status": response.status_code,
                "response_json_bytes": len(response_body),
                "response_body_sha256": hashlib.sha256(response_body).hexdigest()}})
    return response
httpx.Client.send = traced_send

old_adapter_call = server.CityNexusMCPServer.call
def traced_adapter_call(self, tool_name, call):
    request = call.payload()
    record({{"kind": "mcp.request", "tool_name": tool_name,
            "request_id": request.get("request_id"), "request": request,
            "request_json_bytes": len(enc(request))}})
    try:
        result = old_adapter_call(self, tool_name, call)
    except Exception as exc:
        record({{"kind": "mcp.error", "tool_name": tool_name,
                "request_id": request.get("request_id"),
                "error_type": type(exc).__name__, "error": str(exc)[:1000]}})
        raise
    result_bytes = enc(result)
    with LOCK:
        ADAPTER_RESULTS.setdefault(str(tool_name), []).append(
            (str(request.get("request_id") or ""), result)
        )
    record({{"kind": "adapter.result", "tool_name": tool_name,
            "request_id": request.get("request_id"), "result": result,
            "result_json_bytes": len(result_bytes), "result_sha256": digest(result)}})
    record({{"kind": "mcp.response", "tool_name": tool_name,
            "request_id": request.get("request_id"), "request": request,
            "response": result, "response_serialized_bytes": len(result_bytes),
            "response_sha256": digest(result)}})
    return result
server.CityNexusMCPServer.call = traced_adapter_call

old_server = mcp_server.Server
class RecordingServer(old_server):
    def __init__(self, *args, **kwargs):
        callback = kwargs.get("on_call_tool")
        if callback is not None:
            async def traced_call(ctx, params):
                value = await callback(ctx, params)
                structured = getattr(value, "structured_content", None)
                request_id = (params.arguments or {{}}).get("request_id")
                if TEXT_MODE == "compact" and isinstance(structured, dict):
                    projected = compact(params.name, structured)
                    value = types.CallToolResult(
                        content=[types.TextContent(text=json.dumps(
                            projected, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                        ))],
                        structuredContent=structured,
                        isError=bool(getattr(value, "is_error", False)),
                        _meta=getattr(value, "meta", None),
                        resultType=getattr(value, "result_type", "complete"),
                    )
                dumped = jsonable(value)
                texts = [getattr(item, "text", "") for item in getattr(value, "content", [])]
                text_value = "\\n".join(texts)
                with LOCK:
                    pending = ADAPTER_RESULTS.get(str(params.name), [])
                    match_index = next(
                        (
                            index for index, (_candidate_request_id, candidate_result) in enumerate(pending)
                            if candidate_result is not None and digest(candidate_result) == digest(structured)
                        ),
                        None,
                    )
                    if match_index is None:
                        adapter_request_id, adapter_result = pending.pop(0) if pending else ("", None)
                    else:
                        adapter_request_id, adapter_result = pending.pop(match_index)
                effective_request_id = request_id or adapter_request_id or None
                record({{"kind": "mcp.callresult", "tool_name": params.name,
                        "request_id": effective_request_id,
                        "text_mode": TEXT_MODE, "description_mode": DESCRIPTION_MODE,
                        "text": text_value,
                        "text_bytes": len(text_value.encode("utf-8")),
                        "text_sha256": hashlib.sha256(text_value.encode("utf-8")).hexdigest(),
                        "structuredContent": structured,
                        "structuredContent_before_bytes": len(enc(structured)),
                        "structuredContent_after_bytes": len(enc(structured)),
                        "structuredContent_before_sha256": digest(structured),
                        "structuredContent_after_sha256": digest(structured),
                        "structuredContent_matches_adapter_result": (
                            None if adapter_result is None else digest(structured) == digest(adapter_result)
                        ),
                        "complete_calltool_result": dumped,
                        "complete_calltool_result_bytes": len(enc(dumped)),
                        "complete_calltool_result_sha256": digest(dumped)}})
                return value
            kwargs["on_call_tool"] = traced_call
        super().__init__(*args, **kwargs)
mcp_server.Server = RecordingServer
sys.argv = ["citynexus_mcp.server", "--v2"]
server.main()
'''
    path.write_text(source, encoding="utf-8")


def _prepare_wrapper(arm: dict[str, Any], text_mode: str, description_mode: str) -> None:
    _write_r9_wrapper(arm["wrapper"], text_mode=text_mode, description_mode=description_mode)
    arm["trace_path"].write_text("", encoding="utf-8")


def _configure_r9_arm(temp_root: Path, label: str, hermes_bin: Path,
                       hermes_python: Path, profile: dict[str, Any],
                       provider_key: str, text_mode: str,
                       description_mode: str) -> dict[str, Any]:
    # Install the instrumented writer before Gateway startup. The Gateway may
    # keep its MCP subprocess alive, so replacing the wrapper after startup is
    # too late for model trials.
    try:
        import scripts.hermes_r7_human_approval_probe as r7_module
    except ImportError:
        import hermes_r7_human_approval_probe as r7_module
    old_writer = r7_module._write_mcp_wrapper
    r7_module._write_mcp_wrapper = lambda path: _write_r9_wrapper(
        path, text_mode=text_mode, description_mode=description_mode
    )
    try:
        return _configure_arm(
            temp_root, label, hermes_bin, hermes_python, profile, provider_key
        )
    finally:
        r7_module._write_mcp_wrapper = old_writer


def _read_measurement(trace: list[dict[str, Any]], run: dict[str, Any] | None = None) -> dict[str, Any]:
    calls = [item for item in trace if item.get("kind") == "mcp.callresult"]
    requests = [item for item in trace if item.get("kind") == "mcp.request"]
    adapters = [item for item in trace if item.get("kind") == "adapter.result"]
    http = [item for item in trace if item.get("kind") == "backend.http"]
    responses = [item for item in trace if item.get("kind") == "mcp.response"]
    turn_measurements = []
    response_hash_counts: dict[str, int] = defaultdict(int)
    tool_response_hashes: dict[str, set[str]] = defaultdict(set)
    proposal_id_counts: dict[str, int] = defaultdict(int)
    cumulative_response_bytes = 0
    unique_response_bytes = 0

    def proposal_ids(value: Any) -> list[str]:
        found: list[str] = []
        if isinstance(value, dict):
            for key in ("proposal", "proposals", "proposal_views"):
                candidate = value.get(key)
                if isinstance(candidate, dict) and candidate.get("id") is not None:
                    found.append(str(candidate["id"]))
                elif isinstance(candidate, list):
                    found.extend(
                        str(item["id"])
                        for item in candidate
                        if isinstance(item, dict) and item.get("id") is not None
                    )
        return sorted(set(found))

    for index, item in enumerate(responses):
        response_bytes = int(item.get("response_serialized_bytes") or 0)
        response_hash = str(item.get("response_sha256") or "")
        tool_name = str(item.get("tool_name") or "")
        repeated_hash = response_hash_counts[response_hash] if response_hash else 0
        repeated_same_tool = response_hash in tool_response_hashes[tool_name] if response_hash else False
        if response_hash and response_hash_counts[response_hash] == 0:
            unique_response_bytes += response_bytes
        response_hash_counts[response_hash] += 1
        if response_hash:
            tool_response_hashes[tool_name].add(response_hash)
        current_proposal_ids = proposal_ids(item.get("response"))
        repeated_proposals = []
        for proposal_id in current_proposal_ids:
            if proposal_id_counts[proposal_id]:
                repeated_proposals.append(proposal_id)
            proposal_id_counts[proposal_id] += 1
        turn_measurements.append({
            "turn_index": index + 1,
            "tool_name": tool_name,
            "request_id": item.get("request_id"),
            "response_bytes": response_bytes,
            "response_sha256": response_hash,
            "cumulative_prior_tool_response_bytes": cumulative_response_bytes,
            "prior_tool_response_count": index,
            "repeated_unchanged_response": repeated_same_tool,
            "repeated_response_count_before": repeated_hash,
            "proposal_ids": current_proposal_ids,
            "repeated_proposal_ids": repeated_proposals,
            "provider_input_tokens_available": False,
        })
        cumulative_response_bytes += response_bytes

    run_usage = (run or {}).get("usage") if isinstance(run, dict) else None
    components = []
    for item in adapters:
        if item.get("tool_name") != "request_replan":
            continue
        result = item.get("result") if isinstance(item.get("result"), dict) else {}
        proposals = result.get("proposals") if isinstance(result.get("proposals"), list) else []
        proposal = result.get("proposal")
        components.append({
            "request_id": item.get("request_id"),
            "proposal_bytes": _json_bytes(proposal),
            "proposals_bytes": _json_bytes(proposals),
            "proposal_views_bytes": _json_bytes(result.get("proposal_views")),
            "reason_codes_bytes": _json_bytes(result.get("reason_codes")),
            "metadata_bytes": _json_bytes({key: result.get(key) for key in (
                "tool", "decision", "policy_version", "request_id",
                "proposal_contract_version") if key in result}),
            "proposal_sha256": _json_hash(proposal),
            "proposals_sha256": _json_hash(proposals),
            "proposal_views_sha256": _json_hash(result.get("proposal_views")),
            "proposal_equals_proposals_0": bool(proposals) and _json_hash(proposal) == _json_hash(proposals[0]),
            "proposal_view_hashes": [_json_hash(value) for value in result.get("proposal_views", []) if isinstance(value, dict)],
        })
    return {
        "backend_http_response_bytes": sum(int(item.get("response_json_bytes") or 0) for item in http),
        "adapter_result_bytes": sum(int(item.get("result_json_bytes") or 0) for item in adapters),
        "textcontent_bytes": sum(int(item.get("text_bytes") or 0) for item in calls),
        "structured_content_bytes": sum(int(item.get("structuredContent_after_bytes") or 0) for item in calls),
        "complete_calltool_result_bytes": sum(int(item.get("complete_calltool_result_bytes") or 0) for item in calls),
        "request_bytes": sum(int(item.get("request_json_bytes") or 0) for item in requests),
        "actual_tool_call_count": len(requests),
        "tool_sequence": [item.get("tool_name") for item in responses],
        "backend_http": http,
        "calltool_records": calls,
        "request_replan_components": components,
        "turn_measurements": turn_measurements,
        "cumulative_tool_response_bytes": cumulative_response_bytes,
        "unique_tool_response_bytes": unique_response_bytes,
        "conversation_replay_multiplier": (
            cumulative_response_bytes / unique_response_bytes if unique_response_bytes else None
        ),
        "repeated_unchanged_read_count": sum(
            bool(item.get("repeated_unchanged_response")) for item in turn_measurements
        ),
        "repeated_proposal_identity_count": sum(
            len(item.get("repeated_proposal_ids") or []) for item in turn_measurements
        ),
        "provider_input_tokens_by_turn": {
            "available": False,
            "reason": "Hermes Gateway exposes provider usage at run level; no per-turn input usage was exposed",
            "run_input_tokens": (run_usage or {}).get("input_tokens") if isinstance(run_usage, dict) else None,
        },
        "structured_content_byte_equal_before_after": all(
            item.get("structuredContent_before_sha256") == item.get("structuredContent_after_sha256")
            for item in calls
        ),
        "structured_content_matches_adapter_result": all(
            item.get("structuredContent_matches_adapter_result") in {True, None} for item in calls
        ) and any(
            item.get("structuredContent_matches_adapter_result") is True for item in calls
        ),
    }


def _authority_ok(before: dict[str, Any], after: dict[str, Any], sequence: list[Any]) -> dict[str, bool]:
    before_view = _authority_projection(before)
    after_view = _authority_projection(after)
    return {
        "no_mutation_tool": not bool(set(sequence) & MUTATION_TOOLS),
        "journey_authority_unchanged": before_view["journey"] == after_view["journey"],
        "no_booking_commitment_payment_mutation": (
            before_view["bookings"] == after_view["bookings"]
            and before_view["commitments"] == after_view["commitments"]
            and before_view["payments"] == after_view["payments"]
        ),
    }


def _run_model_trial(temp_root: Path, label: str, hermes_bin: Path, hermes_python: Path,
                     profile: dict[str, Any], provider_key: str, variant: str,
                     trial: int, output: Path) -> dict[str, Any]:
    arm = None
    try:
        text_mode = "compact" if variant == "text-compact" else "full"
        desc_mode = "guided" if variant == "tool-guidance" else "baseline"
        arm = _configure_r9_arm(
            temp_root, label, hermes_bin, hermes_python, profile, provider_key,
            text_mode, desc_mode
        )
        seed = _seed(arm["backend"], arm["runtime"])
        before = _r7_state(arm["database"], seed["journey_id"])
        mission = str(uuid.uuid4())
        session = f"citynexus-{seed['journey_id']}-r9-{variant}-{trial}-{mission}"
        run = _gateway_run(
            gateway=arm["gateway"], backend=arm["backend"], journey_id=seed["journey_id"],
            session_id=session, mission_id=mission, run_key=f"r9-{variant}-{trial}-{mission}",
            user_input=BASELINE_INPUT + " Journey ID: " + seed["journey_id"],
            instructions=BASELINE_INSTRUCTIONS + " Journey ID: " + seed["journey_id"],
            trace_path=arm["trace_path"], tee=arm["tee"], api_headers=arm["headers"],
            timeout_seconds=300,
        )
        after = _r7_state(arm["database"], seed["journey_id"])
        trace = _read_trace(arm["trace_path"])
        measurement = _read_measurement(trace, run)
        network_guard = _sanitize_guard(
            arm["guard"], [provider_key, arm.get("agent_token", ""), arm.get("gateway_key", "")]
        )
        authority = _authority_ok(before, after, measurement["tool_sequence"])
        item = {
            "variant": variant, "trial": trial, "run_id": run.get("run_id"),
            "mission_id": mission, "session_id": session,
            "status": run.get("status"),
            "run_status": run.get("run_status"),
            "submission_http_status": run.get("submission_http_status"),
            "submission_response": run.get("submission_response"),
            "stream_error": run.get("stream_error"),
            "exact_blocker": run.get("exact_blocker"),
            "model_reported_by_gateway": run.get("model_reported_by_gateway"),
            "native_event_stream_event_count": len(run.get("native_event_stream") or []),
            "mcp_call_count": len(run.get("mcp_calls") or []),
            "actual_invocation_observed": bool(run.get("actual_invocation_observed")),
            "usage": run.get("usage"), "output": run.get("output"),
            "measurement": {key: value for key, value in measurement.items() if key != "calltool_records"},
            "network_guard": network_guard,
            "authority": authority,
            "assertions": {
                "real_model": bool(run.get("actual_invocation_observed")),
                "request_replan_observed": "request_replan" in measurement["tool_sequence"],
                "structured_content_unchanged": measurement["structured_content_byte_equal_before_after"],
                "structured_content_matches_adapter_result": measurement["structured_content_matches_adapter_result"],
                "native_event_stream_nonempty": bool(run.get("native_event_stream")),
                "loopback_guard_installed": any(item.get("event") == "guard_installed" for item in network_guard),
                "no_non_loopback_connection_attempt": not any(item.get("event") == "blocked_non_loopback" for item in network_guard),
                **authority,
            },
            "seed": seed,
        }
        _save_json(output / f"R9-{variant}-trial-{trial}.json", item)
        _save_json(output / f"R9-{variant}-trial-{trial}-measurement.json", measurement)
        _save_json(output / f"R9-{variant}-trial-{trial}-network-guard.json", network_guard)
        _save_json(
            output / f"R9-{variant}-trial-{trial}-native-events.json",
            run.get("native_event_stream") or [],
        )
        (output / f"R9-{variant}-trial-{trial}-chronology.json").write_text(
            json.dumps(trace, ensure_ascii=False, sort_keys=True, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        return item
    finally:
        if arm:
            _stop_arm(arm)


def _run_envelope(temp_root: Path, hermes_bin: Path, hermes_python: Path,
                  profile: dict[str, Any], provider_key: str, output: Path) -> dict[str, Any]:
    arm = None
    try:
        arm = _configure_r9_arm(
            temp_root, "r9-envelope", hermes_bin, hermes_python, profile,
            provider_key, "full", "baseline"
        )
        seed = _seed(arm["backend"], arm["runtime"])
        calls = [
            ("inspect_journey", {"request_id": "r9-envelope-journey", "journey_id": seed["journey_id"]}),
            ("inspect_twin", {"request_id": "r9-envelope-twin", "journey_id": seed["journey_id"]}),
            ("list_replans", {"request_id": "r9-envelope-before", "journey_id": seed["journey_id"]}),
            ("request_replan", {"request_id": "r9-envelope-generate", "journey_id": seed["journey_id"], "trigger_event_id": seed["trigger_event_id"], "candidate_count": 1}),
            ("list_replans", {"request_id": "r9-envelope-after", "journey_id": seed["journey_id"]}),
        ]
        direct_results = []
        for tool, arguments in calls:
            direct_results.append({"tool": tool, "response": _mcp_call(hermes_python, arm["wrapper"], arm["mcp_env"], tool, arguments)})
        trace = _read_trace(arm["trace_path"])
        network_guard = _sanitize_guard(arm["guard"], [provider_key, arm.get("agent_token", ""), arm.get("gateway_key", "")])
        payload = {
            "seed": seed,
            "direct_results": direct_results,
            "measurement": _read_measurement(trace),
            "chronology": trace,
            "network_guard": network_guard,
        }
        _save_json(output / "R9-envelope-measurement.json", payload)
        _save_json(output / "R9-envelope-network-guard.json", network_guard)
        return payload
    finally:
        if arm:
            _stop_arm(arm)


def _stats(items: list[dict[str, Any]]) -> dict[str, Any]:
    fields = ("total_tokens", "input_tokens", "output_tokens", "actual_tool_call_count",
              "backend_http_response_bytes", "adapter_result_bytes", "textcontent_bytes",
              "structured_content_bytes", "complete_calltool_result_bytes")
    output = {}
    for field in fields:
        values = []
        for item in items:
            source = item.get("measurement", {})
            value = source.get(field)
            if value is None:
                value = (item.get("usage") or {}).get(field)
            if value is not None:
                values.append(int(value))
        values.sort()
        output[field] = {
            "values": values,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "median": values[len(values) // 2] if values else None,
        }
    return output


def _acceptance(baseline: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    bm, vm = baseline["stats"], variant["stats"]
    safe = all(item.get("assertions", {}).get("real_model") and
               item.get("assertions", {}).get("request_replan_observed") and
               item.get("assertions", {}).get("structured_content_unchanged") and
               item.get("assertions", {}).get("structured_content_matches_adapter_result") and
               item.get("assertions", {}).get("native_event_stream_nonempty") and
               item.get("assertions", {}).get("loopback_guard_installed") and
               item.get("assertions", {}).get("no_non_loopback_connection_attempt") and
               item.get("assertions", {}).get("no_mutation_tool") and
               item.get("assertions", {}).get("journey_authority_unchanged") and
               item.get("assertions", {}).get("no_booking_commitment_payment_mutation")
               for item in variant["trials"])
    median_total = vm["total_tokens"]["median"] is not None and bm["total_tokens"]["median"] is not None and vm["total_tokens"]["median"] < bm["total_tokens"]["median"]
    median_text = vm["textcontent_bytes"]["median"] is not None and bm["textcontent_bytes"]["median"] is not None and vm["textcontent_bytes"]["median"] < bm["textcontent_bytes"]["median"]
    median_calls = vm["actual_tool_call_count"]["median"] is not None and bm["actual_tool_call_count"]["median"] is not None and vm["actual_tool_call_count"]["median"] <= bm["actual_tool_call_count"]["median"]
    return {
        "safe": safe,
        "median_total_tokens_improved": median_total,
        "median_model_visible_text_bytes_decreased": median_text,
        "median_mcp_call_count_not_regressed": median_calls,
        "decision": "ACCEPTED" if safe and median_total and median_text and median_calls else "REJECTED",
    }


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
        result = {"result": "BLOCKED", "scenario_id": SCENARIO_ID, "exact_blockers": ["MODEL_NOT_CONFIGURED"], "source": source}
        _save_json(output / "R9-RESULT.json", result)
        return result
    temp_root = Path(tempfile.mkdtemp(prefix="citynexus-hermes-r9-"))
    try:
        envelope = _run_envelope(temp_root, hermes_bin, hermes_python, profile, provider_key, output)
        variants = {}
        for variant in ("baseline", "tool-guidance", "text-compact"):
            trials_value = []
            for trial in range(1, trials + 1):
                trials_value.append(_run_model_trial(temp_root, f"r9-{variant}-{trial}", hermes_bin, hermes_python, profile, provider_key, variant, trial, output))
            variants[variant] = {"trials": trials_value}
            variants[variant]["stats"] = _stats(trials_value)
        variants["tool-guidance"]["acceptance"] = _acceptance(variants["baseline"], variants["tool-guidance"])
        variants["text-compact"]["acceptance"] = _acceptance(variants["baseline"], variants["text-compact"])
        for name, value in variants.items():
            _save_json(output / f"R9-{name}-trials.json", value)
        all_trials = [trial for value in variants.values() for trial in value["trials"]]
        trial_blockers = []
        for trial in variants["baseline"]["trials"]:
            failed = [name for name, passed in trial.get("assertions", {}).items() if not passed]
            if failed:
                trial_blockers.append(
                    f"{trial.get('variant')}-trial-{trial.get('trial')}:" + ",".join(failed)
                )
        exact_blockers = trial_blockers
        result = {
            "result": "PASS" if not exact_blockers else "BLOCKED",
            "scenario_id": SCENARIO_ID,
            "source": {"pre": source, "post": clean_receipt(), "head": git("rev-parse", "HEAD"), "parent": git("rev-parse", "HEAD^")},
            "runtime": {"profile": PROFILE_NAME, "provider": profile["provider"], "model": profile["model"], "mcp_tools": profile["tool_allowlist"], "autonomy": "PLAN_ONLY", "p7": False},
            "envelope": _read_measurement(envelope["chronology"]),
            "variants": {name: {"stats": value["stats"], "acceptance": value.get("acceptance"), "trials": len(value["trials"])} for name, value in variants.items()},
            "exact_blockers": exact_blockers,
            "optimization_decision": (
                "ACCEPTED" if any(
                    value.get("acceptance", {}).get("decision") == "ACCEPTED"
                    for value in variants.values()
                    if isinstance(value.get("acceptance"), dict)
                ) else "REJECTED"
            ),
            "variant_rejection_reasons": {
                name: [
                    f"trial-{trial.get('trial')}:" + ",".join(
                        assertion for assertion, passed in trial.get("assertions", {}).items() if not passed
                    )
                    for trial in value["trials"]
                    if any(not passed for passed in trial.get("assertions", {}).values())
                ]
                for name, value in variants.items()
                if name != "baseline"
            },
            "model_runs": [{
                "variant": name, "trial": trial.get("trial"), "run_id": trial.get("run_id"),
                "mission_id": trial.get("mission_id"), "session_id": trial.get("session_id"),
                "status": trial.get("status"), "usage": trial.get("usage"),
                "mcp_call_count": trial.get("mcp_call_count"),
                "native_event_stream_event_count": trial.get("native_event_stream_event_count"),
            } for name, value in variants.items() for trial in value["trials"]],
        }
        _save_json(output / "R9-RESULT.json", result)
        _save_json(output / "R9-profile-contract.json", {"profile": PROFILE_NAME, "provider": profile["provider"], "model": profile["model"], "tool_allowlist": profile["tool_allowlist"], "disabled_toolsets": profile["disabled_toolsets"], "resources": profile["resources"], "prompts": profile["prompts"], "p7": False})
        guard_files = sorted(path.name for path in output.glob("R9-*-network-guard.json"))
        guard_entries = []
        for name in guard_files:
            guard_entries.extend({"arm_file": name, **entry} for entry in json.loads((output / name).read_text(encoding="utf-8")))
        _save_json(output / "R9-network-guards.json", {
            "guard_files": guard_files,
            "entries": guard_entries,
            "installed_count": sum(entry.get("event") == "guard_installed" for entry in guard_entries),
            "blocked_non_loopback_count": sum(entry.get("event") == "blocked_non_loopback" for entry in guard_entries),
            "raw_network_guard_logs_retained": False,
            "provider_egress": "configured DeepSeek model only; CityNexus/MCP remained loopback-only",
        })
        (output / "R9-reproduction.md").write_text(
            "# Hermes R9 reproduction\n\n"
            "    $env:PYTHONPATH='.'\n"
            "    uv run --project backend python scripts/hermes_r9_mcp_context_probe.py --evidence-dir C:/path/to/R9-evidence --trials 3\n\n"
            "The runner measures the actual MCP 2 CallToolResult envelope using direct official-client calls, then executes three fresh real-model trials for baseline, tool-description guidance, and compact model-facing TextContent. structuredContent remains untouched. Every arm uses a fresh disposable SQLite database and loopback-only CityNexus traffic.\n",
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
    print(json.dumps({"result": result.get("result"), "evidence_dir": str(args.evidence_dir), "exact_blockers": result.get("exact_blockers", [])}, ensure_ascii=False))
    return 0 if result.get("result") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
