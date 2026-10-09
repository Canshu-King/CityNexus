## commander 合并回执 @2026-09-22T13:1x+08 —— 权威树前移两格：`e0fc697 → ebb4b3f → c0d7e3d`（都在我名下验过），另记两条"差点报错"的核验

### 读数（全部 `git archive <sha>` 干净导出树；解释器 `.venv` 3.12.14；`DEEPSEEK_API_KEY` 已 unset）

```
ebb4b3f  13:09 C  refactor(backend): the fourth capability cell takes the arbiter's frozen name (ORD-0197 vocabulary)
         collect-only 1178 / 四门 35 passed + 1 xfailed in 2.64s           ⇒ 改名一条断言都没弄坏
c0d7e3d  13:11 merge(discovery): B 的 reply-level counts 与 C 的冻结名同树（父 = ebb4b3f + 7167ef6）
         事前用 `git merge-tree --write-tree` 干跑 ⇒ 只输出 tree oid、无冲突段（= 干净）才真合并
         collect-only 1178 / 四门 35 passed + 1 xfailed in 2.89s
```

仲裁裁的 B 项（`5771378382` ①）**已到账并被我复跑**：`CAPABILITY_STATES` 现为
`("READY","HYDRATABLE","UNKNOWN_RETRYABLE","UNAVAILABLE")`（`anywhere_capability.py:74`，常量 `:84`、
发射 `:1401`、retryable 联动 `:1467`、`main.py:2826` 文档、两份契约同步）。
B 的字段（`7167ef6`）此前单独验过：`provider_identity.py:98-99` 声明、`:303-304` 填、
`anywhere_capability.py` 随 attempt 传给 C 的载荷，**纯增量 29 行、nullable、不改变既有 35/1 读数**。

### 两条我核验之后**没有报错**的事（写明，免得下一辆车把它们当缺陷去"修"）

1. `integrations/discovery/real_city.py:1279` 在 `ebb4b3f` 仍写 `"NOT_ANSWERED"`。
   我先按"改名漏了一处"立案，读到上下文才否掉自己：那是
   `provider_status["overpass"]` 的取值——**provider 证据轴**（"这个端点有没有回话"），
   不是 capability 轴；`git grep` 显示 `capability` 一侧在 `ebb4b3f` 已全量改名。
   而且它恰好就是仲裁给的改名理由的正面例子：**"没回答"是证据事实，"能不能继续"才是能力语义**。
   ⇒ **这一处不许改**。旁边注释已经写明只有"没有端点回话"才算失败形状。
   顺带量到的小口径缺口（不开单，记下）：`CAPTURED` 在 tests/contracts 里出现 26 次、
   而 `NOT_ANSWERED` 这个取值 0 次 ⇒ 这一侧词表只钉了一半，写错另一个值不会有人报警。
2. `git merge` 第一次尝试（13:09）**被正确拒绝**——那时权威树有 12 个 tracked 文件正被车道编辑，
   其中就包括 B 要改的 `anywhere_capability.py`。我没有 stash、没有强推、没有绕开；等 C 提交后重跑干跑才合并。
   合并后 `git status` 里 D（`DestinationPreparationPanel.tsx`，12:50，+53/-23）与 E（kill drivers）的
   未提交编辑**原样还在**——这是这次合并唯一的验收标准，我逐条看过。

### 现场

`CURRENT_INTEGRATION_REFERENCE_TIP` 我按仲裁口径仍写 `e0fc697`（**我没权力自己升格**；
`ebb4b3f` / `c0d7e3d` 是我的复跑读数，等你一句话再改冻结行）。
D 盘：12:52 曾跌到 **0.255 GiB** 剩余（我建导出树时 `No space left on device` 中断过一次 tar），
处置＝只删我自己的派生物：12 个 `git archive` 导出树（1,405 MB）＋ 5 份 `frontend/node_modules`＋`dist`
（2,045 MB，均可由 lock 文件重放）＋ `__pycache__`。**源码一个字节没删**，被拒的合并、车道工作树、
用户库全部未动；现剩 **3.59 GiB**。
删前我做过可重放性证明：五个快照目录里 `main.py` / `anywhere_capability.py` / `models.py` 的 blob sha1
逐个在仓库 372 个提交里查到匹配（`53fe8e8` / `f2708dd` / `61cde4b` / `23bdf9f` / `fed1861`）——
所以我先前说"它们与 `e9efec6` 不同 ⇒ 可能含未提交内容"是**参照点选错**，不是有孤儿内容；这条也记进我的口径。
