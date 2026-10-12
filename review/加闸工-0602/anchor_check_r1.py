# -*- coding: utf-8 -*-
"""Anchor verifier for ORD-0602 evidence: every `file:line` I cite must actually hold the thing I say
it holds, read from the committed generation (not from my memory of the edit).
"""
import io
import re
import subprocess
import sys

REPO = "D:/moodle/_qoder_integration_20260919"
CAND = "5ed85afea5d86b71be117a6dba80c8f0e24020e9"
EV = "D:/moodle/_jz_0602"

GIT_ANCHORS = [
    ("backend/app/main.py", 5945, "autopilot/recover"),
    ("backend/app/main.py", 209, "app.execution.clock"),
    ("backend/app/main.py", 210, "route_session_contract"),
    ("backend/app/main.py", 5982, "HTTPException(422"),
    ("backend/app/main.py", 5985, "route_truth_fact = fact_payload"),
    ("backend/app/main.py", 5986, "fact_is_eligible_for_live_readiness"),
    ("backend/app/main.py", 5987, "classify_capture"),
    ("backend/app/main.py", 6026, "ALLOW_AUTO"),
    ("backend/app/main.py", 6065, "dedupe_key"),
    ("backend/app/main.py", 6114, '"route_truth"'),
    ("frontend/src/i18n/LocaleContext.tsx", 229, "shell.autopilotTruthLive"),
    ("frontend/src/i18n/LocaleContext.tsx", 230, "shell.autopilotTruthSynthetic"),
    ("frontend/src/i18n/LocaleContext.tsx", 1759, "shell.autopilotTruthLive"),
    ("frontend/src/i18n/LocaleContext.tsx", 1760, "shell.autopilotTruthSynthetic"),
    ("frontend/src/app/V8Experience.tsx", 1388, "route_truth?"),
    ("frontend/src/app/V8Experience.tsx", 1402, "(result.route_truth"),
    ("frontend/src/app/V8Experience.tsx", 1405, "autopilotTruthLive"),
    ("frontend/src/app/V8Experience.tsx", 1406, "autopilotTruthSynthetic"),
    ("frontend/src/app/V8Experience.tsx", 2173, 'className="v8-message"'),
    ("contracts/openapi.yaml", 2608, "type: object"),
    ("backend/tests/test_v8_stay_mobility.py", 190, 'assert body["decision"] == "ALLOW_AUTO"'),
    ("backend/tests/test_v9_real_trip_operations.py", 165, "recover"),
    ("backend/tests/test_route_stub_\u9a8c\u8def\u5de5_0559b_r1.py", 124, "set("),
    ("backend/tests/test_jiazagong_0602_route_truth_r1.py", 1, "0602"),
]

FILE_ANCHORS = [
    ("mine_r1.txt", 2, "ROUTE_READY"),
    ("mine_r1.txt", 3, "ROUTE_PROVIDER_DEGRADED"),
    ("mine_r1.txt", 4, "decisions equal: True"),
    ("mine_r1.txt", 6, ": 422 "),
    ("mine_r1.txt", 18, "2 passed"),
    ("tests_r1.txt", 12, "14 passed"),
    ("collect_baseline.txt", 1948, "1918"),
    ("collect_after.txt", 1950, "1920"),
    ("copy_before.txt", 2, "REGISTER_PARITY"),
    ("copy_after.txt", 2, "REGISTER_PARITY"),
    ("copy_after.txt", 20, "RENDERED"),
    ("copy_after.txt", 20, "gated offenders: 0"),
    ("build_r1.txt", 11, "1.20 kB"),
    ("build_r1.txt", 29, "VITE_RC=0"),
]


def blob(ref, path):
    p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (ref, path)],
                       capture_output=True, timeout=600)
    if p.returncode:
        return None
    return p.stdout.decode("utf-8", "replace").splitlines()


def main():
    bad = 0
    cache = {}
    print("== anchors inside committed generation %s" % CAND[:12])
    for path, line, needle in GIT_ANCHORS:
        if path not in cache:
            cache[path] = blob(CAND, path)
        body = cache[path]
        got = body[line - 1].strip() if body and line <= len(body) else "<NO SUCH LINE>"
        ok = needle in got
        if not ok:
            bad += 1
        print("%-4s %s:%s  期望含 %r  实读 %r" % ("OK" if ok else "BAD", path, line, needle, got[:70]))
    print("== anchors inside my evidence files")
    for name, line, needle in FILE_ANCHORS:
        p = "%s/%s" % (EV, name)
        try:
            body = io.open(p, encoding="utf-8").read().splitlines()
        except IOError:
            print("BAD %s 读不到" % name)
            bad += 1
            continue
        got = body[line - 1].strip() if line <= len(body) else "<NO SUCH LINE, 全文 %d 行>" % len(body)
        ok = needle in got
        if not ok:
            bad += 1
        print("%-4s %s:%s  期望含 %r  实读 %r" % ("OK" if ok else "BAD", name, line, needle, got[:70]))
    print("TOTAL_BAD %d" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
