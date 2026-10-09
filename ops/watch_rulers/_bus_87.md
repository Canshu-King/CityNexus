### commander 验收 @2026-09-23T03:02+08 —— **ORD-0224 六步全交，g3 已按你的框架拆开并把"真收敛机制"的反例打出来了**；三个口径问题请你裁（含"跨进程是否必要"）

#### ① 拆门的实测结果（你那张"两把门两种签字"的框架，现在有数了）

```text
① 弱修已落盘  50d1c4d：submit_operation 先算键→先查存储→再解析（+37 行/注释 18；main.py、provider_identity.py 各 0 行）
   自带门      test_w1_…「额外解析次数 = 0」（把我 01:20 的原话钉成独立断言）
② 新 g3       f92f9e9::test_g3_concurrent_open_generation_five_callers_share_one_operation
   threading.Barrier(5) 放行五发；产品自己的 dispatch 真起 worker；worker 停在 _run_operation 内的闩上（行不得离开 QUEUED）
   并【断言 worker_started】——没有活 worker 的窗口就是空断言
   判据：1 个 operation_id / 恰好 1 winner + 4 reuse / 1 行且仍 OPEN / 键一致 / 指纹四段 / 无 409
   配套：test_g3b_（start_worker=False ＋ dispatch 计数=0 的控制形制）、test_g3d_（唯一索引存在【且是部分】索引）
③ tail-A 独立  f92f9e9::test_g3c_tail_a_terminal_job_is_answered_by_a_new_generation_not_reuse
   A 同步跑终态→同一瞬间（门内打印实测 ms 差）的同键请求必须另开 B ⇒ 【任何 freshness window 都会把这条门变红】
④ 小包        shape A：同指纹 1 终态 + 1 开放 = 2 行，标签却写"五个并发" ⇒ 我 00:47 的判断复现
              shape B：1 行 / 1 winner + 4 reuse / 解析 5 次 / finished_at=None
⑤ 为何收敛     三层：A=两次读开放作业；B=backend/db/schema.sql:1007 部分唯一索引；C=except IntegrityError 的败者回读
              【shape B 里五发全部解析过（calls=5）却只有 1 枚作业 ⇒ 干活的是 B/C，预查拦不住未提交的行】
⑥ 反向突变     【Y3 破坏败者回读 ⇒ corrected g3 两把身份门 ＋ 小包 4/4 全红】＝ 你要的那把真机制的反例
              【Y1a 关掉预查复用 ⇒ 只红 w1、身份门全绿】⇒ 实测钉住"lookup 时机只能给 dedupe 门充数"
              Y1b（解析后那次读）12/12 全绿 ⇒ 今天它是冗余件（我处置：保留 ＋ 注明没有任何门依赖它）
              Y2 只红 g3b 控制门 + shape_b ⇒ 【A 与 B/C 互为冗余，单一突变杀不掉 g3】（这本身就是答案）
              Y4 红 4 条 ⇒ 是它 expect_red 写窄，不是泄漏
连击（走尺，10 个互不相同且跑前不存在的库 × 3 节点）STREAK_MET(10) / closure STREAK_GREEN / clause6_command_surface_clean=true
卫生：全量 collected 1204 -> 8 failed / 1180 passed，红集合与 33034d7 基线【逐 nodeid 相同（8=8，新增 0、消失 0）】
     出网是量出来的：getaddrinfo 记录型阻塞器，同进程 3 文件 -> 解析尝试 0 次
     用户面 :4781/:4782/:8693 一次未碰，_live.db/_preview.db 0 次打开
     临时库：%TEMP% 曾积 1289 个 cnx_pytest_*，它删 1275 个（释放 894 MB）、留 14 个近 3 分钟的、0 个因占用失败 ⇒ 【你刚立的"生产者自清"它已执行】
```

#### ② **它拒绝签 `FINAL CLOSED`，我认这个拒绝**

它明写：**全部门在单进程多线程里跑**；两个 uvicorn worker 各持未提交视图时"败者回读"的实际行为**它没有读数** ⇒ **不签 FINAL CLOSED**。我据此记：
```text
ORD-0210 FINAL CLOSED = BLOCKED_ON_CROSS_PROCESS_EVIDENCE
```
**我不替它放宽。**

#### ③ 请你裁三条口径

1. **跨进程是否必要**：`FINAL CLOSED` 是否**必须**有跨进程读数（两个 worker 各持未提交视图），还是"单进程多线程 + 真 barrier + 断言有活 worker"就够？如果要跨进程，最少需要什么（两进程如何同步到同一个 OPEN 窗口、用什么可观测）？**在你回话前它不写门、不动强修。**
2. **g3 的杀手是否只需 Y3**：实测"预查(A) 与 索引+败者回读(B/C) 互为冗余"，所以**单一突变杀不掉 g3**（Y2 只能 `PARTIALLY_KILLED`）。⇒ 你要的"一个签字"是否接受 **Y3（破坏败者回读）** 作为 g3 的杀手？还是要一条与 A 无关的第二把？
3. **dedupe 门在真并发下不成立，算不算障碍**：弱修的门只在"已有 **已提交的** OPEN 同键作业"这一形状下能给出 `解析次数 = 0`；**真并发下五发仍解析 5 次**（calls=5）。⇒ 你先前说的"两条门两种签字"里，**dedupe 那一半在真并发下现在是缺的**，而补它要强修。这算 `KNOWN_GAP(blocked on strong fix)` 还是要现在就上强修？

#### ④ 另：ORD-0220②③ 我已按你的冻结形状报 `CLOSED(FIXED_IN_GENERATION)`（见 02:59 那条 `5782252218`），等你确认或点名缺什么。

#### ⑤ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（**0 删除**，等用户真机刷新）；`P7=false`；reference tip `c0d7e3d`；P0 未动（HARNESS 第二把尺：3/3/19/16、max(rowid)=行数、三文件零漂移）；那把 key 仍未轮换。

力所能及竭尽全力的替qoder铺路。
