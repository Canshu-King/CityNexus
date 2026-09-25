from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
MCP_PACKAGE = ROOT / "agent-mcp"
LAUNCHER = ROOT / "scripts" / "hermes_r4_launch.py"
sys.path.insert(0, str(ROOT / "scripts"))
import hermes_r4_contract_probe as r4  # noqa: E402

RUN_ID = str(uuid.uuid4())
SCENARIO_ID = "hermes-r5-request-replan-idempotency-upgrade"
REQUEST_ID = "hermes-r5-legacy-cache-0001"
AGENT_ID = "hermes-test"
SERVER_PRINCIPAL_ID = "hermes-r4-server-principal"


def agent_key(kind: str, agent_id: str, request_id: str) -> str:
    # _agent_key hashes only its variadic parts; ``kind`` is used as the key
    # prefix, not as part of the digest.
    material = "|".join((agent_id, request_id))
    return f"agent.{kind}:{hashlib.sha256(material.encode()).hexdigest()}"


def clean_state() -> dict[str, str]:
    return {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "status_porcelain_v1": subprocess.check_output(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=ROOT, text=True
        ),
    }


def table_count(path: Path, table: str) -> int:
    with sqlite3.connect(path) as connection:
        return int(connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def identity_state(path: Path, journey_id: str) -> dict[str, Any]:
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        journey = connection.execute(
            "SELECT id, status, active_plan_version_id, current_activity_id FROM journeys WHERE id = ?",
            (journey_id,),
        ).fetchone()
        state: dict[str, Any] = {"journey": dict(journey) if journey else None}
        for table in ("replan_proposals", "plan_versions", "events"):
            columns = {item[1] for item in connection.execute(f'PRAGMA table_info("{table}")')}
            if "journey_id" not in columns:
                state[table] = []
                continue
            rows = connection.execute(
                f'SELECT * FROM "{table}" WHERE journey_id = ? ORDER BY id', (journey_id,)
            ).fetchall()
            state[table] = [dict(row) for row in rows]
        state["idempotency_keys"] = [
            dict(row) for row in connection.execute(
                "SELECT key, operation, request_hash FROM idempotency_keys ORDER BY key"
            ).fetchall()
        ]
        return state


def tracked_binding() -> dict[str, Any]:
    paths = (
        "backend/app/agent/gateway.py",
        "backend/tests/test_hermes_r5_cached_replan_compatibility.py",
        "agent-mcp/citynexus_mcp/schemas.py",
        "agent-mcp/citynexus_mcp/client.py",
        "agent-mcp/tests/test_client_error_detail.py",
        "scripts/hermes_r5_idempotency_probe.py",
        "scripts/run_hermes_r5_captured.py",
        "scripts/package_hermes_r5_review.py",
        "scripts/validate_hermes_r5_package.py",
        "scripts/reproduce_hermes_r5.ps1",
        "reports/hermes/HERMES_R5_SCENARIO.md",
        "reports/hermes/HERMES_R5_REPORT.md",
    )
    result = {}
    for relative in paths:
        tracked = subprocess.check_output(
            ["git", "rev-parse", f"HEAD:{relative}"], cwd=ROOT, text=True
        ).strip()
        worktree = subprocess.check_output(
            ["git", "hash-object", relative], cwd=ROOT, text=True
        ).strip()
        result[relative] = {"tracked_blob": tracked, "worktree_blob": worktree, "matches": tracked == worktree}
    return result


def idempotency_row(path: Path, key: str) -> tuple[str, str]:
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT response_json, request_hash FROM idempotency_keys WHERE key = ?", (key,)
        ).fetchone()
    if row is None:
        raise RuntimeError(f"missing outer idempotency row: {key}")
    return str(row[0]), str(row[1])


def rewrite_legacy_cache(path: Path, key: str, *, missing_id: bool = False) -> dict[str, Any]:
    raw, request_hash = idempotency_row(path, key)
    response = json.loads(raw)
    original = response.get("proposals")
    if not isinstance(original, list) or not original:
        raise RuntimeError("current request_replan response has no persisted proposals")
    legacy = []
    for index, item in enumerate(original):
        proposal_id = str(item["id"])
        if missing_id and index == 0:
            proposal_id = str(uuid.uuid4())
        legacy.append(
            {
                "id": proposal_id,
                "status": item.get("status", "PRESENTED"),
                "hard_constraints_passed": item.get("hard_constraints_passed", True),
                "locked_commitments_preserved": item.get("locked_commitments_preserved", True),
            }
        )
    response["proposals"] = legacy
    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE idempotency_keys SET response_json = ? WHERE key = ?",
            (json.dumps(response, sort_keys=True), key),
        )
        connection.commit()
    return {
        "idempotency_key": key,
        "request_hash_unchanged": idempotency_row(path, key)[1] == request_hash,
        "legacy_proposal_ids": [item["id"] for item in legacy],
        "missing_id_injected": missing_id,
    }


