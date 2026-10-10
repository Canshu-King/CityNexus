"""ORD-0559 路牌工甲: pair every door I shipped tests for against the contract's declared status codes.

Read-only. For each METHOD+path in my slice, it reads (a) the codes the decorator declares via
`responses={...}` plus FastAPI's implicit 2xx, and (b) the codes the contract lists for that path,
then reports which codes a door can actually answer that the contract never names. That is the
machine-readable form of the three findings in my delivery block (the unconfigured-Hermes 500, the
SSE that answers 200 with an empty body, and the 502 that is not in the contract), so a ruling can
be made against a table instead of prose.
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys

MAIN = pathlib.Path("backend/app/main.py")
CONTRACT = pathlib.Path("contracts/openapi.yaml")

SLICE = [
    ("GET", "/api/v1/journeys/{journey_id}/acl/roles", "/journeys/{journey_id}/acl/roles"),
    ("GET", "/api/v1/journeys/{journey_id}/agent/hermes/runs/{run_id}",
     "/journeys/{journey_id}/agent/hermes/runs/{run_id}"),
    ("GET", "/api/v1/journeys/{journey_id}/agent/hermes/runs/{run_id}/timeline",
     "/journeys/{journey_id}/agent/hermes/runs/{run_id}/timeline"),
    ("GET", "/api/v1/journeys/{journey_id}/agent/hermes/runs/{run_id}/events",
     "/journeys/{journey_id}/agent/hermes/runs/{run_id}/events"),
    ("POST", "/api/v1/journeys/{journey_id}/agent/hermes/runs/{run_id}/stop",
     "/journeys/{journey_id}/agent/hermes/runs/{run_id}/stop"),
    ("POST", "/api/v1/journeys/{journey_id}/authoritative-compose",
     "/journeys/{journey_id}/authoritative-compose"),
    ("PUT", "/api/v1/journeys/{journey_id}/capabilities", "/journeys/{journey_id}/capabilities"),
    ("POST", "/api/v1/journeys/{journey_id}/capabilities/confirm",
     "/journeys/{journey_id}/capabilities/confirm"),
    ("GET", "/api/v1/journeys/{journey_id}/events/{event_id}/impact",
     "/journeys/{journey_id}/events/{event_id}/impact"),
    ("GET", "/api/v1/journeys/{journey_id}/guardian/autopilot/status",
     "/journeys/{journey_id}/guardian/autopilot/status"),
    ("GET", "/api/v1/journeys/{journey_id}/guardian/resilience",
     "/journeys/{journey_id}/guardian/resilience"),
    ("POST", "/api/v1/journeys/{journey_id}/guardian/resilience/refresh",
     "/journeys/{journey_id}/guardian/resilience/refresh"),
    ("POST", "/api/v1/journeys/{journey_id}/guardian/signal-fixture",
     "/journeys/{journey_id}/guardian/signal-fixture"),
    ("GET", "/api/v1/journeys/{journey_id}/inbox", "/journeys/{journey_id}/inbox"),
    ("GET", "/api/v1/journeys/{journey_id}/member-role-limits",
     "/journeys/{journey_id}/member-role-limits"),
    ("POST", "/api/v1/journeys/{journey_id}/members/self-exit",
     "/journeys/{journey_id}/members/self-exit"),
    ("GET", "/api/v1/journeys/{journey_id}/multiday", "/journeys/{journey_id}/multiday"),
]

lines = MAIN.read_text(encoding="utf-8", errors="replace").splitlines()
tree = ast.parse("\n".join(lines))
contract_text = CONTRACT.read_text(encoding="utf-8", errors="replace").splitlines()


def decorator_info(path: str):
    """Every (verb, declared 2xx, named response codes, raise sites) for one literal path."""
    out = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call) or not dec.args:
                continue
            first = dec.args[0]
            if not (isinstance(first, ast.Constant) and first.value == path):
                continue
            verb = dec.func.attr if isinstance(dec.func, ast.Attribute) else "?"
            declared = set()
            for kw in getattr(dec, "keywords", []):
                if kw.arg == "status_code" and isinstance(kw.value, ast.Constant):
                    declared.add(str(kw.value.value))
                if kw.arg == "responses" and isinstance(kw.value, ast.Dict):
                    for key in kw.value.keys:
                        if isinstance(key, ast.Constant):
                            declared.add(str(key.value))
            raised = set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    fname = getattr(sub.func, "id", None) or getattr(sub.func, "attr", None)
                    if fname == "HTTPException" and sub.args:
                        head = sub.args[0]
                        if isinstance(head, ast.Constant):
                            raised.add(str(head.value))
                    if fname == "_share_refusal" and sub.args:
                        head = sub.args[0]
                        if isinstance(head, ast.Constant):
                            raised.add(str(head.value))
            out.append((verb, sorted(declared), sorted(raised), node.lineno))
    return out


def resolve(ref: str):
    """Follow a `#/paths/<escaped>/<verb>` style $ref back into the loaded document."""
    node = DOC
    for part in ref.lstrip("#/").split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~1")]
    return node


def contract_codes(operation_path: str, verb: str):
    """The status codes the contract lists under one operation, exact from the parsed document."""
    paths = DOC["paths"]
    if operation_path not in paths:
        return None, 0
    item = paths[operation_path]
    op = item.get(verb.lower())
    if not isinstance(op, dict):
        return None, 0
    hops = 0
    while "$ref" in op and hops < 3:
        op = resolve(op["$ref"])
        hops += 1
    responses = op.get("responses") or {}
    return sorted({str(key) for key in responses}), hops


import yaml

DOC = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))

print("# ORD-0559 路牌工甲 · 契约码与代码实际会答的码对拍（现读，只读）")
print("# 解释器 %s" % sys.version.split()[0])
missing_total = 0
for verb, main_path, operation_path in SLICE:
    infos = decorator_info(main_path)
    declared, raised, def_line = ([], [], 0)
    for item in infos:
        if item[0].lower() == verb.lower():
            declared, raised, def_line = item[1], item[2], item[3]
    codes, aliased = contract_codes(operation_path, verb)
    contract_set = set(codes or [])
    answerable = set(declared) | set(raised)
    if "200" not in answerable and not any(c.startswith("2") for c in declared):
        answerable.add("200")
    absent = sorted(answerable - contract_set)
    missing_total += len(absent)
    print("\n%s %s" % (verb, main_path))
    print("   装饰器与函数体现读 main.py:%d" % def_line)
    print("   装饰器点名/隐式可答的码 %s" % (",".join(sorted(answerable)) or "-"))
    print("   raise 站点给出的码 %s" % (",".join(raised) or "-"))
    print("   契约列出的码 %s%s" % (",".join(sorted(contract_set)) or "-",
                                    "（经 $ref 复用同一 operation）" if aliased else ""))
    print("   契约里没有的码 %s" % (",".join(absent) or "无"))
print("\n合计：契约里没列、代码却会答的码共 %d 枚（十七枚门全表）" % missing_total)
