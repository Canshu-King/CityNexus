"""The ORD-0320 bus post: short, and every number in it is read out of the published artefact.

The order gave two cells as examples of FIX_IN_PRODUCT; my measurement puts one of them elsewhere, so
that disagreement is stated up front with its reason rather than buried at the bottom.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
SC = ROOT / "_scratch_0320"
REC = json.loads((SC / "ord0320_triage_r2.json").read_text(encoding="utf-8"))
DIR = "evidence/ord0320-triage-d"
OUT = SC / "ord0320-post.md"
CLOSING = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt")


def blob_of(p: Path) -> str:
    data = p.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


rows = REC["rows"]
buckets = {}
for r in rows:
    buckets[r["bucket"]] = buckets.get(r["bucket"], 0) + 1
t02 = next(r for r in rows if r["id"] == "T02")
t15 = next(r for r in rows if r["id"] == "T15")
TR = REC["generation_transfer"]
inbox = sorted(Path("D:/moodle/_qoder_ledger_inbox").glob("d-e345b9d6_*.md"))[-1]

L = []
L.append(f"【D 车道 e345b9d6 → 号令者 494abfd7｜ORD-0320 交（{datetime.now().astimezone():%m-%d %H:%M}）："
         f"16 枚 `upstream_prose` 分完桶，只读，产品字节 0 改动】")
L.append("")
L.append(
    f"三桶：`FIX_IN_PRODUCT` {buckets['FIX_IN_PRODUCT']} 枚、`COMPLIANT_WITH_ATTRIBUTION` "
    f"{buckets['COMPLIANT_WITH_ATTRIBUTION']} 枚、`NEEDS_RULING` {buckets['NEEDS_RULING']} 枚，"
    f"合计 {sum(buckets.values())} 枚 = 清扫件 `classification_tally.upstream_prose`。"
    f"收据 `{DIR}/ord0320_triage_r2.json` {SC.joinpath('ord0320_triage_r2.json').stat().st_size:,} B "
    f"blob `{blob_of(SC / 'ord0320_triage_r2.json')}`（先上架的 `…_r1.json` 一字未改，只是被 r2 超过，"
    f"因为 r1 没有代次复验）。")
L.append("")
L.append(
    f"**一处与你那块举例不一致，先说在前面**：你把 `{t02['file'].replace('frontend/src/', '')}"
    f":{t02['ruler_anchor_line']}` 列为 FIX 的例子，我这侧量下来只能给 `NEEDS_RULING`，理由是"
    f"可查的两件事：① 该文件本身 0 处读响应字段（`{t02['file'].replace('frontend/src/', '')}:104` 渲染的是"
    f"别处抛出的 `Error.message` 与 React 组件栈）；② 全树把响应字段塞进 `Error.message` 的 thrower 共 "
    f"{len(REC['population_upstream_throwers'])} 枚（逐枚 cite 在收据同一个字段里），但错误边界只接得住 "
    f"render/effect 阶段的抛出，事件处理器里的 throw 走不到它面前。所以这是**阶段问题**，不是有没有链的问题。"
    f"若你按『只要可能携上游句子就算』的口径来定，我立刻把它转 FIX——缺的是这句定义，不是证据。")
L.append("")
L.append(
    f"另外两枚 `NEEDS_RULING` 是同一个问题：`features/agent/AgentComposer.tsx:95` 与 "
    f"`features/agent/CopilotDock.tsx:615` 上屏的是服务器写的**助手回话**（不是失败原因）。"
    f"Q64 没定义『服务器 authored 的内容通道』算不算上游正文 ⇒ 我不把它偷转成前两桶。")
L.append("")
L.append(
    f"`COMPLIANT_WITH_ATTRIBUTION` 那枚就是 Q67 等裁的 `PlanWithAiSheet.tsx:{t15['ruler_anchor_line']}`："
    f"我判的是形状——同一块里有 `data-reason-origin` 与两处具名标签（「服务器给出的原因 / 这台设备自己的读数」）。"
    f"**尖在我跑单中途动了**：清扫代次 commit=`{TR['sweep_tip']}` → 现读 commit="
    f"`{TR['current_tip_read_after_the_rows']}`（`same=false`），"
    f"{sum(1 for v in TR['per_cell'].values() if v['verdict'] == 'CITES_HOLD_ON_BOTH_TIPS')} 枚格所在文件"
    f"两代逐字节相同、引用照旧；剩 1 枚（`PlanWithAiSheet.tsx`，blob 变了）我按 sink 原文在新尖上重定位到 "
    f"`frontend/src/features/planning/PlanWithAiSheet.tsx:"
    f"{':'.join(str(x) for x in TR['per_cell']['T15']['remeasured_at_current_tip']['found_at_lines'])}`"
    f"，同窗口归因标签行 "
    f"`:{':'.join(str(x[0]) for x in TR['per_cell']['T15']['remeasured_at_current_tip']['attribution_within_the_same_window'][:3])}`"
    f" ⇒ 结论带得过去，但**行号请用新尖这一组**。")
L.append("")
L.append(
    f"手机那一列：{sum(1 for r in rows if r['phone_side']['verdict'] == 'REACHABLE_IF_THE_STATE_OCCURS')} 枚"
    f" = `REACHABLE_IF_THE_STATE_OCCURS`（组件到根的 import 链逐枚量的，例 `main.tsx`），0 枚 UNKNOWN；"
    f"未知的那一步具名：served bundle 的 asset 归属我没查（边界：不碰手机链、不跑 `vite build`）。"
    f"账本块已按规矩投 `_qoder_ledger_inbox/{inbox.name}`（{inbox.stat().st_size:,} B，blob "
    f"`{blob_of(inbox)}`，Q43 r4c 自查 `--expect-clean` rc=0）。"
    f"边界：产品字节 0、推 ref 0、`demo/reset` 0、凭据打印 0；量具三件也同目录上架"
    f"（`ord0320-tool-triage.py` blob `{blob_of(ROOT / 'review/ord0320_triage_d.py')}` 等）。")
L.append("")
L.append(CLOSING.read_bytes().decode("utf-8"))
text = "\n".join(L) + "\n"
OUT.write_bytes(text.encode("utf-8"))
print(f"wrote {OUT} {OUT.stat().st_size:,} B blob={blob_of(OUT)}")
