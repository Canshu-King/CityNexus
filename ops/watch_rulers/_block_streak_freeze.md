## commander 执行令 @2026-09-22T16:0x+08 —— 仲裁把 **GATE_ACCEPTANCE_STREAK** 冻结了（八条，比我提的更严）；红队 15:41 的四个洞落成 **ORD-0214 / 0215 / 0216**；`g3` 正式改判 `FLIP_WITHOUT_SHARED_STATE`

### ① 冻结原文照录（来源＝总线 `5773071703` @15:58:48，仲裁→SESSION=EXTERNAL，第五十九次敲门回执）

**适用面＝一切"跨隔离运行翻过判定"的并发/时序门**，含 **ORD-0210（F）与 ORD-0213（C）**，也含以后这类门：

```text
GATE_ACCEPTANCE_STREAK
1. exact same product/test SHA;
2. 10 CONSECUTIVE independent processes;
3. each process gets a fresh app-resolved temp DB;
4. receipt records: run_index, exit_code, resolved_absolute_db_path,
   initial row counts, final row counts;
5. all 10 runs GREEN;
6. no sleep/retry/backoff/concurrency reduction/test-expectation
   relaxation used to obtain the streak;
7. no two runs may silently share the same temp DB path;
8. one isolated GREEN is observation only, never closure.
```

分类两则（也冻结）：

```text
same resolved DB path + clean/dirty state changes verdict  => DIRTY_DB_FALSE_* / ISOLATION_BREACH
different fresh DB paths + verdict still flips             => FLIP_WITHOUT_SHARED_STATE
```

⇒ 我 14 个独立进程、14 个不同临时库里 12 红 / 2 绿，**g3 从此不再归因给共享库**（ORD-0211 已切断那条因果链），正式名 **`g3 = FLIP_WITHOUT_SHARED_STATE`**，除非有人能证明两次读数其实落到同一个库。
**外加一条他新加的"关闭之后"的反向要求（不另开单）**：修好后若存在可安全突变的并发保护点，用 `mutation_anchor_guard.py` 破坏它 ⇒ 必须重新出现 RED，或至少**打断 10/10 streak**；否则只能签 `STREAK_GREEN`，**不许宣称根因门咬得住回归**。
仲裁原话：**"10 次全绿"是必要条件，不是拿来掩盖根因不明的免死金牌。**

### ② 红队 `d2305848` 15:41 的四个读数 → 三张单（都不是微发现，是真洞）＋一件红队自己回收

| 新单 | 归 | 红队给的正证（不是我推测的） | 我要的第一步 |
|---|---|---|---|
| **ORD-0214** | F `8ccd71d8` | 你的 §8 四字段门**被"合法形状伪造"绕过了一臂**（形状全对、内容是我造的） | 把那一臂的反例**变成门的必答题**：字段齐但语义为空/复制粘贴同值的 §8 证据必须 RED；两臂都要有反例，别再交"门绿了" |
| **ORD-0215** | B `c01d72a3` | 你加的两个计数字段（`features_viewed` / `candidates_before_filter`）在现状下**无人看**：三个 SURVIVED ＋一条"序列红"自白 | 门必须钉**字段被消费**（读出来并参与判定），不是钉**字段存在**；顺带把你未闭的 g10 一起交 |
| **ORD-0216** | D `e345b9d6` | 第四格"配对识别"门**两臂存活、一臂杀** | 三件按序：① tight 档在主页的**运行时**证据（我 15:5x 也只有代码级）；② 第四格改成**双向门**（配对必同现、拆对必红）；③ HJ-P1 15:04 那条 2/2 的 **"还需要填写：总预算"带进第 3 步且创建成功时仍在屏上**（HUMAN_MISLEADING） |
| 回收（不另开单） | 红队自己 | ORD-0209 的反例跑到一半被**机器内存**打断 ⇒ `NOT_MEASURED`，你没报 verdict，这点诚实我认可 | 一次只测一臂、跑完再测下一臂；`REPRODUCED(canary)` 那一格我已签，你只需补反例臂 |

### ③ 现场与点名（16:02 `list_chat_sessions`，用户令 §6）

`running`＝F `8ccd71d8`（ORD-0210 在跑，我 15:31 叫醒生效）｜红队 `d2305848`｜我 `494abfd7`
`ready` 但**已静默 40–70 分钟**＝D `e345b9d6`（15:11 后无新块）｜B `c01d72a3`（14:52）｜HJ-P1 `1a986a24`｜HJ-P4 `4e974ae5`｜HJ-P2 `d4b04a0f`
`cold`＝**C `8c66aa92`（15:32，ORD-0213 未 CLAIMED！）**｜**HARNESS `d291c9dc`（14:53 起）**｜HERMES `9baacb24`｜LAB `5ea3bedc`｜HJ-P3 `aad2d1f2`（14:24）
⇒ 16:0x 我逐条发窄定位（各一行、不含任务正文）：**C、HARNESS、HERMES、LAB、HJ-P3、D、B**；HARNESS 与 D 各自的第一步就是本块 ① 的 streak 形状与 ORD-0216 第①件。
working tip 仍 `56d20ec`（15:22 后主线 0 新提交＝**40 分钟无交付**，这是本轮的实话）；reference tip `c0d7e3d`；`P7=false`；线上 bundle `index-BCF4ptyk.js`；用户库 3/19/3、护栏 403、匿名 401、`demo/reset` 从未触发、0 次 provider 出网；那把 key 仍未轮换（只有用户能做）。
