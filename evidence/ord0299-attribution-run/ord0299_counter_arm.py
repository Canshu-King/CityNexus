"""ORD-0299 step 3: the counter-arm - force the label to ignore who spoke, and prove the spec has teeth.

The commander's wording: set `from` to the constant "server" (i.e. the label stops consulting the source)
=> the four device arms A1/B1/C1/D must ALL go red, while A2 (server sentence present) stays green.
An arm that cannot tell the difference is not an arm, and the static review already passed the shape - so
this run is what the closure actually needs.

Mechanically: one hunk at the render site (`result.failureReason.from` -> the constant), which is where the
label and its `data-reason-origin` are chosen. Patched from the PRISTINE bytes in memory, restored in the
same `finally`, and the restored digest plus `git status` are printed before any verdict is discussed -
leaving a mutant in the tree would be worse than not measuring.

Per-arm outcomes come from Playwright's own JSON reporter, not from my parsing of a console tail.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
FE = LANE / "frontend"
SHEET = FE / "src/features/planning/PlanWithAiSheet.tsx"
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
SPEC = "e2e/qoder-ord0280-attribution-label-speaks-for-itself.spec.ts"
NEEDLE = 'data-reason-origin={result.failureReason.from}'
NEEDLE2 = '{result.failureReason.from === "server"'
MUT = {NEEDLE: 'data-reason-origin={"server"}',
       NEEDLE2: '{("server" as const) === "server"'}
ARM_IDS = ("A1", "A2", "B1", "B2", "C1", "C2", "D")
DEVICE_ARMS = ("A1", "B1", "C1", "D")
SERVER_ARMS = ("A2", "B2", "C2")


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_arms(json_out: pathlib.Path, log_out: pathlib.Path, evidence_dir: pathlib.Path,
             run_id: str, fe_port: str, be_port: str) -> dict:
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_E2E_AUTHORITATIVE": "1",
        "CITYNEXUS_E2E_PORT": fe_port,
        "CITYNEXUS_BACKEND_PORT": be_port,
        "CITYNEXUS_PYTHON": r"D:\moodle\CityNexus\.venv\Scripts\python.exe",
        "CITYNEXUS_E2E_RUN_ID": run_id,
        "CITYNEXUS_DATABASE_URL": f"sqlite:///{(LANE / 'backend' / ('_' + run_id + '.db')).as_posix()}",
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_EVIDENCE_DIR": str(evidence_dir),
        "PLAYWRIGHT_JSON_OUTPUT_NAME": str(json_out),
    })
    for k in ("DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY"):
        env.pop(k, None)
    r = subprocess.run(["node", "node_modules/@playwright/test/cli.js", "test",
                        "-c", "playwright.config.ts", SPEC, "--reporter=json"],
                       cwd=str(FE), env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    log_out.write_text((r.stdout or "") + (r.stderr or ""), "utf-8", newline="\n")
    outcomes = {}
    if json_out.exists():
        rep = json.loads(json_out.read_text(encoding="utf-8"))

        def walk(node):
            for s in node.get("suites", []) or []:
                walk(s)
            for sp in node.get("specs", []) or []:
                title = sp.get("title") or ""
                for t in ARM_IDS:
                    if f"ord0280-{t} " in title or title.startswith(f"ord0280-{t}"):
                        st = [x.get("status") for x in (sp.get("tests") or [{}])[0].get("results", [])] \
                            if sp.get("tests") else []
                        outcomes[t] = {"title": title[:78], "status": st or [sp.get("ok") and "ok"],
                                       "ok": bool(sp.get("ok"))}
        for s in (rep.get("suites") or []):
            walk(s)
    return {"rc": r.returncode, "outcomes": outcomes,
            "json_report": json_out.name, "log": log_out.name}


def main() -> int:
    if (FE / "src/features/planning").joinpath("PlanWithAiSheet.tsx") != SHEET:
        raise SystemExit("path sanity failed")
    pristine = SHEET.read_bytes()
    text = pristine.decode("utf-8")
    missing = [n for n in MUT if n not in text]
    if missing:
        print("ABORT: the render-site anchors are not present verbatim:", missing)
        return 2
    mutated = text
    for n, rep in MUT.items():
        mutated = mutated.replace(n, rep, 1)
    if mutated == text:
        print("ABORT: the counter-arm would change nothing")
        return 2
    print(f"fixed   sha {sha(SHEET)[:16]}")
    print(f"mutant  sha {hashlib.sha256(mutated.encode()).hexdigest()[:16]}  (one hunk, label blind to source)")
    stamp = time.strftime("%H%M%S")
    fixed_run = run_arms(WORK / f"ord0299_fixed_{stamp}.json", WORK / f"ord0299_fixed_{stamp}.log",
                         WORK / f"e2e_ord0299_fixed_{stamp}", "0299fix" + stamp[-4:], "4391", "8191")
    print("BASELINE (my candidate, unmodified component):")
    for a in ARM_IDS:
        o = fixed_run["outcomes"].get(a) or {}
        print(f"   {a:3s} ok={o.get('ok')} status={o.get('status')}")
    print(f"   rc={fixed_run['rc']}")
    try:
        SHEET.write_text(mutated, encoding="utf-8", newline="\n")
        assert sha(SHEET) == hashlib.sha256(mutated.encode()).hexdigest(), "mutant not in place"
        counter = run_arms(WORK / f"ord0299_counter_{stamp}.json", WORK / f"ord0299_counter_{stamp}.log",
                          WORK / f"e2e_ord0299_counter_{stamp}", "0299cnt" + stamp[-4:], "4392", "8192")
        print("COUNTER-ARM (label forced to \"server\", i.e. not consulting the source):")
        for a in ARM_IDS:
            o = counter["outcomes"].get(a) or {}
            print(f"   {a:3s} ok={o.get('ok')} status={o.get('status')}")
        print(f"   rc={counter['rc']}")
    finally:
        SHEET.write_bytes(pristine)
        ok_restore = sha(SHEET) == hashlib.sha256(pristine).hexdigest()
        dirty = subprocess.run(["git", "-C", str(LANE), "status", "--porcelain", "frontend/src"],
                              capture_output=True, text=True).stdout.strip()
        print("restored byte-exact:", ok_restore, "| frontend/src dirty:", repr(dirty))
    dev_all_red = all(not (counter["outcomes"].get(a) or {}).get("ok") for a in DEVICE_ARMS)
    a2_green = bool((counter["outcomes"].get("A2") or {}).get("ok"))
    base_all_green = all((fixed_run["outcomes"].get(a) or {}).get("ok") for a in ARM_IDS)
    verdict = ("SPEC_HAS_TEETH" if (dev_all_red and a2_green and base_all_green and ok_restore)
               else "ARM_INCONCLUSIVE")
    rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
           "order": "ORD-0299 步骤 2+3 · 真跑 + 反件",
           "candidate_tip": subprocess.run(["git", "-C", str(LANE), "rev-parse", "HEAD"],
                                            capture_output=True, text=True).stdout.strip(),
           "landed_base": "5c4608cede6cb7bd5f3ac7e704bfee379ca47abc",
           "face": {"mode": "playwright authoritative suite: this run OWNS the vite dev server and the uvicorn "
                            "backend on its own ports and its own throwaway db (reuseExistingServer=false)",
                    "grade_honest_label": "dev face => 规格会红/会绿一级；不是发布级证据（发布级要跑在生产构建的产物上）",
                    "command": "node node_modules/@playwright/test/cli.js test -c playwright.config.ts " + SPEC
                               + " --reporter=json"},
           "baseline_fixed_component": fixed_run,
           "counter_arm": {"patch": {k: MUT[k] for k in MUT}, "run": counter,
                           "expected": {"device_arms_all_red": list(DEVICE_ARMS),
                                        "server_arm_A2_still_green": True},
                           "device_arms_all_red": dev_all_red, "A2_still_green": a2_green},
           "baseline_all_seven_green": base_all_green,
           "restored_byte_exact": ok_restore,
           "verdict": verdict,
           "derived_result": None}
    p = WORK / "ord0299_counter_arm_run.json"
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(f"\nverdict={verdict}  device_all_red={dev_all_red}  A2_green={a2_green}  "
          f"baseline_7_green={base_all_green}  restored={ok_restore}")
    print("->", p.name)
    return 0 if verdict == "SPEC_HAS_TEETH" else 1


if __name__ == "__main__":
    raise SystemExit(main())
