"""ORD-0530 retry-wrap counterexample -- take the one line of CSS out and see the arm bite.

One variable: `flex-shrink: 0` on the screen's own button becomes `flex-shrink: 1`, which is the
shape the line held before this order touched it (measured there: box 48x105, four painted text
rects). If the arm still passes with the defect restored, the arm proves nothing and this delivery
must say so instead of shipping the claim.
"""
import io
import json
import os
import subprocess
import time

WT = "D:/moodle/_qoder_ai_ord0387_20260928/wt"
FRONT = WT + "/frontend"
OUT = "D:/moodle/_qoder_ai_ord0387_20260928/ord0530_mutants_retry"
CSS = "src/features/checkin/footprint.css"
SPEC = "e2e/qoder-bac10f40-ord0530-footprints-by-day.spec.ts"
NODE_CLI = "D:/moodle/_qoder_ai_ord0387_20260928/node_modules/@playwright/test/cli.js"
JOURNEY = "22222222-2222-4222-8222-222222222222"
FRONT_PORT = os.environ.get("ORD0530_FRONT", "51685")
BACK_PORT = os.environ.get("ORD0530_BACK", "51679")
GOOD = "  flex-shrink: 0;"
BAD = "  flex-shrink: 1;"


def sh(cmd, env_extra=None):
    env = {k: v for k, v in os.environ.items()
           if k not in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "DEEPSEEK_API_KEY",
                        "CITYNEXUS_AI_API_KEY", "OPENAI_API_KEY")}
    env.update(env_extra or {})
    p = subprocess.run(cmd, cwd=FRONT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800, env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def restore():
    sh(["git", "checkout", "HEAD", "--", CSS])


os.makedirs(OUT, exist_ok=True)
report = {"started_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
          "generation": sh(["git", "rev-parse", "HEAD"])[1].strip(),
          "stack": "frontend=:%s backend=:%s (this lane's private stack)" % (FRONT_PORT, BACK_PORT),
          "runs": []}

path = os.path.join(FRONT, CSS.replace("/", os.sep))
text = io.open(path, encoding="utf-8").read()
if text.count(GOOD) != 1:
    raise SystemExit("the fix is not the single line this counterexample targets (found %d)"
                     % text.count(GOOD))
io.open(path, "w", encoding="utf-8", newline="").write(text.replace(GOOD, BAD, 1))
landed = sh(["git", "status", "--porcelain", "--", CSS])[1].strip()
run_id = "mutshrink" + time.strftime("%H%M%S")
rc, out = sh(["node", NODE_CLI, "test", SPEC, "--reporter=line", "-g", "retry_button_keeps_its_line"],
             {"CITYNEXUS_E2E_PORT": FRONT_PORT, "CITYNEXUS_BACKEND_PORT": BACK_PORT,
              "CITYNEXUS_ORD0530_JOURNEY": JOURNEY, "CITYNEXUS_E2E_RUN_ID": run_id})
log = os.path.join(OUT, "mutant_flex_shrink_%s.log" % run_id)
io.open(log, "w", encoding="utf-8", newline="\n").write(out)
summ = [l.strip() for l in out.splitlines() if " passed" in l or " failed" in l]
err = [l.strip()[:200] for l in out.splitlines() if l.strip().startswith("Error:")]
report["runs"].append({"mutation": "flex-shrink:0 -> flex-shrink:1", "run_id": run_id,
                       "mutation_landed": landed, "playwright_exit": rc,
                       "infra_failure": (not summ or "is already used" in out
                                         or "not able to start" in out),
                       "summary_lines": summ[-2:], "error_heads": err[:4],
                       "log_bytes": os.path.getsize(log), "log": log})
restore()
after = sh(["git", "status", "--porcelain", "--", "src"])[1]
report["tree_after"] = {"dirty_lines_for_src": len([l for l in after.splitlines() if l.strip()]),
                        "raw": after.strip()}

# and the same arm on the unmutated bytes, in the same run set, so the two are comparable
run_id2 = "cleanretry" + time.strftime("%H%M%S")
rc2, out2 = sh(["node", NODE_CLI, "test", SPEC, "--reporter=line", "-g", "retry_button_keeps_its_line"],
               {"CITYNEXUS_E2E_PORT": FRONT_PORT, "CITYNEXUS_BACKEND_PORT": BACK_PORT,
                "CITYNEXUS_ORD0530_JOURNEY": JOURNEY, "CITYNEXUS_E2E_RUN_ID": run_id2})
log2 = os.path.join(OUT, "clean_retry_arm_%s.log" % run_id2)
io.open(log2, "w", encoding="utf-8", newline="\n").write(out2)
summ2 = [l.strip() for l in out2.splitlines() if " passed" in l or " failed" in l]
report["control_run"] = {"run_id": run_id2, "playwright_exit": rc2, "summary_lines": summ2[-2:],
                         "log_bytes": os.path.getsize(log2), "log": log2}
report["ended_local"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
dst = os.path.join(OUT, "mutant_report.json")
json.dump(report, io.open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in report["runs"]:
    print(r["mutation"], "exit", r["playwright_exit"], "infra", r["infra_failure"],
          r["summary_lines"], r["error_heads"][:2])
print("control", report["control_run"]["playwright_exit"], report["control_run"]["summary_lines"])
print("tree_after", report["tree_after"]["dirty_lines_for_src"], "report", dst,
      os.path.getsize(dst), "B")
