"""ORD-0351 邻居门对照：两枚**不是我车道写的**既有门，在尖与修好两代各跑一次，逐格比状态。

为什么按"两代等号"报而不按"绿"报：Q72 —— 门的断言只有门的主人能改。我要证的只有一件事：
我这枚改动没改动它们判的东西。同一仪器、同一端口规则、同一枚空库（`--no-deps`，不带 real-seed
项目，因此 0 次 demo/reset），某一格在两代都红 = 不是我造成的（读数件里点名是哪一格、为什么）。

选哪两枚：
  product-v8.spec.ts            —— 走的就是 /v8/<route> 这一层，我这枚 adopt 若越界，最先在这里露出来；
  qoder-failure-has-an-exit 的 ord0169-a —— 那枚三腿门里唯一不依赖演示种子的一格，我改的正是它管的屏。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
FRONTEND = HERE / "wt" / "frontend"
WORKTREE_MAIN = FRONTEND / "src" / "main.tsx"
TIP_MAIN_SNAP = HERE / "snap" / "frontend" / "src" / "main.tsx"
TIP_BLOB = "4769a6e3712955cc9e5f20b43ee80e893676a9c0"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
FRONTEND_PORT = 4792
BACKEND_PORT = 8140
GATES = [
    {"label": "product-v8", "spec": "e2e/product-v8.spec.ts", "grep": None},
    {"label": "exit-gate-a", "spec": "e2e/qoder-failure-has-an-exit.spec.ts",
     "grep": "ord0169-a-stale-journey-404-is-never-called-a-network-failure"},
]


def blob(path: Path) -> str:
    return subprocess.run(["git", "hash-object", "--no-filters", str(path)], cwd=str(FRONTEND),
                          capture_output=True, text=True, check=True).stdout.strip()


def statuses(report: dict) -> dict:
    out: dict = {}

    def walk(node: dict) -> None:
        for suite in node.get("suites", []):
            walk(suite)
        for spec in node.get("specs", []):
            for test in spec.get("tests", []):
                for res in test.get("results", []):
                    out[spec.get("title", "").split(" — ")[0]] = res.get("status")

    walk(report)
    return out


def run(gate: dict, arm: str, main_bytes: bytes, stamp: str) -> dict:
    WORKTREE_MAIN.write_bytes(main_bytes)
    measured = blob(WORKTREE_MAIN)
    run_id = f"o351n{gate['label']}{arm}{stamp}"
    (HERE / "db").mkdir(exist_ok=True)
    env = dict(os.environ)
    for key in ("DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY"):
        env.pop(key, None)
    env.update(
        {
            "CITYNEXUS_E2E_AUTHORITATIVE": "1",
            "CITYNEXUS_E2E_PORT": str(FRONTEND_PORT),
            "CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT),
            "CITYNEXUS_PYTHON": PY,
            "CITYNEXUS_E2E_RUN_ID": run_id,
            "CITYNEXUS_DATABASE_URL": f"sqlite:///{(HERE / 'db' / f'_{run_id}.db').as_posix()}",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_EVIDENCE_DIR": (HERE / "evidence" / f"neighbors_{gate['label']}_{arm}_{stamp}").as_posix(),
        }
    )
    cmd = ["node", "node_modules/@playwright/test/cli.js", "test", gate["spec"],
           "--project=chromium", "--no-deps", "--reporter=json"]
    if gate["grep"]:
        cmd += ["-g", gate["grep"]]
    proc = subprocess.run(cmd, cwd=str(FRONTEND), env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=1800)
    path = HERE / f"neighbor_report_{gate['label']}_{arm}_{stamp}.json"
    path.write_text(proc.stdout, "utf-8")
    try:
        parsed = statuses(json.loads(path.read_text("utf-8")))
    except Exception as exc:  # noqa: BLE001
        parsed = {"_parse_error": f"{type(exc).__name__}: {exc}"}
    return {"arm": arm, "main_tsx_blob_measured": measured, "command": " ".join(cmd),
            "exit": proc.returncode, "run_id": run_id, "report_file": path.name,
            "statuses": parsed, "stderr_tail": (proc.stderr or "")[-1000:]}


def main() -> int:
    if blob(TIP_MAIN_SNAP) != TIP_BLOB:
        print("snap 那枚 main.tsx 与尖不等，对照不成立")
        return 2
    fixed_bytes = WORKTREE_MAIN.read_bytes()
    fixed_blob = blob(WORKTREE_MAIN)
    stamp = time.strftime("%H%M%S")
    arms: dict = {}
    for gate in GATES:
        tip = run(gate, "tip", TIP_MAIN_SNAP.read_bytes(), stamp)
        fixed = run(gate, "fixed", fixed_bytes, stamp)
        common = sorted(set(tip["statuses"]) & set(fixed["statuses"]))
        drift = [n for n in common if tip["statuses"][n] != fixed["statuses"][n]]
        only = sorted(set(tip["statuses"]) ^ set(fixed["statuses"]))
        arms[gate["label"]] = {
            "spec": gate["spec"],
            "tip": tip,
            "fixed": fixed,
            "nodes_compared": len(common),
            "drift": drift,
            "nodes_present_in_only_one_arm": only,
            "red_both_arms": [n for n in common if tip["statuses"][n] == "failed"],
            "clean": (not drift and not only and tip["main_tsx_blob_measured"] == TIP_BLOB
                      and fixed["main_tsx_blob_measured"] == fixed_blob and len(common) > 0),
        }
        print(f"[{gate['label']}] tip={tip['statuses']}")
        print(f"[{gate['label']}] fixed={fixed['statuses']}")
        print(f"[{gate['label']}] compared={len(common)} drift={drift} only={only}")
    WORKTREE_MAIN.write_bytes(fixed_bytes)
    restored = blob(WORKTREE_MAIN)
    out = {
        "purpose": "existing gates owned by other lanes: same instrument, tip vs fixed, per-node status equality",
        "main_tsx_tip_blob": TIP_BLOB,
        "main_tsx_fixed_blob": fixed_blob,
        "restored_equals_fixed": restored == fixed_blob,
        "gates": arms,
        "zero_drift": all(g["clean"] for g in arms.values()) and restored == fixed_blob,
        "written_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    target = HERE / f"ord0351_neighbor_gates_r1_{stamp}.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print("readings:", target.name, "zero_drift =", out["zero_drift"])
    return 0 if out["zero_drift"] else 1


if __name__ == "__main__":
    sys.exit(main())
