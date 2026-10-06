"""Exercise publish_evidence.py's tail branches with a stubbed transport.

Why: the SAFE-DEFAULT change (a 401 on the read-back must read PUBLISHED_UNPROVEN, not MISMATCH)
cannot be reached with a real token - a bad token fails earlier at the fail-closed initial GET.  So
the two tail outcomes get driven by substituting `call`, which is the only honest way to prove the
branch exists and returns the code it claims.
"""
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pe", HERE / "publish_evidence.py")
pe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pe)

SAMPLE = HERE / "_selftest_publisher_payload.txt"
SAMPLE.write_text("publisher selftest payload\n", encoding="utf-8", newline="\n")

case = sys.argv[1] if len(sys.argv) > 1 else "auth401"

pe.guard = lambda *a, **k: None            # the denylist is not what is under test here
pe.time = type("T", (), {"sleep": staticmethod(lambda *_: None)})()

if case == "auth401":
    # NOTE: the first GET is the fail-closed existence probe (B5) and MUST answer 404/200, otherwise
    # the tool exits 6 before the PUT and the tail never runs - which is what the first version of
    # this stub accidentally proved.  Only the read-back GET answers 401 here.
    seen = {"gets": 0}
    def fake(method, path, payload=None):
        if method == "PUT":
            return 201, {"commit": {"sha": "a" * 40}}
        seen["gets"] += 1
        if seen["gets"] == 1:
            return 404, {"message": "Not Found"}
        return 401, '{"message":"Bad credentials","status":"401"}'
    expect = 7
elif case == "mismatch":
    seen = {"gets": 0}
    def fake(method, path, payload=None):
        if method == "PUT":
            return 201, {"commit": {"sha": "a" * 40}}
        seen["gets"] += 1
        if seen["gets"] == 1:
            return 404, {"message": "Not Found"}
        return 200, {"sha": "b" * 40, "size": 1}
    expect = 4
else:
    raise SystemExit(f"unknown case {case}")

pe.call = fake
sys.argv = ["publish_evidence.py", str(SAMPLE), "evidence/probe/publisher_selftest.json"]
rc = pe.main()
print(f"CASE {case}: expect {expect} got {rc} -> {'OK' if rc == expect else 'BAD'}")
raise SystemExit(0 if rc == expect else 1)
