仲裁: SESSION=494abfd7（Commander）— 条件 6 我自己验了前半段（重放复用真成立），顺带**撞见那条"轮换红"背后的真缺陷**：一条非法状态迁移会把 hydration worker 打死

**① 我自己跑的（一次性临时库、正常入口，不碰任何用户库）**
```
POST /api/v1/catalog-hydrations {query:"贡山县"}   → 202  op=cc3d24fb…  QUEUED   reused=false
POST 同 body                                      → 200  op=cc3d24fb…  RUNNING  reused=true
⇒ 同一 operation_id、不另起一单 ⇒ 条件 6 的"重放复用"由我亲验（后半段"不产生第二个 canonical"待 0197 交完）
```

**② 紧接着 worker 死了，我留下完整栈**
```
catalog hydration worker died for cc3d24fb-…
  app/catalog_hydration_operations.py:278 mark(...)
  TransitionRefused: ABANDON_REQUESTED -> UNAVAILABLE is not a legal transition
```
⇒ 这条就是 `catalog_hydration::a_job_stopped_before_its_worker_starts_still_closes_itself` **红绿轮换的真身**：**不是 flaky 测试**，是"已被请求放弃的作业在收尾时试图标 UNAVAILABLE"⇒ 撞非法迁移 ⇒ worker 死。
⇒ 已派 C 补迁移（或让终态走具名 ABANDONED 支路），并让 F 加两道门：**终态断言** + **"为方便放宽迁移"必红** 的突变。
⇒ 同时给基线口径补一条分类规则（F 的 `baseline-is-a-set` 条目）：**当轮换红能定位到确定可复现代码路径时，改记 `real-defect, reproducible`，不得继续当噪声**。我们今夜花了不少算力解释"为什么它会漂"，其中至少一条根本就不是漂移。

**③ 一处我自己的假结论，主动撤回**：我当时还想报"表行数无增长"，但我的**表名过滤器没匹配到任何表**（两次都是 `{}`）⇒ 那是空集上的结论，不成立，已改记"该项未测"。同一族第九次：**检查返回空，往往是检查坏了，不是世界干净。**

**冻结不变**：tip `16cc652`；P7=false（§8 四字段仍只落 1 个、未答仍报 HYDRATABLE、malformed 仍叫 NO_RESULTS、elapsed 0.0）；canary `:8596` 仍 closed；Harness/P1–P4 继续睡；P0 全维持（后端 `53fe8e8`、护栏 403、匿名 401、用户 3/19/3）；镜像 `9f60e1ce3770` 字节级相等。
（上一轮问你那件小事仍然开着：**§8"四字段必到"要不要写成常驻硬门。**）

竭尽所能的替qoder铺路
