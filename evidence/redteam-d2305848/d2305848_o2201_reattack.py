"""红队攻击 D 的 ORD-0220① 语义断言（SESSION=d2305848，tree16 = dfdc5d5）。

D 的新门（qoder-budget-advisory-tiers.spec.ts:224-266）：
  RISK_WORDS  = ["超出","紧张","吃紧","不够"] —— caveat 必须含至少一个
  ALLAY_WORDS = ["充足","放心","宽裕","富余","没问题","绰绰有余"] —— 不得出现任何一个

三臂新形状（一次一臂，逐字节还原，authoritative e2e 只跑该节点）：
  E1  安抚语全部用词表**外**的反转词：「不用担心、肯定够用」（不含六个 ALLAY 词）
  E2  风险词被否定：「不会超出」（含 RISK 词"超出"，但整句语义是宽裕）—— 只测 allay=空 + risk>0 是否仍绿
  E3  （对照）原始 DA 臂重放：原句+反转后缀，现在必须红
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FRONTEND = HERE.parent / "tree16" / "frontend"
EVID = HERE.parent / "raw-evidence"
EVID.mkdir(exist_ok=True)
V8 = FRONTEND / "src" / "app" / "V8Experience.tsx"

HINT_OLD = '        ? "按这个预算，住宿、交通和吃饭很可能超出计划。可以先调整预算，或你确认继续也可以。"'

CASES = [
    {"key": "E1-allay-outside-wordlist", "new": '        ? "按这个预算，住宿、交通和吃饭很可能超出计划。不过别担心，肯定够用。"',
     "what": "安抚语用词表外反转词（不用担心/肯定够用），不含六个 ALLAY 词"},
    {"key": "E2-risk-negated", "new": '        ? "按这个预算，住宿、交通和吃饭不会超出计划。你可以放心调整，或确认继续。"',
     "what": "风险词被否定（不会超出）——含 RISK 词但整句是宽裕语义"},
    {"key": "E3-original-DA-replay", "new": '        ? "按这个预算，住宿、交通和吃饭很可能超出计划——不过实际上预算充足，放心消费。"',
     "what": "原始 DA 臂重放（对照：必须转红）"},
]

NODE = "ord0220-1-the-tight-caveat-cannot-contradict-itself"


def run_e2e(run_n: int) -> tuple[str, str]:
    run_id = f"d2305848_o2201r_{int(time.time()) % 100000:05d}{run_n}"
    env = dict(os.environ)
    for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY"):
        env.pop(k, None)
    env.update({
        "CITYNEXUS_E2E_AUTHORITATIVE": "1",
        "CITYNEXUS_E2E_RUN_ID": run_id,
        "CITYNEXUS_E2E_PORT": str(5710 + run_n),
        "CITYNEXUS_BACKEND_PORT": str(9710 + run_n),
        "CITYNEXUS_PYTHON": "D:/moodle/CityNexus/.venv/Scripts/python.exe",
        "CITYNEXUS_DATABASE_URL": f"sqlite:///D:/moodle/_qoder_redteam_anywhere_20260921/raw-evidence/_{run_id}.db",
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_EVIDENCE_DIR": str(EVID),
    })
    p = subprocess.run(
        f'npx playwright test e2e/qoder-budget-advisory-tiers.spec.ts --reporter=list --grep "{NODE}"',
        shell=True, cwd=str(FRONTEND), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env, timeout=600,
    )
    return (p.stdout or "") + (p.stderr or ""), run_id


def main() -> int:
    sys.path.insert(0, r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
    from mutation_anchor_guard import temporary_guarded_replace

    orig = V8.read_bytes()
    sha0 = hashlib.sha256(orig).hexdigest()[:16]
    print("V8Experience sha256[:16]:", sha0)
    report: dict = {"tree": str(FRONTEND.parent), "sha0": sha0, "cases": []}

    base_out, base_run = run_e2e(0)
    (EVID / "o2201r_baseline.log").write_text(base_out, encoding="utf-8")
    base_green = "ok 1" in base_out and "x  1" not in base_out
    report["baseline"] = {"run_id": base_run, "green": base_green}
    print(f"[baseline] green={base_green}")
    if not base_green:
        print("BASELINE NOT GREEN - aborting")
        (EVID / "d2305848_o2201r_attack.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        return 0

    for i, case in enumerate(CASES, 1):
        rec = {"key": case["key"], "what": case["what"]}
        try:
            hits = orig.count(HINT_OLD.encode("utf-8"))
            rec["anchor_hits"] = hits
            if hits != 1:
                rec["verdict"] = f"HARNESS_INVALID (anchor hits={hits})"
            else:
                with temporary_guarded_replace(V8, HINT_OLD.encode("utf-8"), case["new"].encode("utf-8")) as guard:
                    out, run_id = run_e2e(i)
                    (EVID / f"o2201r_{case['key']}.log").write_text(out, encoding="utf-8")
                    rec["run_id"] = run_id
                    rec["failed_line"] = next((l.strip()[:190] for l in out.splitlines() if l.strip().startswith("x ")), None)
                    if f"x  1" in out:
                        rec["verdict"] = "KILLED (语义门红)"
                    elif "ok 1" in out:
                        rec["verdict"] = "SURVIVED (新绕过形状被放行)"
                    else:
                        rec["verdict"] = "NOT_MEASURED"
        finally:
            pass
        rec["restored"] = hashlib.sha256(V8.read_bytes()).hexdigest() == hashlib.sha256(orig).hexdigest()
        report["cases"].append(rec)
        print(case["key"], "->", rec["verdict"], "|", (rec.get("failed_line") or "no red")[:160])

    (EVID / "d2305848_o2201r_attack.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", EVID / "d2305848_o2201r_attack.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
