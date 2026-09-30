"""ORD-0497 counterexample harness r2 -- three ways to take something away, and does the gate notice.

  0 `base_generation` -- nothing is edited: the four product files this order touches are put back the
    way the tip has them and the new module is removed, so the tree is the line WITHOUT this order
    while the spec is still this order's.  Every arm that judges a stamp claim must go red.  An arm
    that stayed green here is reading something the product never put on screen.
  A `solid`           -- delete the line that paints a stamped stop solid.  `solid_after_a_real_stamp`
                         must redden, and the filter arm that counts on it with it.
  B `unguarded`       -- delete the guard that says only an answered read may claim anything.
                         `read_never_arrived` must redden: this is the shape of "遮掉回读腿时凭空多出
                         已打印章", which is the counterexample the order names.

Bolts, learned in this project and put in the code that writes:
  * a run id unique per attempt (the sqlite guard refuses a reused one, and the refusal arrives as
    `Exit code: 1` from config.webServer -- indistinguishable from a red gate by exit code alone);
  * an `infra_failure` verdict for that shape, so a run that never reached a browser is never counted;
  * the log file name carries the run id, so no attempt overwrites another one's witness;
  * the tree is restored from HEAD after every step, whatever happened, and the restored dirtiness is
    itself a reading in the report.
"""
import json
import os
import subprocess
import time

WT = "D:/moodle/_qoder_ai_ord0387_20260928/wt"
FRONT = WT + "/frontend"
OUT = "D:/moodle/_qoder_ai_ord0387_20260928/ord0497_mutants_r2"
SPEC = "e2e/qoder-bac10f40-ord0497-footprints-on-map.spec.ts"
TARGET = "src/components/v8/MapPanel.tsx"
PRODUCT = ["src/app/V8Experience.tsx", "src/components/v8/MapPanel.tsx",
           "src/i18n/mapPanelCopy.ts", "src/map-selection.css",
           "src/features/checkin/footprintRead.ts"]
BASE_TIP = "c482f179745a8883aca166dfebd020c6726b421e"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE_CLI = "D:/moodle/_qoder_ai_ord0387_20260928/node_modules/@playwright/test/cli.js"
LF = chr(10)

MUTANTS = [
    (
        "solid",
        '      entry.el.classList.add("stamped");',
        '      /* ORD-0497 mutant: the solid determination is gone */',
        "4921",
        "8790",
    ),
    (
        "unguarded",
        '    const read = footprintsRef.current?.kind === "read" ? footprintsRef.current : null;',
        '    const read = footprintsRef.current ?? null;',
        "4923",
        "8792",
    ),
]

os.makedirs(OUT, exist_ok=True)
report = {"started_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "spec": SPEC, "target": TARGET,
          "product_surface": PRODUCT, "base_tip": BASE_TIP, "runs": []}


def sh(cmd, env_extra=None):
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY", "OPENAI_API_KEY"):
        env.pop(k, None)
    env.update(env_extra or {})
    p = subprocess.run(cmd, cwd=FRONT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800, env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def restore():
    sh(["git", "checkout", "HEAD", "--"] + PRODUCT)


def run_spec(run_id, port, backend):
    return sh(["node", NODE_CLI, "test", SPEC, "--reporter=line"], {
        "CITYNEXUS_E2E_AUTHORITATIVE": "1", "CITYNEXUS_E2E_PORT": port, "CITYNEXUS_BACKEND_PORT": backend,
        "CITYNEXUS_PYTHON": PY, "CITYNEXUS_E2E_RUN_ID": run_id,
        "CITYNEXUS_DATABASE_URL": "sqlite:///D:/moodle/_qoder_ai_ord0387_20260928/_%s.db" % run_id,
        "CITYNEXUS_AI_ENABLED": "false",
    })


def record(name, run_id, ports, landed, rc, out, log_name):
    log = os.path.join(OUT, log_name)
    open(log, "w", encoding="utf-8", newline=LF).write(out)
    tail = out[out.rindex(" failed"):] if " failed" in out else ""
    report["runs"].append({
        "arm_mutated": name, "run_id": run_id, "ports": ports,
        "mutation_landed": landed, "playwright_exit": rc,
        "infra_failure": "not able to start" in out or "browserType.launch" in out,
        "summary_lines": [l.strip() for l in out.splitlines() if " passed" in l or " failed" in l][-2:],
        "failing_arms": sorted(set(l.split("arm=")[1].split()[0] for l in tail.splitlines() if "arm=" in l)),
        "error_heads": [l.strip()[:200] for l in out.splitlines() if l.strip().startswith("Error:")][:8],
        "log_bytes": os.path.getsize(log), "log": log,
    })


rc, out = sh(["git", "rev-parse", "HEAD"])
report["generation_under_mutation"] = out.strip()

# ---- counterexample 0: the arms against the base generation -------------------------------
restore()
sh(["git", "checkout", BASE_TIP, "--"] + [p for p in PRODUCT if "footprintRead" not in p])
new_module = os.path.join(FRONT, "src", "features", "checkin", "footprintRead.ts")
if os.path.exists(new_module):
    os.remove(new_module)
rc2, landed2 = sh(["git", "status", "--porcelain", "--", "src"])
run0 = "basegen" + time.strftime("%H%M%S")
rc0, out0 = run_spec(run0, "4919", "8788")
record("base_generation", run0, "frontend=:4919 backend=:8788", landed2.strip(), rc0, out0,
       "mutant_base_generation_%s.log" % run0)
restore()

# ---- counterexamples A and B: one judgement taken out at a time ---------------------------
for name, old, new, port, backend in MUTANTS:
    restore()
    path = os.path.join(FRONT, TARGET.replace("/", os.sep))
    text = open(path, encoding="utf-8").read()
    if text.count(old) != 1:
        report["runs"].append({"arm": name, "refused": "mutation anchor found %d times" % text.count(old)})
        continue
    open(path, "w", encoding="utf-8", newline="").write(text.replace(old, new, 1))
    rc2, landed = sh(["git", "status", "--porcelain", "--", TARGET])
    run_id = "mut%s%s" % (name[:7], time.strftime("%H%M%S"))
    rc, out = run_spec(run_id, port, backend)
    record(name, run_id, "frontend=:%s backend=:%s" % (port, backend), landed.strip(), rc, out,
           "mutant_%s_%s.log" % (name, run_id))
    restore()

rc, out = sh(["git", "status", "--porcelain", "--", "src"])
report["tree_after"] = {"dirty_lines_for_frontend_src": len([l for l in out.splitlines() if l.strip()]),
                        "raw": out.strip()}
report["ended_local"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
dst = os.path.join(OUT, "mutant_report.json")
json.dump(report, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("runs", len(report["runs"]), "tree_after", report["tree_after"]["dirty_lines_for_frontend_src"])
for r in report["runs"]:
    print(" ", r.get("arm_mutated"), "exit", r.get("playwright_exit"), "infra", r.get("infra_failure"),
          r.get("summary_lines"), r.get("failing_arms"))
print("out", dst, os.path.getsize(dst), "B")
