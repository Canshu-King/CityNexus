**值守 13:18 · 现成的落地顺序表：8 枚候选里 6 对互斥，另有 3 枚与谁都不撞——先落这三枚最省**

- 现尖 `57ff5d1c2f85`；最近 150 分钟块里**申报了但未落地**的车道枝 15 枚（枝尖以远端 `ls-remote` 为准）
- 剔除「同族已有代次在线上」的 3 枚（这些族的工作已在线，只是块里留的是旧代名）
- 最终候选 9 枚（同族折叠后）
- 同族只取最新一代、补 fetch 并重测落地状态后剩 9 枚（折叠旧代 3 枚）

候选（枝名 / 远端头 / 该枝自报改动的文件数）：
- review/qoder-0449-invite-and-revoke-r1         头 05628b3a776a 自报改动 10 枚
- review/R-ord0437-link-import-r6                头 ea532c95f0ec 自报改动 46 枚
- review/Q-ord0432-robust-blind-to-major-4       头 4c7caed59e3f 自报改动  7 枚
- review/ord0435-poi-batch-multiselect-r3        头 b4bb6c065a3e 自报改动 33 枚
- review/Q-ord0456-entry-limits-r2               头 48d16fc7f34a 自报改动  2 枚
- review/N3-ord0440-exposure-cells-r2            头 ab171b0c407a 自报改动 30 枚
- review/newlane2-ord0450-place-on-a-day-r1      头 de1aaf321ab5 自报改动  7 枚
- review/newlane-ord0444-collections-r2          头 a4c8b0e94a71 自报改动 16 枚
- review/Q-ord0406-v8-message-recipe-r1          头 4c343d358d5d 自报改动  3 枚

互斥对（同一跳两枚都复切，后落那枚按判据必 ABORT）：
- review/R-ord0437-link-import-r6          × review/newlane-ord0444-collections-r2    共 5 枚：backend/app/main.py, backend/app/schemas.py, contracts/openapi.yaml, frontend/src/app/v8PanelRegistry.tsx
- review/Q-ord0432-robust-blind-to-major-4 × review/R-ord0437-link-import-r6          共 2 枚：backend/app/main.py, contracts/openapi.yaml
- review/Q-ord0432-robust-blind-to-major-4 × review/newlane-ord0444-collections-r2    共 2 枚：backend/app/main.py, contracts/openapi.yaml
- review/R-ord0437-link-import-r6          × review/newlane2-ord0450-place-on-a-day-r 共 1 枚：frontend/src/app/v8PanelRegistry.tsx
- review/R-ord0437-link-import-r6          × review/ord0435-poi-batch-multiselect-r3  共 1 枚：frontend/src/i18n/LocaleContext.tsx
- review/newlane-ord0444-collections-r2    × review/newlane2-ord0450-place-on-a-day-r 共 1 枚：frontend/src/app/v8PanelRegistry.tsx

- 与谁都不同改的枝 4 枚：review/N3-ord0440-exposure-cells-r, review/Q-ord0406-v8-message-recipe, review/Q-ord0456-entry-limits-r2, review/qoder-0449-invite-and-revok

我从这张表里能给的只有顺序，不替你决定落谁：**撞得最多的是 `frontend/src/app/v8PanelRegistry.tsx`（4 枚都改）与后端契约那一族（`backend/app/main.py` / `contracts/openapi.yaml` / `backend/app/schemas.py`，3 枚都改）**。最省的做法是先落那 3 枚谁都不撞的（含 N3 的 ORD-0440 后半与 S4 的 0406 配方件），再挑一枚 registry 的落，其余两枚让车道按新尖重交——顺序你定，我只把谁撞谁数出来。

尺与自曝：`patrol/_landing_plan_r1.py`（只读：块里枝名+申报头 → 远端 `ls-remote` 逐字回读 → 同族取最新一代 → 「同族已有代次在线上」的族整族剔除 → 两两比 `ls-tree` blob）。这把尺第一版有两处我自己造的红，都已修：① 同一族的旧代（例如 0437 的 `-r3`/`-r5`/`-r6`、0436 的 `-r3`）被各列成一枚候选，读起来像 9 枚要落，其实每族只有最新那一代是活的；② 远端头不在本地对象库时会被误判成「未落地」，现在先 `fetch` 再判，取不到对象就明说不算读数。表里那句「merge-tree 干净 / 互斥」全是**我的只读预测**，门的实判归你那一跑。

边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准、0 次改动 cron。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
