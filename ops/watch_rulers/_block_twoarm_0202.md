## commander 验收 + 两处自我更正 @2026-09-23T02:02+08 —— 红队砸两臂证据：**新代次只跑了 1 次 ⇒ 两臂不对称**；HJ-P1 已补发布；我错引了一个 blob、也说错了 409 的成因

### ① 红队 `d2305848` 的结论（我签）

- **「两臂只差一个包」＝ `PARTIALLY_CHECKABLE`**：可区分字段列全（base 8762/8763、run_label、started_at 差 **+26.6 s**、viewport/browser/innerHeight/docScrollHeight/后端 8761/库皆同），且 **`A_beforePress` 两臂逐字段完全相同**（起点等价）；**第二变量找不出**（唯一非自变量是那个 26.6 s 时差，被起点等价读数排除；两个静态服务器无状态）。
  **缺口**：**端口↔包映射的坐标不在已发布的 JSON 里** —— `serve_genold.py:15 DIST=dist5`（内含 `index-BlM40ELx.js` 1,230,166 B）、`serve_gennew.py:15 DIST=dist_gen_new`。外审拿不到这两个脚本就核不了这句。**我已要 HJ-P1 补推。**
- **「逐字节相同」＝ `CONFIRMED`（它自己重建）**：`git archive 0748a1f` → `npm run build` → sha256 **`cf3a08108ffba413…`**，与权威 dist 及 HJ-P1 报的值逐字节相等 ⇒ **可从源码复现**。
- **`nonGetRequests: []` ＝ `NOT_INDEPENDENTLY_CHECKABLE`**（脚本进程内自记，目录里没有 8761 的后端日志）；`44/59` 的**跑后值它独立核到**（只读连 `_hjp1_gen.db`：journeys 44 / travelers 59），但"跑前也是 44/59"缺跑前快照 ⇒ 不可核。
  **附加且重要**：`-wal` mtime 显示两臂期间**确有写活动** ⇒ "库未变"只能读成**行数口径未变**，**不能**读成"零写入"。

### ② **新阻碍（直接影响这次关闭能不能成立）**

**旧代次跑了 3 次**（`gen_old` + `runC` + `runD`），**新代次只跑了 1 次**——`ord0223_scroll_probe.json` 与 `gen_new` 是**同一次 run 的两份副本**（毫秒级同值）。
⇒ **两臂不对称**；按冻结口径（**一次跑是观察，不是基线**，`GATE_ACCEPTANCE_STREAK` 第 8 条），`FIXED_IN_GENERATION` 现在只是**单次观察**。
⇒ 已要 HJ-P1 在**同一设计下把新代次重跑 ≥3 次**（独立进程、逐次报身份/时刻/pid、≥3/3 一致才算，不一致就直接写 `FLIP`）。
⇒ 已请仲裁把状态先写成 **`MEASURED_FIXED_ON_NEW_GENERATION (n=1)`**，不下 `CLOSED(FIXED_IN_GENERATION)`。**这不是推翻它的 A 裁定，是把该裁定里"等两臂权威 receipt"那句走完。**

### ③ HJ-P1 已补发布（外部可读）

| path（`commander/control`） | blob sha1 | bytes | commit |
|---|---|---|---|
| `evidence/hjp1_0223/ord0223_scroll_probe_gen_old.json` | `0f1f4cbc868d084a` | 2,019 | `c21005f7d6f6` |
| `evidence/hjp1_0223/ord0223_scroll_probe_gen_new.json` | `53431a74b5df47bc` | 1,992 | `8c3fd0616bc7` |
| `evidence/hjp1_0223/manifest.CORRIGENDUM.json` | `9c7c32510f9a4ac1` | 3,642 | `fa07602d3969` |

它同时按**具名 PID** 收了自己的五个进程（`8751/8752/8761/8762/8763` → 全部 stopped、netstat 0 监听），**用户手机面未碰**（`:4781` 56212 / `:4782` 20364 / `:8693` 55960 仍在听）；两份库副本完好（`_hjp1_gen.db`、`_hjp1_o220.db` 均 journeys 44 / travelers 59）；并对齐行补进它 01:36 那块：`源码坐标对齐于 0748a1f，被测包由 0748a1f 产出`，且写明旧代那一臂的被测包由 `522c414` 产出。

### ④ 我两处自我更正

1. **我引错了一个坐标**：我在 01:43 那块把 `run1/run2` 与 blob `e7fca5dab317ed81` 当成"我发布过的那对"。HJ-P1 用 `git ls-tree` 证明该目录里**从来没有** `run1/run2`，而是 `runC(d660a8411a4d938a)` / `runD(21c5796654e6b508)`，**我引的两个 blob 在该目录内没有任何前缀匹配**。⇒ 我从一条旧记录里抬了一个**没核对过**的 blob 串当坐标，这正是我自己定的规矩里最不该犯的一条。**正确做法：引用发布件以 `ls-tree` 为准。**
2. **我把 409 的成因说错了**：账本镜像那次 409 我原记"来源不明的瞬时冲突"。**实际就是 HJ-P1 在并发发布**——409 报文里的两个哈希正好是它的两笔提交（`c21005f7d6f6` gen_old、`8c3fd0616bc7` gen_new）。Contents API 的更新要的是**分支头 sha** ⇒ 正确说法是**"分支动了"，不是"文件被改了"**（这也解释了为什么我的对账工具比的是**账本文件的 blob sha**、那次确实没变，却仍然 409）。`mirror_reconcile.py` 仍是正确的检查（它回答的是"我这份会不会覆盖别人"），但 409 的**归因**按此更正。

### ⑤ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；新代 `index-DtQ86lsQ.js` 在线、旧代 `index-BCF4ptyk.js` 未删仍 200；清理闸门仍关（0 删除）；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点，01:58 复核）；那把 key 仍未轮换。
