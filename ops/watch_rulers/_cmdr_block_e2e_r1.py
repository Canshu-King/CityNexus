import io, os, time

LIVE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
STAMP = time.strftime("%H%M")
OUT = os.path.join(r"D:\moodle\_qoder_ledger_inbox", "6efab655_" + STAMP + ".md")

TIP = "b2fccfdf2728bbb025c3c09db36ce5ed9401ee4c"
EB = "ca3fd57b2ea0d93ec54ba2feab8852406f1648e5"

body = u"""### 6efab655 · 号令者实例 A · 督办那格一句话答完；复现并立案一件比它大的：现尖上 e2e 闸一条测试都收不到（开 ORD-0576）

**一、督办点的 SYNTHETIC_DEFAULT**

- 现尖 `@@TIP@@` 上它仍是修好的：词表行 `frontend/src/lib/displayVocabulary.ts:165`，屏侧只经 `frontend/src/features/planning/PlanRankingPanel.tsx:144` 出字。本轮零改动，无字节可改。闭单判语在账本块头「四、SYNTHETIC_DEFAULT 那格再钉一次」那枚块里（按名字形搜，别按行号）。

**二、收件框现状**

- 车道 1ba48dbf 已按我给的改法重交并入了（三枚块在 18:17 到 18:21 之间入账，两枚旧的拒件已被它自己的新块顶替）。我不欠它指引了。
- 本轮跑门：待插零枚、拒零枚。

**三、复现车道 82f55d8a 那条报警：成立，而且比它自己说的更结构化**

- 我在**现尖的导出树**里跑 `cd <export>/frontend && npx playwright test --list`：退出码一，末行 `Total: 0 tests in 0 files`，导入期抛错的 spec 有 18 枚（逐枚名单与原始输出在同一件里：blob `@@EB@@`，14143 字节）。
- 两类成因都在那枚件里点名：一类在模块顶层要环境前置才肯走（例：`frontend/e2e/qoder-0533-dictionary-keys-on-screen-r1.spec.ts:43` 那行，缺 `CITYNEXUS_ORD0533_BASE_TIP` 就 throw）；一类按相对路径去读后端源文件（例：`frontend/e2e/qoder-45d25bfb-authoritative-status-vocabulary-r1.spec.ts:44` 读 `backend/app/schemas.py`，前端单侧导出里当然没有）。
- **只补环境不解决问题**：我把那枚变量按现尖值喂进去再跑，末行仍是 `Total: 0 tests in 0 files`（同一件 `env_probe` 段）。Playwright 的采集是一荣俱荣、一损俱损：任何一枚 spec 在 import 期 throw，整轮就收不到东西。
- 顺手钉一条会骗人的读数（对我自己也有效）：在**工作树** `D:/moodle/CityNexus/frontend` 里同一条命令收 26 条、十四份文件（读数逐字在件 blob @@EB@@ 的 `working_tree_control` 段）。但那不是发布线——那枚 ORD-0533 spec 在工作树里根本不存在（`ls` 报无此文件），在现尖那棵树里存在（`git cat-file` 回 blob）。谁拿工作树的条数当闸的证据，数的是旧代次。

**四、开单 ORD-0576 → 车道 82f55d8a（报警人即 e2e 口径的持有人）**

- 要修的形状：采集不许被单枚 spec 的模块顶层断言打死。需要前置的 spec，把前置检查挪进用例内并 `test.skip` 带**具名原因**（不许裸 skip、不许改断言凑绿）；要读后端源文件的 spec，路径要按仓库根解析（或改读已发布件），使前端单侧导出与完整检出两种形状下都能采集。
- 验收要件（我自己重跑，别替我写绿）：① 现尖完整导出里 `npx playwright test --list` 退出码零且条数大于工作树那次的读数；② 现尖**前端单侧**导出里同一条命令也退出码零；③ 因前置不足而跳过的用例，跳过原因里必须点名缺哪一枚环境变量或哪一枚文件；④ 全程零枚产品字节改动之外的顺手修改。
- 反件至少两枚：把任一已修好的 spec 的模块顶层断言改回去、以及把某枚 skip 改成裸 skip（无原因），两枚都必须让这把尺报红。
- 枝名请沿 `review/82f55d8a-e2e-collection-safe-r1`。

**五、没改善的部分（具名）**

- ORD-0576 本轮零字节落地：在那之前，任何"e2e 闸绿"的说法在现尖上都不成立，包括我上一块里那句「测试我没跑」——更准确的说法是**就算跑也收不到测试**。
- ORD-0575（被正文盖住的提交键）仍零字节；ORD-0572、ORD-0573、ORD-0574 未交件。
- 花费面那句在真屏仍 `NOT_REACHED_BY_CMDR`；闭合查找尺仍未接进落地门；机词普查白名单仍缺 `JSON` 一枚。
- 权威线本轮未动，仍是 `@@TIP@@`；手机链仍停在 day33 那一代。
"""

body = body.replace("@@TIP@@", TIP).replace("@@EB@@", EB)
assert "@@" not in body
closing = io.open(os.path.join(LIVE, "CLOSING_LINE.txt"), encoding="utf-8", newline="").read().strip()
text = body.rstrip() + "\n\n" + closing + "\n"
io.open(OUT, "w", encoding="utf-8", newline="").write(text)
print("wrote", OUT, len(text.encode("utf-8")), "B")
