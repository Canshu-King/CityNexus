"""ORD-0559 路牌工甲: re-read every coordinate the delivery block cites, from the tree at the branch tip."""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(".")
MAIN = (ROOT / "backend/app/main.py").read_text(encoding="utf-8", errors="replace").splitlines()
SCHEMA = (ROOT / "backend/app/schemas.py").read_text(encoding="utf-8", errors="replace").splitlines()
CONTRACT = (ROOT / "contracts/openapi.yaml").read_text(encoding="utf-8", errors="replace").splitlines()
TEST = (ROOT / "backend/tests/test_route_gap_lupaigongjia_0559_r1.py").read_text(
    encoding="utf-8", errors="replace").splitlines()

PATHS = [
    "/api/v1/journeys/{journey_id}/acl/roles",
    "/api/v1/journeys/{journey_id}/agent/hermes/runs/{run_id}",
    "/api/v1/journeys/{journey_id}/agent/hermes/runs/{run_id}/timeline",
    "/api/v1/journeys/{journey_id}/agent/hermes/runs/{run_id}/events",
    "/api/v1/journeys/{journey_id}/agent/hermes/runs/{run_id}/stop",
    "/api/v1/journeys/{journey_id}/authoritative-compose",
    "/api/v1/journeys/{journey_id}/capabilities",
    "/api/v1/journeys/{journey_id}/capabilities/confirm",
    "/api/v1/journeys/{journey_id}/events/{event_id}/impact",
    "/api/v1/journeys/{journey_id}/guardian/autopilot/status",
    "/api/v1/journeys/{journey_id}/guardian/resilience",
    "/api/v1/journeys/{journey_id}/guardian/resilience/refresh",
    "/api/v1/journeys/{journey_id}/guardian/signal-fixture",
    "/api/v1/journeys/{journey_id}/inbox",
    "/api/v1/journeys/{journey_id}/member-role-limits",
    "/api/v1/journeys/{journey_id}/members/self-exit",
    "/api/v1/journeys/{journey_id}/multiday",
]

print("== route declaration lines in backend/app/main.py (method + path line) ==")
for path in PATHS:
    found = []
    for i, line in enumerate(MAIN, 1):
        if path in line and ('@app.' in line or line.strip().startswith('"/api/v1/journeys')):
            verb = ""
            match = re.search(r"@app\.(\w+)\(", line)
            if match:
                verb = match.group(1)
            else:
                verb = MAIN[i - 2].strip(" ()@app") if i >= 2 else "?"
            found.append((i, verb or "?", line.strip()[:70]))
    for line_no, verb, text in found:
        print(f"main.py:{line_no}\t{verb}\t{text}")

print("\n== contract path lines in contracts/openapi.yaml ==")
for path in PATHS:
    tail = path[len("/api/v1/journeys/{journey_id}"):] if "{journey_id}" in path else path
    needle = f"/journeys/{{journey_id}}{tail}"
    for i, line in enumerate(CONTRACT, 1):
        if line.strip().startswith(f"{needle}:"):
            print(f"openapi.yaml:{i}\t{line.strip()}")

print("\n== helper definitions the assertions read their field names from ==")
HELPERS = {
    "backend/app/main.py": ["_draft_payload", "_member_payload", "_native_event_stream",
                            "_persist_native_event", "_capability_input_rows", "_share_refusal",
                            "require", "_member_admin_count_in_force"],
    "backend/app/schemas.py": ["JourneyRoleRule", "MemberRoleLimits", "JourneyMember",
                               "CitySignalFixtureRequest", "AuthoritativeComposeRequest",
                               "CapabilityInput", "ResilienceRefreshRequest"],
    "backend/app/intelligence/impact_resolver.py": ["impact_payload"],
    "backend/app/agent/predictive.py": ["snapshot_payload", "counterfactual_payload",
                                        "build_resilience_snapshot"],
    "backend/app/agent/signal_pipeline.py": ["set_fixture_state", "fixture_payload"],
    "backend/app/agent/autorun.py": ["autorun_status"],
    "backend/app/execution/traveler_twin.py": ["capability_payload"],
    "backend/app/capabilities.py": ["summarize_capabilities", "capability_write_refusal",
                                    "CAPABILITY_CODES"],
    "backend/app/stay_mobility.py": ["experience_payload"],
    "backend/app/services.py": ["plan_schema"],
    "backend/app/integrations/hermes/native_client.py": ["HermesNativeClient", "get_run", "stop",
                                                          "iter_events"],
    "backend/app/planning/authoritative_v12.py": ["compose_authoritative_multiday", "_place_facts"],
    "backend/app/core/config.py": ["hermes_native_api_url"],
}
for rel, names in HELPERS.items():
    lines = (ROOT / rel).read_text(encoding="utf-8", errors="replace").splitlines()
    for name in names:
        for i, line in enumerate(lines, 1):
            if re.match(rf"^\s*(def|class) {re.escape(name)}\b", line) or line.startswith(
                    f"{name} ="):
                print(f"{rel}:{i}\t{name}\t{line.strip()[:60]}")
                break

print("\n== my test module: test function lines and every assert line count per function ==")
current = None
counts: dict[str, int] = {}
starts: dict[str, int] = {}
for i, line in enumerate(TEST, 1):
    match = re.match(r"^def (test_\w+)", line)
    if match:
        current = match.group(1)
        starts[current] = i
        counts.setdefault(current, 0)
    elif current and line.strip().startswith("assert"):
        counts[current] += 1
total_asserts = 0
for name in starts:
    print(f"test_route_gap_lupaigongjia_0559_r1.py:{starts[name]}\t{name}\tasserts={counts[name]}")
    total_asserts += counts[name]
print(f"TOTAL tests={len(starts)} assert_lines={total_asserts}")
