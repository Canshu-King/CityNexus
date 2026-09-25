from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MCP_PACKAGE = ROOT / "agent-mcp"
LAUNCHER = ROOT / "scripts" / "hermes_r4_launch.py"
sys.path.insert(0, str(MCP_PACKAGE))
from citynexus_mcp.schemas import HermesReplanProposalView  # noqa: E402

RUN_ID = str(uuid.uuid4())
SCENARIO_ID = "hermes-r4-request-replan-contract"
SYNTHETIC_AGENT_TOKEN = "hermes-r4-isolated-test-token"
TRACKED_CREDENTIAL_NAMES = (
    "CITYNEXUS_AI_API_KEY",
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "CITYNEXUS_HERMES_API_KEY",
    "CITYNEXUS_HERMES_API_SERVER_KEY",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_database_path(path: Path) -> Path:
    resolved = path.resolve()
    lowered = str(resolved).casefold()
    forbidden = ("_live.db", "_preview.db", "user.db", "user_db", "user-data", "userdata")
    if any(marker in lowered for marker in forbidden):
        raise ValueError(f"refusing database path with protected-data marker: {resolved}")
    return resolved


def free_loopback_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def child_environment(*, database: Path | None, audit_path: Path, base_url: str | None = None) -> dict[str, str]:
    inherited_names = ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "HOMEDRIVE", "HOMEPATH")
    environment = {name: os.environ[name] for name in inherited_names if os.environ.get(name)}
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "HERMES_R4_NETWORK_AUDIT": str(audit_path),
            "CITYNEXUS_ENV": "test",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_SOLVER": "deterministic",
            "CITYNEXUS_IMPACT_PROVIDER": "disabled",
            "CITYNEXUS_REAL_CITY_ENABLED": "false",
            "CITYNEXUS_GUARDIAN_AUTORUN": "false",
            "CITYNEXUS_AGENT_TOKEN": SYNTHETIC_AGENT_TOKEN,
            "CITYNEXUS_AGENT_PRINCIPAL_ID": "hermes-r4-server-principal",
            "NO_PROXY": "127.0.0.1,localhost,::1",
        }
    )
    if database is not None:
        environment["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
    if base_url is not None:
        environment["CITYNEXUS_API_BASE_URL"] = base_url
    python_path = [str(ROOT / "scripts")]
    if database is not None:
        python_path.append(str(BACKEND))
    else:
        python_path.append(str(MCP_PACKAGE))
    environment["PYTHONPATH"] = os.pathsep.join(python_path)
    return environment


class BackendProcess:
    def __init__(
        self,
        database: Path,
        log_path: Path,
        audit_path: Path,
        *,
        database_must_be_new: bool = True,
    ):
        self.database = safe_database_path(database)
        self.log_path = log_path
        self.port = free_loopback_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        if database_must_be_new and self.database.exists():
            raise FileExistsError(f"isolated database path already exists: {self.database}")
        if not database_must_be_new and not self.database.exists():
            raise FileNotFoundError(f"isolated database snapshot is missing: {self.database}")
        self.log_stream = self.log_path.open("wb")
        environment = child_environment(database=self.database, audit_path=audit_path)
        self.process = subprocess.Popen(
            [
                sys.executable,
                str(LAUNCHER),
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
                "--log-level",
                "warning",
            ],
            cwd=BACKEND,
            env=environment,
            stdout=self.log_stream,
            stderr=subprocess.STDOUT,
        )
        self.wait_ready()

    def wait_ready(self) -> None:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"backend exited before health check; see {self.log_path}")
            try:
                response = httpx.get(
                    f"{self.base_url}/api/v1/health", timeout=1, trust_env=False
                )
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.25)
        raise TimeoutError(f"isolated backend did not become ready; see {self.log_path}")

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=10)
        self.log_stream.close()

    def __enter__(self) -> "BackendProcess":
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()


def request_json(client: httpx.Client, method: str, path: str, **kwargs: Any) -> tuple[int, Any]:
    response = client.request(method, path, **kwargs)
    try:
        body = response.json()
    except ValueError:
        body = response.text
    return response.status_code, body


def clone_sqlite(source: Path, target: Path) -> None:
    safe_database_path(target)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite evidence database: {target}")
    source_db = sqlite3.connect(source)
    target_db = sqlite3.connect(target)
    try:
        source_db.backup(target_db)
    finally:
        target_db.close()
        source_db.close()


