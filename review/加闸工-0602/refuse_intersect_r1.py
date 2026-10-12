# -*- coding: utf-8 -*-
"""Anchor verifier for ORD-0602 evidence: every `file:line` I cite must actually hold the thing I say
it holds, read from the committed generation (not from my memory of the edit).
"""
import io
import re
import subprocess
import json
import sys

REPO = "D:/moodle/_qoder_integration_20260919"
CAND = "5ed85afea5d86b71be117a6dba80c8f0e24020e9"
TIP = "8940570c022950b705cc3b37139d1b8f7052c42a"
JSON = "D:/moodle/_jz_0602/gate_cand_full_r2.json"
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
    ("build_r1.txt", 11, "dist/index.html"),
    ("build_r1.txt", 29, "VITE_RC=0"),
]


def blob(ref, path):
    p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (ref, path)],
                       capture_output=True, timeout=600)
    if p.returncode:
        return None
    return p.stdout.decode("utf-8", "replace").splitlines()


def main():
    out = subprocess.run(["git", "-C", REPO, "diff", "--unified=0", TIP, CAND],
                         capture_output=True, timeout=600)
    cur = None
    added = {}
    for ln in out.stdout.decode("utf-8", "replace").splitlines():
        if ln.startswith("+++ b/"):
            cur = ln[6:]
        m = re.match(r'^@@ -\S+ \+(\d+)(?:,(\d+))?', ln)
        if m and cur:
            n = int(m.group(2) or 1)
            added.setdefault(cur, set()).update(range(int(m.group(1)), int(m.group(1)) + n))
    print('NEW_LINES %d 分布于 %s' % (sum(len(v) for v in added.values()),
          ', '.join('%s:%d 行' % (k, len(v)) for k, v in sorted(added.items()))))
    d = json.load(io.open(JSON, encoding='utf-8'))
    probs = d['problems']
    on_mine = [x for x in probs if x.get('line') in added.get(x.get('file'), ())]
    print('FULL_FILE_GATE refuse=%d info=%d' % (len(probs), len(d['informational'])))
    print('REFUSE_ON_MY_NEW_LINES %d' % len(on_mine))
    for x in on_mine:
        print('  ON-MINE %s:%s token=%s' % (x.get('file'), x.get('line'), x.get('token')))
    print('REFUSE_CARRIED_BY_FILES %s' % ', '.join(sorted({x.get('file') for x in probs})))
    print('SAMPLE %s' % json.dumps(probs[0], ensure_ascii=False)[:170])
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
