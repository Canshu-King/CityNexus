"""ORD-0480 counterexample harness: break one closing path at a time and record what the gate says.

The order asks that disconnecting any one of the three paths must redden the gate. A claim about a
red run is only worth what its log is worth, so this writes the raw playwright stdout per mutant
next to the mutation it applied, and reverts the tree afterwards no matter how the run ended.
Nothing here is committed as a product candidate: V8Experience.tsx is patched in place, measured,
and restored by `git checkout --`.
"""
import json
import os
import subprocess
import time

FRONT = "D:/moodle/_qoder_ai_ord0387_20260928/wt/frontend"
OUT = "D:/moodle/_qoder_ai_ord0387_20260928/ord0480_mutants"
SPEC = "e2e/qoder-bac10f40-ord0480-drawer-close-arms.spec.ts"
CSS = "src/app/V8Experience.tsx"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE_CLI = "D:/moodle/_qoder_ai_ord0387_20260928/node_modules/@playwright/test/cli.js"

MUTANTS = [
    ("close_button", '                data-testid="v8-drawer-close"\n                onClick={() => setNavOpen(false)}',
     '                data-testid="v8-drawer-close"\n                onClick={() => undefined}'),
    ("backdrop", '            className="v8-drawer-backdrop"\n            aria-label={t("shell.closeNav")}\n            onClick={() => setNavOpen(false)}',
     '            className="v8-drawer-backdrop"\n            aria-label={t("shell.closeNav")}\n            onClick={() => undefined}'),
    ("escape", '      if (event.key !== "Escape") return;',
     '      if (event.key !== "Escape-that-never-arrives") return;'),
]

os.makedirs(OUT, exist_ok=True)
report = {"started_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "spec": SPEC, "runs": []}


def sh(cmd, env_extra=None):
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY"):
        env.pop(k, None)
    env.update(env_extra or {})
    p = subprocess.run(cmd, cwd=FRONT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=1800, env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def revert():
    sh(["git", "checkout", "--", CSS])


for name, old, new in MUTANTS:
    revert()
    path = os.path.join(FRONT, CSS.replace("/", os.sep))
    text = open(path, encoding="utf-8").read()
    if text.count(old) != 1:
        report["runs"].append({"arm": name, "refused": "mutation anchor found %d times" % text.count(old)})
        continue
    open(path, "w", encoding="utf-8", newline="").write(text.replace(old, new, 1))
    run_id = "mut" + name[:6].replace("_", "")
    rc, out = sh([
        "node", NODE_CLI, "test", SPEC, "--reporter=line",
    ], {
        "CITYNEXUS_E2E_AUTHORITATIVE": "1", "CITYNEXUS_E2E_PORT": "4875", "CITYNEXUS_BACKEND_PORT": "8746",
        "CITYNEXUS_PYTHON": PY, "CITYNEXUS_E2E_RUN_ID": run_id,
        "CITYNEXUS_DATABASE_URL": "sqlite:///D:/moodle/_qoder_ai_ord0387_20260928/_%s.db" % run_id,
        "CITYNEXUS_AI_ENABLED": "false",
    })
    log = os.path.join(OUT, "mutant_%s.log" % name)
    open(log, "w", encoding="utf-8", newline="\n").write(out)
    red = sorted({l.split("spec.ts:")[1].split("]")[0].strip() for l in out.splitlines()
                  if l.strip().startswith("Error:") and "arm=" in l} )
    report["runs"].append({
        "arm_mutated": name, "playwright_exit": rc,
        "summary_lines": [l.strip() for l in out.splitlines() if " passed" in l or " failed" in l][-2:],
        "error_heads": [l.strip()[:160] for l in out.splitlines() if l.strip().startswith("Error:")][:6],
        "log_bytes": os.path.getsize(log), "log": log,
    })
    revert()

rc, out = sh(["git", "status", "--porcelain", "--", CSS])
report["tree_after"] = {"dirty_lines_for_V8Experience": len([l for l in out.splitlines() if l.strip()]), "raw": out.strip()}
end = time.strftime("%Y-%m-%dT%H:%M:%S%z")
report["ended_local"] = end
dst = os.path.join(OUT, "mutant_report.json")
json.dump(report, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("runs", len(report["runs"]), "tree_after", report["tree_after"]["dirty_lines_for_V8Experience"])
for r in report["runs"]:
    print(" ", r.get("arm_mutated"), "exit", r.get("playwright_exit"), r.get("summary_lines"))
print("out", dst, os.path.getsize(dst), "B")