def schema_digest(path: Path) -> str:
    last_error: sqlite3.OperationalError | None = None
    for attempt in range(5):
        try:
            with sqlite3.connect(path) as connection:
                rows = connection.execute(
                    "SELECT type, name, sql FROM sqlite_master "
                    "WHERE type IN ('table','index','trigger','view') "
                    "ORDER BY type, name"
                ).fetchall()
            return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
        except sqlite3.OperationalError as exc:
            if "disk I/O error" not in str(exc) or attempt == 4:
                raise
            last_error = exc
            time.sleep(0.25)
    raise last_error  # pragma: no cover


def database_state_digest(path: Path) -> str:
    last_error: sqlite3.OperationalError | None = None
    for attempt in range(5):
        try:
            with sqlite3.connect(path) as connection:
                table_names = [
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                    )
                ]
                state: dict[str, list[list[Any]]] = {}
                for table in table_names:
                    escaped = table.replace('"', '""')
                    rows = [list(row) for row in connection.execute(f'SELECT * FROM "{escaped}"')]
                    rows.sort(key=lambda row: json.dumps(row, sort_keys=True, default=str))
                    state[table] = rows
            payload = json.dumps(state, sort_keys=True, separators=(",", ":"), default=str)
            return hashlib.sha256(payload.encode("utf-8")).hexdigest()
        except sqlite3.OperationalError as exc:
            if "disk I/O error" not in str(exc) or attempt == 4:
                raise
            last_error = exc
            time.sleep(0.25)
    raise last_error  # pragma: no cover


def prepare_seed(output: Path, audit_path: Path) -> tuple[Path, dict[str, Any]]:
    seed_db = output / "seed-runtime.sqlite3"
    snapshot_db = output / "seed-prestate-snapshot.sqlite3"
    if seed_db.exists() or snapshot_db.exists():
        raise FileExistsError(seed_db if seed_db.exists() else snapshot_db)
    transitions: list[dict[str, Any]] = []
    with BackendProcess(seed_db, output / "seed-backend.log", audit_path) as backend:
        with httpx.Client(base_url=backend.base_url, timeout=120, trust_env=False) as client:
            status, seed = request_json(client, "POST", "/api/v1/demo/reset")
            if status != 200:
                raise RuntimeError(f"RESET/SEED failed HTTP {status}: {seed}")
            journey_id = seed["journey_id"]
            transitions.append({"transition": "RESET -> SEED", "journey_id": journey_id})
            status, plans = request_json(
                client,
                "POST",
                f"/api/v1/journeys/{journey_id}/plans/generate",
                json={"candidate_count": 1},
            )
            if status != 201 or not plans:
                raise RuntimeError(f"seed plan generation failed HTTP {status}: {plans}")
            plan_id = plans[0]["id"]
            transitions.append({"transition": "SEED -> PLAN_SELECTED", "plan_id": plan_id})
            status, selected = request_json(
                client, "POST", f"/api/v1/journeys/{journey_id}/plans/{plan_id}/select"
            )
            if status != 200:
                raise RuntimeError(f"seed plan selection failed HTTP {status}: {selected}")
            status, started = request_json(
                client, "POST", f"/api/v1/journeys/{journey_id}/start"
            )
            if status != 200:
                raise RuntimeError(f"seed journey start failed HTTP {status}: {started}")
            current_activity_id = started.get("current_activity_id")
            if not current_activity_id:
                current_activity_id = selected.get("current_activity_id")
            if not current_activity_id:
                raise RuntimeError("seed start did not return a current_activity_id")
            transitions.append({"transition": "PLAN_SELECTED -> ACTIVE", "active_plan_id": plan_id})
            status, event = request_json(
                client,
                "POST",
                f"/api/v1/journeys/{journey_id}/events",
                json={
                    "event_type": "CLOSURE",
                    "severity": "MAJOR",
                    "affected_activity_id": current_activity_id,
                    "payload": {"kind": "SYNTHETIC_CLOSURE", "reason": "R4 deterministic fixture"},
                },
            )
            if status != 201:
                raise RuntimeError(f"synthetic disruption injection failed HTTP {status}: {event}")
            transitions.append(
                {"transition": "ACTIVE -> EVENT_DETECTED", "event_id": event["id"], "event_type": event["event_type"]}
            )
            clone_sqlite(seed_db, snapshot_db)
            seed_context = {
                "journey_id": journey_id,
                "initial_plan_id": plan_id,
                "current_activity_id": current_activity_id,
                "trigger_event_id": event["id"],
                "trigger_event_type": event["event_type"],
                "seed_provider_identity": "mock-city + mock-mobility; synthetic closure fixture",
                "transitions": transitions,
            }
    return snapshot_db, seed_context


