"""ORD-0530 counterexample harness r4 -- the stale-data counterexample that r1's first try could not be.

r1 ran three steps.  Two of them bit:

  A `base_generation`  3 failed / 2 passed  -- without this order's screen there is no day line at all,
     so the grouping arms and the refusal arm go red.  Good.
  B `invented_day`     5 passed            -- VACUOUS.  Making `days` hand back a group with no stamps
     in it changed nothing on the glass, because the empty / refused / unreachable branches of the
     render never reach the day list at all.  A mutant that cannot reach the DOM proves nothing, so
     r1's B is reported as a bad anchor, not as a defence.
  C `grouping_merged`  2 failed / 3 passed  -- dropping the day-key comparison puts every stamp under
     the first day, and both grouping arms go red.  Good.

r2 keeps A and C and replaces B with the shape that actually carries the order's false-green risk, and
that one line can reach: a re-read that fails while the screen is already showing stamps.  If the
component keeps the old state on a failed answer, the glass goes on asserting footprints the server
did not just hand over -- which is exactly "屏上凭空长出印", arrived at through staleness rather than
through invention.  The arm that must notice is `retry_after_the_door_stops`.

Bolts unchanged from r1: a run id per attempt, the run id inside the log name, and `infra_failure`
for any attempt that produced no playwright summary.
"""
import json
import os
import subprocess
import time

WT = "D:/moodle/_qoder_ai_ord0387_20260928/wt"
FRONT = WT + "/frontend"
OUT = "D:/moodle/_qoder_ai_ord0387_20260928/ord0530_mutants_r4"
SPEC = "e2e/qoder-bac10f40-ord0530-footprints-by-day.spec.ts"
PANEL = "src/features/checkin/FootprintPanel.tsx"
PRODUCT = ["src/features/checkin/FootprintPanel.tsx", "src/features/checkin/footprint.css",
           "src/features/checkin/footprintCopy.ts", "src/app/v8PanelRegistry.tsx"]
BASE_TIP = "2f0568e05fb2540266b8e4fdbafb1e03d25a29c7"
NODE_CLI = "D:/moodle/_qoder_ai_ord0387_20260928/node_modules/@playwright/test/cli.js"
JOURNEY = "22222222-2222-4222-8222-222222222222"
STACK_FRONT = "52509"
STACK_BACK = "52508"
LF = chr(10)

STALE = (
    "stale_on_failed_read",
    PANEL,
    '    if (answer.kind === "read") setState({ kind: "read", stamps: answer.stamps });\n'
    '    else if (answer.kind === "refused") setState({ kind: "refused", reason: answer.refusal });\n'
    '    else setState({ kind: "unreachable" });',
    '    if (answer.kind === "read") setState({ kind: "read", stamps: answer.stamps });\n'
    "    /* ORD-0530 mutant: a failed answer leaves whatever the screen already had on the glass */",
)
MERGED = (
    "grouping_merged",
    PANEL,
    "      if (last && last.key === key) last.stamps.push(stamp);",
    "      if (last) last.stamps.push(stamp);",
)
MUTANTS = [STALE, MERGED]

os.makedirs(OUT, exist_ok=True)
report = {"started_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "spec": SPEC,
          "denominator_journey": JOURNEY,
          "stack": "frontend=:%s backend=:%s (this lane's private stack)" % (STACK_FRONT, STACK_BACK),
          "base_tip": BASE_TIP, "vacuous_attempt_kept_from_r1": "invented_day", "runs": []}


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
        "error_heads": [l.strip()[:220] for l in out.splitlines() if l.strip().startswith("Error:")][:6],
        "log_bytes": os.path.getsize(log), "log": log,
    })


def run_spec(run_id):
    return sh(["node", NODE_CLI, "test", SPEC, "--reporter=line"], {
        "CITYNEXUS_E2E_PORT": STACK_FRONT, "CITYNEXUS_BACKEND_PORT": STACK_BACK,
        "CITYNEXUS_ORD0530_JOURNEY": JOURNEY, "CITYNEXUS_E2E_RUN_ID": run_id,
    })


rc, out = sh(["git", "rev-parse", "HEAD"])
report["generation_under_mutation"] = out.strip()

# ---- A: the arms against the base generation ------------------------------------------------
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

# ---- B' and C: one rule taken out at a time --------------------------------------------------
for name, target, old, new in MUTANTS:
    restore()
    path = os.path.join(FRONT, target.replace("/", os.sep))
    text = open(path, encoding="utf-8").read()
    if text.count(old) != 1:
        report["runs"].append({"arm": name, "refused": "mutation anchor found %d times" % text.count(old)})
        continue
    open(path, "w", encoding="utf-8", newline="").write(text.replace(old, new, 1))
    rc2, landed = sh(["git", "status", "--porcelain", "--", target])
    run_id = "mut%s%s" % (name[:8], time.strftime("%H%M%S"))
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
