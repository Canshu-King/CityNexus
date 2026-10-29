# 2026-10-25 夜班交付审计（rescue/v3-final-departure-20261022）

写这份审计时的分支尖 `492a6dee57fcf3c75ab2c5a1912e42214ccde499`（本地与远端两读一致）；审计文件自身的提交会让尖再前移一格，**以 PR head 的现读为准**。PR #43 仍 Draft；USER_VERIFIED = PENDING。

## 一、本班九个提交

| 提交 | 内容 | 回执 / 账本 |
|---|---|---|
| `1d2fa26400` | 多人同行牌写人数并落到真卡（同套 52 条全绿） | 25 / 五十七 |
| `525c89eb75` | 有方案的行程重认证后能恢复（409 不是拒绝） | 26 / 五十八 |
| `d398c7a8a1` | 「排不下」现场读数：手动挪时间、重排按钮不出现 | 29（并入）/ 无独立块 |
| `c0f9180122` | 启动器两处断点：指向旧副本、就绪判定等错进程 | 27 / 五十九 |
| `767dfcfc30` | 启动器证据摘要 | — |
| `80a3b96712` | 询问屏：有待答问题时选项是唯一主操作 | 28 / 六十 |
| `6a2715ce65` | 询问屏证据摘要 | — |
| `2f2a91e58c` | 日期冲突现场 + 八步单页第 2 步 | 29 / 六十一 |
| `492a6dee57` | 日期冲突证据摘要 | — |

## 二、门与回归（现读）

- 整套手机夹具 **52 passed / 0 failed / 12.6 分钟**（`trial/results/20261022_v3_human_chrome/fixture-suite-p1d-1.log`）——本班唯一一次整套，之后新增/修改的三刀**未整套复跑**。
- 恢复夹具 **5 passed**（`recovery-spec-2.log`）；对话夹具 **3 passed**（`ask-choice-spec-1.log`）。
- 类型检查 rc=0：`typecheck-p1d-2.log`、`typecheck-recover-1.log`、`typecheck-ask1-1.log`。
- 真栈读数：cap3 恢复前后（`cap3-recover-before/after-1.txt`）、422 披露（`cap3-diag-1.txt`）、试玩栈（`play-ready-1.txt` / `play-preflight-1.txt` / `play-providers-1.txt`）、询问屏（`play-v3-ask-1.txt:13`）、研究与日期（`play-v3-research-1.txt:22`）。

## 三、产品刀（四枚）

1. 多人同行牌：`frontend/src/trial/mobile/MissionCockpit.tsx:344`、`frontend/src/trial/RevolutionFirstLook.tsx:400`、`frontend/src/features/execution/LiveRecovery.tsx:1582`。
2. 恢复腿：`frontend/src/trial/RevolutionFirstLook.tsx:524`（门 `frontend/e2e/revolution-human-session-recovery.spec.ts:241`）。
3. 询问屏：`frontend/src/trial/mobile/WorkspaceActions.tsx:595`（门 `frontend/e2e/revolution-dialogue.spec.ts:60`）。
4. 启动器：`trial/play_launcher/citynexus-play.bat:8`、`citynexus-play-server.bat:8`、`_cmdr_v3_serve_human_r1.py:132`。

## 四、待裁与缺口（不冒充）

- **安全再认证**：P0-3 仍 BLOCKED；本班只修了「已有合法令牌时被 409 误判」。
- **排不下时的重排可达性**：现场给手动挪时间，重排放不到屏上（§五十九）。
- **日期合并**：话里的日期与「日期与天数」不一致时，研究出不了正式方案（§六十二，任务 #330）。
- **研究→选用方案终屏**：未拍到；研究确实跑过（45 事件 / 8 工具 / 16 地点）。
- **物理手机**：所有证据来自桌面窗口；USER_VERIFIED 需主人真机。

## 五、环境

- 本班起的隔离栈（cap3 60532/14532、play 60361/14461）已全部停止，四个端口现读空闲。
- 未触碰用户真库与在跑服务（wb2api 7863、codex-shim 7864、preview 4173 未动）。
- 隔离副本保留：`D:\moodle\_cmdr_v3_live_1022\citynexus_v3_cap3_1025.db`、`citynexus_v3_play_1024.db`。

## 六、审计结论

本班交付均带坐标（提交 / 回执 / 账本 / 屏证），未完成项逐条列出。**不把本任务标 complete**：时间目标未到，且 USER_VERIFIED 要主人自己用手机按一遍。