def semantic_view(payload: dict[str, Any]) -> dict[str, Any]:
    view = json.loads(
        json.dumps(asdict(HermesReplanProposalView.from_payload(payload)), default=str)
    )
    view.pop("proposal_id")
    view.pop("proposed_plan_version_id")
    return view


def canonical_candidates(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for item in payloads:
        if "diff" in item:
            view = semantic_view(item)
        else:
            view = dict(item)
            view.pop("proposal_id", None)
            view.pop("proposed_plan_version_id", None)
        candidates.append(view)
    return sorted(candidates, key=lambda item: json.dumps(item, sort_keys=True, default=str))


async def call_real_mcp_stdio(base_url: str, journey_id: str, trigger_event_id: str, audit_path: Path) -> dict[str, Any]:
    environment = child_environment(database=None, audit_path=audit_path, base_url=base_url)
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(LAUNCHER), "citynexus_mcp.server", "--v2"],
        cwd=MCP_PACKAGE,
        env=environment,
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [tool.name for tool in tools.tools]
            result = await session.call_tool(
                "request_replan",
                {
                    "request_id": "hermes-r4-stdio-0001",
                    "journey_id": journey_id,
                    "trigger_event_id": trigger_event_id,
                    "candidate_count": 3,
                },
            )
            if result.isError:
                raise RuntimeError(f"stdio MCP request_replan returned isError: {result.content}")
            payload = result.structuredContent
            if payload is None:
                payload = json.loads(result.content[0].text)
            payload["_discovered_tools"] = names
            return payload


