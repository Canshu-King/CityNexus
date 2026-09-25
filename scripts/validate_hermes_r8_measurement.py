from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


EXPECTED_TOOLS = {
    "inspect_journey", "inspect_twin", "list_replans", "search_city_services",
    "request_replan", "accept_replan", "replace_activity", "reschedule_activity",
    "create_booking", "cancel_refundable_booking", "request_commitment_change",
}
FORBIDDEN_TOOLS = {
    "accept_replan", "replace_activity", "reschedule_activity", "create_booking",
    "cancel_refundable_booking", "request_commitment_change",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _fail(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_dir", type=Path)
    args = parser.parse_args()
    root = args.evidence_dir
    errors: list[str] = []
    result = _load(root / "R8-RESULT.json")
    table = _load(root / "R8-context-cost-table.json")
    profile = _load(root / "R8-profile-contract.json")
    chronology = _load(root / "R8-mcp-chronology.json")
    native_path = root / "R8-native-events.jsonl"

    source = result.get("source", {})
    pre = source.get("pre", {})
    post = source.get("post", {})
    _fail(errors, result.get("result") == "PASS", "R8 result is not PASS")
    _fail(errors, bool(result.get("run", {}).get("actual_invocation_observed")), "real model invocation not observed")
    _fail(errors, pre.get("porcelain") == "" and post.get("porcelain") == "", "source was not clean before and after")
    _fail(errors, pre.get("head") == post.get("head") == source.get("head"), "source HEAD changed during run")
    _fail(errors, bool(native_path.is_file()) and native_path.stat().st_size > 0, "native event stream missing")
    _fail(errors, profile.get("p7") is False and result.get("runtime", {}).get("p7") is False, "P7 is not explicitly false")
    _fail(errors, profile.get("tool_allowlist") and set(profile["tool_allowlist"]) == EXPECTED_TOOLS, "MCP tool surface mismatch")
    _fail(errors, profile.get("resources") is False and profile.get("prompts") is False, "MCP resources/prompts are not disabled")

    calls = [item for item in chronology if item.get("kind") in {"mcp.request", "mcp.response", "mcp.error"}]
    response_tools = [item.get("tool_name") for item in calls if item.get("kind") == "mcp.response"]
    request_tools = [item.get("tool_name") for item in calls if item.get("kind") == "mcp.request"]
    _fail(errors, bool(calls), "MCP chronology is empty")
    _fail(errors, not (set(response_tools) & FORBIDDEN_TOOLS), "authoritative mutation tool observed")
    _fail(errors, set(request_tools).issubset(EXPECTED_TOOLS), "chronology contains tool outside current surface")
    _fail(errors, all(isinstance(item.get("request"), dict) for item in calls if item.get("kind") == "mcp.request"), "request payload missing")
    _fail(errors, all(int(item.get("response_serialized_bytes") or 0) > 0 for item in calls if item.get("kind") == "mcp.response"), "response byte measurement missing")

    per_call = table.get("per_call", [])
    _fail(errors, len(per_call) == len([item for item in calls if item.get("kind") == "mcp.request"]), "per-call measurement does not cover every MCP request")
    _fail(errors, all(int(item.get("request_json_bytes") or 0) > 0 for item in per_call), "request JSON bytes not measured")
    _fail(errors, all(int(item.get("response_json_bytes") or 0) > 0 for item in per_call if item.get("response_summary") is not None), "response JSON bytes not measured")
    _fail(errors, all(int(per_call[index].get("cumulative_context_bytes_proxy") or 0) >= int(per_call[index - 1].get("cumulative_context_bytes_proxy") or 0) for index in range(1, len(per_call))), "context proxy is not cumulative")
    _fail(errors, isinstance(table.get("ranked_context_cost_table"), list), "ranked context table missing")
    _fail(errors, table.get("model_usage", {}).get("total_tokens") is not None, "provider token usage missing")

    authority = result.get("authority_before_after", {})
    before = authority.get("before", {})
    after = authority.get("after", {})
    _fail(errors, before.get("journey") == after.get("journey"), "Journey authority changed")
    _fail(errors, before.get("bookings") == after.get("bookings"), "booking state changed")
    _fail(errors, before.get("commitments") == after.get("commitments"), "commitment state changed")
    _fail(errors, before.get("payments") == after.get("payments"), "payment state changed")

    forbidden_names = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if re.search(r"(?i)(^\.env($|\.)|\.sqlite(?:3)?$|\.db$|\.wal$|\.shm$|\.pyc$|[\\/]__pycache__[\\/]|id_(rsa|dsa|ecdsa|ed25519)|\.(pem|key|p12|pfx)$)", str(path)):
            forbidden_names.append(str(path.relative_to(root)))
    _fail(errors, not forbidden_names, "forbidden credential/database/cache file present")

    output = {
        "result": "PASS" if not errors else "FAIL",
        "errors": errors,
        "derived": {
            "source_head": source.get("head"),
            "source_pre_clean": pre.get("porcelain") == "",
            "source_post_clean": post.get("porcelain") == "",
            "real_model_invocation": bool(result.get("run", {}).get("actual_invocation_observed")),
            "mcp_request_count": len(request_tools),
            "mcp_response_tools": response_tools,
            "mutation_tools_observed": sorted(set(response_tools) & FORBIDDEN_TOOLS),
            "ranked_context_cost_table": table.get("ranked_context_cost_table", []),
            "provider_model": {"provider": result.get("runtime", {}).get("provider"), "model": result.get("runtime", {}).get("model")},
            "authority_unchanged": before.get("journey") == after.get("journey") and before.get("bookings") == after.get("bookings") and before.get("commitments") == after.get("commitments") and before.get("payments") == after.get("payments"),
            "forbidden_names": forbidden_names,
        },
    }
    (root / "independent-validator.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