def child_environment(audit_path: Path, base_url: str) -> dict[str, str]:
    environment = r4.child_environment(database=None, audit_path=audit_path, base_url=base_url)
    environment["CITYNEXUS_AGENT_ID"] = AGENT_ID
    return environment


async def call_mcp(
    base_url: str, journey_id: str, trigger_event_id: str, audit_path: Path
) -> dict[str, Any]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(LAUNCHER), "citynexus_mcp.server", "--v2"],
        cwd=MCP_PACKAGE,
        env=child_environment(audit_path, base_url),
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "request_replan",
                {
                    "request_id": REQUEST_ID,
                    "journey_id": journey_id,
                    "trigger_event_id": trigger_event_id,
                    "candidate_count": 3,
                },
            )
            payload: dict[str, Any] = {
                "is_error": bool(result.isError),
                "content": [getattr(item, "text", str(item)) for item in result.content],
            }
            if result.structuredContent is not None:
                payload["structured"] = result.structuredContent
            elif not result.isError and result.content:
                payload["structured"] = json.loads(result.content[0].text)
            return payload


def run_once(db: Path, log_path: Path, audit_path: Path, journey_id: str, trigger_id: str) -> dict[str, Any]:
    with r4.BackendProcess(db, log_path, audit_path, database_must_be_new=False) as backend:
        return asyncio.run(call_mcp(backend.base_url, journey_id, trigger_id, audit_path))


def complete_view(payload: dict[str, Any]) -> bool:
    structured = payload.get("structured") or {}
    views = structured.get("proposal_views") or []
    return bool(views) and all(
        item.get("proposed_plan_version_id")
        and item.get("utility_score") is not None
        and item.get("candidate_family")
        and isinstance(item.get("moved"), list)
        and isinstance(item.get("removed"), list)
        and isinstance(item.get("added"), list)
        and isinstance(item.get("feasibility_envelope"), dict)
        for item in views
    )


