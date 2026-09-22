"""红队攻击 D 的 ORD-0216 双向门（SESSION=d2305848，tree14 = 50b35e0）。

门形状（budget-advisory-tiers.spec.ts:93-106）：
  hasNumber = /每人每天约/ ; hasCaveat = /按这个预算，住宿、交通和吃饭很可能超出计划/
  三断言：hasNumber 必真；hasCaveat 必真；hasNumber !== hasCaveat 必假。
攻击臂（在 50b35e0 的 V8Experience.tsx 上做突变，逐字节还原，一次一臂）：
  DA  tight 分支的 hint 换成语义相反的措辞（"预算充足"），但保留"很可能超出计划"子串
      ——数字与 caveat 都在（配对没拆），但 caveat 说的话是假的 ⇒ 门是否对"同现但语义造假"有牙？
  DB  hint 整段删空（string literal → ""）——hasCaveat 变 false ⇒ 预期门红（这是门本该咬的形状，作对照）。
判定：DA 预期 SURVIVED（门钉的是"子串同现"，不是"caveat 说真话"）——若真存活，
     记为与 B 计数同族的"字段被钉、语义没人钉"新样本；DB 预期 KILLED。
e2e 用 authoritative 模式，一次只跑 budget-tiers 一条 spec 的 tight 臂（内存友好）。
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
FRONTEND = HERE.parent / "tree14" / "frontend"
EVID = HERE.parent / "raw-evidence"
EVID.mkdir(exist_ok=True)
V8 = FRONTEND / "src" / "app" / "V8Experience.tsx"

HINT_OLD = '        ? "按这个预算，住宿、交通和吃饭很可能超出计划。可以先调整预算，或你确认继续也可以。"'
HINT_FAKE = '        ? "按这个预算，住宿、交通和吃饭很可能超出计划——不过实际上预算充足，放心消费。"'
HINT_EMPTY = '        ? ""'

CASES = [
    {"key": "DA-caveat-says-opposite", "old": HINT_OLD, "new": HINT_FAKE,
     "what": "caveat 保留子串但整句语义反转（配对同现、内容说假话）"},
    {"key": "DB-caveat-emptied", "old": HINT_OLD, "new": HINT_EMPTY,
     "what": "caveat 整段删空（拆对）——门本该咬的形状（对照臂）"},
]

NODE = "ord0212-the-hub-keeps-only-the-tight-verdict"


def run_e2e(run_n: int) -> tuple[str, str]:
    run_id = f"d2305848_o216_{int(time.time()) % 100000:05d}{run_n}"
    env = dict(os.environ)
    for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY"):
        env.pop(k, None)
    env.update({
        "CITYNEXUS_E2E_AUTHORITATIVE": "1",
        "CITYNEXUS_E2E_RUN_ID": run_id,
        "CITYNEXUS_E2E_PORT": str(5610 + run_n),
        "CITYNEXUS_BACKEND_PORT": str(9610 + run_n),
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
    orig = V8.read_bytes()
    sha0 = hashlib.sha256(orig).hexdigest()[:16]
    print("V8Experience sha256[:16]:", sha0)
    report: dict = {"tree": str(FRONTEND.parent), "sha0": sha0, "cases": []}

    base_out, base_run = run_e2e(0)
    (EVID / "o216_baseline.log").write_text(base_out, encoding="utf-8")
    base_green = "ok 2" in base_out and "x  2" not in base_out
    report["baseline"] = {"run_id": base_run, "green": base_green}
    print(f"[baseline] green={base_green}")
    if not base_green:
        print("BASELINE NOT GREEN - aborting attacks (would judge nothing)")
        (EVID / "d2305848_o216_attack.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        return 0

    for i, case in enumerate(CASES, 1):
        rec = {"key": case["key"], "what": case["what"]}
        try:
            with_open = False
            old_b = case["old"].encode("utf-8")
            hits = orig.count(old_b)
            rec["anchor_hits"] = hits
            if hits != 1:
                rec["verdict"] = f"HARNESS_INVALID (anchor hits={hits})"
            else:
                with temporary_guarded_replace(V8, old_b, case["new"].encode("utf-8")) as guard:
                    with_open = True
                    out, run_id = run_e2e(i)
                    (EVID / f"o216_{case['key']}.log").write_text(out, encoding="utf-8")
                    rec["run_id"] = run_id
                    rec["failed_line"] = next((l.strip()[:180] for l in out.splitlines() if l.strip().startswith("x ")), None)
                    if "x  2" in out or "x 2" in out:
                        rec["verdict"] = "KILLED (门红)"
                    elif "ok 2" in out:
                        rec["verdict"] = "SURVIVED (伪造被放行)"
                    else:
                        rec["verdict"] = "NOT_MEASURED"
        finally:
            pass
        rec["restored"] = hashlib.sha256(V8.read_bytes()).hexdigest() == hashlib.sha256(orig).hexdigest()
        report["cases"].append(rec)
        print(case["key"], "->", rec["verdict"], "|", (rec.get("failed_line") or "no red")[:150])

    (EVID / "d2305848_o216_attack.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", EVID / "d2305848_o216_attack.json")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
    from mutation_anchor_guard import temporary_guarded_replace  # noqa: F401
    raise SystemExit(main())
