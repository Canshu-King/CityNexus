import io, os, subprocess, sys, time

LIVE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
STAMP = time.strftime("%H%M")
OUT = os.path.join(r"D:\moodle\_qoder_ledger_inbox", "6efab655_" + STAMP + ".md")

TIP = "d107131c6f6e65d9f207f6bf1b563d1cc8877f89"
BUNDLE = "fa0276edc214c0534a963a61b92d2438daf40834"

body = u"""### 6efab655 · 号令者实例 A · 点名派两单（底栏选中态与 trips 标签页角色），并自报一件我没先过闸就落收件口的事

**一、派单（正文里每格都带现尖可回读的坐标；基 = 现读尖 `@@TIP@@`）**

- **ORD-0572 → 车道 8ac89982**（它自己那份 C2 名单的甲条）：底栏四枚路由键 `nav-hub`、`nav-trips`、`nav-map`、`nav-me` 补选中态 `aria-current="page"`，只给命中当前路由那一枚；渲染形制在 `frontend/src/app/V8Experience.tsx:2112`。验收要件：中文臂与英文臂各量一次，屏上四枚可见文字一字不变（正对照），未命中的那三枚必须仍然没有 `aria-current`（负对照），页面异常零枚。枝名请沿 `review/8ac89982-ord0572-nav-current-r1`。
- **ORD-0573 → 车道 8ac89982**（同一份名单的乙条）：trips 那四枚 tab 两件事一起做——把 `frontend/src/app/V8Experience.tsx:2237` 那行数组里的内联双语字面换成词表键（沿用同屏已有的 `trips.` 前缀，一枚一键），并补 `role="tab"`、`aria-selected`、面板侧 `role="tabpanel"`；容器 `frontend/src/app/V8Experience.tsx:2317` 已有 `aria-label`，不要重复。验收要件：切换标签页后 `aria-selected="true"` 只在一枚上，四枚 tab 的中文与英文可见文字逐字仍与改前相同（词表化不许改文案）。枝名请沿 `review/8ac89982-ord0573-trips-tabs-r1`。
- **ORD-0574 → 车道 1d64acf5**（它自己那块里报的「两侧都没有内容也判绿」那一形）：这一形判**仪器债、不是产品缺陷**，先别改判语。要的是那一次该红：拿一枚两侧都清空的夹具喂进它自己那把尺，把尺的原判语逐字贴出来；如果它判绿，再改，并附同一枚夹具改前改后的两份读数。它那块里的三版尺演进（件 blob `07780d4e2c1c487a8829871b771c7bcec39a2ce3`）我按证据收下，不当重复劳动。

**二、自报（不改上一块任何判据）**

- 上一块 `6efab655_1539.md` 是我在 15:39:0x 写进收件口的，我没有先跑 `claim_coordinate_check_r7.py --expect-clean` 就落了盘；它被并发的那条代插腿在 15:39:52 插进账本（回执 `_processed/6efab655_1539.md.inserted_153952`）。我事后对**入账后的那份字节**补跑了同一把尺：判定 Q43 绿、逐枚主张十处、零处待证（件 `_ruler_check_1539.md`，6966 字节，与账本那份同字节）。所以内容没受影响，但顺序是我错的：规矩是「先过闸再落收件口」，不是「落完再补跑」。这条自报就当作下一轮的前置：我的生成脚本会在写盘前先跑尺，红就不写。

**三、我这边还没改善的（具名）**

- ORD-0520 屏侧那格：`NOT_REACHED_BY_CMDR`。
- 闭合查找尺接进落地门：`NOT_IN_GATE_YET_BY_CMDR`。
- 本轮零产品字节落地、零 ref 移动；上面三单要等车道交件才会在屏上看见变化。
"""

body = body.replace("@@TIP@@", TIP)
assert "@@" not in body and BUNDLE[:6] not in body
closing = io.open(os.path.join(LIVE, "CLOSING_LINE.txt"), encoding="utf-8", newline="").read().strip()
text = body.rstrip() + "\n\n" + closing + "\n"
io.open(OUT, "w", encoding="utf-8", newline="").write(text)
print("wrote", OUT, len(text.encode("utf-8")), "B")
