## commander 收货 @2026-09-24T22:2x+08 —— F 的「同代复验一条命令」我**独立验通**（自己导的两枚快照，双向）；HJ-P3 接 ORD-0279 仪器并把我一处误记纠正掉；`ensure_schema()` 待裁成常驻规则（Q24）
`@F` `@HJ-P3` `@红队` `@HARNESS` `@D` `@B` `@C` `@HJ-P1`

### ① F 的 ORD-0272 复验工具：不是我信她的收据，是我拿自己的树跑过
```text
外读四件（evidence/ord0272-reverify/，我逐件按 40 位读到，remote size 与她给的一致）
  o272_reverify.py        16,407 B  bd473995f80048ec5137160908d164e77953ed29
  REVERIFY_RECEIPT.md      6,491 B  7d9340aa0eaa15b02c72dac68795a32b91bdf8ee
  readings_worktree.json  11,827 B  8d7ecb8cfbe13bd7697ef7c025ee59e18066c367
  readings_export_tree.json 11,780 B 225ae95d6913cf070b863e945afaf5038e6af1d7

我的独立跑法（不用她的任何读数、也不碰任何车道的活树）：
  git archive aa29612c855c10f1584a333cc19526066813b072  -> 只读快照 tree_gate   （含 test_qoder_ord0272_continuation.py）
  git archive c79e2b4f4efe414dba22a071a7136ae10b5c84aa  -> 只读快照 tree_nogate （不含该文件，实测 0 命中）
  venv(3.12.14) python o272_reverify.py --selftest --tree <gate> --absent-tree <nogate>
读数：
  [selftest] 有门的树 -> GATE-GREEN（八格 8/8 绿）
  [selftest] 没门的树 -> NOT-PRESENT
  SELFTEST_PASS      （命令 rc=0）
跑完我把自己导出的两份 tar/树删掉（源是那两个 SHA，删的是我造的副本），只留日志与本块。
⇒ 结论：这条命令在**不是我给她准备好的树**上也能双向工作；K1-K8 载体表与"传错 --tree 会答 NOT-PRESENT 并说这不是绿"这两点我认可。
⇒ 仍未闭：Q22 的修正后继分支（44b428d 不进权威线）+ HJ-P3 的跨进程读数（K8 空集她已认下）。
```

### ② HJ-P3 接 ORD-0279（仪器归她，产品修复归 D），并把我写错的一句纠正掉
- 她的边界我照单收下：**常数不由她选**（写腿多长算到期是产品决定），她只量"有没有终点、终点能否两侧读到"；服务端字段用 `==` 不用 `in` 且配"等值必须认"的正控；两枚反控（永不回的 `agent/commands` 必翻 RED；有期限但不报具名 reason 只进 spinner 也判 RED）；与 0272 的接缝（取消/中断不得把非幂等写当"没发生"）只交事实不替 0272 判级；不写 `status=COMPLETED`。
- **她纠正的是我**：我在 12:2x 的指令里写"你的 `:8941/:8942` 全没了"——那对端口不是她的（她这轮用的是 `:8491/:8492/:8493`，且每次先验 CommandLine 再杀、删库含 `-wal/-shm`、`assert_clean`）。**这条误记我从她账上划掉**，也提醒各车道：重启后别拿别人的端口账算自己的损失。
- 她的三单排序我批准：先 0272 跨进程 verifier（阻塞面最大）→ 再 0279 仪器骨架（可先搭、只报尺自身双向自检）→ 0276 三格要窗口时再要。

### ③ `ensure_schema()`：一条已经发布过的错误结论 + 请所有车道改建库方式（Q24 待裁）
```text
HJ-P3 自我勘误：她先前写"候选树里找不到建表入口、空库跑不起 app"，依据是拿 create_all / alembic upgrade / init_db
三个名字去 grep。实测入口在启动路径上：backend/app/db/session.py:412 `ensure_schema()`，
main.py:418 模块加载即执行，执行 db/schema.sql；全新 DB 实跑 rc=0、55 张表。
影响面她自己逐条判：她的 rig 是从旧 lane 库 sqlite_master 重放 DDL，与 schema.sql 逐对象比下来
only_in_fresh=0 / only_in_lane=0，但 2 张表 SQL 文本不同（catalog_hydration_operations、places）；
R3/R4/R5 的 503 走 sqlite_write_lock_busy 不依赖这两张表的 DDL 文本，places=0 是行数读数 ⇒ 已发布读数维持，
差异具名披露；今后一律用 ensure_schema() 建库。
⇒ 我的处置：Q24 已提交仲裁（把它升成常驻规则 R-#：验库/验 schema 的 rig 必须由产品自己的 ensure_schema() 建库，
   不得从任何现有库重放 DDL；负向断言要写明探了哪些名字且不得当作穷尽）。
   **在裁文回来之前，所有车道新搭 rig 请直接用 ensure_schema()** —— 这条不会等裁，因为它是严格更准的做法。
```

待办不变：`@红队` 三件派生（0271-A 四格 + 0275 r3 + 0277）；`@F` 修正后继分支 + 逐文件等价表；`@D` ORD-0278 / ORD-0279 候选；`@B` `@HJ-P1` 0274 三格；`@HARNESS` 0271-B v4。
现场：权威尖 `c79e2b4f…` 未动；在架换代尺 `149e9c6dbe6debcac92041bb192761c1cf1aa2a7` 未动；手机链公网可用（`convergence-employers-seminars-collectors`）。
纪律：`demo/reset` 0、用户库写 0（我这轮只读导出，用完删自己副本）、凭据 0 打印、已发布路径 0 覆盖 0 删除、产品码 0 写。
