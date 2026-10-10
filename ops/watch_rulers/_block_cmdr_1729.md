

### CMDR-0925-1729 今晚的落地与换代顺序（我自己执行，写给下一班核）· Q55=① 已得字

1. **一次把可落的都落进同一条线，只做一次换代**。当前可落状态：
 - F 的 `ORD-0296 r3` = `fd8eaf3644b66b44c44ce3178a7babac2bf561c0`，ref `review/ord0296-write-deadline-f-r3`。我按两路外读核过：`git/ref` 与 `commits` 同值，**parent = 权威尖 `dc964086c9d412573ac19d70b24b30e6c3ee6168`**，只动 1 个文件（`backend/tests/test_qoder_ord0296_write_deadline.py`）。⇒ 只差 F 的收据/回执落到 `evidence/` 新路径，落我就 ff-only 落这一枚。
 - B 的 `ORD-0281` 有键半支 gen-2 = `64d14b205263ec03fd4810b1b0877418495b87b0`（ref `review/0281-write-deadline-keyed-b2`，parent 也是当前尖，我核过）。⇒ 等红队 ORD-0305-A1 的 gen-2 派生。
 - B 的 `ORD-0302`（null-body 两处 + X-5 那一格，Q53=① 口径）。⇒ 交付后我亲测再落。
 三枚的先后按"到齐即落、一次换代"，**不是一枚一跳**。换代前件按工单：P1 尖相等、P2 双尺跑在要部署的字节上（`claims checked > 0` 才算量到）、P3 无外部硬链、P4 数据面状态如实标。今晚 P3 我 17:24 已实测 `hits=0`；仪表 63/63 自测 17:21 已过（两件都在 `evidence/cmdr-runbook/`）。
2. 换代后**同一小时**内做手机侧逐资产回读（`phone_side_probe_r1.py`）并把发布件路径写进总线；X-5 运行时那一半继续挂 `NOT-DEPLOYED-OBSERVED`，等 `:8000` 恢复（用户的字）。
3. 顺序上唯一可能互相打架的是 0302 与 0281：两枚都碰 `PlanWithAiSheet.tsx`。我核过 0281 那枚只动 `frontend/src/lib/*` + 两个 panel + 自己的 spec，**不碰** `PlanWithAiSheet.tsx`；但 0302 落地会让 0281 的 e2e 跑在新代上——所以若 0302 先落，0281 的格按 Q24 重跑一次（这一条我已让 D 用 ORD-0308 预演路径相交来独立核，别只信我这段）。

本拍我 0 权威线写入、0 ref 推送、产品码 0 改动、`demo/reset` 0、`_live`/`_preview` 0 读写、凭据 0 打印、连接器 0 安装。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
