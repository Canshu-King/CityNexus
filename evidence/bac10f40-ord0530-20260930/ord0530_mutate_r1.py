"""ORD-0530 counterexample harness r1 -- take a rule out of the footprint screen and see who notices.

Three steps, all against THIS LANE's private stack (a copied, read-only-original denominator, so the
screen has stamps on two days to group):

  A `base_generation`  -- the three product files this order touches are put back the way the tip has
    them and the new copy module is removed, so the tree is the line WITHOUT this order while the spec
    is still this order's.  The day-grouping arms must go red on it: an arm that stayed green would be
    passing on a screen that never grew a day line.
  B `invented_day`     -- the guard that says "no read, no groups" is made to hand back one group with
    no stamps under it.  The arms that must go red are `answered_empty`, `refused` and `unreachable`:
    this is the false-green defence the order names -- the server gave nothing, so the screen must not
    grow a day of its own.
  C `grouping_merged`  -- the day key stops being compared, so every stamp lands under the first day.
    `grouped_by_the_trips_own_day` must go red at both shapes.  This one can only bite where the
    denominator has two days, which is why it runs here and not on a fresh authoritative database
    (there the trip has one day, and the same mutation passes -- named in the block, not hidden).

Bolts carried over from the previous order and kept in the code that writes: a run id per attempt, the
run id inside the log file name, and an `infra_failure` verdict for any attempt that produced no
playwright summary at all -- an exit code of 1 with nothing measured is not a red gate.
"""
import json
import os
import socket
import subprocess
import time

WT = "D:/moodle/_qoder_ai_ord0387_20260928/wt"
FRONT = WT + "/frontend"
OUT = "D:/moodle/_qoder_ai_ord0387_20260928/ord0530_mutants_r1"
SPEC = "e2e/qoder-bac10f40-ord0530-footprints-by-day.spec.ts"
PANEL = "src/features/checkin/FootprintPanel.tsx"
PRODUCT = ["src/features/checkin/FootprintPanel.tsx", "src/features/checkin/footprint.css",
           "src/features/checkin/footprintCopy.ts", "src/app/v8PanelRegistry.tsx"]
BASE_TIP = "1e95d106f81b29048ba17695fd0e49172516b9b1"
NODE_CLI = "D:/moodle/_qoder_ai_ord0387_20260928/node_modules/@playwright/test/cli.js"
JOURNEY = "22222222-2222-4222-8222-222222222222"
STACK_FRONT = "4795"
STACK_BACK = "4791"
LF = chr(10)

MUTANTS = [
    (
        "invented_day",
        PANEL,
        '    if (state.kind !== "read") return [];',
        '    if (state.kind !== "read") return [{ key: "invented", when: new Date(), stamps: [] }];',
    ),
    (
        "grouping_merged",
        PANEL,
        "      if (last && last.key === key) last.stamps.push(stamp);",
        "      if (last) last.stamps.push(stamp);",
    ),
]

os.makedirs(OUT, exist_ok=True)
report = {"started_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "spec": SPEC,
          "denominator_journey": JOURNEY, "stack": "frontend=:%s backend=:%s (this lane's private stack)" % (STACK_FRONT, STACK_BACK),
          "base_tip": BASE_TIP, "runs": []}


def sh(cmd, env_extra=None):
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY", "OPENAI_API_KEY"):
        env.pop(k, None)
    env.update(env_extra or {})
    p = subprocess.run(cmd, cwd=FRONT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800, env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def restore():
    sh(["git", "checkout", "HEAD", "--"] + [p for p in PRODUCT if "footprintCopy" not in p])
    module = os.path.join(FRONT, "src", "features", "checkin", "footprintCopy.ts")
    if not os.path.exists(module):
        sh(["git", "checkout", "HEAD", "--", "src/features/checkin/footprintCopy.ts"])


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def record(name, run_id, landed, rc, out):
    log = os.path.join(OUT, "mutant_%s_%s.log" % (name, run_id))
    open(log, "w", encoding="utf-8", newline=LF).write(out)
    tail = out[out.rindex(" failed"):] if " failed" in out else ""
    report["runs"].append({
        "arm_mutated": name, "run_id": run_id, "mutation_landed": landed, "playwright_exit": rc,
        "infra_failure": (not any(" passed" in l or " failed" in l for l in out.splitlines())
                          or "not able to start" in out or "is already used" in out),
        "summary_lines": [l.strip() for l in out.splitlines() if " passed" in l or " failed" in l][-2:],
        "failing_arms": sorted(set(l.split("arm=")[1].split(" ")[0] for l in tail.splitlines() if "arm=" in l)),
        "error_heads": [l.strip()[:200] for l in out.splitlines() if l.strip().startswith("Error:")][:6],
        "log_bytes": os.path.getsize(log), "log": log,
    })


def run_spec(run_id):
    return sh(["node", NODE_CLI, "test", SPEC, "--reporter=line"], {
        "CITYNEXUS_E2E_PORT": STACK_FRONT, "CITYNEXUS_BACKEND_PORT": STACK_BACK,
        "CITYNEXUS_ORD0530_JOURNEY": JOURNEY, "CITYNEXUS_E2E_RUN_ID": run_id,
    })


rc, out = sh(["git", "rev-parse", "HEAD"])
report["generation_under_mutation"] = out.strip()

# ---- A: the arms against the base generation -----------------------------------------------
restore()
sh(["git", "checkout", BASE_TIP, "--"] + [p for p in PRODUCT if "footprintCopy" not in p])
module = os.path.join(FRONT, "src", "features", "checkin", "footprintCopy.ts")
if os.path.exists(module):
    os.remove(module)
rc2, landed = sh(["git", "status", "--porcelain", "--", "src"])
run_id = "basegen" + time.strftime("%H%M%S")
rc, out = run_spec(run_id)
record("base_generation", run_id, landed.strip(), rc, out)
restore()

# ---- B and C: one rule taken out at a time ---------------------------------------------------
for name, target, old, new in MUTANTS:
    restore()
    path = os.path.join(FRONT, target.replace("/", os.sep))
    text = open(path, encoding="utf-8").read()
    if text.count(old) != 1:
        report["runs"].append({"arm": name, "refused": "mutation anchor found %d times" % text.count(old)})
        continue
    open(path, "w", encoding="utf-8", newline="").write(text.replace(old, new, 1))
    rc2, landed = sh(["git", "status", "--porcelain", "--", target])
    run_id = "mut%s%s" % (name[:7], time.strftime("%H%M%S"))
    rc, out = run_spec(run_id)
    record(name, run_id, landed.strip(), rc, out)
    restore()

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
