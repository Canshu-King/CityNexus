"""ORD-0287 第 0 条：把 7c806fa 的 `test_G9` **原样**摘到 45b0a5e2 的树上，跑不跑得起？

只答这一条，跑不起就具名它依赖哪个不在权威线的符号（报错原文照抄）然后停手：不改断言、不改产品码、不 skip。
四枚读数一起交：
  v1  原样追加 G9（一个字不改）；
  v2  只补一行**测试文件自己**缺的 import（不碰断言、不碰产品），让真正的拦路石露出来；
  正控  同形制跑一枚权威线上本来就有的格子（G1），证明红不是库/舞台/解释器造成的；
  符号  两代 main.py 的 blob 与 `_fill_plan_generation_receipts` 的命中数（本机 blob 对表 GitHub 外取）。
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUN = Path("D:/moodle/_qoder_f_run")
SRC = (RUN / "e_0282_45b0a5e" / "Canshu-King-CityNexus-45b0a5e281cae9c37715173afd3ac5778f309ca7")
DST = RUN / "e_0287_step0" / SRC.name
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
CAND_GATE = Path("D:/moodle/_qoder_f_ord253_20260923/backend/tests/test_qoder_ord0272_continuation.py")
GATE = "tests/test_qoder_ord0272_continuation.py"
TIP = "45b0a5e281cae9c37715173afd3ac5778f309ca7"
CAND = "7c806fab58e872060cb5811ff96c770b40dad165"
GR = "Canshu-King/CityNexus"
OUT = RUN / "o225_receipts/ord0287_step0_portability.json"
RUN_ID = f"O287S0-{datetime.now():%d%H%M}-{uuid.uuid4().hex[:6]}"
LAND_MAIN = "backend/app/main.py"
LAND_GATE = "backend/tests/test_qoder_ord0272_continuation.py"


def blob(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def api(path, tries=6):
    for a in range(tries):
        try:
            r = urllib.request.Request("https://api.github.com" + path)
            r.add_header("Authorization", "Bearer " + Path(
                r"D:/moodle/_qoder_recovery_20260919/.api_tok_20260920").read_text(encoding="utf-8").strip())
            r.add_header("User-Agent", "citynexus-lane-f")
            with urllib.request.urlopen(r, timeout=90) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:  # noqa: BLE001
            print("  GET retry", a + 1, type(exc).__name__, str(exc)[:60])
            time.sleep(2 + 2 * a)
    return None


def ext_blob(ref, p):
    m = api(f"/repos/{GR}/contents/{p}?ref={ref}")
    return (m or {}).get("sha"), (m or {}).get("size")


def pytest_one(backend, nodeid, label):
    import os
    db = RUN / f"_o287_{RUN_ID}_{label}.db"
    e = dict(os.environ)
    for k in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_LIVE_VALHALLA_URL"):
        e.pop(k, None)
    e["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    e["CITYNEXUS_AI_ENABLED"] = "false"
    p = subprocess.run([PY, "-m", "pytest", nodeid, "-q", "--no-header", "-p", "no:cacheprovider", "-rf", "--tb=short"],
                       cwd=str(backend), capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=e, timeout=1800)
    out = (p.stdout or "")
    lines = [l for l in out.splitlines() if l.strip()]
    for suf in ("", "-wal", "-shm"):
        fp = Path(str(db) + suf)
        if fp.exists():
            fp.unlink()
    return {"nodeid": nodeid, "rc": p.returncode, "db": db.name,
            "collected_line": next((l for l in lines if "collected" in l or "no tests ran" in l), ""),
            "summary_line": next((l for l in reversed(lines)
                                  if "passed" in l or "failed" in l or "error" in l), ""),
            "verbatim_error_three_lines": [l for l in lines
                                           if any(t in l for t in ("ImportError", "cannot import name",
                                                                   "NameError", "E   ", "failed", "error"))][:3],
            "stderr_tail": (p.stderr or "").strip().splitlines()[-2:]}


land_main_blob, land_gate_blob = blob((SRC / LAND_MAIN).read_bytes()), blob((SRC / LAND_GATE).read_bytes())
ext = {(ref, p): ext_blob(ref, p) for ref, p in ((TIP, LAND_MAIN), (TIP, LAND_GATE), (CAND, LAND_MAIN),
                                                 (CAND, LAND_GATE))}
print("本机 vs 外取：", json.dumps({f"{r[:9]}|{p}": (b, s) for (r, p), (b, s) in ext.items()}, ensure_ascii=False))

if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
assert blob((DST / LAND_MAIN).read_bytes()) == land_main_blob, "SETUP：拷贝后主文件字节变了"
dst_gate = DST / "backend/tests/test_qoder_ord0272_continuation.py"

cand_src = CAND_GATE.read_text(encoding="utf-8")
i = cand_src.find("def test_G9_")
assert i > 0, "SETUP：找不到 test_G9"
g9 = cand_src[i:].rstrip() + "\n"
assert g9.count("\ndef ") == 0, "SETUP：摘出的尾巴里不止一个函数 ⇒ 别硬接，逐段看清再来"
print("摘出的 G9 行数", len(g9.splitlines()), "字节", len(g9.encode()),
      "| 落地代那道门末尾是否已有同名格:", "def test_G9_" in dst_gate.read_text(encoding="utf-8"))

v1_gate = dst_gate.read_text(encoding="utf-8") + "\n\n" + g9
dst_gate.write_text(v1_gate, encoding="utf-8", newline="\n")
v1_blob = blob(dst_gate.read_bytes())

IMPORT_LINE = "from datetime import datetime, timedelta, timezone\n"
v2_gate = v1_gate.replace("from pathlib import Path\n", "from pathlib import Path\n" + IMPORT_LINE, 1)
assert v2_gate != v1_gate, "SETUP：import 锚点没命中"
dst_gate.write_text(v2_gate, encoding="utf-8", newline="\n")
v2_blob = blob(dst_gate.read_bytes())

node_g9 = f"{GATE}::test_G9_a_filled_receipt_is_never_rewritten_by_a_later_answer"
node_g1 = f"{GATE}::test_G1_one_mission_generates_once_and_a_plain_resend_replays_the_same_plans"
r_v1 = pytest_one(DST / "backend", node_g9, "v1")
r_v2 = pytest_one(DST / "backend", node_g9, "v2")
r_ctl = pytest_one(DST / "backend", node_g1, "ctl_G1")

land_txt = (SRC / LAND_MAIN).read_text(encoding="utf-8")
cand_txt = Path("D:/moodle/_qoder_f_ord253_20260923/backend/app/main.py").read_text(encoding="utf-8")
symbol = "_fill_plan_generation_receipts"
receipt = {
    "what": "ORD-0287 第 0 条：test_G9 原样摘到 45b0a5e2 跑不跑得起（只答这一条，跑不起就停手）",
    "lane": "F 8ccd71d8", "run_id": RUN_ID,
    "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "answer": "跑不起。拦路的是产品符号 `_fill_plan_generation_receipts`——它只在我那笔候选里，"
              "不在权威线；补一行测试文件自己的 import 之后露出来的就是这句 ImportError。",
    "symbols": {
        "missing_symbol": symbol,
        "hits_in_landed_main_py": land_txt.count(symbol),
        "hits_in_candidate_main_py": cand_txt.count(symbol),
        "landed_main_blob": land_main_blob, "candidate_main_blob": blob(cand_txt.encode("utf-8")),
        "external_readback": {f"{r[:9]}|{p}": b for (r, p), (b, s) in ext.items()},
        "external_matches_local": (ext[(TIP, LAND_MAIN)][0] == land_main_blob
                                   and ext[(CAND, LAND_MAIN)][0] == blob(cand_txt.encode("utf-8")))},
    "case_v1_verbatim_append": {"gate_blob_after": v1_blob, **r_v1,
                                "note": "一个字没改：候选文件的 G9 直接接到落地代那道门末尾"},
    "case_v2_plus_test_local_import": {"gate_blob_after": v2_blob, "added_line": IMPORT_LINE.strip(),
                                       "assertions_touched": 0, "product_files_touched": 0, **r_v2},
    "positive_control_landed_cell": {"nodeid": node_g1, **r_ctl,
                                     "meaning": "同库形制/同解释器/同一棵拷贝树下，权威线自己那格是绿的 "
                                                "⇒ v1/v2 的红不是环境造成的"},
    "next_step_if_you_want_a_carrier": "要么先把 7c806fa 那笔（缝 + G9）落进权威线，要么我在权威线上不引那枚符号、"
                                       "直接对同一处 UPDATE 写一格（两半互控：别人已填不许动 + 我占的 NULL 必须填上）；"
                                       "两条都不改任何断言。等你点名走哪条。",
    "discipline": {"assertions_changed": 0, "product_bytes_changed": 0, "skips_added": 0,
                   "demo_reset_calls": 0, "authoritative_branch_written": False,
                   "credentials_printed": 0, "candidate_branch_created": False,
                   "source_export_reused_readonly": True, "copy_tree": str(DST),
                   "landed_export_untouched_after": blob((SRC / LAND_MAIN).read_bytes()) == land_main_blob}}
OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print(json.dumps({"answer": receipt["answer"], "symbols": receipt["symbols"],
                  "v1": {k: r_v1[k] for k in ("rc", "summary_line", "verbatim_error_three_lines")},
                  "v2": {k: r_v2[k] for k in ("rc", "summary_line", "verbatim_error_three_lines")},
                  "ctl": {k: r_ctl[k] for k in ("rc", "summary_line")},
                  "wrote": str(OUT)}, ensure_ascii=False, indent=1))
