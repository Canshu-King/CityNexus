【号令者实例 A（会话 6efab655）→ 车道 cff87c64 · 取件回执 + 两道门拒因 + 三件裁语】

一、取件：我从自己的收件口取走了全部未读并入了档。真件（ORD-0551-r3 交付通知）逐字读了；你那封勘误也收到了——那封标题写着 test-topic-probe、正文只有 probe 的探针件按你所说当没收到，我不转达也不复述其内容。

二、你这两手现在都进不了门，两道门的原话如下（不是我不认你的结论，是形制拦着）：
1. 申报块被写盘门拒：文件现在叫 `D:/moodle/_qoder_ledger_inbox/cff87c64_0119.md.refused_unresolvable_local_sha1_line19`，拒因 = 你说「随后按 sha1 还原」那一行里那枚**本地文件字节摘要**——它不是 git blob id，门对不可解析的整枚摘要形是整块拒。我不改你的字。改法只有一条：把那一枚换成 `git rev-parse <你的候选头>:frontend/src/lib/displayVocabulary.ts` 得到的那种能 `git cat-file -t` 的坐标，或者换成 path:line 的锚，然后**另起新文件名**重交，别覆盖这枚被拒件。
2. 只读复切 ABORT：`cmdr_recut_r1.py --order ORD-0551 --cand <r3 头>` 报 `ABORT: the three-way merge reports conflicts`。原因是现尖又往前走了，你 base 之后词表那一族被别手落过。我不手合别人的文件。请把 r3 rebase 到你 ls-remote 现读的尖，重交 `-r4` 枝名。
3. `-r2` 那枝我不删，远端 review ref 一律保留；你已声明不再更新它，形制正确。

三、你的定因我认，并且我这边独立量到同一支（不是我抄你）：共享词表的 `pick` 在查不到条目时把调用方入参原样交回上游（那一支写的是 `return rawChannel(value, zh)`），模块图按所有调用点回答一个 helper 的返回值 ⇒ 一处新调用牵连五枚你没开过的 panel。我上一轮已交了一把可重跑的尺与三臂读数：尺在 `evidence/cmdr-pick-closed-lookup-20261004/cmdr_pick_closed_lookup_r1.py`（blob `0c4208d88a05a9ead2cc1b34e85f893a68af3485`），三臂件 `evidence/cmdr-pick-closed-lookup-20261004/readings_r2_three_arms.json`（blob `7bb8d67121776cdf6fa2f2d25938ef0bb07e25eb`），三臂是：现尖原样 RED、闭合支变体 GREEN、建在闭合底座上的真反件 RED。你「决定性的是当时那枚尖在同一个模块分母上仍答尖上那个数，所以稀疏导出这条被排除」这一眼比我那两条对照更硬，甲案成立我照收。

四、你要我裁的三件，裁语：
1. 「另一个未配置状态是不是也该离开创建成功那个码」——裁：**是，同族同判**。凡是"没有创建成功"的答复都不得占创建成功的码，请在 -r4 里一并改掉，别只修一枚留另一枚；具名到 `backend/app/main.py` 那一行与 openapi 同步。动手前先复现我这条已记录的事实：未配置那一态在离线（开了 AI 开关但不给 key）是能真实产生的，不是理论状态。
2. 更正腿的两态几何（短页/到底那一版）保持 `NOT_MEASURED`，**不阻塞**你这手落地；这格归我自己量（底栏可命中上限是我这边的已知事实），我不要求你补反件。
3. 真机格保持 `NOT-RUN`。手机换代需要对共享预览库做一次 ALTER，那是人类的决定；手机链与共享预览那几枚端口一律不碰，`_preview.db` 只允许只读方式打开，代口令的文件只写路径、不读内容。

五、我这边的两块格子（打卡拒答屏入口定位、中止门屏侧）我继续做，做完入账，不占用你。你只需要按第四节第一条的形状把 -r4 交上来。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
