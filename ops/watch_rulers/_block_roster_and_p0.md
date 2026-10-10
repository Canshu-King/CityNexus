## commander 点名 + P0 口径再收窄 @2026-09-22T14:5x+08 —— **12 个窗口现在全有活**（14:52–14:55 逐个叫醒）；同时**我自己推翻一条今天还在用的 P0 判据**

### ① 巡逻点名（用户令 §6 要求逐条列；`list_chat_sessions` 14:51 读数 + 我随后发的窄定位）

| 线 | session | 14:51 状态 | 当前动作（我给的第一步） | 上一份工件 | blocker | 下一步 |
|---|---|---|---|---|---|---|
| HARNESS | `d291c9dc` | ready→已叫 | 开下一个实验：库状态污染门(ORD-0210)独立复现 或 6 个"永不生成约束行"码 | 六面 12/12 reached、10/12 operable；EXP-004/004b/005；自撤 v1 | 无 | 检查点按 §1 六要素 |
| HJ-P1 | `1a986a24` | ready→已叫 | 继续 journey（目标 ≥8，已 J1–J6）＋ D 交 ORD-0209 后**手机尺寸真跑入口**，把 ACCEPTED-CODE 升 REPRODUCED | 隔离收据＋六格矩阵＋J5/J6 | 无（只等 D） | 连点三次不新建，人眼看过 |
| HJ-P2 | `d4b04a0f` | ready→已叫 | **检查点已过且无交付块**：先交隔离收据（副本库＋行数差），再报第一个承诺密集 finding | 无 | 未知 | 碰 blocker 记录后换场景 |
| HJ-P3 | `aad2d1f2` | **running** | 390×844 中断/恢复/重复提交 | 尚未交 | — | 同 P2 口径 |
| HJ-P4 | `4e974ae5` | ready→已叫 | 隔离收据＋五条偏好（晚出发/少走/饮食/风景/休息）**哪些被静默吞掉**（正指 14:2x 立案的 severity 未接线） | 无 | 未知 | 同上 |
| HERMES | `9baacb24` | cold→已叫 | H4–H10 并行（不等主线门槛） | ORD-0190 三步（manifest 182 条含 sha256） | 无 | 最高真实 H 门＋逐条证据 |
| LAB | `5ea3bedc` | **running** | **换底到 `c0d7e3d`**（14:49 实测仍落后 25 笔，主线在它编辑的四个文件上已 +695/+148/+87/+177），换底后只交三行 | Mission A 旧底读数 `422 CATALOG_INSUFFICIENT / blocker_stage=PLAN_COMPOSITION`；round-2 收据 | 未换底＝产出全部押着 | 换底复现 |
| 红队 | `d2305848` | cold→已叫 | 新靶：F 双向门能否被"为过门伪造四字段"绕过／D `retryable` 恒真／B 计数是不是摆设／ORD-0209"改回 POST 必报警" | ORD-0204 重钉（a/c/d KILLED、b 与 M17 一致 SURVIVED），我已独立复现 (c) | 无 | 用 `mutation_anchor_guard.py` |
| 后端 C | `8c66aa92` | ready→已叫 | ORD-0211（临时库隔离）＋偏好接线（复用 `_has_hard_marker`＋表驱动同义簇＋双向门）；B 的两个计数已在 `c0d7e3d` | 改名 `ebb4b3f`（我复跑）＋11 条 triage | 无 | 各自第一步 |
| 外部数据 B | `c01d72a3` | ready→已叫 | **先恢复它自己合并造成的 3 条新红**（g14a/g14c/city_failure）＋未闭的 g10，再动新行为 | `7167ef6` 计数字段（已合并）；`6cb9298` 七闭三开 | 无 | 两序对照复测后再报 |
| 门 F | `8ccd71d8` | **running** | ORD-0210（干净库/脏库同判定常驻门）＋三件量具 | ORD-0200 两步 `ACCEPTED` | 无 | 收据含两遍 DB 路径与行数 |
| 前端 D | `e345b9d6` | cold→已叫 | **ORD-0209**：入口只读寻址封存 journey，验收含"连点三次 POST 计数 0"＋"改回 POST 必红"反例 | ORD-0203/0208（我签 ACCEPTED-CODE） | 无 | 交完让 HJ-P1 手机复跑 |

### ② 我自己推翻一条今天还在用的 P0 判据（重要，全体改口）

我一直用"`_live.db` 主文件 sha256 前后相同 ⇒ 用户数据未动"。**这条在 WAL 库上是错的，刚才被现实推翻**：

```
14:55 读：_live.db 主文件 size 3,710,976 B（与 12:28 同大小）但 sha256 变了、mtime 09-22 13:40:32
          -wal 4,243,632 B（大小未变）、mtime 09-22 14:56:10  ← 有进程正持有它（就是我 13:20 重拉的预览后端）
六张用户表的行数：journeys 3 / plan_versions 19 / travelers 3 / commitments 1 / bookings 1 / replan_proposals 1
```
⇒ 主文件在 13:40 被**改写过而大小不变**，最合理的机制是 **WAL 自动 checkpoint 把 `-wal` 里的页合回主文件**
（时间也对得上：那正是我重启预览后端之后、它第一次被真实使用的一段时间）。
**但"最合理"不是证据**：我没有 13:40 之前那把的行同一性快照，所以现在只能说——

**新判据（今后 P0 只认这三条）**：
1. **各表行数**与**行同一性**（`SELECT id, COALESCE(updated_at,created_at) … ORDER BY id` 的 sha256 指纹）；
   本次我留了底：journeys `ade925b48c250afe`、plan_versions `149a1a602ef3925b`、travelers `4d28fdc84542f99d`、
   commitments `b0306dd2e13905a3`、bookings `32aee9e5251baec1`、replan_proposals `02526bbf95fd1f4d`；
2. **主文件哈希只作辅证**，且必须同时报 `-wal` 的 size/mtime（WAL 库的"字节没变"根本不是不变的条件）；
3. 任何**未解释的主文件改写**（尤其 mtime 落在某个我启动/停止进程的窗口里）要写明"疑似 checkpoint，未证实"，
   不许写"无损"。今天的措辞我按这条改口：**用户库无 reset、无 reseed、无行增删（六表行数与三次先前读数一致）**，
   但"逐字节未变"这句我撤回。
