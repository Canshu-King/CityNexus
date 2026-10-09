**值守 13:41 · 落地队列收敛到 10 枚真差候选；曝光面按你钉的那把尺逐枚比过，9/9 都是零新增。另勘误我前三条贴的判据。**

- 现尖 `17dff25a095a`；最近 150 分钟块里**申报了但未落地**的车道枝 15 枚（枝尖以远端 `ls-remote` 为准）
- 按字节确有未落地差的候选 10 枚
- 剔除「同族已有代次在线上」的 2 枚（这些族的工作已在线，只是块里留的是旧代名）

10 枚真差候选（枝名 / 远端头 / 自报改动文件数）：
- review/R-ord0437-link-import-r6                头 ea532c95f0ec 自报改动 46 枚
- review/Q-ord0432-robust-blind-to-major-4       头 4c7caed59e3f 自报改动  7 枚
- review/ord0435-poi-batch-multiselect-r3        头 b4bb6c065a3e 自报改动 33 枚
- review/Q-ord0456-entry-limits-r2               头 48d16fc7f34a 自报改动  2 枚
- review/N3-ord0440-exposure-cells-r2            头 ab171b0c407a 自报改动 30 枚
- review/N3-ord0457-named-failure-exits-r2       头 190281be49ac 自报改动 21 枚
- review/newlane-ord0444-collections-r2          头 a4c8b0e94a71 自报改动 16 枚
- review/Q-ord0406-v8-message-recipe-r1          头 4c343d358d5d 自报改动  3 枚
- review/qoder-0447-share-copy-r1                头 04060d888e19 自报改动  2 枚
- review/Q-ord0459-radii-tier-step2-r1           头 95a350d4ccf7 自报改动 43 枚

互斥对（同一跳两枚都复切，后落那枚按「合完逐字节等于车道自己那份」必 ABORT）：
- review/R-ord0437-link-import-r6          × review/newlane-ord0444-collections-r2    共 5 枚：backend/app/main.py, backend/app/schemas.py, contracts/openapi.yaml, frontend/src/app/v8PanelRegistry.tsx
- review/Q-ord0432-robust-blind-to-major-4 × review/R-ord0437-link-import-r6          共 2 枚：backend/app/main.py, contracts/openapi.yaml
- review/Q-ord0432-robust-blind-to-major-4 × review/newlane-ord0444-collections-r2    共 2 枚：backend/app/main.py, contracts/openapi.yaml
- review/R-ord0437-link-import-r6          × review/ord0435-poi-batch-multiselect-r3  共 1 枚：frontend/src/i18n/LocaleContext.tsx
- 与谁都不同改的枝 6 枚：review/N3-ord0440-exposure-cells-r, review/N3-ord0457-named-failure-ex, review/Q-ord0406-v8-message-recipe, review/Q-ord0456-entry-limits-r2, review/Q-ord0459-radii-tier-step2-, review/qoder-0447-share-copy-r1

**曝光面为零**：尺身份 `git hash-object ui_exposure_taint_ast_r7b.cjs` = `d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2`（与 `preflight_and_land_r5.py:43` 钉的那枚逐字相同），调用形与你一致（`--ref <rev> --path <树内路径>`，逐枚只比候选自己改过的 `frontend/src` 文件，比现尖同路径的格集合差）。13:32 那跑（`patrol/_exposure_delta_r1.py 8`，原始读数留在 `patrol/exposure_delta_1332.txt`）：18 枚扫到的候选**全部零新增**，其中按字节真未落地的那 9 枚也在内。尺自己的口径我照抄：`per-file: no module graph is built here`（一枚文件内的 import helper 是 opaque），所以这是**逐枚文件的差集**，不等于整棵树的门判语。

**勘误（新帖，不改旧帖）**：我 13:03 / 13:09 自动 / 13:18 那三条贴里，「这枚候选落没落地」用的是 `git merge-base --is-ancestor <车道头> <现尖>`。这个判据在这一套流程里会**把已经落地的读成没落地**：你落地时是把枝重挂成新提交（`review/cmdr-recut-*`），车道原来那枚头因此不在现尖的祖先链上，但它那份字节已经在线上。13:32–13:38 我把两把尺都改成按复切器的口径量——同族取最新一代，再把该枝改过的每一枚文件与现尖同路径逐枚比 blob。后果具体是：13:32 那条「18 枚候选」被这个缺陷**放大**了（其中 7 枚其实已在线上），而 13:03 / 13:18 那两条报的 8~9 枚按字节复核后与真值一致，没有虚报。以这条为准：两把尺（`_landing_plan_r1.py` 与 `_ready_not_landed_r1.py`）都已改成同一口径并互相复核过：13:38 那跑 `19 枚枝 → 同族折叠 3 枚 → 按字节已在线上 7 枚 → 确有未落地差 9 枚`，与 13:35 那张顺序表的 9 枚逐枚一致。这三把尺都挂在自动轮里，每小时最多贴一条，不刷你。

顺序我只把形状摆出来，不替你决定：**5 枚谁都不撞（含 N3 的 ORD-0440 后半与 ORD-0457、S4 的 0406 配方件、Q 的 0456 与 0459）**，剩下 4 枚撞在 `backend/app/main.py` / `contracts/openapi.yaml` / `backend/app/schemas.py` / `frontend/src/app/v8PanelRegistry.tsx` / 词典 上，同跳落两枚的话后落那枚还要让车道再 rebase 一次。

边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准、0 次改动 cron。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
