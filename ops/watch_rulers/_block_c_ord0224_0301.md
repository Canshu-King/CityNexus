## commander 验收 @2026-09-23T03:01+08 —— **C `8c66aa92` 交回 ORD-0224 六步**：g3 已拆成两把门、**反向突变打在"真正让五发收敛的机制"上**（Y3 ⇒ 身份门 4/4 全红）、弱修带 provider 计数门；**它拒绝签 FINAL CLOSED（跨进程证据缺）——我认这个拒绝**

### ① 坐标修正（先收它自己的更正）

你 01:20 那块写的基线 `0437b5c` **已过时**；三件"脏文件"其实早已在提交里：产品两文件在 **`50d1c4d`**(01:41)、门在 **`f92f9e9`**(02:46)；`git status --porcelain -- backend/` 现在 **0 行**。当前 tip `e3329c8`（别人的前端/review 提交），`f92f9e9..e3329c8` 之间 **backend/ 变更 0 个文件** ⇒ 数字在两者上同时成立，**引用写 `f92f9e9`**（尺是按这个号跑的）。
它还自曝：第一块末尾把"当前 tip"当成"我的交付点"印成 `e3329c8`，**自己核对后当场更正**——"引用一个没产出的坐标"这周第三次，已记进它的记忆。

### ② 六步状态（每步都有坐标）

| 步 | 状态 | 坐标与读数 |
|---|---|---|
| 1 弱修 | **已落盘** | `50d1c4d`：`submit_operation` 先算键→先查存储→再解析（产品 +37 行/注释 18；`anywhere_capability.py` +14、`catalog_hydration_operations.py` +23；`main.py`/`provider_identity.py` 各 **0 行**）。门 `tests/test_qoder_ord213_ask_store_before_world.py::test_w1_…`，**把你原话钉成独立断言「额外解析次数 = 0」** |
| 2 新 g3 | **已落盘** | `f92f9e9::test_g3_concurrent_open_generation_five_callers_share_one_operation`：`threading.Barrier(5)` 放行五发，产品自己的 `dispatch` 真起 worker、worker 停在 `_run_operation` 内的闩上（行不得离开 QUEUED），**并断言 `worker_started`**——没有活 worker 的窗口就是空断言。判据：1 个 operation_id、恰好 1 winner + 4 reuse、1 行且仍 OPEN、键一致、指纹四段、无 409。配套 `test_g3b_…`（`start_worker=False` ＋ `dispatch` 计数=0 的控制形制）、`test_g3d_…`（唯一索引存在**且是部分**索引） |
| 3 tail-A | **已独立** | `f92f9e9::test_g3c_tail_a_terminal_job_is_answered_by_a_new_generation_not_reuse`：A 同步跑终态→同一瞬间（门内打印实测 ms 差）的同键请求必须另开 B、不得拿 A ⇒ **任何 freshness window 都会把这条门变红** |
| 4 小包 | **已交付** | `tests/test_qoder_ord224_g3_generation_measurement.py`(3 nodes) → `ord213/ord224_measurement_package.json`。**shape A：同指纹 1 终态 + 1 开放 = 2 行，标签却写"五个并发" ⇒ 我的判断复现**；五发的 distinct ids 只作读数不作判据。**shape B：1 行 / 1 winner + 4 reuse / 解析 5 次 / `finished_at=None`**；字段不齐＝门红 |
| 5 为何收敛 | **已答（实测）** | 三层：A＝两次读开放作业；B＝`backend/db/schema.sql:1007` **部分唯一索引**；C＝`except IntegrityError` 的**败者回读**。shape B 里五发**全部解析过（calls=5）**却只有 1 枚作业 ⇒ **干活的是 B/C，预查拦不住未提交的行** |
| 6 反向突变 | **已做且改口** | 见 ③ |

**连击**（尺 + F 的共享判据 blob `ebe4e24c177d8e18` 复制进 `snap_f92f9e9` 才跑得起来；判级只取尺的输出）：三条都是 `--runs 10 --sha f92f9e9…`、**`STREAK_MET(10)` / closure `STREAK_GREEN`**、逐 run 全绿、10 个互不相同且跑前不存在的临时库、`clause6_command_surface_clean=true`：`test_g3_concurrent_open_generation…`、`test_g3c_tail_a…`、`test_w1_a_repeat…`。三张 **`closure_allowed=False`**（那个格子吃字符串声明，照旧留空）。

### ③ 步 6：**反向突变换口径后打对了**

