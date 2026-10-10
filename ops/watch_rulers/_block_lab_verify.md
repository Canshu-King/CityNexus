## commander 亲测 @2026-09-22T13:5x+08 —— **REVOLUTION LAB 真的把 Mission A 跑到具名阻塞了**（我从它的提交里读证据，不等它落账）

`794dc63`(13:45) 与 `0f4385c`(13:48) 我直接读了产物，关键读数（不是我转述它的自述）：

```
准备作业 job.status=COMPLETED  elapsed_ms=211207  retry_after_ms=0  status_url=/api/v1/catalog-hydrations/924a7287-…
目录变化 before.reason_code=COVERAGE_INCOMPLETE place_count=0  →  after.place_count=2
计划答案 HTTP 422  code=VALIDATION_ERROR  reason_code=CATALOG_INSUFFICIENT
          plan_count=0  selectable=false  blocker_stage=PLAN_COMPOSITION
报告 reports/revolution-lab-mission-a-20260922.md（144 行，含身份与隔离段）
```

⇒ 这一格按仲裁口径就是**成功**：**跑到第一个真实阻塞，并准确命名它**（`422 + CATALOG_INSUFFICIENT + blocker_stage=PLAN_COMPOSITION`），
plan_count=0 / selectable=false 它**没有伪造**——这正是 R11／"不许为了晨报好看造 SELECTABLE"要求的形状。
`lab_h4_plan_probe.py` / `lab_h4_prepare_probe.py` 两支探针＋e2e 两个测试文件（24 行×2）在树里可跑，`0f4385c` 还让 lab 的门**自己收尾**（RUNNING_LOG 41 行）。

### 但两条限定，我已经写进 13:4x 的换底令，这里再钉一次
1. **基座落后 25 个提交**：`1a80a8f` 里"修终态迁移杀掉已解析作业"那半，主线在 `1cce4bf`(03:55) 已修；
   换底到 `c0d7e3d` 时**主动丢弃那一半**并写明"由 `1cce4bf` 承担"，否则会盖回主线。
2. **`CATALOG_INSUFFICIENT` 在新底上是否仍是同一个具名阻塞**要在换底后重量一次——这正是要给 C 的候选发现：
   一个没见过目的地跑完真实准备之后，规划层给出的仍是"目录不足"，而 place_count 只从 0 到 2。
   ⇒ 我把这条转给 **C**（不换底、不改 lab）：如果它在新底上成立，那是 R11"可规划性≠覆盖完整度"的第二个真实样本，
   值得一条门；如果不成立，说明实验室那份读数属于旧底，**两种结果都是答案**，不要为了对上而修一次。
