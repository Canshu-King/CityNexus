"""ORD-0253 门证据：改动前 / 改动后各跑一次同一份门文件，并顺手证明"已发布 patch 能重出候选提交"。

跑法（等全量频率对比结束后再跑，避免两棵树同时抢临时库）：
  python o253_gate_evidence.py
所有数字都由本脚本现场算出，不从对话里抄。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = "D:/moodle/_qoder_integration_20260919"
WT = Path("D:/moodle/_qoder_f_ord253_20260923")
GATE_REL = "backend/tests/test_qoder_agent_command_idempotency.py"
BASE = "dea8410be809ebf6c5046581873584e9dbf32b64"
CAND = "a4a452c08889eea3fb2d61bcc0068a6ff8c4366e"
PATCH = Path("D:/moodle/_qoder_f_run/o225_receipts/ord0253_f_a4a452c.patch")
EXPORT = Path("D:/moodle/_qoder_f_run/e_ord0253_dea8410")   # 复用已有导出树（D 盘 98%，不再开第二份 110 MB）
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
OUT = Path("D:/moodle/_qoder_f_run/o225_receipts/ord0253_gate_before_after.json")
COUNT_RE = re.compile(r"(\d+) (?:passed|error)")
FAIL_RE = re.compile(r"^FAILED (\S+)", re.MULTILINE)
COLLECT_RE = re.compile(r"(\d+) items? collected|collected (\d+) items?")


def git(*a: str, binary: bool = False):
    p = subprocess.run(["git", "-C", REPO, *a], capture_output=True)
    return p.stdout if binary else p.stdout.decode("utf-8", "replace").strip()


def pytest_run(root: Path, gate_path: str, collect_only: bool) -> dict:
    cmd = [PY, "-m", "pytest", "--no-header", "-p", "no:cacheprovider", gate_path]
    cmd += ["--collect-only", "-q"] if collect_only else ["-q", "--tb=no", "-rf"]
    p = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1500)
    out = p.stdout or ""
    tail = next((l for l in reversed(out.splitlines()) if "passed" in l or "collected" in l
                 or "error" in l), "")
    m = re.search(r"(\d+)", tail)
    return {"exit_code": p.returncode, "summary_line": tail,
            "count": int(m.group(1)) if m else None,
            "failed_nodeids": sorted(set(FAIL_RE.findall(out)))}


def main() -> int:
    res: dict = {"generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                 "gate_file_blob_in_candidate": git("rev-parse", f"{CAND}:{GATE_REL}"),
                 "gate_file_sha256_12": hashlib.sha256((WT / GATE_REL).read_bytes()).hexdigest()[:12]}

    # ① 已发布 patch 能否重出候选提交（不看文件名，看树）——**纯 plumbing，不碰工作树**
    idx = Path(f"/tmp/o253idx_{datetime.datetime.now():%H%M%S}")
    env = dict(os.environ, GIT_INDEX_FILE=str(idx))
    subprocess.run(["git", "-C", REPO, "read-tree", BASE], env=env, check=True)
    applied = subprocess.run(["git", "-C", REPO, "apply", "--cached", str(PATCH)],
                             env=env, capture_output=True, text=True)
    applied_ok = applied.returncode == 0
    tree_after = subprocess.run(["git", "-C", REPO, "write-tree"], env=env,
                                capture_output=True, text=True).stdout.strip()
    idx.unlink(missing_ok=True)
    cand_tree = git("rev-parse", f"{CAND}^{{tree}}")
    base_tree = git("rev-parse", f"{BASE}^{{tree}}")
    res["published_patch_replay"] = {
        "method": "read-tree(base) → git apply --cached <已发布 patch> → write-tree（临时 index，0 次 checkout）",
        "apply_rc": applied.returncode, "apply_stderr": (applied.stderr or "")[:200],
        "patch_blob_sha1": hashlib.sha1(b"blob %d\0" % PATCH.stat().st_size
                                        + PATCH.read_bytes()).hexdigest(),
        "replayed_tree": tree_after, "candidate_tree": cand_tree, "base_tree": base_tree,
        "reproduces_candidate": bool(applied_ok) and tree_after == cand_tree,
        "temp_index_left_behind": str(idx) if idx.exists() else "无",
    }

    # ② 同一份门文件：改动前的主线上跑一次（真实形态，不是合成反例），改动后再跑一次
    if not EXPORT.exists():
        EXPORT.mkdir(parents=True)
        subprocess.run(f"git -C {REPO} archive {BASE} | tar -x -C {EXPORT}", shell=True, check=True)
    (EXPORT / GATE_REL).write_bytes((WT / GATE_REL).read_bytes())
    before_col = pytest_run(EXPORT / "backend", f"tests/{Path(GATE_REL).name}", True)
    before = pytest_run(EXPORT / "backend", f"tests/{Path(GATE_REL).name}", False)
    after_col = pytest_run(WT / "backend", f"tests/{Path(GATE_REL).name}", True)
    after = pytest_run(WT / "backend", f"tests/{Path(GATE_REL).name}", False)
    res["gate_before_fix"] = {
        "tree": f"git archive {BASE[:7]} 导出（**没有**我的补丁）+ 同一份门文件",
        "collected": before_col.get("count"), "summary": before["summary_line"],
        "exit_code": before["exit_code"], "failed": before["failed_nodeids"],
        "failed_count": len(before["failed_nodeids"]),
    }
    res["gate_after_fix"] = {
        "tree": f"候选 worktree @ {CAND[:7]}（分支 agent/f-ord253-candidates）",
        "collected": after_col.get("count"), "summary": after["summary_line"],
        "exit_code": after["exit_code"], "failed": after["failed_nodeids"],
        "failed_count": len(after["failed_nodeids"]),
    }
    turned_green = sorted(set(before["failed_nodeids"]) - set(after["failed_nodeids"]))
    res["reading"] = {
        "由红转绿": turned_green, "由红转绿数量": len(turned_green),
        "改动后仍红": sorted(after["failed_nodeids"]),
        "结论": ("验收形状在改动前必然红、改动后全绿 ⇒ 这 10 格量的就是本单要的东西；"
                 "若某格改前改后都绿，那一格就不该被算作本单的证明"),
        "两向都有": bool(before["failed_nodeids"]) and not after["failed_nodeids"],
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"\nWROTE {OUT} ({OUT.stat().st_size} B)")
    return 0 if res["reading"]["两向都有"] and res["published_patch_replay"]["reproduces_candidate"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
