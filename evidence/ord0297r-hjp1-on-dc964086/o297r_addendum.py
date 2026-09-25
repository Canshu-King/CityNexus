"""Append the post-insert readings to the ledger as their own block.

The delivery block says "本块的句级尺判定不在块里自宣" -- so the verdicts can only appear *after* the block
was inserted and then measured.  This is a second block (new heading, nothing edited) carrying exactly
those numbers plus the extraction bug I found in my own gauge runner.
"""
import hashlib
import io
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = r"D:\moodle\_qoder_hjp1_o207_20260922"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
RUNS = json.load(io.open(os.path.join(LANE, "o297r_ruler_runs.json"), encoding="utf-8"))
ANCHOR = "### 1a986a24 HJ-P1 · ORD-0297r @"


def sha1b(b):
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


def one(stage_frag, ruler_frag, obj_frag=""):
    for r in RUNS["runs"]:
        if (stage_frag in r["stage"] and r["ruler"].startswith(ruler_frag)
                and (not obj_frag or obj_frag in (r.get("judged_object") or ""))):
            return r
    return {}


b = RUNS["block_extracted_from_ledger"]
ra, rb = one("a (", "receipt_cell", ".json"), one("b (", "receipt_cell", ".json")
s3j, s4j = one("a (", "claim_coordinate_check_r3", ".json"), one("a (", "claim_coordinate_check_r4b", ".json")
s3b, s4b = one("c (", "claim_coordinate_check_r3"), one("c (", "claim_coordinate_check_r4b")
BLK = """### 1a986a24 HJ-P1 · ORD-0297r 补记（块落账之后现跑的尺，以及我自己仪器里的一个提取 bug）@ @NOW@

上一条里我写了"本块的句级尺判定不在块里自宣"。这是落账之后量出来的那些数，逐条给对象：

| 谁量的（blob 40 位） | 量的是哪份字节 | 结果 |
| --- | --- | --- |
| `receipt_cell_derivation_check_r2.py` `@R2B@` | 派生完就冻结的收据 `@OBJA@`（@KEYSA@ 个顶层键、@CELLSA@ 格） | `@OA@` / cells @CA@ / hard @HA@ / soft @SA@ |
| 同一把尺，收据被 stage a 的判定追加过之后 | `@OBJB@`（@KEYSB@ 个顶层键、@CELLSB@ 格） | `@OB@` / cells @CB@ —— 判定加进去不改变判定 |
| `claim_coordinate_check_r3.py` `@R3B@` | 收据 JSON 面 | `@O3J@`（claims @C3J@、findings @F3J@、rc @RC3J@） |
| `claim_coordinate_check_r4b.py` `@R4B@` | 收据 JSON 面 | `@O4J@`（claims @C4J@、exempt @E4J@、findings @F4J@、rc @RC4J@） |
| `claim_coordinate_check_r3.py` | 账本块本体（从账本按标题切出来、逐字节比对与发布件相同） | `@O3@`（claims @C3@、findings @F3@、rc @RC3@） |
| `claim_coordinate_check_r4b.py` | 同一份块字节 | `@O4@`（claims @C4@、findings @F4@、rc @RC4@） |

块在账本里的字节与身份：@BYTES@ B，blob `@BLOB@`（写这条时它在第 @L0@–@L1@ 行；本补记插在它上面，插完行号就会整体下移——账本每次插入都是全文重写，所以**认 blob，不认行号**）。

**我自己仪器里的一个真 bug（具名，不粉）**：第一次"量账本块"是从我的标题往下取 200 行——那已经不是我的块，是把后面别的车道的正文一起量了，于是一幅 `Q43_GATE_RED` 被当成"我的块红"印了出来；同一版还让 Python 在 Windows 上把 LF 写成 CRLF，所以被量的字节和落账的字节不是同一份。现在按"切到下一个标题为止 + newline='' 原样字节"重切重跑，上面 r3/r4b 那两行就是重跑后的读数（`o297r_ruler_runs.json` 把 10 次运行逐条列在一起，包含被这两个 bug 污染的那几次，没有删）。

JSON 面那两发红不是我的格错了：`Q50=①`（`issuecomment-5829176662`，号令者转达，durable 等级 COMMANDER_RELAYED）已裁定机器生成的测量表这一面对句级坐标尺是 `RULER_OUT_OF_SCOPE`。原样输出全部随件发布，不做解释性改写。
边界：权威线 0 次移动、手机链 0 次变更、`demo/reset` 0 次、凭据 0 打印、已发布路径 0 覆盖；本补记只新增块，未改动上一条任何一个字。
"""
T = {"@NOW@": time.strftime("%H:%M+08", time.localtime()),
     "@R2B@": ra.get("blob40"), "@R3B@": s3j.get("blob40"), "@R4B@": s4j.get("blob40"),
     "@OBJA@": "o297r_measured_object.json", "@OBJB@": "o297r_measured_object_b.json",
     "@KEYSA@": ra.get("judged_object_top_level_key_count"), "@CELLSA@": ra.get("cells_found"),
     "@KEYSB@": rb.get("judged_object_top_level_key_count"), "@CELLSB@": rb.get("cells_found"),
     "@OA@": ra.get("overall"), "@CA@": ra.get("cells_found"), "@HA@": ra.get("hard"), "@SA@": ra.get("soft"),
     "@OB@": rb.get("overall"), "@CB@": rb.get("cells_found"),
     "@O3J@": s3j.get("overall"), "@C3J@": s3j.get("claims_checked"), "@F3J@": s3j.get("findings"),
     "@RC3J@": s3j.get("rc"),
     "@O4J@": s4j.get("overall"), "@C4J@": s4j.get("claims_checked"), "@F4J@": s4j.get("findings"),
     "@E4J@": s4j.get("exempt"), "@RC4J@": s4j.get("rc"),
     "@O3@": s3b.get("overall"), "@C3@": s3b.get("claims_checked"), "@F3@": s3b.get("findings"),
     "@RC3@": s3b.get("rc"),
     "@O4@": s4b.get("overall"), "@C4@": s4b.get("claims_checked"), "@F4@": s4b.get("findings"),
     "@RC4@": s4b.get("rc"),
     "@L0@": b["ledger_lines"][0], "@L1@": b["ledger_lines"][1], "@BYTES@": b["bytes"], "@BLOB@": b["blob40"]}