def run_probe(output_dir: Path) -> dict[str, Any]:
    output = output_dir.resolve()
    if output.exists():
        raise FileExistsError(f"choose a new evidence directory; refusing existing path: {output}")
    output.mkdir(parents=True)
    network_audit = output / "network-guard.jsonl"
    evidence: dict[str, Any] = {
        "run_id": RUN_ID,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "scenario_id": SCENARIO_ID,
        "environment_identity": {
            "citynexus_env": "test",
            "ai_enabled": False,
            "solver": "deterministic",
            "network": "loopback-only socket guard installed in every service child",
            "production_credential_names_in_child": {name: False for name in TRACKED_CREDENTIAL_NAMES},
            "synthetic_agent_token_present": True,
            "synthetic_agent_token_value": "excluded from evidence",
        },
        "runtime_provider_identity": {
            "python": sys.version.split()[0],
            "mcp_sdk": importlib.metadata.version("mcp"),
            "citynexus_backend": evidence_commit(),
            "mobility": "mock-mobility",
            "impact_provider": "disabled",
            "hermes_model_runtime": "NOT_USED",
            "live_providers": "DISABLED",
        },
        "inputs": {
            "candidate_count": 3,
            "solver_mode": "deterministic",
            "scenario_event": {"event_type": "CLOSURE", "severity": "MAJOR", "provenance": "SIMULATED"},
            "direct_route": "POST /api/v1/journeys/{journey_id}/replans",
            "mcp_tool": "request_replan via stdio MCP V2",
        },
        "actions": [],
        "assertions": [],
        "blockers": [],
    }
    try:
        seed_db, seed_context = prepare_seed(output, network_audit)
        evidence["inputs"].update(seed_context)
        direct_db = output / "direct-planner.sqlite3"
        mcp_db = output / "mcp-stdio.sqlite3"
        for path in (direct_db, mcp_db):
            evidence.setdefault("database_identity", []).append(
                {"path": str(path), "did_not_exist_before_clone": not path.exists()}
            )
            clone_sqlite(seed_db, path)
        seed_digest_direct = database_state_digest(direct_db)
        seed_digest_mcp = database_state_digest(mcp_db)
        evidence["database_identity"].extend(
            [
                {"path": str(path), "schema_digest": schema_digest(path), "prestate_digest": database_state_digest(path)}
                for path in (direct_db, mcp_db)
            ]
        )
        same_prestate = seed_digest_direct == seed_digest_mcp
        evidence["assertions"].append({"name": "same_seed_snapshot_prestate", "passed": same_prestate})
        if not same_prestate:
            raise RuntimeError("cloned direct/MCP databases do not have the same logical prestate")

        with BackendProcess(
            direct_db,
            output / "direct-backend.log",
            network_audit,
            database_must_be_new=False,
        ) as direct_server, BackendProcess(
            mcp_db,
            output / "mcp-backend.log",
            network_audit,
            database_must_be_new=False,
        ) as mcp_server:
            journey_id = seed_context["journey_id"]
            trigger_id = seed_context["trigger_event_id"]
            with httpx.Client(base_url=direct_server.base_url, timeout=120, trust_env=False) as client:
                before_journey = client.get(f"/api/v1/journeys/{journey_id}").json()
                before_plans = client.get(f"/api/v1/journeys/{journey_id}/plans").json()
                direct_response = client.post(
                    f"/api/v1/journeys/{journey_id}/replans",
                    json={
                        "trigger_event_id": trigger_id,
                        "candidate_count": 3,
                        "solver_mode": "deterministic",
                    },
                )
                if direct_response.status_code != 201:
                    raise RuntimeError(
                        f"direct product planner returned HTTP {direct_response.status_code}: {direct_response.text}"
                    )
                direct_selected = direct_response.json()
                direct_candidates = client.get(f"/api/v1/journeys/{journey_id}/replans").json()
                after_journey = client.get(f"/api/v1/journeys/{journey_id}").json()
                after_plans = client.get(f"/api/v1/journeys/{journey_id}/plans").json()
            evidence["actions"].append(
                {
                    "lane": "direct_product_planner",
                    "action": "POST /api/v1/journeys/{journey_id}/replans",
                    "status": 201,
                    "candidate_count": len(direct_candidates),
                    "selected_proposal_id": direct_selected["id"],
                }
            )
            evidence["direct_receipt"] = {
                "run_id": RUN_ID,
                "scenario_id": SCENARIO_ID,
                "journey": before_journey,
                "plans_before": before_plans,
                "proposal": direct_selected,
                "proposals": direct_candidates,
                "journey_after": after_journey,
                "plans_after": after_plans,
                "database": str(direct_db),
            }

            mcp_before_journey_response = httpx.get(
                f"{mcp_server.base_url}/api/v1/journeys/{journey_id}", timeout=30, trust_env=False
            )
            mcp_before_plans_response = httpx.get(
                f"{mcp_server.base_url}/api/v1/journeys/{journey_id}/plans", timeout=30, trust_env=False
            )
            mcp_before_journey = mcp_before_journey_response.json()
            mcp_before_plans = mcp_before_plans_response.json()
            mcp_payload = asyncio.run(
                call_real_mcp_stdio(mcp_server.base_url, journey_id, trigger_id, network_audit)
            )
            mcp_after_journey = httpx.get(
                f"{mcp_server.base_url}/api/v1/journeys/{journey_id}", timeout=30, trust_env=False
            ).json()
            mcp_after_plans = httpx.get(
                f"{mcp_server.base_url}/api/v1/journeys/{journey_id}/plans", timeout=30, trust_env=False
            ).json()
            mcp_candidates = mcp_payload.get("proposal_views", [])
            evidence["actions"].append(
                {
                    "lane": "hermes_mcp_stdio",
                    "action": "stdio MCP request_replan",
                    "status": "success",
                    "discovered_tools": mcp_payload.pop("_discovered_tools"),
                    "candidate_count": len(mcp_candidates),
                    "selected_proposal_id": (mcp_payload.get("proposal") or {}).get("id"),
                }
            )
            evidence["mcp_receipt"] = {
                "run_id": RUN_ID,
                "scenario_id": SCENARIO_ID,
                "journey": mcp_before_journey,
                "plans_before": mcp_before_plans,
                "response": mcp_payload,
                "journey_after": mcp_after_journey,
                "plans_after": mcp_after_plans,
                "database": str(mcp_db),
            }

        direct_semantics = canonical_candidates(direct_candidates)
        mcp_semantics = canonical_candidates(mcp_candidates)
        semantic_match = direct_semantics == mcp_semantics
        nonempty_candidate = any(
            view["proposed_plan_version_id"]
            and view["utility_score"] is not None
            and (view["moved"] or view["removed"] or view["added"])
            for view in [asdict(HermesReplanProposalView.from_payload(item)) for item in direct_candidates]
        )
        direct_sole_active = [item["id"] for item in after_plans if item["status"] == "ACTIVE"]
        mcp_sole_active = [item["id"] for item in mcp_after_plans if item["status"] == "ACTIVE"]
        active_unchanged = (
            before_journey["status"] == "ACTIVE"
            and after_journey["status"] == "ACTIVE"
            and before_journey["active_plan_version_id"] == after_journey["active_plan_version_id"]
            and direct_sole_active == [before_journey["active_plan_version_id"]]
            and mcp_before_journey["active_plan_version_id"] == mcp_after_journey["active_plan_version_id"]
            and mcp_sole_active == [mcp_before_journey["active_plan_version_id"]]
        )
        discovered_tools = evidence["actions"][-1]["discovered_tools"]
        exact_tool_surface = discovered_tools == [
            "inspect_journey", "inspect_twin", "list_replans", "search_city_services",
            "request_replan", "accept_replan", "replace_activity", "reschedule_activity",
            "create_booking", "cancel_refundable_booking", "request_commitment_change",
        ]
        assertions = [
            {"name": "real_direct_planner_candidate_exists", "passed": len(direct_candidates) > 0},
            {"name": "real_stdio_mcp_candidate_exists", "passed": len(mcp_candidates) > 0},
            {"name": "nonempty_candidate_diff_plan_id_and_score", "passed": nonempty_candidate},
            {"name": "candidate_semantic_parity", "passed": semantic_match},
            {"name": "mcp_contract_versioned_and_complete", "passed": mcp_payload.get("proposal_contract_version") == "hermes-replan-proposal-view.v1"},
            {"name": "proposal_only_one_active_plan_unchanged", "passed": active_unchanged},
            {"name": "mcp_tool_surface_exactly_v2_allowlist", "passed": exact_tool_surface},
        ]
        evidence["assertions"].extend(assertions)
        evidence["semantic_comparison"] = {
            "direct_candidate_count": len(direct_candidates),
            "mcp_candidate_count": len(mcp_candidates),
            "semantic_match": semantic_match,
            "direct_candidates": direct_semantics,
            "mcp_candidates": mcp_semantics,
            "normalized_only": ["generated proposal IDs", "generated proposed PlanVersion IDs"],
        }
        network_events = []
        if network_audit.exists():
            network_events = [json.loads(line) for line in network_audit.read_text(encoding="utf-8").splitlines() if line]
        guard_pids = [item["pid"] for item in network_events if item["event"] == "guard_installed"]
        blocked = [item for item in network_events if item["event"] == "blocked_non_loopback"]
        evidence["network_audit"] = {
            "guard_installed_process_count": len(guard_pids),
            "guard_installed_pids": guard_pids,
            "blocked_non_loopback_attempts": len(blocked),
            "non_loopback_connections_allowed": 0,
        }
        evidence["assertions"].append(
            {"name": "all_service_children_guarded_loopback_only", "passed": len(guard_pids) >= 4 and not blocked}
        )
        evidence["evidence_database_identity"] = [
            {
                "path": str(path),
                "sha256": sha256(path),
                "schema_digest": schema_digest(path),
                "prestate_digest": seed_digest_direct if path == direct_db else seed_digest_mcp if path == mcp_db else None,
                "size_bytes": path.stat().st_size,
            }
            for path in (seed_db, direct_db, mcp_db)
        ]
    except Exception as exc:
        evidence["blockers"].append(f"{type(exc).__name__}: {exc}")
    finally:
        if network_audit.exists():
            evidence["network_audit_artifact"] = str(network_audit)
        evidence["result"] = "PASS" if evidence["assertions"] and all(
            assertion["passed"] for assertion in evidence["assertions"]
        ) and not evidence["blockers"] else "FAIL"
        for name, body in (
            ("hermes-r4-request-replan-original.json", evidence),
            ("hermes-r4-direct-planner.json", evidence.get("direct_receipt", {"run_id": RUN_ID, "blockers": evidence["blockers"]})),
            ("hermes-r4-mcp-stdio.json", evidence.get("mcp_receipt", {"run_id": RUN_ID, "blockers": evidence["blockers"]})),
        ):
            (output / name).write_text(
                json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
                encoding="utf-8",
            )
        print(json.dumps({"run_id": RUN_ID, "result": evidence["result"], "output_dir": str(output), "blockers": evidence["blockers"], "assertions": evidence["assertions"]}, ensure_ascii=False, indent=2))
    return evidence


def evidence_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes R4 isolated planner/MCP parity probe")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run_probe(args.output_dir)
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
