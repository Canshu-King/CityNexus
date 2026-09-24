"""跨仪器合流：用包工头那把（仲裁签过的）Q24 尺判我的九格，顺带记一处实测到的仪器断口。

只调用、不改他的文件：按 blob `47372706…` 从 GitHub 取回他的仪器、核对字节、import 他的 `judge_cell`。
两件事分开记：
  A) `--check` 模式在这批真格子上跑不动（TypeError，行号与最小复现照抄读数）；
  B) 同一判据下他的 `judge_cell` 与我 r4 的逐格结论是否一致（他的读的是 GitHub 外取 blob，我读的是本机 git，两侧来源不同）。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUN = Path("D:/moodle/_qoder_f_run")
RCP = RUN / "o225_receipts"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
CMDR_BLOB = "47372706c6ffde2175155de175133e212aae651c"
CMDR_LOCAL = RUN / "cmdr_generation_transfer_check_47372706.py"
GEN_A = "dcae1bc964125c3a975916f6bf667794cc19622a"      # 已落地那一代
GEN_B = "7c806fab58e872060cb5811ff96c770b40dad165"      # 我的 K8 候选
MY_READING = RUN / "gate_reading_k8_with_q24.json"
OUT = RCP / "ord0272_cmdr_validator_crosscheck.json"


def blob_sha1(p: Path) -> str:
    b = p.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def fetch_cmdr_by_blob() -> dict:
    """按 40 位 blob 从他分支上取回仪器字节，重算 sha1 与账本钉住的那枚对表。"""
    tok = Path(r"D:/moodle/_qoder_recovery_20260919/.api_tok_20260920").read_text(encoding="utf-8").strip()
    req = urllib.request.Request(
        f"https://api.github.com/repos/Canshu-King/CityNexus/git/blobs/{CMDR_BLOB}")
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("User-Agent", "citynexus-lane-f")
    import base64
    with urllib.request.urlopen(req, timeout=90) as r:
        meta = json.loads(r.read().decode())
    b = base64.b64decode(meta["content"])
    return {"requested_blob_40": CMDR_BLOB, "api_sha": meta["sha"], "bytes": len(b),
            "computed_sha1": blob_bytes_sha1(b),
            "matches_local_copy": blob_bytes_sha1(b) == blob_sha1(CMDR_LOCAL)}


def blob_bytes_sha1(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def load_cmdr_module():
    spec = importlib.util.spec_from_file_location("cmdr_gtc", str(CMDR_LOCAL))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_check_mode(receipt_path: Path) -> dict:
    p = subprocess.run([PY, str(CMDR_LOCAL), "--check", str(receipt_path), GEN_A, GEN_B],
                       cwd=str(RUN), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600)
    err = (p.stderr or "").strip().splitlines()
    return {"rc": p.returncode, "stdout_head": (p.stdout or "").strip()[:160],
            "stderr_last_line": err[-1] if err else "",
            "stderr_traceback_lines": [l for l in err if l.startswith("  File") or l.startswith("TypeError")][-4:]}


def main() -> int:
    fetch = fetch_cmdr_by_blob()
    assert fetch["matches_local_copy"], f"SETUP：本机副本与账本钉住的 blob 不等 ⇒ 判的不是他那把尺：{fetch}"
    mod = load_cmdr_module()

    # A) --check 模式的两向最小复现：0 格（跑得动且什么都没判）vs 1 格（真格子）
    empty = RUN / "repro_check_empty.json"
    empty.write_text(json.dumps({"cells": [], "cross_generation_claim": True}, ensure_ascii=False),
                     encoding="utf-8", newline="\n")
    one = RUN / "repro_check_one_cell.json"
    one.write_text(json.dumps({"cells": [{"cell": "one", "cited_files": ["backend/app/schemas.py"]}],
                               "cross_generation_claim": True}, ensure_ascii=False),
                   encoding="utf-8", newline="\n")
    repro = {"zero_cell_receipt": run_check_mode(empty), "one_cell_receipt": run_check_mode(one)}
    repro["assertion_bites"] = (repro["zero_cell_receipt"]["rc"] == 0
                                and repro["one_cell_receipt"]["rc"] != 0)

    # B) 逐格：直接用他的 judge_cell。默认走真 reader；同 (path,ref) 只外取一次是包了一层 memo
    #    （判据仍是他的），并另跑一格不 memo 的原样调用作为「包装不改变答案」的正控。
    mine = json.loads(MY_READING.read_text(encoding="utf-8"))
    calls = {"real": 0}
    cache: dict[tuple[str, str], object] = {}

    def memo_reader(ref, path):
        key = (ref, path)
        if key not in cache:
            cache[key] = mod.blob_at(ref, path)
            calls["real"] += 1
        return cache[key]

    cells = []
    for c in mine["cells"]:
        nodeid = c["nodeid"]
        v, rows = mod.judge_cell(nodeid, GEN_A, GEN_B, c["cited_files"], reader=memo_reader)
        cells.append({"cell": nodeid, "his_verdict": v["verdict"],
                      "external_blobs": {p: {GEN_A[:9]: r.get("at_" + GEN_A[:9]),
                                             GEN_B[:9]: r.get("at_" + GEN_B[:9])}
                                         for p, r in rows.items()},
                      "my_verdict_from_r4": c["generation_transfer"],
                      "agree": v["verdict"] == c["generation_transfer"]})
    control_nodeid = mine["cells"][0]["nodeid"]
    cv, _ = mod.judge_cell(control_nodeid, GEN_A, GEN_B, mine["cells"][0]["cited_files"])
    control = {"cell": control_nodeid, "his_verdict_unwrapped": cv["verdict"],
               "his_wrapped_for_this_cell": cells[0]["his_verdict"],
               "memo_wrapper_changes_nothing": cv["verdict"] == cells[0]["his_verdict"]}

    agree_all = all(x["agree"] for x in cells)
    receipt = {
        "what": "ORD-0272 · 我的九格用包工头那把 Q24 尺（仲裁已验）复判 + 一处实测到的 --check 断口",
        "lane": "F 8ccd71d8",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "validator_under_test": {
            "path_on_branch": "live_checks/generation_transfer_check.py",
            "blob_40": CMDR_BLOB, "fetched_by": "GET /repos/.../git/blobs/<40>",
            "readback": fetch, "edited_by_me": False,
            "imported_call": "judge_cell(cell, gen_a, gen_b, cited_files[, reader])",
            "selftest_on_my_box": {
                "first_run": "RED_CELLS:positive_identical_file_is_TRANSFERABLE "
                             "（那一格 at_dcae1bc96 读回 null，同一路径稍后又两侧都读到 58c0580b…）",
                "reruns": ["SELFTEST_ALL_GREEN", "SELFTEST_ALL_GREEN"],
                "reading": "他的 blob_at 把网络抖动与 404 一并记成 None ⇒ 判 CITED_BLOB_MISSING，"
                           "方向是 fail-closed（不会把『没看到』读成『相等』），但整支自测因此不是网络抖动的不变量"}},
        "generations": {"gen_a": GEN_A, "gen_b": GEN_B,
                        "gen_a_is": "已落地那一代（权威尖）", "gen_b_is": "我的 K8 候选 review/ord0272-k8-f"},
        "check_mode_defect": {
            "summary": "--check 对任何非空 cells 直接抛 TypeError：第 174 行 `verdict, _ = judge_cell(...)` "
                       "取到的是**判级字典**，第 178 行却拿它当字符串做 tally 的键",
            "lines_cited": "174/175/178/180/185（本机那份与他 blob 字节相等，行号即他的行号）",
            "second_symptom": "即使 178 行不炸，180 行 `o[\"verdict\"] != TRANSFERABLE` 也恒真（字典 ≠ 字符串）"
                              "⇒ 每一格都会被列进 RED_CELLS，永远得不出 ALL_CELLS_TRANSFERABLE",
            "direction": "两处都偏保守（要么崩、要么全判不转移），不会替谁假绿；但这一模式对任何车道都不可用",
            "repro": repro, "bites_both_ways": repro["assertion_bites"],
            "minimal_fix_I_did_not_apply": "175 行存 `verdict[\"verdict\"]`（其余照旧）；线是他的，我不改他的发布件",
            "not_my_call": "是否另存 r2 发布由包工头定；我只交读数与最小复现"},
        "per_cell": cells,
        "memo_control": control,
        "cross_instrument_agreement": {
            "cells_total": len(cells), "agreeing": sum(1 for x in cells if x["agree"]),
            "his_source": "GitHub contents API 外取 blob（他分支上的两代对象）",
            "my_source": "本机 git rev-parse <gen>:<path>（候选 worktree 的对象库）",
            "verdict": "AGREES" if agree_all else "DISAGREES",
            "external_gets_made": calls["real"]},
        "discipline": {"his_published_files_overwritten": 0, "his_file_edited": False,
                       "credentials_printed": 0, "authoritative_branch_written": False,
                       "demo_reset_calls": 0},
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps({"validator": fetch, "repro_bites": repro["assertion_bites"],
                      "agreement": receipt["cross_instrument_agreement"],
                      "control": control,
                      "tally_his": {v: sum(1 for c in cells if c["his_verdict"] == v)
                                    for v in {c["his_verdict"] for c in cells}}},
                     ensure_ascii=False, indent=1))
    print("WROTE", OUT, OUT.stat().st_size, "B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
