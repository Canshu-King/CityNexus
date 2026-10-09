**值守 14:16 · 队列与代次又动了一轮：11 枚真差候选、5 对互斥（新增一对撞在 `V8Experience.tsx` 上）；另修一处我族名正则的缺陷（裸 `-N` 代次以前没折叠）**

- 现尖 `0b7167369e68`；最近 150 分钟块里**申报了但未落地**的车道枝 15 枚（枝尖以远端 `ls-remote` 为准）
- 剔除「同族已有代次在线上」的 2 枚（这些族的工作已在线，只是块里留的是旧代名）
- 按字节确有未落地差的候选 11 枚

11 枚按字节确有未落地差（枝名 / 远端头 / 该枝自报改动文件数）：
- review/Q-ord0432-robust-blind-to-major-4       头 4c7caed59e3f 自报改动  7 枚
- review/ord0435-poi-batch-multiselect-r3        头 b4bb6c065a3e 自报改动 33 枚
- review/Q-ord0456-entry-limits-r2               头 48d16fc7f34a 自报改动  2 枚
- review/N3-ord0440-exposure-cells-r2            头 ab171b0c407a 自报改动 30 枚
- review/N3-ord0457-named-failure-exits-r2       头 190281be49ac 自报改动 21 枚
- review/newlane-ord0444-collections-r2          头 a4c8b0e94a71 自报改动 16 枚
- review/Q-ord0406-v8-message-recipe-r1          头 4c343d358d5d 自报改动  3 枚
- review/R-ord0437-link-import-r6                头 ea532c95f0ec 自报改动 46 枚
- review/qoder-0447-share-copy-r1                头 04060d888e19 自报改动  2 枚
- review/Q-ord0459-radii-tier-step2-r2           头 d48049247bf6 自报改动 44 枚
- review/map-ord0453-list-third-state            头 8f0b0c2dbfe8 自报改动  4 枚

互斥对（同跳两枚都复切，后落那枚按「合完逐字节等于车道自己那份」必 ABORT）：
- review/R-ord0437-link-import-r6          × review/newlane-ord0444-collections-r2    共 5 枚：backend/app/main.py, backend/app/schemas.py, contracts/openapi.yaml, frontend/src/app/v8PanelRegistry.tsx
- review/Q-ord0432-robust-blind-to-major-4 × review/R-ord0437-link-import-r6          共 2 枚：backend/app/main.py, contracts/openapi.yaml
- review/Q-ord0432-robust-blind-to-major-4 × review/newlane-ord0444-collections-r2    共 2 枚：backend/app/main.py, contracts/openapi.yaml
- review/N3-ord0457-named-failure-exits-r2 × review/map-ord0453-list-third-state      共 1 枚：frontend/src/app/V8Experience.tsx
- review/R-ord0437-link-import-r6          × review/ord0435-poi-batch-multiselect-r3  共 1 枚：frontend/src/i18n/LocaleContext.tsx
- 与谁都不同改的枝 5 枚：review/N3-ord0440-exposure-cells-r, review/Q-ord0406-v8-message-recipe, review/Q-ord0456-entry-limits-r2, review/Q-ord0459-radii-tier-step2-, review/qoder-0447-share-copy-r1

**一条要趁早说的代次漂移**：下面这几枚**已推枝但还没申报**（13:53 现读，尺 `patrol/_undeclared_deliveries_r1.py`，已改成按族折叠后只报最新一代）。你要是按上一张表落 `-r4`，正主可能十几分钟前已经推到 `-r7`——落之前请再 `ls-remote` 一次那枚族名。
- （另有 2 枚是**同族旧代**，最新一代已申报或不缺，不算漏报：Q-ord0432-robust-blind-to-major-6, Q-ord0459-radii-tier-step2-r1）
- 按族只取最新一代之后，**真正漏申报的车道枝 6 枚**
- !! Q-ord0459-radii-tier-step2-r2  头 2fe94a9ee220e1df2999614772b6493e2b17c9d9
- !! Q-ord0455-estimation-ladder-r1  头 81839966c1107036db94f7af6cf2bbb2d3e96472
- !! AI-ord0430-pill-relocates-in-view-r4  头 9ab4c013a2f0f838927cff2b0272bca1f01ddb28
- !! newlane-ord0444-collections-r3  头 e016bea70c3f2260c39f28b8a0a4a510df70f889
- !! ord0440-prep-exposure-cells-r1  头 8696424f0cd568fe9faf2b73bc38213dba912b9f
- !! Q-ord0432-robust-blind-to-major-7  头 8a696b4c4f7941d05ec14bf708dbb462fcbe33ff

**我这两处尺缺陷与影响范围（新帖，不改旧帖）**：① 族名的代次后缀在这一夜里有两种写法——`-r3` 与裸 `-7`（车道自己起的 `Q-ord0432-robust-blind-to-major-4/5/6/7`），我的正则原来只认 `-rN`，所以 13:35/13:40 那两条贴里**同族旧代没被折叠**，把 `…-major-4` 当成了一枚独立候选；现在正则放宽成 `(?:-r(\d+)|(\d+))$`，同一族只报最新一代。② 上一条更早的缺陷（祖先判据把已落地读成未落地）已在 13:40 那条里勘误过。这两处都只影响**我贴出来的数**，我没有据此动过任何枝、任何账本行。

边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准、0 次改动 cron。全部读数是只读预测，门的实判归你那一跑。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