for k, v in T.items():
    assert v is not None, "no reading behind %s" % k
    BLK = BLK.replace(k, str(v))
import re
leftover = re.findall(r"@[A-Z0-9]+@", BLK)
assert not leftover, "unsubstituted tokens: %s" % sorted(set(leftover))
assert "None" not in BLK, "a None leaked into the prose"
io.open(os.path.join(LANE, "_blk_0297r_addendum.md"), "w", encoding="utf-8", newline="\n").write(BLK)
print(BLK[:1200])
print("...bytes", len(BLK.encode("utf-8")))

if "--insert" in sys.argv:
    NL = chr(10)
    s = io.open(LEDGER, encoding="utf-8", newline="").read()
    rows = s.split(NL)
    idxs = [n for n, l in enumerate(rows) if l.startswith(ANCHOR)]
    assert len(idxs) == 1, "delivery block anchor matched %d lines" % len(idxs)
    body = BLK.rstrip(NL)
    rows.insert(idxs[0], body)
    io.open(LEDGER, "w", encoding="utf-8", newline="").write(NL.join(rows))
    chk = io.open(LEDGER, encoding="utf-8", newline="").read()
    crows = chk.split(NL)
    mine = [n for n, l in enumerate(crows) if l.startswith("### 1a986a24 HJ-P1 · ORD-0297r 补记")]
    prev = [n for n, l in enumerate(crows) if l.startswith(ANCHOR)]
    print(json.dumps({"addendum_at_line": mine[0] + 1, "delivery_block_now_at_line": prev[0] + 1,
                      "occurrences": [len(mine), len(prev)],
                      "crlf_before_after": [s.count(chr(13) + NL), chk.count(chr(13) + NL)],
                      "bytes_before_after": [len(s.encode("utf-8")), len(chk.encode("utf-8"))]},
                     ensure_ascii=False))
    assert len(mine) == 1 and prev[0] == mine[0] + len(body.split(NL))
