**S1-q64sweep → 换尺令已执行：r3 重扫全树，清单未变；但抓到两代尺共同漏掉的三链上游正文（附可复跑证明）**

generation = {{TIP}}（换尺前后各读一次 `ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`，同一枚，`tip_moved=False`）。账本镜像 blob {{LEDGER}}。总线参 issuecomment-5838017559。

**你给的四枚坐标逐一 `git rev-parse origin/cmdcontrol:<route>` 回读全等**：尺 `evidence/cmdr-ui-exposure-r3-0200/ui_exposure_field_check_r3.py` = 44e062e6ce9c7b5d97d78e09e432072da102292c（尺体我按 blob 取字节、只读不改），自测件 3b42290b6f66492dfa6355f59db360408ccab882、差分件 a8807c857cfc2d5ca7d43dec90fe4346b347fc44、捕获件 5e0b53bd7cdc7455ae931148b54b889684a207d1。r3 `--selftest` = SELFTEST_PASS，n_fixtures 13（红 8 / 净 5），13 条 assertion_met 全 True，你三枚新夹具各响、两枚干净侧各 0 响。

**重扫**（尺本体逐文件 `--ref/--path`，files_scanned=74、files_failed=0，计数由尺的工件重算）：hits_total=25、files_with_hits=12、分类 upstream_prose 16 / local_wording 6 / machine_label 3 —— 与 r2 那份**完全一致**。

**代际差分（与本令预期相反，故写明）**：按 (path, line, rule, taint_chain) 四元组比，`identical_hit_set=True`、`only_in_r3` 与 `only_in_r2` 皆空。不是"尺没响所以没有"：我正向普查了载体 —— `shape_A_tail_name_in_interp` 计数 2、`shape_C_paren_alias` 计数 0、`shape_B_bare_local_in_text_sink` 计数 25。B 形大量存在，但 r3 的裸局部臂要求名字绑定自一个 *返回* 上游读取的 `function` 声明 helper，全树这类 helper 一枚没有（`generic_signature_function_helper` 计数 11，样本 api/citynexus.ts:645、app/V8Experience.tsx:192，全是 `<T>` 签名；`arrow_helper_returning_forbidden_read` 计数 0）。所以 r3 的三处新文法在尖上无从兑现，**`sweep_r1.json` 那份清单不是"不能用了"而是仍然成立**。基准与负控在 r3 下各自复跑仍成立：`PlanWithAiSheet.tsx` 仍 1 命中（规则、:1016、链 `serverReasonSentence`→`failureReason` 全符）、`frontend/src/lib/money.ts` 仍 0 命中，verdict=SWEEP_VALID 由这两格派生。

**换来的真收获：三链服务器正文出屏，r2 与 r3 都答 NO_EXPOSURE_SHAPE_FOUND**。两代尺对这三枚文件各跑各 0 命中，并把真实链路裁成最小复现件与一枚正控同批过尺：**正控在 r2 与 r3 下均响 1，k1/k2/k3 在两代下均 0** ⇒ 沉默是规则缺口而非跑具坏。

- K1 `frontend/src/features/discovery/RealCityDiscoveryPanel.tsx`：:65 `throw new Error(body?.error?.message ?? body?.detail …)` → :110 局部 `message` → :116 `setError` → :150 `<div role="alert">{error}</div>`（taint 臂要 return、direct 臂要花括号，两跳都不沾）
- K2 `frontend/src/features/recovery/V14RecoveryTruthPanel.tsx`：:82 抛 `body?.detail` → :93 `error.message` 落在 `setMessage(` 的调用实参位 → :162 `{message}`（穿过的是调用括号）
- K3 `frontend/src/features/studio/V12TripStudioPanel.tsx`：:106 `{(previewMutation.error ?? acceptMutation.error)?.message}` —— 这正是 r2 文件头声称 UPSTREAM_READ_DIRECT 覆盖的"上游读取直插 JSX 插值"，不响只因 `.message` 左侧是右括号而非那九个名字；正文来源 `frontend/src/api/v12Authoritative.ts:27`
- 给 r4 的三形即：**抛出型 helper 装载 Error.message**、**调用实参位**、**右括号/空合并之后再取禁用名**。边界我也量了：`throw_embedding_upstream_prose` 计数 4 其中 3 在零命中文件；`setstate_called_with_error_message` 计数 10 全部落在已响文件（不算新盲区）。B 形里 4 枚我追到并非服务器正文（`BookingArtifactScanner.tsx:33` 本机摄像头解出的二维码文本、`StayExplorer.tsx:37` city_code 派生、`V12StatePrimitives.tsx:16` 走字典映射），`JourneyTrialSetup.tsx:637` 的 `message` 是 prop、我没追到底，按未测出列出而非清账。

**上架（新路径，0 覆盖，decision=CREATED 且 proof=BYTE-LEVEL MATCH）**

- `commander/control:evidence/q64-sweep-S1/sweep_r2.json` = blob 33576c7390ec431ba0fad5d6dd73a76a99fe59e0，publish commit eba3f04dd955ce753fcdc3f4ee00bffbadc683f3
- 独立回读走第二扇门：fetch 后 `git rev-parse origin/cmdcontrol:evidence/q64-sweep-S1/sweep_r2.json` = 33576c7390ec431ba0fad5d6dd73a76a99fe59e0，`git cat-file -s` 与本地 `hash-object` 三处全等
- 回读收据 `commander/control:evidence/q64-sweep-S1/readback_proof_r2.json` = blob 5054c3c3d07e035de14306c4a6e444e722a0e4ba，commit e6fdc348964635c1effdf6539beed18593ba0c9d，`rev-parse` 同值，verdict READBACK_CONCORDANT

**我自纠一笔**：发布前我那条"预配 blob"one-liner 写成 `sha1(b'blob %d\x00' % len(b))`、漏了拼接文件字节，报出 6f8282fb29b5ab5696486704b6b9a739796fd282 与门回读的 33576c7390ec431ba0fad5d6dd73a76a99fe59e0 不符。我按不符追查到自己的表达式：磁盘件 mtime 未变、补上拼接后逐字复现即得 33576c73。上架字节自始正确，错在我的读数，故不重发、不动已发路径。

**账本块** `D:\moodle\_qoder_ledger_inbox\S1-q64sweep_0315.md`（首行 `### `，自跑 Q43 r4c = Q43_GATE_GREEN，findings 0）。**边界** 0 改产品字节（交付前 `git status --porcelain frontend` 读回 0 行）、0 推权威分支、未 import 尺、未 demo/reset、未碰 `*_live.db`/`*_preview.db`、未 vite build、未读未打印任何凭据；同检出 `backend/app/main.py` 等 modified 属别的车道既有状态（R14）。**下一步归属** 是否升 r4 归你与量具车道，判据用 K1/K2/K3 裁剪件加正控即可双向跑；本车道零产品修复。
