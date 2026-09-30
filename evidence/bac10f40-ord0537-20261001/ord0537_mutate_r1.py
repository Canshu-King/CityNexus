"""ORD-0537 counterexample harness r1 -- mask the switch's filter condition and see if the gate notices.

The order's one counterexample: with the condition that hides the unstamped pins taken out, the
marker census must stop following the switch.  The arm that should notice is `two_states`, which
asserts `off.pins_hidden == 0` and `on.pins_hidden == pins_claim - pins_solid` from two real passes
over the same control.

Bolts kept from the previous two orders, in the code that writes rather than in prose: a run id
unique per attempt (the sqlite guard's refusal to reopen a database arrives as `Exit code: 1` from
config.webServer, which is indistinguishable from a red gate by exit code alone), the run id inside
the log file name, and an `infra_failure` verdict for any attempt whose output holds no playwright
summary at all.
"""
import json
import os
import socket
import subprocess
import time

FRONT = "D:/moodle/_qoder_ai_ord0387_20260928/wt/frontend"
WT = "D:/moodle/_qoder_ai_ord0387_20260928/wt"
OUT = "D:/moodle/_qoder_ai_ord0387_20260928/ord0537_mutants_r1"
SPEC = "e2e/qoder-bac10f40-ord0537-map-toggle-reach.spec.ts"
TARGET = "src/components/v8/MapPanel.tsx"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE_CLI = "D:/moodle/_qoder_ai_ord0387_20260928/node_modules/@playwright/test/cli.js"
LF = chr(10)

MUTANTS = [
    (
        "filter_masked",
        "        if (only) entry.el.classList.add(\"filtered-out\");",
        "        /* ORD-0537 mutant: the switch's filter condition is masked out */",
    ),
]

os.makedirs(OUT, exist_ok=True)
report = {"started_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "spec": SPEC, "target": TARGET, "runs": []}


def sh(cmd, env_extra=None):
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY", "OPENAI_API_KEY"):
        env.pop(k, None)
    env.update(env_extra or {})
    p = subprocess.run(cmd, cwd=FRONT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800, env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def free_pair():
    taken = []
    for _ in range(40):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        finally:
            s.close()
        if port > 1024 and port not in taken:
            taken.append(port)
        if len(taken) == 2:
            return taken
    raise SystemExit("no free pair")


rc, out = sh(["git", "rev-parse", "HEAD"])
report["generation_under_mutation"] = out.strip()

for name, old, new in MUTANTS:
    sh(["git", "checkout", "HEAD", "--", TARGET])
    path = os.path.join(FRONT, TARGET.replace("/", os.sep))
    text = open(path, encoding="utf-8").read()
    if text.count(old) != 1:
        report["runs"].append({"arm": name, "refused": "mutation anchor found %d times" % text.count(old)})
        continue
    open(path, "w", encoding="utf-8", newline="").write(text.replace(old, new, 1))
    rc2, landed = sh(["git", "status", "--porcelain", "--", TARGET])
    run_id = "mut%s%s" % (name[:7], time.strftime("%H%M%S"))
    front, back = free_pair()
    rc, out = sh(["node", NODE_CLI, "test", SPEC, "--reporter=line"], {
        "CITYNEXUS_E2E_AUTHORITATIVE": "1", "CITYNEXUS_E2E_PORT": str(front), "CITYNEXUS_BACKEND_PORT": str(back),
        "CITYNEXUS_PYTHON": PY, "CITYNEXUS_E2E_RUN_ID": run_id,
        "CITYNEXUS_DATABASE_URL": "sqlite:///D:/moodle/_qoder_ai_ord0387_20260928/_%s.db" % run_id,
        "CITYNEXUS_AI_ENABLED": "false",
    })
    log = os.path.join(OUT, "mutant_%s_%s.log" % (name, run_id))
    open(log, "w", encoding="utf-8", newline=LF).write(out)
    tail = out[out.rindex(" failed"):] if " failed" in out else ""
    first_err = next((l.strip()[:200] for l in out.splitlines()
                      if l.strip().startswith(("Error:", "TimeoutError:"))), "no error line recovered")
    report["runs"].append({
        "arm_mutated": name, "run_id": run_id, "ports": "frontend=:%d backend=:%d" % (front, back),
        "mutation_landed": landed.strip(), "playwright_exit": rc,
        "infra_failure": (not any(" passed" in l or " failed" in l for l in out.splitlines())
                          or "not able to start" in out or "is already used" in out),
        "summary_lines": [l.strip() for l in out.splitlines() if " passed" in l or " failed" in l][-2:],
        "failing_arms": sorted(set(l.split("arm=")[1].split(" ")[0] for l in tail.splitlines() if "arm=" in l)),
        "first_error": first_err,
        "census_lines": [l.strip()[:400] for l in out.splitlines() if ":: two_states" in l][:1],
        "log_bytes": os.path.getsize(log), "log": log,
    })
    sh(["git", "checkout", "HEAD", "--", TARGET])

rc, out = sh(["git", "status", "--porcelain", "--", "src"])
report["tree_after"] = {"dirty_lines_for_src": len([l for l in out.splitlines() if l.strip()]), "raw": out.strip()}
report["ended_local"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
dst = os.path.join(OUT, "mutant_report.json")
json.dump(report, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("runs", len(report["runs"]), "tree_after", report["tree_after"]["dirty_lines_for_src"])
for r in report["runs"]:
    print(" ", r.get("arm_mutated"), "exit", r.get("playwright_exit"), "infra", r.get("infra_failure"),
          r.get("summary_lines"), r.get("failing_arms"))
print("out", dst, os.path.getsize(dst), "B")
