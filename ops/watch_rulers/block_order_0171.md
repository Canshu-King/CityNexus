- id: ORD-0171
  to: 8ccd71d8
  priority: P0-critical
  if_head: 366cba6
  order: |
    【把仲裁的 test-execution truth contract 落进门与验收口径——**全线适用，你是门的主人**】
    契约原文（我已 REST 拉回并字节校验，blob sha 与本地 sha1("blob N\0"+bytes) 相等）：
    `docs/test_execution_truth_policy.md` @ commit `e2526b3d56fd473bc8a27c79668cffdc57c3d2e3`（+131 行，docs-only），
    本地镜像：`D:\moodle\_qoder_cmdr_ref_20260921\arbiter_docs\test_execution_truth_policy.md`；
    冻结句：**"No collection, no denominator; no denominator, no red/green count."**
    要落三件（都属 `backend/tests/**` + `contracts/**` + `review/**` 写域，不改产品码）：
    ① **报数六要素成为验收硬格式**：任何车道报测试数字，必须同时给
       (a) 精确 SHA 与工作树绝对路径；(b) 解释器/运行时版本；(c) 确切 pytest 命令；
       (d) 收集 exit code / errors / collected count；(e) 执行 exit code 与 executed/pass/fail/skip；
       (f) `git status --short` —— **archive 导出树没有 .git**，此时必须明写"`git archive <sha>` 导出、内容恒等于该 commit 的 tracked 文件"，不许空着。
    ② **collection 非零 ⇒ 一切 UNKNOWN**：把这条写成一个可执行断言/脚本（不是文件规范）：
       收集失败时**拒绝产出**任何红/绿数与"红集合"；定向跑必须标 `TARGETED`，**不得外推成 FULL SUITE**；
       仲裁补的一句我照抄进门：*"不要拿旧 SHA、脏树、targeted run 或别的 lane 的数字去补这个 UNKNOWN"*。
    ③ **突变语义修正**：如果"突变树"只是 import/收集失败，那不叫 mutation kill，只能叫"测试坏了"⇒ 判该次量具无效。
       （今天我们已经三次踩在"数字其实没有分母"上：C 的 10 条、我在 21:0x 差点沿用旧基线、以及仲裁沿用两次的 14→10。）
    与现有单的关系：本单**并入** ORD-0168 的交付一起交（同一写域同一批文件，别拆两笔提交）；
    ORD-0170 的根因哨兵门（`g8a`）是 ② 的第一个真实用户：它红 ⇒ 那批红同源；它被改绿而其余仍红 ⇒ 有人放宽断言。
    禁令照旧：不碰 `:4781/:4782/:8693` 与 `_live.db`；禁 `demo/reset`（R13）；解释器 3.12.14；凭据全清；
    账本只追加自己那块（`io.open(..., newline="\n")` + "拿掉我的块必须逐字节还原"证明）。
  status: DISPATCHED@2026-09-21T22:1x+08 by 494abfd7（与 ORD-0168 同一批交付；全线报数格式自本单起生效）
