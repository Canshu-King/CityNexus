"""Export the research/route tool handoff for Codex's PR #23 `goal_tasks.py`.

The handoff is generated from the live runtime definitions and the git objects they came from,
not typed by hand.  Each tool gets:

  * the exact model-facing function definition (name, description, parameters);
  * a schema signature -- sha256 over the canonical JSON of that definition -- so Codex can
    compare the bytes it copies against this branch without trusting prose;
  * the catalog metadata (does it mutate domain truth / money / C4);
  * its PLAN_ONLY grant state, read from the same `build_mission_plan` the runtime enforces;
  * the named test that fails if the tool stops being reachable.

The repository has no per-directory SHA; `git rev-parse HEAD:backend/app/agent` is the tree
object id, and each file's blob id is listed beside it.

Usage (from the repository root):
    PYTHONPATH=backend python tools/reform/export_codex_tool_handoff.py \
        --out-dir docs/reform
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.agent.mission_plan import build_mission_plan
from app.agent.runtime import citynexus_tool_definitions
from app.agent.tool_catalog import TOOL_BY_NAME

TOOLS: tuple[tuple[str, str], ...] = (
    ("search_city_services", "tests/test_agent_alternatives_v3.py"),
    ("research_place_sources", "tests/test_reform_research_place_sources_adapter_r1.py"),
    ("estimate_place_facts", "tests/test_reform_estimate_place_facts_adapter_r1.py"),
    ("generate_plans", "tests/test_reform_generate_plans_adapter_r1.py"),
    ("discover_places", "tests/test_reform_discover_places_adapter_r1.py"),
    ("acquire_place_facts", "tests/test_reform_acquire_place_facts_adapter_r1.py"),
    ("compare_routes", "tests/test_reform_compare_routes_adapter_r1.py"),
    ("acquire_route", "tests/test_reform_acquire_route_adapter_r1.py"),
)

FILES: tuple[str, ...] = (
    "backend/app/agent/contracts.py",
    "backend/app/agent/delegation_policy.py",
    "backend/app/agent/gateway.py",
    "backend/app/agent/mission_plan.py",
    "backend/app/agent/runtime.py",
    "backend/app/agent/tool_catalog.py",
    "backend/app/execution/launch_origin.py",
    "backend/app/route_session_operations.py",
    "backend/app/integrations/web/research_service.py",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _signature(definition: dict) -> str:
    function = definition.get("function") or {}
    material = {
        "name": function.get("name"),
        "description": function.get("description"),
        "parameters": function.get("parameters"),
    }
    return hashlib.sha256(_canonical(material).encode("utf-8")).hexdigest()


def build() -> dict:
    definitions = {
        item["function"]["name"]: item for item in citynexus_tool_definitions()
    }
    plan_only = build_mission_plan(autonomy="PLAN_ONLY")
    granted = set(plan_only.allowed_tools)
    approval_required = set(plan_only.approval_required_tools)

    rows = []
    for name, test in TOOLS:
        definition = definitions.get(name)
        if definition is None:
            raise SystemExit(f"{name} is not advertised by the runtime")
        catalog = TOOL_BY_NAME[name].as_dict()
        if name in granted:
            grant = "ALLOWED"
        elif name in approval_required:
            grant = "APPROVAL_REQUIRED"
        else:
            grant = "NOT_GRANTED"
        rows.append(
            {
                "name": name,
                "schema_signature": _signature(definition),
                "definition": definition,
                "catalog": catalog,
                "plan_only_grant": grant,
                "proof_test": test,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "head": _git("rev-parse", "HEAD"),
        "agent_tree": _git("rev-parse", "HEAD:backend/app/agent"),
        "files": {path: _git("rev-parse", f"HEAD:{path}") for path in FILES},
        "tool_count": len(rows),
        "tools": rows,
        "call_contract": {
            "model_facing_schemas": "app.agent.runtime.citynexus_tool_definitions()",
            "catalog_metadata": "GET /api/v1/agent/tools/v2 (name + mutates/money/C4 only)",
            "call_envelope": "app.schemas.AgentToolCall",
            "required_fields": ["request_id (8-128 chars)", "journey_id"],
            "server_resolved_identity": (
                "the HTTP door resolves the agent principal and overwrites agent_id; "
                "in-process callers must pass the owner-verified journey id, never a "
                "client-supplied actor as authority"
            ),
            "runtime_grant": (
                "PLAN_ONLY grants READ_TOOLS + DRAFT_WRITE_TOOLS + request_replan; "
                "the loop refuses any tool outside that tuple before dispatch"
            ),
            "approval": (
                "acquire_route uses approval_fingerprint over action/journey/target/"
                "policy_version/decision/facts/proposal_diff; the target is "
                "origin_key->target_place_id and the mode is bound too. Mock/local capture "
                "has no external cost and stays ALLOW_AUTO; a configured live provider "
                "returns REQUIRE_CONFIRMATION until one receipt is consumed."
            ),
            "no_sql_no_free_http": (
                "the model names ids and keywords only; every provider call is written as "
                "a ProviderCall/WebObservation/RouteAcquisitionOperation row"
            ),
        },
    }


def render_markdown(payload: dict) -> str:
    lines = [
        "# Codex handoff — research/route tools (2026-10-18)",
        "",
        "Generated by `tools/reform/export_codex_tool_handoff.py` from the live runtime, not typed.",
        "",
        f"- branch: `{payload['branch']}`",
        f"- head: `{payload['head']}`",
        f"- agent tree: `{payload['agent_tree']}`",
        f"- tools: {payload['tool_count']}",
        "",
        "## Files (blob ids)",
        "",
        "| path | blob |",
        "| --- | --- |",
    ]
    for path, blob in payload["files"].items():
        lines.append(f"| `{path}` | `{blob}` |")
    lines += [
        "",
        "## Tools",
        "",
        "| tool | required | schema signature | PLAN_ONLY | mutates | money | C4 | proof |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["tools"]:
        catalog = row["catalog"]
        required = ", ".join(
            row["definition"]["function"]["parameters"].get("required") or []
        )
        lines.append(
            "| `{name}` | {required} | `{sig}` | {grant} | {mutates} | {money} | {c4} | `{test}` |".format(
                name=row["name"],
                required=required,
                sig=row["schema_signature"],
                grant=row["plan_only_grant"],
                mutates=catalog["mutates_domain_truth"],
                money=catalog["changes_money"],
                c4=catalog["changes_c4"],
                test=row["proof_test"],
            )
        )
    lines += [
        "",
        "### Differences Codex must handle when wiring `goal_tasks.py`",
        "",
        "- `AgentToolCall` is `extra=\"forbid\"`. The current local `discover_places` schema in",
        "  `goal_tasks.py` carries `public_action`; the gateway tool does not. Drop that field",
        "  (or keep the local handler) before calling `gateway.dispatch`.",
        "- `generate_plans` requires at least two server-owned `place_ids`; one place is a",
        "  refusal, not a plan.",
        "- `estimate_place_facts` records the three `estimated_*` values as",
        "  `AGENT_PROVIDED_HYPOTHESIS`, never as canonical provider truth.",
        "- `acquire_route` is not in the PLAN_ONLY grant. With the built-in mock provider it",
        "  is `ALLOW_AUTO`; with a configured live provider it returns `REQUIRE_CONFIRMATION`",
        "  and one named receipt bound to origin, target and mode.",
        "",
        "## Signing / call contract",
        "",
    ]
    for key, value in payload["call_contract"].items():
        lines.append(f"- **{key}**: {value}")
    lines += [
        "",
        "## Schemas",
        "",
    ]
    for row in payload["tools"]:
        lines.append(f"### `{row['name']}`")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(row["definition"], ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="docs/reform")
    args = parser.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = build()
    (out / "CODEX_HANDOFF_TOOLS_20261018.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out / "CODEX_HANDOFF_TOOLS_20261018.md").write_text(
        render_markdown(payload) + "\n", encoding="utf-8"
    )
    print(f"tools={payload['tool_count']} head={payload['head']}")


if __name__ == "__main__":
    main()
