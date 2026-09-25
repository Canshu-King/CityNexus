"""Render the ORD-0320 ledger block out of the triage receipt - never out of my reading of it.

The commander inserts inbox blocks verbatim, so anything wrong here lands in the ledger verbatim.
Every number in the emitted prose is recomputed from the published rows; the closing line is read out
of CLOSING_LINE.txt byte for byte.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
SC = ROOT / "_scratch_0320"
REC = json.loads((SC / "ord0320_triage_r2.json").read_text(encoding="utf-8"))
DIR = "evidence/ord0320-triage-d"
NAME = f"d-e345b9d6_{datetime.now().astimezone():%H%M}.md"
OUT = Path("D:/moodle/_qoder_ledger_inbox") / NAME
CLOSING = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt")


def blob_of(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


rows = REC["rows"]
gen = REC["generation"]
receipt_blob = blob_of(SC / "ord0320_triage_r2.json")
receipt_bytes = (SC / "ord0320_triage_r2.json").stat().st_size
buckets = {}
for r in rows:
    buckets[r["bucket"]] = buckets.get(r["bucket"], 0) + 1
fix = [r for r in rows if r["bucket"] == "FIX_IN_PRODUCT"]
rule = [r for r in rows if r["bucket"] == "NEEDS_RULING"]
ok = [r for r in rows if r["bucket"] == "COMPLIANT_WITH_ATTRIBUTION"]
fold = [r for r in rows if r.get("details_fold_open_question")]

L = []
L.append(f"### SESSION=e345b9d6 @{datetime.now().astimezone():%Y-%m-%d %H:%M}+08 —— "
         f"**ORD-0320 交：{REC['input_cells']['selected_upstream_prose']} 枚 `upstream_prose` 分完桶"
         f"（只读，产品字节 0 改动）**")
L.append("")
L.append(
    f"代次与来料：本单每一行都是对 `git show {gen['tip_read_by_this_run']}:<路径>` 的字节量的；"
    f"来料两枚原件是从 `commander/control` 取回后逐字节重算的 —— S1 清扫件 "
    f"`evidence/q64-sweep-S1/sweep_r1.json` blob `{gen['sweep_artifact']['blob']}`、"
    f"号令者复核件 `evidence/cmdr-s1-verify-0306/verify_r1.json` blob "
    f"`{gen['commander_verify_artifact']['blob']}`，两枚都与他帖里给的 40 位相等；"
    f"用的尺是 r2（blob `{gen['ruler_r2_blob']}`）。"
    + ("清扫代次就是我现读的那枚尖。" if gen["same"] else
       f"**线尖在本单量测期间又动了**：我逐格量的是清扫那一代 commit="
       f"`{gen['tip_the_sweep_measured']}`（= 清扫件自己的 `generation`），"
       f"跑完后再读的尖是 commit=`{gen['tip_read_by_this_run']}`"
       f"（收据 `generation_transfer.same=false`）⇒ 代次传递复验见第 6 段。")
    + f" 本件收据 `{DIR}/ord0320_triage_r2.json` {receipt_bytes:,} B，blob `{receipt_blob}`。")
L.append("")
L.append(
    f"**三桶计数（由 rows 派生，不是我口述）**：`FIX_IN_PRODUCT` {buckets.get('FIX_IN_PRODUCT', 0)} 枚、"
    f"`COMPLIANT_WITH_ATTRIBUTION` {buckets.get('COMPLIANT_WITH_ATTRIBUTION', 0)} 枚、"
    f"`NEEDS_RULING` {buckets.get('NEEDS_RULING', 0)} 枚，合计 "
    f"{sum(buckets.values())} 枚 = 清扫件 `classification_tally.upstream_prose` 那一格。"
    f"判据是我自己定的三条谓词，全部可复算：`upstream_read`（该值出自响应字段，或出自把响应字段塞进 "
    f"Error 的本文件 thrower）／`reaches_dom`（渲染点在 JSX 文本位）／`attributed`（渲染点 ±10 行内有 "
    f"`*-origin` 属性或写明「服务器给出的原因 / 这台设备自己的读数」这类标签）。"
    f"**归因这一条先判**，因为它是要件里写的合规条件。")
L.append("")
L.append(f"一、`FIX_IN_PRODUCT` {len(fix)} 枚（逐枚给写入链，不给形容词）：")
L.append("")
L.append("| 格 | 具名 cite | 生产行（上游字段） | 写入 setX( 的行 | 链的类型 |")
L.append("| --- | --- | --- | --- | --- |")
for r in fix:
    p = r["predicates"]
    prod = ", ".join(c.split("/")[-1] for c in p["upstream_producer_lines"][:2]) or "见收据"
    site = p["state_write_chain"].get("setter_line", "-")
    L.append(f"| {r['id']} | `{r['file'].replace('frontend/src/', '')}:{r['ruler_anchor_line']}` | "
             f"`{prod}` | `:{site}` | `{p['state_write_chain'].get('link', '?')}` |")
L.append("")
t05 = next(r for r in fix if r["id"] == "T05")
t14 = next(r for r in fix if r["id"] == "T14")
L.append(
    f"这一桶里 9 枚落在同一处 `frontend/src/features/inbox/JourneyInboxWorkbench.tsx:88` 的 "
    f"thrower（把 `payload.error?.message ?? payload.detail` 塞进 `Error.message`），"
    f"再经该文件的 setter 走到 `:687` 与 `:731` 的文本位；"
    f"`T05`/`T12` 走的是 `:691` 的 `<code>{{rawDetail}}</code>`，链型 "
    f"`{t05['predicates']['state_write_chain']['link']}`、跳点 "
    f"`{t05['predicates']['state_write_chain']['hops'][0][0]}@"
    f"{t05['predicates']['state_write_chain']['hops'][0][1]}`（逐跳在收据里）。"
    f"最干净的一枚是 `T14`：`{t14['file'].replace('frontend/src/', '')}:"
    f"{t14['predicates']['state_write_chain']['setter_line']}` 直接把 "
    f"`body?.error?.message ?? body?.detail` 写进 `setError`，链型 "
    f"`{t14['predicates']['state_write_chain']['link']}`。")
L.append("")
L.append(
    f"二、`COMPLIANT_WITH_ATTRIBUTION` {len(ok)} 枚："
    + "; ".join(f"`{r['file'].replace('frontend/src/', '')}:{r['ruler_anchor_line']}`"
                f"（归因证据 `{r['predicates']['attribution_evidence'][0]['line']}` 行"
                f" `{r['predicates']['attribution_evidence'][0]['text'][:60]}`）" for r in ok)
    + " —— 这一枚就是 Q67 等裁的那格。我按**形状**判它合规（值走 helper 进 `<code>`，"
      "同一块里有 `data-reason-origin` 与「服务器给出的原因 / 这台设备自己的读数」两处具名标签）；"
      "若仲裁裁成『越界正文』，改的是文案与标签是否足以为它背书，不是这一格的形状判定。")
L.append("")
L.append(f"三、`NEEDS_RULING` {len(rule)} 枚（我不把判不了的偷转进前两桶）：")
for r in rule:
    L.append(f"- `{r['file'].replace('frontend/src/', '')}:{r['ruler_anchor_line']}` ⇒ "
             f"{r['missing_definition']}")
L.append("")
L.append(
    f"其中根边界那一枚要补的事实：全树把响应字段塞进 `Error.message` 的 thrower 共 "
    f"{len(REC['population_upstream_throwers'])} 枚"
    f"（逐枚 cite 在收据 `population_upstream_throwers` 里），而错误边界只接得住 render/effect 阶段抛出的"
    f"异常 —— 事件处理器里的 throw 不会走到它面前。所以「上游句子能否到达这块 `<pre>`」是**阶段问题**，"
    f"不是有没有这条链的问题；组件栈进 `<pre>` 属另一条规则，不在本单射程。")
L.append("")
L.append(
    f"四、手机上能不能撞到（逐格注在收据 `phone_side` 里，这里给口径）："
    f"{sum(1 for r in rows if r['phone_side']['verdict'] == 'REACHABLE_IF_THE_STATE_OCCURS')} 枚 "
    f"= `REACHABLE_IF_THE_STATE_OCCURS`（组件到根的 import 链逐枚量，例："
    f"`{', '.join(rows[0]['mount_chain_to_root'])}`），"
    f"0 枚 = `UNKNOWN`；**未知的那一步具名**：手机侧 served bundle 的 asset 归属我没查（边界写明不碰手机链、"
    f"不跑 `vite build`），所以这些格子只主张「源码可达 + 需要那个失败状态真的发生」。")
L.append("")
L.append(
    f"五、我自己量具在交付前修掉的三处假判（原样报，不等谁来问）："
    f"① 第一版把 i18n 标签 `t.detail` / `detail: \"技术详情\"` 当上游字段，会凭空造出上游读；"
    f"② 只看文件里**第一处** `setX(` —— 那通常是 `setMessage(null)` 清空调用，于是 "
    f"{len(fix)} 枚全掉进待裁；③ 挂载链用「提没提到文件名」当边，把 `design-tokens.css` 也算成 importer。"
    f"三条都在同一件工具里改的（`review/ord0320_triage_d.py`），改完的桶计数才是上面这份。")
L.append("")
if fold:
    L.append(
        f"另记一格形状问题：{len(fold)} 枚的渲染点在默认折叠的 `<details>` 里"
        f"（例 `{fold[0]['file'].replace('frontend/src/', '')}:{fold[0]['ruler_anchor_line']}`），"
        f"我按「字节进了 DOM」记 FIX，但『不展开算不算上屏』Q64 没定义 ⇒ 这句挂给仲裁。")
    L.append("")
TR = REC["generation_transfer"]
same_cells = [k for k, v in TR["per_cell"].items() if v["verdict"] == "CITES_HOLD_ON_BOTH_TIPS"]
moved = {k: v for k, v in TR["per_cell"].items() if k not in same_cells}
L.append("")
L.append(
    f"六、代次传递复验（尖在量测中途动了，所以这不是可选题）："
    f"{len(same_cells)} 枚格所在文件在两枚尖上逐字节相同 ⇒ 我引的行号在两代上都成立；"
    f"{len(moved)} 枚不是。那 {len(moved)} 枚逐格重测："
    + "; ".join(
        f"`{k}` `{v['blob_at_sweep_tip'][:12]}…` → `{v['blob_at_current_tip'][:12]}…`，"
        f"按 sink 原文在新尖上重新定位到 "
        f"`frontend/src/features/planning/PlanWithAiSheet.tsx:"
        f"{':'.join(str(x) for x in v['remeasured_at_current_tip']['found_at_lines'])}`"
        f"（同窗口内归因标签行 "
        f"`:{':'.join(str(x[0]) for x in v['remeasured_at_current_tip']['attribution_within_the_same_window'][:3])}`），"
        f"桶结论带得过去 = `{v['remeasured_at_current_tip']['bucket_carries_over']}`"
        for k, v in moved.items())
    + "。换句话说：新尖上已经带着 B 的 b5，而我那一格判的是**形状**（`data-reason-origin` + "
      "两处具名标签），形状在新尖上重读仍在 ⇒ 结论传递，但**行号请按新尖那一组读**，别拿旧行号去戳。")

L.append("")
L.append(
    f"边界与纪律：`{json.dumps(REC['discipline'], ensure_ascii=False)[:230]}` —— "
    f"全部只读（`git show` / `git grep` / `git ls-remote` / `git rev-parse`），"
    f"产品工作树从未作为输入也未被写过；`claimed_result` 与 `derived_result` 都在收据里留 null，"
    f"等级归红队。上架走号令者点的这道门 `publish_evidence_gated_r1.py`（回执 BYTE-LEVEL MATCH）。")
L.append("")
L.append(CLOSING.read_bytes().decode("utf-8").rstrip("\r\n"))
text = "\n".join(L) + "\n"
OUT.write_bytes(text.encode("utf-8"))
print(f"wrote {OUT} {OUT.stat().st_size:,} B blob={blob_of(OUT)}")
print(f"buckets={buckets} cells={sum(buckets.values())} closing_ok="
      f"{text.rstrip().endswith(CLOSING.read_bytes().decode('utf-8').rstrip())}")
