### SESSION=494abfd7 · 条件 6 我**自己验了一半**：重放确实复用同一作业；而且我**当场撞见**那条"轮换红"背后的真缺陷（`ABANDON_REQUESTED → UNAVAILABLE` 非法迁移）@02:5x

`STATUS: REPLAY-REUSE-VERIFIED + SWIMMER-IS-REAL | 树 `v_16cc652/backend`，venv 3.12.14，**一次性临时库**（我自己新建的 `idem.db`，不碰 `:4781/:4782/:8693` 与 `_live.db`），`CITYNEXUS_ANYWHERE_RESOLVER=photon`，正常入口 POST ×2 |`

#### ① 重放语义（我亲眼看到的返回）
```
第一次 POST /api/v1/catalog-hydrations {query:"贡山县"} → 202  op=cc3d24fb-…  status=QUEUED   reused=false
第二次 同样 body                                            → 200  op=cc3d24fb-…  status=RUNNING  reused=true
⇒ 同一个 operation_id、状态向前推进、没有另起一单
```
⇒ **条件 6 的"重放不产生第二份作业"这一半，由我验证成立**（不是引用车道的断言）。另一半"不产生第二个 canonical 身份"要看 0197 那批交完再测。
⇒ **一处我自己的空检查要说清**：我还想比"表行数没增长"，但我的表名过滤器**没匹配到任何表**，两次都返回 `{}` ⇒ 那句"无行增长"是**空集上的假结论**，我不写进结论，改成"该项未测（过滤器失效）"。

#### ② 更值钱的意外：我**抓到那条轮换红的真身**
第二次跑之后，后台 worker 抛了：
```
catalog hydration worker died for cc3d24fb-…
  app/catalog_hydration_operations.py:278 mark(...)
  TransitionRefused: ABANDON_REQUESTED -> UNAVAILABLE is not a legal transition
```
⇒ 这正是 `catalog_hydration` 三兄弟里那条 **`a_job_stopped_before_its_worker_starts_still_closes_itself`** 反复红绿轮换的同一处代码路径：
**它不是测试噪声**——在真实运行里，一个"已被请求放弃"的作业走到"结束时标 UNAVAILABLE"就会撞上非法迁移，把 worker 打死。
⇒ 也就是说：**我一直盯着的"红集合成员会轮换"里，至少有一条对应真缺陷**；修法不是把断言放宽，而是补这条迁移（或让终态走具名的 ABANDONED 支路）。
⇒ 已同时给 C（实现）与 F（门）：**F 的门请断言"被放弃的作业终态只能是 ABANDONED/等价具名，且 worker 不抛 TransitionRefused"**，并配突变：把该迁移放宽 ⇒ 必红。

status: 重放复用由我验证（同 op id / 202→200 / reused=true）⇒ 条件 6 半成；我自己的"行数无增长"检查是空集假结论，已撤回；当场复现 ABANDON_REQUESTED→UNAVAILABLE 非法迁移，证明那条轮换红是真缺陷，已派 C 修 + F 加门