- **Y3 破坏"败者回读" ⇒ corrected g3 两把身份门 ＋ 小包 4/4 全红** ＝ **我要的那把"真正让五发收敛的机制"的反例**。
- **Y1a 把预查复用关掉 ⇒ 只红 `w1`，身份门全绿** ⇒ **实测钉住"lookup 时机只能给 dedupe 门充数、不能给 g3 充数"**（它上一轮的 X1 正属此类，已按此降级）。
- **Y1b（解析后那次读）12/12 全绿＝今天它是冗余件**（产品事实，报我处置 → 见 ⑤）。
- **两处它声明错了、按实测改口**：Y2（索引谓词永不命中）只红了 `g3b` 控制门 + `shape_b`（`PARTIALLY_KILLED`）——预查在路线形制里替它兜住 ⇒ **A 与 B/C 互为冗余，单一突变杀不掉 g3**（这本身就是答案）；Y4（索引改全量唯一）红了 4 条（tail-A + g3d + w2 + shape A）⇒ **是它 `expect_red` 写窄了，不是突变泄漏**。
`mutation_anchor_guard`：anchor 全部 `hits=1`、`bytes_changed=True`、逐文件 sha256 跑后与权威树一致。

### ④ ORD-0234 已做（提交 `1ea6250`）

两行改成 `severity="HARD" if hard else None`，显式 HARD 提升保留。**删前先量等价性**：`default_severity('STROLLER'/'LARGE_LUGGAGE', hard_asserted=True/False)` **都返回 STRONG**（两码在 CONTEXT_CODES）⇒ 它码内那句"会落 SOFT"是旧事实，一并改掉。删后：名下两条 ORD-0219 门文件 **15 passed**；能力面 13 文件合跑 collected 307 / **294 passed / 13 skipped / 0 failed**；钉住"只是提到⇒STRONG"的 `test_8` 仍绿 ⇒ **实测等价，不是"看起来等价"**。`TOILET_BREAK_EVERY_MIN` 那行没动（不在裁定里）。

### ⑤ 我认它拒绝签 FINAL CLOSED —— 并给出其余处置

**它明写的四件"没做完/做不到"**：
1. **强修 `claim-before-work` 一行没动**（按令登记）✓；
2. **跨进程证据缺失**：全部门在**单进程多线程**里跑；两个 uvicorn worker 各持未提交视图时"败者回读"的实际行为**它没有读数** ⇒ **FINAL CLOSED 它不签**；
3. **真并发下 provider-work dedupe 未达成**（calls=5）：要它就得做强修，不属本轮放行范围；
4. 正式 `ORD-0224_receipt.md` 未生成（账本两块的坐标/产物名完整，不靠口头）；`ORD-0220`/`ORD-0218④` 的坐标仍对不上本树，未动。
⇒ **我的判定**：`ORD-0210 FINAL CLOSED = BLOCKED_ON_CROSS_PROCESS_EVIDENCE`（**它拒签是对的**；跨进程那一格要么补读数、要么由仲裁改口径，我不替它放宽）。
⇒ **Y1b 冗余件的处置**：**保留**，但要求它在那行上写一句"**当前没有任何门依赖它（Y1b 12/12），它是第二道机会**"；若将来强修真要删，必须由强修那单明写。理由：现在删会在并发路径上再掀一次改动，而那正是未来强修的作业面。

### ⑥ 门禁与卫生（全部实测）

```text
三文件合跑      19 collected -> 18 passed / 1 failed（那条 test_g5… 属 ORD-0218 方向，B 分支 d5667cf 在改）；连跑三次同一红集合
全量            collected 1204 -> 8 failed / 1180 passed；红集合与 33034d7 基线逐 nodeid 相同（8=8，新增 0、消失 0）
出网            量出来的：getaddrinfo 记录型阻塞器，同进程 3 文件 -> 解析尝试 0 次（nosock_ord224.log）
用户面          :4781/:4782/:8693 一次都没碰；_live.db/_preview.db 0 次打开
临时库          %TEMP% 曾积 1289 个 cnx_pytest_*，它删 1275 个（释放 894 MB），留 14 个近 3 分钟的；0 个因占用失败
清理            另删两个旧导出（snap_b_4d9ceae / snap_50d1c4d，事实已入账本可重出），现只剩 snap_f92f9e9 供复跑
```
⇒ **它自己执行了仲裁刚立的"生产者自清"规矩**：删的都是它自己名下、且留下近 3 分钟的；**我的 GC 候选清单因此失效一部分**（我 02:47 数是 852 个 >6h，现在已被它清掉 1,275 个含 <6h 的）。**这正是新规矩想要的效果**，我下一轮会重新盘一次再决定具名 GC。

### ⑦ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（0 删除，等用户真机刷新）；`P7=false`；reference tip `c0d7e3d`；P0 未动（HARNESS 第二把尺）；那把 key 仍未轮换。
