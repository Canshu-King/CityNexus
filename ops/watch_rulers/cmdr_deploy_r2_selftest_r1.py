"""Two-way self-test for deploy_bundle_r2's F arm - run outside the tool, assertions computed from output.

Arms:
  A1 tunnel transport-fails + proxy GREEN + declared      -> F_REMOTE_LEG_UNREACHABLE (switch may proceed)
  A2 same, NOT declared                                   -> RED                       (fail closed)
  A3 tunnel transport-fails + proxy answers 200/html + declared -> RED                 (product defect never forgiven)
  A4 everything GREEN + declared                          -> GREEN
  A5 tunnel base unset + declared                         -> F_UNPROBED_DECLARED       (r1 behaviour intact)
  A6 repeated_verdict over injected transport errors      -> UNREACHABLE
  A7 repeated_verdict over injected 200+text/html         -> RED
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("dbr2", os.path.join(HERE, "deploy_bundle_r2.py"))
dbr2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dbr2)


def P(verdict, surface="tunnel"):
    return {"surface": surface, "got": {"verdict": verdict}}


def main():
    checks = {}
    checks["A1_declared_transport_fail_allows_named_gap"] = (
        dbr2.f_verdict_of([P("GREEN", "proxy_4782"), P("UNREACHABLE", "tunnel")], True)
        == "F_REMOTE_LEG_UNREACHABLE")
    checks["A2_undeclared_same_case_fails_closed"] = (
        dbr2.f_verdict_of([P("GREEN", "proxy_4782"), P("UNREACHABLE", "tunnel")], False) == "RED")
    checks["A3_wrong_answer_never_forgiven"] = (
        dbr2.f_verdict_of([P("RED", "proxy_4782"), P("UNREACHABLE", "tunnel")], True) == "RED")
    checks["A4_all_green_stays_green"] = (
        dbr2.f_verdict_of([P("GREEN", "proxy_4782"), P("GREEN", "tunnel")], True) == "GREEN")
    checks["A5_unset_base_unchanged"] = (
        dbr2.f_verdict_of([{"surface": "tunnel", "verdict": "NOT_CONFIGURED"}, P("GREEN", "proxy_4782")], True)
        == "F_UNPROBED_DECLARED")

    # A6 / A7 exercise repeated_verdict itself by injecting the probe answer, so the classification of
    # "no HTTP status + transport error" versus "200 + text/html" is measured, not assumed.
    real = dbr2.asset_verdict
    try:
        dbr2.asset_verdict = lambda *a, **k: {"verdict": "RED", "status": None, "content_type": None,
                                              "error": "URLError: getaddrinfo failed"}
        v6 = dbr2.repeated_verdict("/assets/x.js", "javascript", None, base="http://x", times=2)
        checks["A6_repeated_verdict_names_transport_only"] = (
            v6["verdict"] == "UNREACHABLE" and v6["transport_only"] is True and v6["times"] == 2)

        dbr2.asset_verdict = lambda *a, **k: {"verdict": "RED", "status": 200, "content_type": "text/html",
                                              "error": None}
        v7 = dbr2.repeated_verdict("/assets/x.js", "javascript", None, base="http://x", times=2)
        checks["A7_html_answer_still_RED"] = (v7["verdict"] == "RED" and v7["transport_only"] is False
                                              and v7["red_refs"] == ["200/text/html", "200/text/html"])

        dbr2.asset_verdict = lambda *a, **k: {"verdict": "GREEN", "status": 200, "content_type": "application/javascript",
                                              "error": None}
        v8 = dbr2.repeated_verdict("/assets/x.js", "javascript", None, base="http://x", times=2)
        checks["A8_green_still_green"] = v8["verdict"] == "GREEN"
    finally:
        dbr2.asset_verdict = real

    ok = all(checks.values())
    print(json.dumps({"checks": checks, "overall_pass": ok,
                      "note": "no network is touched by this tester; A6-A8 inject the probe answers"},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 6


if __name__ == "__main__":
    sys.exit(main())
