### CMDR-0943 · ORD-0280 已 LANDED（第 4 次 ff-only 跳）— 但手机上还看不到（Q45=①）

**做了什么**：`mirror/integration-frontend-apple-pass1` 由 `6d041dcc…` → **`90d29a172e186aab6e6cb138ab4583ccf93bfa68`**
（`fix(frontend): let the attribution label speak only for the server (ORD-0280)`，parents 实测 `['6d041dcce11d05f28a55abadd40717f321b4db38']` == 跳之前的尖 ⇒ 纯 fast-forward，`PATCH force=false` http 200）。

**落地前那一秒重读尖**：两条路由各自独立读，`git/ref/heads` 与 `commits?sha=` 都给 `6d041dcc…`，与 B 报的 parent 一致才动手。

**为什么算亲测而不是自宣**（B-1：落地方不自宣 KILLED，这里我只宣"移动 + 字节等价"两件事，二者都是仪器读数）：
- 双路由回读新尖一致 = `True`；
- 两枚命名文件在**新尖**的 blob 与**落地前我已量过的候选 `549ac8f1b20bc04e70eadbd238ade737eefbff01`** 的 blob，逐字节重算 `git hash-object` 后相等：
  `frontend/e2e/qoder-ord0280-attribution-label-speaks-for-itself.spec.ts` → `0edae5cf262833e996bbfc3b56f60d0548ca3e3f`（12,134 B）
  `frontend/src/features/planning/PlanWithAiSheet.tsx` → `c22cf42506a4175db992bde387ed8d9c6f1ffb9d`（47,470 B）
  ⇒ 落下来的就是我量过的那两枚，不是"同一支重写的另一版"。
- Q38 尺子重新对**已发布字节**跑了一遍：先按 blob `02dfbb817e5add8577c4c47a7e898983743b7202` 取回 ORD-0299 收据（本地重算 sha1 == 被引 sha1 = `True`，31,760 B），再跑 `receipt_cell_derivation_check_r2.py` ⇒ `cells 10 | Q38_GATE_GREEN | hard 0 | soft 0`，rc=0，且用了 `--expect Q38_GATE_GREEN`（预期不成立就非零）。

**外读坐标**（`Canshu-King/CityNexus @ commander/control`，blob sha1 证明）：
仪器 `evidence/ord0280-landing/ord0280_landing_receipt_r1.py` = `d14f73fbfe25e11c7c5481557cf9a8acf14ccaef`（9,114 B）
收据 `evidence/ord0280-landing/commander_landing_receipt_r1.json` = `b089d6671d563c94eeacc52bc1156702d164df7d`（3,058 B）
尺子输出 `evidence/ord0280-landing/q38_ruler_on_ord0299_rerun_r1.json` = `c32c75047ed952f99dd9eb0f09309a25c0bc9bb0`（10,877 B）
仪器的每个 verdict 字段都是从读数派生的（`decisions` 四枚布尔各自由实测比较得出），`overall` 只在四枚全真时写 `LANDED_AND_VERIFIED`。

**状态口径（不许漂）**：`LANDED / NOT-YET-DEPLOYED-to-phone`。
Q45=① 禁止在 10:00 前动用户可见链 ⇒ **没切 `dist/index.html`、没重启预览后端、没碰 tunnel**。手机现在仍是 08:36 那一代（`index-xKIGmoBz.js` 那一代）。谁把这笔说成"用户已经能看到"就是错的。

**给 D 的一个必须注意的事实（不是猜测，是上面 blob 比较的直接后果）**：这一跳改的是 `PlanWithAiSheet.tsx`——正是移动/归因那几条臂要渲染的那个组件。所以 ORD-0278 / ORD-0253 的红队 `derived_result` 若要在新尖上算数，**测量代次必须是 `90d29a172e186aab6e6cb138ab4583ccf93bfa68`**；在 `6d041dcce11d05f28a55abadd40717f321b4db38` 上跑出来的臂，只能记成"前一代的证据"，不能改口说覆盖了 ORD-0280。我不要求重跑，只要求**具名代次**（R14：读数属于它实际跑的那个尖）。

**下一步（按 10:00 收口）**：只剩交接。落地质检、换代、以及上面三单加 ORD-0298 的闭单，都写进 `live_checks/_block_handoff_0925.md`（本块插入后立刻生成并镜像），交给下一班在第一分钟做：重启预览后端让 ORD-0296 在手机上真生效，再谈非紧急窗口的 index 切换。
