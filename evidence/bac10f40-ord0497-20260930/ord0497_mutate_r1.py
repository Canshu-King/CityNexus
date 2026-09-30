"""ORD-0497 counterexample harness r1 -- take one judgement out of the map and see whether the gate notices.

Two mutants, each aimed at a different promise the order makes:

  A `solid`     -- delete the class that paints a stamped stop solid. The arm that must go red is
                   `solid_after_a_real_stamp`, which counts exactly one solid pin and one date.
  B `unguarded` -- remove the guard that says "only an answered read may claim anything". The arm that
                   must go red is `read_never_arrived`, which counts zero claims on a cut read: this is
                   the shape of "去掉回读那一腿时屏上凭空多出印章".

Bolted from the previous order's own lessons, in the code that writes rather than in prose:
  * a run id unique per attempt -- reusing one makes the sqlite guard refuse, and that refusal comes
    back as `Exit code: 1` from config.webServer, which reads exactly like a red gate;
  * an `infra_failure` verdict for that shape, so a run that never reached a browser is never counted;
  * the log file name carries the run id, so no attempt can overwrite another one's witness.

Product code is patched in place, measured, and restored with `git checkout --` whatever happens.
"""
import json
import os
import subprocess
import time

WT = "D:/moodle/_qoder_ai_ord0387_20260928/wt"
FRONT = WT + "/frontend"
OUT = "D:/moodle/_qoder_ai_ord0387_20260928/ord0497_mutants_r1"
SPEC = "e2e/qoder-bac10f40-ord0497-footprints-on-map.spec.ts"
TARGET = "src/components/v8/MapPanel.tsx"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE_CLI = "D:/moodle/_qoder_ai_ord0387_20260928/node_modules/@playwright/test/cli.js"

MUTANTS = [
    (
        "solid",
        '      entry.el.classList.add("stamped");',
        '      /* ORD-0497 mutant: the solid determination is gone */',
    ),
    (
        "unguarded",
        '    const read = footprintsRef.current?.kind === "read" ? footprintsRef.current : null;',
        '    const read = footprintsRef.current ?? null;',
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


def revert():
    sh(["git", "checkout", "--", TARGET])


rc, out = sh(["git", "rev-parse", "HEAD"])
report["generation_under_mutation"] = out.strip()

for index, (name, old, new) in enumerate(MUTANTS):
    revert()
    path = os.path.join(FRONT, TARGET.replace("/", os.sep))
    text = open(path, encoding="utf-8").read()
    if text.count(old) != 1:
        report["runs"].append({"arm": name, "refused": "mutation anchor found %d times" % text.count(old)})
        continue
    open(path, "w", encoding="utf-8", newline="").write(text.replace(old, new, 1))
    rc2, landed = sh(["git", "status", "--porcelain", "--", TARGET])
    stamp = time.strftime("%H%M%S")
    run_id = "mut%s%s" % (name[:7], stamp)
    port = str(4901 + 2 * index)
    backend = str(8770 + 2 * index)
    rc, out = sh([
        "node", NODE_CLI, "test", SPEC, "--reporter=line",
    ], {
        "CITYNEXUS_E2E_AUTHORITATIVE": "1", "CITYNEXUS_E2E_PORT": port, "CITYNEXUS_BACKEND_PORT": backend,
        "CITYNEXUS_PYTHON": PY, "CITYNEXUS_E2E_RUN_ID": run_id,
        "CITYNEXUS_DATABASE_URL": "sqlite:///D:/moodle/_qoder_ai_ord0387_20260928/_%s.db" % run_id,
        "CITYNEXUS_AI_ENABLED": "false",
    })
    log = os.path.join(OUT, "mutant_%s_%s.log" % (name, run_id))
    open(log, "w", encoding="utf-8", newline="\n").write(out)
    # the failure list at the bottom of the line reporter names each red test by its `arm=` token
    tail = out[out.rindex(" failed"):] if " failed" in out else ""
    failing = sorted(set(l.split("arm=")[1].split()[0] for l in tail.splitlines() if "arm=" in l))
    report["runs"].append({
        "arm_mutated": name, "run_id": run_id, "ports": "frontend=:%s backend=:%s" % (port, backend),
        "mutation_landed": landed.strip(),
        "playwright_exit": rc,
        "infra_failure": "not able to start" in out or "browserType.launch" in out,
        "summary_lines": [l.strip() for l in out.splitlines() if " passed" in l or " failed" in l][-2:],
        "failing_arms": failing,
        "error_heads": [l.strip()[:200] for l in out.splitlines() if l.strip().startswith("Error:")][:8],
        "log_bytes": os.path.getsize(log), "log": log,
    })
    revert()

rc, out = sh(["git", "status", "--porcelain", "--", TARGET])
report["tree_after"] = {"dirty_lines_for_MapPanel": len([l for l in out.splitlines() if l.strip()]), "raw": out.strip()}
report["ended_local"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
dst = os.path.join(OUT, "mutant_report.json")
json.dump(report, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("runs", len(report["runs"]), "tree_after", report["tree_after"]["dirty_lines_for_MapPanel"])
for r in report["runs"]:
    print(" ", r.get("arm_mutated"), "exit", r.get("playwright_exit"), "infra", r.get("infra_failure"),
          r.get("summary_lines"))
print("out", dst, os.path.getsize(dst), "B")
