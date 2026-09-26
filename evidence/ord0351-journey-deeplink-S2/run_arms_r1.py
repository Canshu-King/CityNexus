"""ORD-0351 两向读数驱动器：同一份 spec，在**尖那一代**与**修好那一代**各跑一次。

为什么两代都要跑：本单的要件是"改前红、改后绿"，而红必须是量出来的。只跑修好的那一代，
一个从不读地址栏的壳也可能被写成"通过"（它只要不报错就行）；先跑尖，才知道那五格真的在判
一件事 —— 尤其 A/B/C/D 四格在尖上应当是红的，E 格在尖上就应该是绿的（它管的是"别把路由名
当成行程"，尖上没人认领任何东西，所以 naturally 绿）。

形制：一次一格不叫两向，所以按 arm 循环；每个 arm 全新的 run id + 全新的 `_*.db`（后端有
fresh-or-no-run 的规矩），端口自己挑、跑前确认空闲；`DEEPSEEK_API_KEY` 从子进程环境里删掉
（authoritative 模式自己会为此拒绝启动，这里只删不打印）。期望的红集合是**跑之前**写下的。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WT = HERE / "wt"
FRONTEND = WT / "frontend"
TIP_MAIN_SNAP = HERE / "snap" / "frontend" / "src" / "main.tsx"
WORKTREE_MAIN = FRONTEND / "src" / "main.tsx"
SPEC = "e2e/qoder-stored-journey-link-is-an-entry.spec.ts"
DB_DIR = HERE / "db"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
TIP_BLOB = "4769a6e3712955cc9e5f20b43ee80e893676a9c0"  # git rev-parse ab12c17a:frontend/src/main.tsx
FRONTEND_PORT = 4791
BACKEND_PORT = 8139
NODES = [
    "ord0351-a-a-link-to-a-saved-trip-opens-that-trip",
    "ord0351-b-a-link-the-server-denies-says-so-by-name",
    "ord0351-c-an-unanswered-link-is-never-blamed-on-the-server",
    "ord0351-d-a-dead-link-empties-a-reference-not-a-trip",
    "ord0351-e-route-names-are-not-journey-links",
]
#: 跑之前写下的期望：尖那一代这四格必须红（壳不读地址栏），E 格必须绿。
EXPECTED = {
    "tip": {NODES[0]: "failed", NODES[1]: "failed", NODES[2]: "failed", NODES[3]: "failed", NODES[4]: "passed"},
    "fixed": {node: "passed" for node in NODES},
}


def git_blob(path: Path) -> str:
    return subprocess.run(
        ["git", "hash-object", "--no-filters", str(path)],
        cwd=str(FRONTEND), capture_output=True, text=True, check=True,
    ).stdout.strip()


def ports_are_free() -> dict:
    import socket

    out = {}
    for port in (FRONTEND_PORT, BACKEND_PORT):
        s = socket.socket()
        out[port] = "free" if s.connect_ex(("127.0.0.1", port)) != 0 else "listening"
        s.close()
    return out


def run_arm(arm: str, main_bytes: bytes, run_stamp: str) -> dict:
    WORKTREE_MAIN.write_bytes(main_bytes)
    assert git_blob(WORKTREE_MAIN) == expected_blob(arm), f"{arm}: 换上去的 main.tsx 不是我预期的那一代"
    run_id = f"o351{arm}{run_stamp}"
    DB_DIR.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    dropped = [k for k in ("DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY") if k in env]
    for key in dropped:
        env.pop(key, None)
    env.update(
        {
            "CITYNEXUS_E2E_AUTHORITATIVE": "1",
            "CITYNEXUS_E2E_PORT": str(FRONTEND_PORT),
            "CITYNEXUS_BACKEND_PORT": str(BACKEND_PORT),
            "CITYNEXUS_PYTHON": PY,
            "CITYNEXUS_E2E_RUN_ID": run_id,
            "CITYNEXUS_DATABASE_URL": f"sqlite:///{(DB_DIR / f'_{run_id}.db').as_posix()}",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_EVIDENCE_DIR": (HERE / "evidence" / f"{arm}_{run_stamp}").as_posix(),
        }
    )
    cmd = ["node", "node_modules/@playwright/test/cli.js", "test", SPEC,
           "--project=chromium", "--no-deps", "--reporter=json"]
    proc = subprocess.run(cmd, cwd=str(FRONTEND), env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=1800)
    (HERE / f"report_{arm}.json").write_text(proc.stdout, "utf-8")
    return {
        "arm": arm,
        "command": " ".join(cmd),
        "cwd": str(FRONTEND),
        "exit": proc.returncode,
        "run_id": run_id,
        "database_url": env["CITYNEXUS_DATABASE_URL"],
        "db_exists": (DB_DIR / f"_{run_id}.db").exists(),
        "ai_key_names_removed_from_child_env": dropped,
        "stderr_tail": (proc.stderr or "")[-2500:],
        "results": parse_report(HERE / f"report_{arm}.json"),
    }


def expected_blob(arm: str) -> str:
    return TIP_BLOB if arm == "tip" else FIXED_BLOB


def parse_report(path: Path) -> dict:
    try:
        report = json.loads(path.read_text("utf-8"))
    except Exception as exc:  # noqa: BLE001 - a report that will not parse is itself a reading
        return {"parse_error": f"{type(exc).__name__}: {exc}"}
    out: dict = {}
    collected = 0

    def walk(node: dict) -> None:
        nonlocal collected
        for suite in node.get("suites", []):
            walk(suite)
        for spec in node.get("specs", []):
            for test in spec.get("tests", []):
                for res in test.get("results", []):
                    collected += 1
                    # Playwright's title carries the node id plus its 中文说明, joined by an em dash.
                    title = spec.get("title", "").split(" — ")[0]
                    out[title] = {
                        "status": res.get("status"),
                        "duration_ms": res.get("duration"),
                        "error": ((res.get("error") or {}).get("message") or "")[:600],
                    }

    walk(report)
    out["_collected_executed"] = collected
    return out


def main() -> int:
    if not TIP_MAIN_SNAP.exists():
        print(f"缺尖那一代的 main.tsx 副本：{TIP_MAIN_SNAP}")
        return 2
    global FIXED_BLOB
    fixed_bytes = WORKTREE_MAIN.read_bytes()
    FIXED_BLOB = git_blob(WORKTREE_MAIN)
    tip_bytes = TIP_MAIN_SNAP.read_bytes()
    if git_blob(TIP_MAIN_SNAP) != TIP_BLOB:
        print("snap 里那枚 main.tsx 与尖上的 blob 不等，两向读数不成立")
        return 2
    free = ports_are_free()
    if list(free.values()) != ["free", "free"]:
        print(f"端口不空闲，这一轮会挂到别人的进程上：{free}")
        return 2
    stamp = time.strftime("%H%M%S")
    readings = {
        "order": "ORD-0351",
        "spec": SPEC,
        "pre_written_expectations": EXPECTED,
        "playwright_version": json.loads(
            (FRONTEND / "node_modules" / "@playwright" / "test" / "package.json").read_text("utf-8")
        )["version"],
        "node_version": sys.version.split()[0] + " / " + subprocess.run(["node", "-v"], capture_output=True,
                                                                        text=True).stdout.strip(),
        "worktree_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(FRONTEND), capture_output=True,
                                         text=True).stdout.strip(),
        "main_tsx_tip_blob": TIP_BLOB,
        "main_tsx_fixed_blob": FIXED_BLOB,
        "ports": free,
        "arms": {},
        "written_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    for arm, blob in (("tip", tip_bytes), ("fixed", fixed_bytes)):
        readings["arms"][arm] = run_arm(arm, blob, stamp)
        print(f"[{arm}] exit={readings['arms'][arm]['exit']} "
              f"nodes={ {k: v.get('status') for k, v in readings['arms'][arm]['results'].items() if k != '_collected_executed'} }")
    WORKTREE_MAIN.write_bytes(fixed_bytes)
    readings["restored_blob_after_run"] = git_blob(WORKTREE_MAIN)
    readings["restored_equals_fixed"] = readings["restored_blob_after_run"] == FIXED_BLOB

    verdicts = {}
    for arm in ("tip", "fixed"):
        results = readings["arms"][arm]["results"]
        got = {node: (results.get(node) or {}).get("status", "MISSING") for node in NODES}
        verdicts[arm] = {"expected": EXPECTED[arm], "got": got,
                         "matches_expectation": got == EXPECTED[arm]}
    readings["verdicts"] = verdicts
    readings["two_way"] = (verdicts["tip"]["matches_expectation"] and verdicts["fixed"]["matches_expectation"]
                           and readings["restored_equals_fixed"])
    target = HERE / f"ord0351_two_way_readings_r1_{stamp}.json"
    target.write_text(json.dumps(readings, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print("readings:", target.name)
    print("two_way =", readings["two_way"])
    for arm in ("tip", "fixed"):
        print(f"  {arm}: {verdicts[arm]['got']}  match={verdicts[arm]['matches_expectation']}")
    return 0 if readings["two_way"] else 1


if __name__ == "__main__":
    sys.exit(main())
