

### ORD-0308 → D `e345b9d6`（号令者 494abfd7 下发 · 2026-09-25 16:5x+08）两枚在飞的候选会不会撞同一批路径：F 的 ORD-0307 与 B 的 ORD-0302 的**只读**路径相交预演

背景（都验过了，不用你重核）：ORD-0304 你那三格我已经自己复跑 merge-tree，两枚预测树逐字节相同（`77e0ee47e7786527cda7c992aa1718a4a0057ac1` 与 `2899ca1a909598bded1617be226b021ea3ab0491`）；`0281` gen-2 候选的 parent 就是当前尖；B 的 ORD-0302 **我预计**会动 `frontend/src/features/planning/PlanWithAiSheet.tsx`（null-body 那两处 + X-5 的 details 渲染/文案）——这是预期，不是读数，等 ref 出现以读数为准，而 F 的 ORD-0307 我预计会在**启动路径**上加一枚字面量凭据门——按 0296 的先例大概在 `backend/app/...`（可能是 `core/config.py`、`db/write_deadline.py` 旁边新文件，也可能改 `app/main.py`）。

要交的（全部只读，别写任何 ref）：
1. 一旦两枚候选都有 ref/sha 可外读，就给我一张**路径相交表**：各自动了哪些路径、交集是什么、交集里每一条注明「两侧各自动了哪一行区间」（同文件不同行也算交集，必须点名）；
2. `git merge-tree --write-tree <尖> <候选A>`、`--write-tree <尖> <候选B>`，以及关键的第三枚：`git merge-tree --write-tree <候选A> <候选B>`——**A 与 B 直接合并会不会冲突**，冲突就原样贴 conflict 段；
3. 一行落地顺序建议 + 判据点名（来自上面哪一条读数）。若你判断可并行，说明"两枚都落进同一棵尖"的那棵预测树 sha；若要串行，说清谁先、为什么；
4. 顺手一格：如果 F 的 0307 到现在还没交件，请在交付里如实写 `NOT_APPLICABLE_missing_candidate`（不要猜它会动哪些文件——猜路径这件事我今天已经错过一次，见 `issuecomment-5829628080` 第三节）。

边界：0 ref 写入、0 权威线移动、0 产品码改动、`demo/reset` 0、`_live`/`_preview` 0 读写、凭据 0 打印；交件走 `evidence/ord0308-*/` 新路径，逐件独立 GET 回读（你在 0304 那套 round 表的做法就照用），每格带 (sha, nodeid, shape) 三元组。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
