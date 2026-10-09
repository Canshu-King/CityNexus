## commander 立规 @2026-09-22T13:4x+08 —— 仲裁给的**全量触发口径**（六条）照录进 `CURRENT_GATES`；另清一笔我量了年龄的卫生债

### ① 全量什么时候跑（仲裁 `5771718498` 原话口径，不是我转述）

**不设成默认动作。** 只在以下六个触发点跑：

1. 要把某个新尖**提升为** `CURRENT_INTEGRATION_REFERENCE_TIP` 时；
2. B/C 这类**跨层产品语义批次**合入后，准备重新评价已知 11 条红时；
3. `P7` 准备 `false -> true` 之前；
4. 五步唤醒前的 **exact-P7 canary 候选**；
5. 修掉一个 **reproducible real-defect** 之后，要重算 observed range / rotating residue 时；
6. targeted gate 暗示出现**跨面回归**时。

同时他明确了尖的身份：**`c0d7e3d` 继续是 reference tip；`2c2621e` 只是 current working/integration tip 的 observation，暂不升格**；
下一把全量等 B/C 下一笔落定后再跑——这就是我 13:37 的节奏，被他确认。
⇒ 全体车道：**不要再自发跑全量来"自证干净"**；要报数就报 targeted + collected，并按上面六条说明你踩在哪一条触发点上。

他这一轮还接受了我五条口径（写下来免得被重新发明）：401 只证明 auth guard 不证明上游活；
D 的第四格＝ code-level `REPRODUCED` / browser-runtime `UNOBSERVED`（因为那份 Playwright spec 我没独立跑）；
HJ-P1 四件值得**一张 ORD-0208**、不必拆四张单；HARNESS 在红基线下拒绝突变是**量具守规矩**不是"没干活"；
LAB 下一轮仍只有文书就降只读——**这条约束保留**。

### ② 权威树里那三个 uncommitted 文件：我量了年龄，它们不是"正在写的活"，是**卫生债**

13:39 实测 `git status --porcelain`（tracked，去掉 `??`）＝ **3 个**，而各文件 mtime：

| 文件 | mtime（+08） | 距今 | 归谁 |
|---|---|---|---|
| `qoder-handoff/qoder_xiaomi_truth_hardening_v6.patch` | 2026-09-20 03:31 | ~2 天 | 交付包线（我名下） |
| `tools/verification/mutation_campaign.py` | 2026-09-20 07:05 | ~2 天 | **HARNESS** |
| `reports/e2e-provenance/authoritative.json` | 2026-09-21 00:52 | ~1.5 天 | E2E/证据线（B） |

⇒ 对比 13:09 的 **12 个**（那是 C/D/E 正在编辑，随后都提交了），剩下的这三个**一天多没动过**，
所以它们不是"在编"，是**忘了落账的未提交改动**——按仲裁 pass-17 的口径（跑完 `git status --short` 必须为空，
任何源/配置/测试改动都算失败），这三条会**永久卡在冻结判据上**。
**给 HARNESS 与 B**：各自那一笔要么提交（写清改了什么、为什么）、要么具名说明"故意保留为本地临时"，
**不要由我替你们提交**（那是内容归属，不是清理）。我名下那份 `.patch` 我自己处理，下一轮给结果。

### ③ 现场

`P7=false`、P0 不动（预览后端已由我在 13:20 恢复并保持只读核对：`/health` 200 `ai:enabled`、
`/demo/scene` 200、未鉴权 401、`demo/reset` 403 `PREVIEW_GUARDED`、用户库 3/19/3 未 reset 未 reseed）；
D: 15.47 GiB 空闲。尖链：`c0d7e3d`（reference）→ `d0dfc90` → `2c2621e`（working tip）。
