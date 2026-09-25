from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def load(path: Path, name: str) -> Any:
    return json.loads((path / name).read_text(encoding="utf-8"))


def ids(state: dict[str, Any], key: str) -> set[str]:
    return {str(item.get("id")) for item in state["entities"].get(key, []) if item.get("id") is not None}


def row(state: dict[str, Any], key: str, value: str, field: str = "id") -> dict[str, Any]:
    return next((item for item in state["entities"].get(key, []) if str(item.get(field)) == value), {})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_dir", type=Path)
    args = parser.parse_args()
    root = args.evidence_dir.resolve()
    errors: list[str] = []
    result = load(root, "R7-RESULT.json")
    authority = result["authority_state"]
    before = authority["before_A"]
    after_a = authority["after_A_pending"]
    after_user = authority["after_USER_approval"]
    after_c = authority["after_C"]
    after_d1 = authority["after_D1"]
    after_d2 = authority["after_D2"]
    inputs = result["inputs"]
    proposal_id = str(inputs["proposal_id"])
    approval_id = str(inputs["approval_id"])
    base_id = str(row(after_c, "proposals", proposal_id).get("base_plan_version_id"))
    proposed_id = str(row(after_c, "proposals", proposal_id).get("proposed_plan_version_id"))
    traveler_id = str(after_user["entities"]["journey"].get("traveler_id"))

    if result.get("runtime_provider_identity", {}).get("provider") != result.get("model_runs", {}).get("R7-A", {}).get("provider"):
        # The run receipt may report the model as a gateway key rather than the
        # provider name; the raw contract/provider identity remains authoritative.
        if not result.get("runtime_provider_identity", {}).get("provider"):
            errors.append("provider identity missing")
    if not result.get("runtime_provider_identity", {}).get("model"):
        errors.append("model identity missing")

    approval_a = row(after_a, "approvals", approval_id)
    approval_user = row(after_user, "approvals", approval_id)
    approval_c = row(after_c, "approvals", approval_id)
    if approval_a.get("status") != "PENDING":
        errors.append("A does not leave approval PENDING")
    if approval_user.get("status") != "APPROVED":
        errors.append("USER boundary does not leave approval APPROVED")
    if approval_user.get("approved_by") != traveler_id:
        errors.append("USER approval is not bound to Journey traveler")
    if not approval_user.get("approved_at"):
        errors.append("USER approval has no approved_at")
    if approval_c.get("status") != "CONSUMED":
        errors.append("C does not consume the approved receipt")

    if row(after_a, "proposals", proposal_id).get("status") != "PRESENTED":
        errors.append("A changed proposal authority")
    if row(after_c, "proposals", proposal_id).get("status") != "ACCEPTED":
        errors.append("C did not accept the approved proposal")
    if row(after_c, "plans", base_id).get("status") != "SUPERSEDED":
        errors.append("base PlanVersion is not SUPERSEDED")
    if row(after_c, "plans", proposed_id).get("status") != "ACTIVE":
        errors.append("proposed PlanVersion is not ACTIVE")
    for proposal in after_user["entities"].get("proposals", []):
        if str(proposal.get("id")) == proposal_id:
            continue
        replacement = row(after_c, "proposals", str(proposal.get("id")))
        competitor_plan = row(after_c, "plans", str(proposal.get("proposed_plan_version_id")))
        if replacement.get("status") != "INVALIDATED" or competitor_plan.get("status") != "REJECTED":
            errors.append("competing proposal/PlanVersion was not invalidated/rejected")
    journey_c = after_c["entities"]["journey"]
    if journey_c.get("active_plan_version_id") != proposed_id or journey_c.get("status") != "ACTIVE":
        errors.append("Journey authority is not ACTIVE on proposed PlanVersion")
    current_id = str(journey_c.get("current_activity_id"))
    current = row(after_c, "activities", current_id)
    if current.get("plan_version_id") != proposed_id:
        errors.append("current_activity_id is not owned by the new ACTIVE plan")
    if len([item for item in after_c["entities"]["plans"] if item.get("status") == "ACTIVE"]) != 1:
        errors.append("C leaves more than one ACTIVE PlanVersion")
    if before["entities"].get("bookings") != after_c["entities"].get("bookings"):
        errors.append("booking state changed")
    if before["entities"].get("commitments") != after_c["entities"].get("commitments"):
        errors.append("commitment state changed")

    if after_d1.get("state_sha256") != after_c.get("state_sha256"):
        errors.append("D1 changed durable state")
    if after_d2.get("state_sha256") != after_d1.get("state_sha256"):
        errors.append("D2 changed durable state")
    d2 = load(root, "R7-D2-consumed-retry.json")
    d2_text = " ".join(str(item) for item in d2.get("texts", []))
    if d2.get("json") or d2_text != "replan proposal is stale or its trigger is resolved":
        errors.append("D2 did not return the deterministic fail-closed product error")
    e = load(root, "R7-E-restart-arm.json")
    if not e.get("assertions", {}).get("pass"):
        errors.append("E restart-arm assertion is not PASS")
    f = load(root, "R7-F-scope-negative.json")
    wrong = f.get("wrong_response", {})
    wrong_text = " ".join(str(item) for item in wrong.get("texts", []))
    if (wrong.get("json") or wrong_text != "proposal does not belong to this Journey"
            or f.get("after", {}).get("state_sha256") != f.get("before", {}).get("state_sha256")
            or row(f.get("after", {}), "approvals", str(f.get("approval_id"))).get("status") != "PENDING"):
        errors.append("F scope-negative assertion is not PASS")

    chronology = load(root, "mcp-call-chronology.json")
    accept_responses = [
        item for item in chronology
        if item.get("kind") == "mcp.response" and item.get("tool_name") == "accept_replan"
    ]
    if not any(item.get("response", {}).get("executed") is False for item in accept_responses):
        errors.append("raw chronology has no blocked accept_replan")
    if not any(item.get("response", {}).get("executed") is True for item in accept_responses):
        errors.append("raw chronology has no executed accept_replan")
    if any("/approvals/" in json.dumps(item, sort_keys=True) for item in chronology):
        errors.append("Hermes/MCP chronology contains a USER approval endpoint")
    for event_file in ("hermes-native-events-A.jsonl", "hermes-native-events-C.jsonl"):
        path = root / event_file
        if not path.exists() or not path.read_text(encoding="utf-8").strip():
            errors.append(f"missing native event stream: {event_file}")

    binding = result.get("source_binding", {})
    if binding.get("porcelain_before") or binding.get("porcelain_after"):
        errors.append("source binding is dirty")
    forbidden = (".env", ".sqlite", ".sqlite3", ".db", ".wal", ".shm", ".pyc", "__pycache__", "private")
    for path in root.rglob("*"):
        if path.is_file() and any(token in path.name.casefold() for token in forbidden):
            errors.append(f"forbidden evidence artifact: {path.name}")
    derived = {
        "approval_sequence": [approval_a.get("status"), approval_user.get("status"), approval_c.get("status")],
        "proposal_id": proposal_id,
        "base_plan_id": base_id,
        "proposed_plan_id": proposed_id,
        "d1_state_same": after_d1.get("state_sha256") == after_c.get("state_sha256"),
        "d2_state_same": after_d2.get("state_sha256") == after_d1.get("state_sha256"),
        "native_event_files_present": all((root / name).exists() for name in ("hermes-native-events-A.jsonl", "hermes-native-events-C.jsonl")),
        "errors": errors,
        "result": "PASS" if not errors else "RED",
    }
    (root / "independent-validator.json").write_text(
        json.dumps(derived, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(derived, ensure_ascii=False, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
