"""Probe: dump the source of the route handlers ORD-0559 lane 路牌工甲 claims.

Read-only. Prints, per route, the decorator line, the function name, and the full function
source with absolute line numbers taken from the working tree at the tip I rebased onto.
"""

from __future__ import annotations

import ast
import pathlib
import sys

TARGETS = [
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

src_path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "backend/app/main.py")
lines = src_path.read_text(encoding="utf-8").splitlines()
tree = ast.parse("\n".join(lines))

by_path = {}
for node in tree.body:
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        continue
    for dec in node.decorator_list:
        if not isinstance(dec, ast.Call):
            continue
        args = [a.value for a in dec.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if not args:
            continue
        verb = ""
        if isinstance(dec.func, ast.Attribute):
            verb = dec.func.attr
        by_path.setdefault(args[0], []).append((verb, node))

for path in TARGETS:
    entries = by_path.get(path)
    if not entries:
        print(f"\n########## {path} :: NO DECORATOR FOUND")
        continue
    for verb, node in entries:
        print(f"\n########## {verb.upper()} {path} :: def at line {node.lineno} name={node.name}")
        for offset in range(node.lineno - 1, min(node.end_lineno, len(lines))):
            print(f"{offset + 1}\t{lines[offset]}")
