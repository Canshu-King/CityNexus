#!/usr/bin/env python3
"""同代复验（ORD-0272）r2：落地后**一条命令**复跑，不需要交付方在场。

r3 补的是包工头 02:2x 实测到的工具形状缺陷：导出树若被解在**另一个 git 仓库里面**，
工具从上层取到的是那台仓库的 HEAD ⇒ cell 级 `exact_sha` 会盖成**别人的 sha**（他第一次跑
就撞到：8 格里 stamp 成了 e9efec6bff2f…，而不是落地 sha）。r3 的规则：解析到的 HEAD 与申报
sha 不等、或 git 根不是被验树本身 ⇒ verdict=SHA_SOURCE_MISMATCH 并**退出**（不盖章、不出读数），
自测里两向都钉：嵌在别的仓库里必拒、干净目录必绿。

r2 改的两处（都是包工头 00:0x 点名的坐标缺陷）：① K2/K3/K4 与 K6 首条载体 nodeid 之前写成
`backend/tests/...` 而记录的 run cwd 是 `<tree>/backend` ⇒ 4 条根不对，verifier 按 nodeid 复收会
“收不到”；② 收集判定原本只比 `::` 后面的格名，所以那 4 条错根被读成了 collect=True —— 现在按
**整条 nodeid 相等**判定，并给出 mismatch_kind（ROOT-MISMATCH / CELL-ABSENT）与可复跑的 collect 命令。

用法
----
  python o272_reverify.py --tree <落地后的工作树根> [--gen <换代 bundle 名>]
                          [--python <解释器>] [--json <输出文件>]
  python o272_reverify.py --selftest --tree <有门的树> --absent-tree <没有门的树>

输出
----
  · 八格门：逐格 nodeid + PASS/FAIL + (exact_sha, nodeid, run_shape) 三元组
  · 反突变载体归属：K1–K8 每一臂**具名**它该带走哪一格（取自 mutation_receipt.json 的
    arms[*].carriers_removed），并逐条核对那个 nodeid 在**落地树里还能被收集到**（改名即报 MISSING）
  · K8 的归属：本臂在单进程里没有载体 —— 打印它的跨进程归属给 verifier，本命令**不宣称**已验
  · 顺带（不改变本单判据）：本单回归的两枚既存载体文件也跑一遍

只读声明（本脚本自己的纪律，也是它唯一的写动作都在这句里）
--------------------------------------------------------
  1) 只在被测树里**跑 pytest**：带 `-p no:cacheprovider` 与 `PYTHONDONTWRITEBYTECODE=1`，
     不落 `.pytest_cache` / `__pycache__`；
  2) **不部署、不起服务、不发网络请求**；
  3) **不写任何数据库**：套件按 ORD-0211 自己用一次性临时库，本脚本把 pytest 报告头里
     "ORD-0211 test database: resolved=…" 那行原样贴出来当证据，并断言其中不含 `_live.db`/`_preview.db`；
  4) 不动被测树：对被验的产品/门文件跑前跑后各算一次 sha256，落任何差异都判 FAIL；
  5) 本命令的 verdict 只由八格门推导；载体表是**归属说明**，不是把存活说成击杀。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GATE_FILE = "backend/tests/test_qoder_ord0272_continuation.py"          # 仓库根相对（存在性/sha256）
GATE_TARGET = "tests/test_qoder_ord0272_continuation.py"                # 跑 pytest 时用 backend 相对
PRODUCT_FILES = ["backend/app/main.py", "backend/app/schemas.py", GATE_FILE,
                 "contracts/openapi.yaml"]
#: 本单回归的两枚既存载体（顺带跑；不是因为它们是本单判据）
REGRESSION_TARGETS = ["tests/test_qoder_current_plan_is_named.py",
                      "tests/test_qoder_simulation_mode.py"]


def load_arms(receipt: str | None) -> dict | None:
    """臂表只认 campaign 收据，不认仪器里的副本。

    为什么（r4 修的第二处松尺）：r3 内嵌了一份 ARM_CARRIERS，K8 在 campaign 里升格成有载体的一臂之后，
    仪器里它还是 `0/0` —— 副本不会自己跟上事实。读不到收据就返回 None，由调用方**拒判**，不给绿。
    """

    if not receipt:
        return None
    path = Path(receipt)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for name, arm in data["arms"].items():
        out[name] = {"line_named": arm["line_named"],
                     "carriers_removed": arm["carriers_removed"],
                     "carriers_declared_by": "campaign 收据 arms[*].carriers_removed（本工具不再自带副本）",
                     "claimed_result_from_receipt": arm["claimed_result"],
                     "cross_process_note": arm.get("note") or ""}
    named = data.get("denominator", {}).get("named_carriers") or []
    return {"arms": out, "named_carriers": [n for n in named if GATE_TARGET in n],
            "receipt_head": data.get("coordinates", {}).get("head")}


def sha256_file(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def pick_python(tree: Path, given: str | None) -> str:
    if given:
        return given
    for cand in (tree / ".venv/Scripts/python.exe", tree / "backend/.venv/Scripts/python.exe",
                 Path("D:/moodle/CityNexus/.venv/Scripts/python.exe")):
        if cand.is_file():
            return str(cand)
    return sys.executable


def git_of(tree: Path, *args: str) -> str | None:
    p = subprocess.run(["git", "-C", str(tree), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.stdout.strip() if p.returncode == 0 else None


def run_pytest(tree: Path, python: str, targets: list[str], extra: list[str] | None = None) -> dict:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"          # 只读声明 (1)：不往被测树里落 __pycache__
    cmd = [python, "-X", "utf8", "-m", "pytest", *targets, "--tb=line",
           "-p", "no:cacheprovider", *(extra or [])]   # 刻意不带 -q/--no-header：ORD-0211 的库路径就在报告头里，-q 会把整块头吞掉（实测）
    p = subprocess.run(cmd, cwd=str(tree / "backend"), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800, env=env)
    out = p.stdout or ""
    failed = sorted(set(re.findall(r"^(?:FAILED|ERROR) (\S+?::\S+)", out, re.M)))
    summary = next((l for l in reversed(out.splitlines())
                    if re.search(r"\d+ (passed|failed|error)", l)), "<没有汇总行>")
    db_line = next((l for l in out.splitlines() if "ORD-0211 test database" in l), None)
    return {"rc": p.returncode, "failed": failed, "summary": summary.strip(),
            "db_header_line": db_line,
            "command": " ".join(cmd) + f"   (cwd={tree / 'backend'})"}


def collected(tree: Path, python: str, targets: list[str]) -> list[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    p = subprocess.run([python, "-m", "pytest", *targets, "--collect-only", "-q",
                        "-p", "no:cacheprovider"], cwd=str(tree / "backend"), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=900, env=env)
    return sorted({ln.split(" ")[0] for ln in (p.stdout or "").splitlines() if "::" in ln})


def _as_sha(value: str | None) -> str | None:
    """--gen 里常写成 `ord0272-corrected-<40hex>`；能提出 40 位十六进制就当申报 sha 用。"""
    import re
    if not value:
        return None
    m = re.search(r"[0-9a-f]{40}", value)
    return m.group(0) if m else None


def verify(tree: Path, gen: str | None, python: str | None,
           declared_sha: str | None = None, mutation_receipt: str | None = None) -> dict:
    tree = tree.resolve()
    py = pick_python(tree, python)
    declared = declared_sha or _as_sha(gen)
    toplevel = git_of(tree, "rev-parse", "--show-toplevel")
    head40 = git_of(tree, "rev-parse", "HEAD")
    owns_git = bool(toplevel) and Path(toplevel).resolve() == tree
    pre: dict = {"tree": str(tree), "python": py, "gen": gen, "declared_sha": declared,
                 "git_toplevel": toplevel, "git_head_resolved": head40,
                 "git_root_is_the_verified_tree": owns_git}
    # 规则（包工头 02:2x 实测的形状缺陷）：
    #   ① 解析得到 HEAD（哪怕来自**外层仓库**）且与申报 sha 不等 ⇒ SHA_SOURCE_MISMATCH，退出、不盖章；
    #   ② 解析不到 HEAD（git archive 的导出树本来就没有 .git）⇒ 用申报 sha 盖章，但把来源**写明**是
    #      declared，不冒充 git-resolved；
    #   ③ 既没申报、又解析不到可信 HEAD ⇒ SHA_SOURCE_UNTRUSTED（拿不出坐标就明说）。
    # ②′ 外层仓库的 HEAD 与被验快照无关：**哪怕申报值恰好等于它也不给过**（第一版 r3 放过了这一例，
    #     实测 = 嵌在别的仓库里 + 申报外层 HEAD → GATE-GREEN，那就是把别人的戳盖在我的读数上）。
    if head40 and not owns_git:
        pre["verdict"] = "SHA_SOURCE_MISMATCH"
        pre["sha_source"] = f"OUTER-REPO HEAD of {toplevel}（与被验快照无关）"
        pre["reason"] = (f"被验树 {tree} 不是自己的 git 根，但 git 往上解析到了 {head40}（属于外层仓库 "
                         f"{toplevel}）。这种形状的 exact_sha 一定是错的 —— 包工头实测到的正是它（戳成了那台"
                         f"仓库的 HEAD）。要么把快照解到**周围没有 .git 的目录**（走申报戳），要么在树自己的"
                         f" git 检出上跑。申报值是否等于外层 HEAD 都不作为放行条件。")
        return pre
    if owns_git and declared and head40 != declared:
        pre["verdict"] = "SHA_SOURCE_MISMATCH"
        pre["sha_source"] = "git-resolved"
        pre["reason"] = (f"被验树自己的 git 根 HEAD={head40} 与申报 sha={declared} 不等 ⇒ 退出，"
                         f"不给任何一格盖别人的戳")
        return pre
    if not head40 and not declared:
        pre["verdict"] = "SHA_SOURCE_UNTRUSTED"
        pre["reason"] = ("周围没有 git、又没有 --expect-sha/--gen 里的 40 位申报 ⇒ 这一代给不出可信坐标；"
                         "请申报落地 sha 后重跑")
        return pre
    pre["sha_source"] = ("git-resolved（被验树自己就是 git 根）" if owns_git
                         else "declared(--expect-sha / --gen)")
    pre["stamp_sha"] = head40 if owns_git else declared
    pre["content_provenance"] = ("verified-by-git" if owns_git else
                                 "declared-only：本树周围无 .git，读数只证明『这一代能跑』，"
                                 "不证明『这一代 == 该 sha』")
    arms = load_arms(mutation_receipt)
    gate = tree / GATE_FILE
    before = {f: sha256_file(tree / f) for f in PRODUCT_FILES}
    cache_before = {rel: (tree / rel).exists()
                    for rel in ("backend/.pytest_cache", ".pytest_cache")}
    report: dict = {
        **pre,
        "gen": gen or (head40[:9] if head40 else "<没给 --gen 且不是 git 树>"),
        "tree_head40": head40,
        "tree_branch": git_of(tree, "rev-parse", "--abbrev-ref", "HEAD"),
        "started_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "read_only": ["-p no:cacheprovider + PYTHONDONTWRITEBYTECODE=1（不落 .pytest_cache/__pycache__）",
                      "不部署、不起服务",
                      "不写任何数据库（套件用 ORD-0211 一次性临时库；本报告贴出该行并断言不含 _live.db）",
                      "跑前跑后对被验文件做 sha256，任何差异判 FAIL"],
        "verdict": "NOT-PRESENT", "cells": [], "arms": {}, "extra": {},
        "silent_alarms": [],
        "pytest_cache_preexisting": None,
    }
    if not (tree / "backend" / "tests").is_dir():
        looks_like_backend = (tree / "tests").is_dir()
        report["reason"] = (
            "本命令要的是**仓库根**（含 backend/tests）。你给的这不是一个能复验的树"
            + ("：看起来你传的是 backend 本身（里面有 tests/）" if looks_like_backend else "")
            + " ⇒ 这不是绿，是没验。")
        return report
    if not gate.is_file():
        report["reason"] = f"落地树里没有门文件 {GATE_FILE} ⇒ 这一代不可用本命令复验（不是绿）"
        report["files_before"] = before
        report["files_after"] = {f: sha256_file(tree / f) for f in PRODUCT_FILES}
        return report

    present = collected(tree, py, [GATE_TARGET])
    present_tails = {n.split("::", 1)[1] for n in present}
    declared_cells = [n.split("::")[1] for n in (arms or {}).get("named_carriers", [])]
    if not declared_cells:
        report["verdict"] = "ARM_TABLE_UNTRUSTED"
        report["reason"] = ("没有可信的 campaign 收据（--mutation-receipt 没给或读不到，或它没写"
                            " named_carriers）⇒ 期望格子清单无从确定，本工具拒判，不给绿")
        return report
    missing = [c for c in declared_cells if c not in present_tails]
    extra = sorted({c for c in present_tails if c not in declared_cells})
    if missing:
        report["verdict"] = "CELLS-MISSING"
        report["reason"] = (f"收据点名的格子里有收集不到的：{missing} ⇒ 门被改名/删过，别当绿；"
                            f"树里另有点名之外的格 {extra}（新格要进收据）")
        return report
    report["cells_declared_by"] = {"source": "campaign 收据 denominator.named_carriers",
                                   "collected_extra_not_in_receipt": extra}

    gate_run = run_pytest(tree, py, [GATE_TARGET], extra=["-rf"])
    red = {n.split("::", 1)[1] for n in gate_run["failed"]}
    run_shape = gate_run["command"]
    report["run_shape"] = run_shape
    report["db_header_line"] = gate_run["db_header_line"]
    report["silent_alarms"] += ([] if gate_run["db_header_line"] else
                                ["pytest 报告头里没有 ORD-0211 那行 ⇒ 库隔离无法证明"])
    if gate_run["db_header_line"] and re.search(r"_live\.db|_preview\.db", gate_run["db_header_line"]):
        report["silent_alarms"].append("解析出的库名命中 _live.db/_preview.db ⇒ 拒绝判绿")
    for cell in declared_cells:
        report["cells"].append({
            "nodeid": f"{GATE_TARGET}::{cell}", "exact_sha": report["stamp_sha"],
            "run_shape": run_shape,
            "result": "RED" if cell in red else "GREEN",
        })
    report["cells_summary"] = gate_run["summary"]

    # 载体归属：逐臂具名 + 核对那个 nodeid 在落地树里仍可收集
    scope = [GATE_TARGET, "tests/test_v1923_final_code_gate.py",
             "tests/test_v1924_final_truth_gate.py"]
    pool = set(collected(tree, py, scope))
    pool_tails = {n.split("::", 1)[1] for n in pool}
    for arm, spec in arms["arms"].items():
        resolved = []
        for nid in spec["carriers_removed"]:
            tail = nid.split("::", 1)[1]
            # 整条相等才算「可收集」：格名在但根不对 ⇒ ROOT-MISMATCH（上一版就是只比格名，把 4 条错根
            # 读成了 collect=True；那种宽松判定等于没有判定）
            resolved.append({"nodeid": nid,
                             "collectible_in_landed_tree": nid in pool,
                             "mismatch_kind": ("OK" if nid in pool else
                                               "ROOT-MISMATCH(cell 在树里存在，路径根不对)"
                                               if tail in pool_tails else "CELL-ABSENT"),
                             "collect_cmd": f"python -m pytest --collect-only -q {nid}"})
        report["arms"][arm] = {
            "line_named": spec["line_named"], "carriers_removed": resolved,
            "collectible_count": sum(1 for r in resolved if r["collectible_in_landed_tree"]),
            "expected": len(resolved),
            "cross_process_owner": spec.get("cross_process_owner"),
        }
        if len(resolved) != sum(1 for r in resolved if r["collectible_in_landed_tree"]):
            report["silent_alarms"].append(f"{arm}: 有载体 nodeid 在落地树里收集不到（改名了？）")

    extra = run_pytest(tree, py, REGRESSION_TARGETS, extra=["-rf"])
    report["extra"] = {"what": "本单回归的两枚既存载体（顺带；不改变本单判据）",
                       "targets": REGRESSION_TARGETS, "summary": extra["summary"],
                       "failed": extra["failed"]}

    report["pytest_cache_preexisting"] = cache_before
    report["files_before"] = before
    report["files_after"] = {f: sha256_file(tree / f) for f in PRODUCT_FILES}
    if any(before[f] != report["files_after"][f] for f in PRODUCT_FILES):
        report["silent_alarms"].append("被验文件的 sha256 在跑前跑后变了 ⇒ 本命令声称的只读不成立")
    for rel in ("backend/.pytest_cache", ".pytest_cache"):
        if not cache_before[rel] and (tree / rel).exists():
            report["silent_alarms"].append(
                f"{rel} 是本次跑**新出现的** ⇒ 只读声明 (1) 破（跑前没有它）")

    all_green = all(c["result"] == "GREEN" for c in report["cells"])
    report["verdict"] = ("GATE-GREEN" if all_green and not report["silent_alarms"] else
                         "GATE-RED" if not all_green else "GATE-GREEN-WITH-ALARM")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="ORD-0272 同代复验（只读）")
    ap.add_argument("--tree", required=True, help="落地后的工作树根")
    ap.add_argument("--gen", default=None, help="换代后的 bundle 名（不给就从 git 推）")
    ap.add_argument("--python", default=None, help="解释器（不给就依次找 tree/.venv、backend/.venv、已知 venv）")
    ap.add_argument("--json", default=None, help="把读数写到这个文件")
    ap.add_argument("--absent-tree", default=None, help="仅 --selftest 用：没门的树，用来验证反向")
    ap.add_argument("--nested-tree", default=None,
                    help="仅 --selftest 用：被解在**别的 git 仓库里面**的导出树，必须被拒")
    ap.add_argument("--expect-sha", default=None,
                    help="申报的落地 sha（40 位）；与解析到的 HEAD 不等 ⇒ SHA_SOURCE_MISMATCH，不盖章")
    ap.add_argument("--mutation-receipt", default=None,
                    help="campaign 收据路径：臂表与点名格子只从这里读（读不到就拒判）")
    ap.add_argument("--pair", default=None,
                    help="Q24 两代：<代A sha>,<代B sha>；对每个被引文件出两侧 40 位 blob 并逐格判可转移性")
    ap.add_argument("--selftest", action="store_true",
                    help="五向自测：有门的树算读数 / 没门的树必须 NOT-PRESENT / 错根探针必须 BITES / "
                         "嵌在别的仓库里必须被拒 / 不给 campaign 收据必须拒判")
    a = ap.parse_args()

    if a.selftest:
        good = verify(Path(a.tree), a.gen, a.python, a.expect_sha, a.mutation_receipt)
        bad = (verify(Path(a.absent_tree), a.gen, a.python, a.expect_sha, a.mutation_receipt)
               if a.absent_tree else None)
        nested = (verify(Path(a.nested_tree), a.gen, a.python, a.expect_sha,
                         a.mutation_receipt) if a.nested_tree else None)
        noarms = verify(Path(a.tree), a.gen, a.python, a.expect_sha, None)
        ok = good["verdict"].startswith("GATE-") and bad is not None and \
            bad["verdict"] == "NOT-PRESENT"
        print(f"[selftest] 有门的树 -> {good['verdict']}（收据点名 " f"{len(good['cells'])} 格，"
              f"{sum(1 for c in good['cells'] if c['result'] == 'GREEN')}/{len(good['cells'])} 绿）")
        print(f"[selftest] 没有那扇门的树 -> {bad['verdict'] if bad else '<没给 --absent-tree>'}")
        # 反向探针：故意把一条载体写成 backend/ 根，严格的整条相等判定必须把它判成 ROOT-MISMATCH
        probe_pool = {"tests/test_qoder_ord0272_continuation.py::x"}
        probe_tails = {n.split("::", 1)[1] for n in probe_pool}
        wrong = "backend/tests/test_qoder_ord0272_continuation.py::x"
        bite = (wrong not in probe_pool) and (wrong.split("::", 1)[1] in probe_tails)
        print(f"[selftest] 错根探针（backend/…::x 必被判不匹配）-> {'BITES' if bite else 'LOOSE'}")
        ok = ok and bite
        if nested is not None:
            rej = str(nested.get("verdict", "")).startswith("SHA_SOURCE_")
            print(f"[selftest] 嵌在别的仓库里的导出树 -> {nested.get('verdict')}"
                  f"{'（被拒：不给别人的 HEAD 盖章）' if rej else '（没被拒 ⇒ 工具兜不住这个形状）'}")
            ok = ok and rej
        else:
            print("[selftest] 没给 --nested-tree ⇒ SHA 来源这一向**未测**（不算过）")
            ok = False
        rej2 = str(noarms.get("verdict", "")) == "ARM_TABLE_UNTRUSTED"
        print(f"[selftest] 不给 campaign 收据 -> {noarms.get('verdict')}"
              f"{'（拒判：仪器不再自带臂表副本）' if rej2 else '（没拒 = 还在用副本凑绿）'}")
        ok = ok and rej2
        print("SELFTEST_PASS" if ok else "SELFTEST_FAIL")
        return 0 if ok else 5

    report = verify(Path(a.tree), a.gen, a.python, a.expect_sha, a.mutation_receipt)
    if a.pair and str(report.get("verdict", "")).startswith("GATE-"):
        ga, gb = [x.strip() for x in a.pair.split(",")][:2]
        files = [f for f in PRODUCT_FILES if (Path(a.tree) / f).is_file()]
        rows, per_file = [], {}
        for f in files:
            ba = git_of(Path(a.tree), "rev-parse", "--verify", "-q", f"{ga}:{f}")
            bb = git_of(Path(a.tree), "rev-parse", "--verify", "-q", f"{gb}:{f}")
            per_file[f] = {ga: ba, gb: bb}
            if not ba or not bb:
                v, why = "NOT_TRANSFERABLE_GENERATION", "缺任一代的 blob 读数"
            elif ba == bb:
                v, why = "TRANSFERABLE_BY_CITED_BLOB_EQUALITY", "两代 40 位逐位相等"
            else:
                v, why = "NOT_TRANSFERABLE_GENERATION", "两代内容不同 ⇒ 该格须在目标代重跑"
            rows.append({"file": f, "cited_blob_at_each_generation": {ga: ba, gb: bb},
                         "generation_transfer": v, "reason": why})
        cited = [r["file"] for r in rows]
        for cell in report.get("cells", []):
            unequal = [r["file"] for r in rows
                       if r["generation_transfer"] != "TRANSFERABLE_BY_CITED_BLOB_EQUALITY"]
            cell["cited_files"] = cited
            cell["cited_blob_at_each_generation"] = {f: per_file[f] for f in cited}
            cell["generation_transfer"] = ("TRANSFERABLE_BY_CITED_BLOB_EQUALITY"
                                           if not unequal else "NOT_TRANSFERABLE_GENERATION")
            cell["transfer_blocking_files"] = unequal
        report["q24"] = {"rule": "GENERATION_TRANSFER_BY_CITED_BLOB_EQUALITY_V1（仲裁 Q24 = ①）",
                        "pair": [ga, gb], "files": rows,
                        "cells_transferable": sum(1 for c in report["cells"]
                                                  if c["generation_transfer"].startswith("TRANSFERABLE")),
                        "cells_total": len(report["cells"]),
                        "unit": "观察格：每格只许声明实际跑过的那一代；引用旧代须逐文件两侧 blob 相等"}
    print(json.dumps(report, ensure_ascii=False, indent=1))
    if a.json:
        Path(a.json).write_text(json.dumps(report, ensure_ascii=False, indent=1),
                                encoding="utf-8", newline="\n")
        print(f"WROTE {a.json}")
    if str(report.get("verdict", "")).startswith("SHA_SOURCE_"):
        return 6
    if report["verdict"] == "NOT-PRESENT":
        return 3
    if report["verdict"] == "CELLS-MISSING":
        return 4
    return 0 if report["verdict"].startswith("GATE-GREEN") else 1


if __name__ == "__main__":
    raise SystemExit(main())
