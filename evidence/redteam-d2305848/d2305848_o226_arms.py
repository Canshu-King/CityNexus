"""红队 ORD-0226 三臂（tree18 = e08131e）。一次一臂；锚点守卫；逐字节还原。

臂 A（靶1 残留面）：突变**英文** caveat 串加反转后缀 —— 跑 D 的门（中文场景，预期绿）
                    再跑英文探针（预期屏上出现英文自相矛盾）⇒ 英文面可被污染且无人看
臂 B（靶2 覆盖）：  突变 advisory.text（数字那半）加安抚词 —— 门是否红（覆盖是否够）
臂 C（靶3 空白）：  ① 中文常量里的半角空格换成全角空格（归一化后应相等 ⇒ 门绿）
                    ② 中文常量里插入零宽字符 U+200B（\s 不吃 ⇒ 门应红）
用法：D:/moodle/CityNexus/.venv/Scripts/python.exe raw/d2305848_o226_arms.py <arm>
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
sys.path.insert(0, r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
from mutation_anchor_guard import temporary_guarded_replace  # noqa: E402

FRONTEND = HERE.parent / "tree18" / "frontend"
EVID = HERE.parent / "raw-evidence"
V8 = FRONTEND / "src" / "app" / "V8Experience.tsx"
GATE_NODE = "ord0220-1-the-tight-caveat-cannot-contradict-itself"

ZH_SENTENCE = '  "按这个预算，住宿、交通和吃饭很可能超出计划。可以先调整预算，或你确认继续也可以。";'
EN_SENTENCE = '"At this budget, lodging, transport and food are likely to exceed the plan. Adjust the budget, or continue intentionally."'
EN_MUTANT = '"At this budget, lodging, transport and food are likely to exceed the plan. Adjust the budget, or continue intentionally. Don\'t worry, you have plenty."'
TEXT_LINE = '      ? `${days} 天 · ${people} 人 · 每人每天约 ${amount}`'
TEXT_MUTANT = '      ? `${days} 天 · ${people} 人 · 每人每天约 ${amount}，预算充足请放心`'


def run_playwright(spec: str, grep: str, run_n: int) -> str:
    run_id = f"d2305848_o226a{int(time.time()) % 100000:05d}{run_n}"
    env = dict(os.environ)
    for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY"):
        env.pop(k, None)
    env.update({
        "CITYNEXUS_E2E_AUTHORITATIVE": "1", "CITYNEXUS_E2E_RUN_ID": run_id,
        "CITYNEXUS_E2E_PORT": str(5820 + run_n), "CITYNEXUS_BACKEND_PORT": str(9820 + run_n),
        "CITYNEXUS_PYTHON": "D:/moodle/CityNexus/.venv/Scripts/python.exe",
        "CITYNEXUS_DATABASE_URL": f"sqlite:///D:/moodle/_qoder_redteam_anywhere_20260921/raw-evidence/_{run_id}.db",
        "CITYNEXUS_AI_ENABLED": "false", "CITYNEXUS_EVIDENCE_DIR": str(EVID),
    })
    p = subprocess.run(
        f'npx playwright test {spec} --reporter=list --grep "{grep}"',
        shell=True, cwd=str(FRONTEND), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env, timeout=600,
    )
    return (p.stdout or "") + (p.stderr or "")


def main() -> int:
    arm = sys.argv[1]
    orig = V8.read_bytes()
    sha0 = hashlib.sha256(orig).hexdigest()[:16]
    rep: dict = {"tree": str(FRONTEND.parent), "arm": arm, "sha0": sha0, "cases": []}
    print("V8 sha256[:16]:", sha0)

    if arm == "A":
        old = EN_SENTENCE.encode("utf-8")
        new = EN_MUTANT.encode("utf-8")
        print("anchor hits:", orig.count(old))
        try:
            with temporary_guarded_replace(V8, old, new) as g:
                gate_out = run_playwright("e2e/qoder-budget-advisory-tiers.spec.ts", GATE_NODE, 1)
                (EVID / "o226_A_gate_cn.log").write_text(gate_out, encoding="utf-8")
                probe_out = run_playwright("e2e/rt-probe-en-locale.spec.ts", "rt-probe-en-locale", 2)
                (EVID / "o226_A_probe_en.log").write_text(probe_out, encoding="utf-8")
                rep["cases"].append({
                    "key": "A_english_mutant",
                    "receipt": {"anchor_hits": g.anchor_hits, "bytes_changed": g.bytes_changed,
                                "before": g.before_sha256[:16], "mutated": g.mutated_sha256[:16]},
                    "gate_cn": {"red": "x  " in gate_out, "green": "ok 2" in gate_out},
                    "probe_en": {"ran": "ok 2" in probe_out or "passed" in probe_out},
                })
        finally:
            pass
        restored = hashlib.sha256(V8.read_bytes()).hexdigest()[:16]
        rep["cases"][-1]["restored_exact"] = restored == sha0
        print("A:", json.dumps(rep["cases"][-1], ensure_ascii=False)[:400])

    elif arm == "B":
        old = TEXT_LINE.encode("utf-8")
        new = TEXT_MUTANT.encode("utf-8")
        print("anchor hits:", orig.count(old))
        try:
            with temporary_guarded_replace(V8, old, new) as g:
                out = run_playwright("e2e/qoder-budget-advisory-tiers.spec.ts", GATE_NODE, 3)
                (EVID / "o226_B_text_mutant.log").write_text(out, encoding="utf-8")
                rep["cases"].append({"key": "B_text_allay", "receipt": {"anchor_hits": g.anchor_hits, "bytes_changed": g.bytes_changed},
                                     "gate": {"red": "x  2" in out, "green": "ok 2" in out}})
        finally:
            pass
        rep["cases"][-1]["restored_exact"] = hashlib.sha256(V8.read_bytes()).hexdigest()[:16] == sha0
        print("B:", json.dumps(rep["cases"][-1], ensure_ascii=False)[:300])

    elif arm == "C":
        # C1 全角空格：把常量里的半角空格（" 人 · " 那段）换一个
        c1_old = ZH_SENTENCE.encode("utf-8")
        c1_new = ZH_SENTENCE.replace("可以先调整预算", "可以先\u3000调整预算").encode("utf-8")
        # C2 零宽字符
        c2_new = ZH_SENTENCE.replace("可以先调整预算", "可以先\u200b调整预算").encode("utf-8")
        for label, newb in (("C1_ideographic_space", c1_new), ("C2_zero_width", c2_new)):
            try:
                with temporary_guarded_replace(V8, c1_old, newb) as g:
                    out = run_playwright("e2e/qoder-budget-advisory-tiers.spec.ts", GATE_NODE, 4 if label.startswith("C1") else 5)
                    (EVID / f"o226_{label}.log").write_text(out, encoding="utf-8")
                    rep["cases"].append({"key": label, "receipt": {"anchor_hits": g.anchor_hits, "bytes_changed": g.bytes_changed},
                                         "gate": {"red": "x  2" in out, "green": "ok 2" in out}})
            finally:
                pass
            rep["cases"][-1]["restored_exact"] = hashlib.sha256(V8.read_bytes()).hexdigest()[:16] == sha0
            print(label, ":", json.dumps(rep["cases"][-1], ensure_ascii=False)[:250])
    else:
        print("unknown arm"); return 2

    out = HERE / f"d2305848_o226_arm{arm}.json"
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