def run_probe(output_dir: Path) -> dict[str, Any]:
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(f"choose a new evidence directory: {output}")
    preflight = clean_state()
    if preflight["status_porcelain_v1"]:
        raise RuntimeError("refusing runtime before product call: source worktree is dirty")
    binding_before = tracked_binding()
    if not all(item["matches"] for item in binding_before.values()):
        raise RuntimeError("refusing runtime before product call: tracked source/blob mismatch")
    output.mkdir(parents=True)
    audit_path = output / "network-guard.jsonl"
    source_head = preflight["head"]
    parent_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD^"], cwd=ROOT, text=True
    ).strip()
    changed_files = subprocess.check_output(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", source_head],
        cwd=ROOT, text=True,
    ).splitlines()
    evidence: dict[str, Any] = {
        "run_id": RUN_ID,
        "scenario_id": SCENARIO_ID,
        "source_binding_before": preflight,
        "tracked_blob_binding_before": binding_before,
        "source_identity": {"commit": source_head, "direct_parent": parent_head,
                            "changed_files": changed_files},
        "assertions": [],
        "blockers": [],
        "inputs": {
            "request_id": REQUEST_ID, "agent_id": AGENT_ID,
            "CITYNEXUS_AGENT_ID": AGENT_ID, "journey_id": None,
            "trigger_event_id": None, "candidate_count": 3,
            "solver_mode": None, "solver_mode_meaning": "gateway default (MCP field omitted)",
            "mission_id": None, "mission_id_meaning": "default/no mission",
            "server_resolved_principal_id": SERVER_PRINCIPAL_ID,
        },
        "provenance": {"model": "NOT_USED", "mobility": "mock-mobility", "P7": False},
    }
    if evidence["source_binding_before"]["status_porcelain_v1"]:
        evidence["blockers"].append("dirty worktree before first runtime call")
    try:
        seed_db, seed_context = r4.prepare_seed(output, audit_path)
        evidence["inputs"].update(seed_context)

        # Arm A is the full R4 regression, executed from this exact clean source.
        r4_dir = output / "r4-regression"
        r4_process = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "hermes_r4_contract_probe.py"), "--output-dir", str(r4_dir)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        r4_receipt_path = r4_dir / "hermes-r4-request-replan-original.json"
        r4_report = json.loads(r4_receipt_path.read_text(encoding="utf-8"))
        evidence["r4_regression_stdout"] = r4_process.stdout[-4000:]
        evidence["r4_regression_stderr"] = r4_process.stderr[-4000:]
        (output / "r4-regression-receipt.json").write_text(
            json.dumps(r4_report, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        evidence["assertions"].append({
            "name": "r4_regression_pass",
            "passed": r4_report.get("result") == "PASS",
        })

        legacy_db = output / "legacy-cache.sqlite3"
        missing_db = output / "missing-cache.sqlite3"
        r4.clone_sqlite(seed_db, legacy_db)
        journey_id = seed_context["journey_id"]
        trigger_id = seed_context["trigger_event_id"]
        evidence["inputs"].update({"journey_id": journey_id, "trigger_event_id": trigger_id})
        original = run_once(
            legacy_db, output / "legacy-original-backend.log", audit_path, journey_id, trigger_id
        )
        key = agent_key("request_replan", SERVER_PRINCIPAL_ID, REQUEST_ID)
        counts_before = {
            "replan_proposals": table_count(legacy_db, "replan_proposals"),
            "plan_versions": table_count(legacy_db, "plan_versions"),
            "idempotency_keys": table_count(legacy_db, "idempotency_keys"),
        }
        state_before_retry = identity_state(legacy_db, journey_id)
        active_before = [item["id"] for item in state_before_retry["plan_versions"]
                         if item["status"] == "ACTIVE"]
        authority_before = {
            "journey_status": (state_before_retry["journey"] or {}).get("status"),
            "active_plan_version_id": (state_before_retry["journey"] or {}).get("active_plan_version_id"),
            "active_plan_ids": active_before,
            "proposal_ids": [item["id"] for item in state_before_retry["replan_proposals"]],
            "plan_version_ids": [item["id"] for item in state_before_retry["plan_versions"]],
            "event_ids": [item["id"] for item in state_before_retry["events"]],
            "idempotency_keys": [item["key"] for item in state_before_retry["idempotency_keys"]],
        }
        legacy_mutation = rewrite_legacy_cache(legacy_db, key)
        legacy_raw, legacy_request_hash = idempotency_row(legacy_db, key)
        legacy_response = json.loads(legacy_raw)
        original_structured = original.get("structured") or {}
        original_views = original_structured.get("proposal_views", [])
        r4.clone_sqlite(legacy_db, missing_db)
        missing_mutation = rewrite_legacy_cache(missing_db, key, missing_id=True)

        retry = run_once(
            legacy_db, output / "legacy-retry-backend.log", audit_path, journey_id, trigger_id
        )
        state_after_retry = identity_state(legacy_db, journey_id)
        persisted_after_retry, persisted_signature_after_retry = idempotency_row(legacy_db, key)
        counts_after = {
            "replan_proposals": table_count(legacy_db, "replan_proposals"),
            "plan_versions": table_count(legacy_db, "plan_versions"),
            "idempotency_keys": table_count(legacy_db, "idempotency_keys"),
        }
        missing = run_once(
            missing_db, output / "missing-retry-backend.log", audit_path, journey_id, trigger_id
        )
        missing_state_after = identity_state(missing_db, journey_id)
        missing_counts = {
            "replan_proposals": table_count(missing_db, "replan_proposals"),
            "plan_versions": table_count(missing_db, "plan_versions"),
            "idempotency_keys": table_count(missing_db, "idempotency_keys"),
        }
        retry_structured = retry.get("structured") or {}
        retry_views = retry_structured.get("proposal_views", [])
        same_semantics = [
            {key: value for key, value in item.items() if key not in {"proposal_id", "proposed_plan_version_id"}}
            for item in original_views
        ] == [
            {key: value for key, value in item.items() if key not in {"proposal_id", "proposed_plan_version_id"}}
            for item in retry_views
        ]
        same_ids = [item.get("proposal_id") for item in original_views] == [
            item.get("proposal_id") for item in retry_views
        ]
        legacy_pass = (
            not original.get("is_error")
            and not retry.get("is_error")
            and retry_structured.get("proposal_contract_version") == "hermes-replan-proposal-view.v1"
            and complete_view(retry)
            and same_ids
            and same_semantics
            and counts_after == counts_before
        )
        missing_pass = (
            missing.get("is_error")
            and "AGENT_IDEMPOTENCY_RESPONSE_SCHEMA_UNAVAILABLE" in " ".join(missing.get("content", []))
            and missing_counts == counts_before
            and missing_state_after == state_before_retry
            and not missing.get("structured")
        )
        evidence["legacy_cache"] = {
            "database": str(legacy_db),
            "original": original,
            "legacy_mutation": legacy_mutation,
            "exact_legacy_response": legacy_response,
            "legacy_request_hash": legacy_request_hash,
            "retry": retry,
            "persisted_outer_response_after_retry": json.loads(persisted_after_retry),
            "persisted_outer_response_unchanged": persisted_after_retry == legacy_raw,
            "request_hash_unchanged": persisted_signature_after_retry == legacy_request_hash,
            "counts_before": counts_before,
            "counts_after": counts_after,
            "identity_state_before_retry": state_before_retry,
            "identity_state_after_retry": state_after_retry,
            "authority_identity_sets_before_retry": authority_before,
            "authority_identity_sets_after_retry": {
                "journey_status": (state_after_retry["journey"] or {}).get("status"),
                "active_plan_version_id": (state_after_retry["journey"] or {}).get("active_plan_version_id"),
                "active_plan_ids": [item["id"] for item in state_after_retry["plan_versions"] if item["status"] == "ACTIVE"],
                "proposal_ids": [item["id"] for item in state_after_retry["replan_proposals"]],
                "plan_version_ids": [item["id"] for item in state_after_retry["plan_versions"]],
                "event_ids": [item["id"] for item in state_after_retry["events"]],
                "idempotency_keys": [item["key"] for item in state_after_retry["idempotency_keys"]],
            },
            "entity_identity_sets_unchanged": state_after_retry == state_before_retry,
            "same_persisted_proposal_ids": same_ids,
            "same_semantic_views": same_semantics,
        }
        evidence["missing_cache"] = {
            "database": str(missing_db),
            "legacy_mutation": missing_mutation,
            "retry": missing,
            "counts_before": counts_before,
            "counts_after": missing_counts,
            "identity_state_before_retry": state_before_retry,
            "identity_state_after_retry": missing_state_after,
            "deterministic_code_observed": "AGENT_IDEMPOTENCY_RESPONSE_SCHEMA_UNAVAILABLE" in " ".join(missing.get("content", [])),
        }
        evidence["assertions"].extend(
            [
                {"name": "legacy_cached_retry_upgraded_without_mutation", "passed": legacy_pass},
                {"name": "missing_cached_proposal_fails_closed_without_regeneration", "passed": missing_pass},
            ]
        )
        evidence["assertions"].append({
            "name": "legacy_cache_entities_and_outer_record_unchanged",
            "passed": state_after_retry == state_before_retry
            and persisted_after_retry == legacy_raw
            and persisted_signature_after_retry == legacy_request_hash,
        })
        evidence["assertions"].append({
            "name": "original_journey_and_single_active_plan_authority_preserved",
            "passed": authority_before["journey_status"] == "ACTIVE"
            and authority_before["active_plan_ids"] == [authority_before["active_plan_version_id"]],
        })
    except Exception as exc:
        evidence["blockers"].append(f"{type(exc).__name__}: {exc}")
    finally:
        evidence["source_binding_after"] = clean_state()
        evidence["tracked_blob_binding_after"] = tracked_binding()
        if evidence["source_binding_after"]["status_porcelain_v1"]:
            evidence["blockers"].append("dirty worktree after runtime calls")
        if (evidence["source_binding_before"]["head"] != evidence["source_binding_after"]["head"]
                or evidence["source_binding_before"]["branch"] != evidence["source_binding_after"]["branch"]
                or not all(item["matches"] for item in evidence["tracked_blob_binding_after"].values())):
            evidence["blockers"].append("source binding changed during runtime calls")
        evidence["result"] = "PASS" if evidence["assertions"] and all(
            item["passed"] for item in evidence["assertions"]
        ) and not evidence["blockers"] else "FAIL"
        receipt_text = json.dumps(
            evidence, ensure_ascii=False, indent=2, sort_keys=True, default=str
        ) + "\n"
        (output / "hermes-r5-request-replan-original.json").write_text(
            receipt_text, encoding="utf-8"
        )
        (output / "hermes-r5-legacy-cache-retry.json").write_text(
            json.dumps(evidence.get("legacy_cache", {"run_id": RUN_ID, "blockers": evidence["blockers"]}), ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        (output / "hermes-r5-missing-proposal.json").write_text(
            json.dumps(evidence.get("missing_cache", {"run_id": RUN_ID, "blockers": evidence["blockers"]}), ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        sys.stdout.write(receipt_text)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    return 0 if run_probe(args.output_dir)["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
