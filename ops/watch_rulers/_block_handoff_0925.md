### CMDR-0945 · SHIFT-HANDOFF（10:00 收口态：什么已落地 / 什么只是"验过没上线" / 下一班第一分钟做什么）

写这块的目的是：我这一班到 10:00 停手，**不许把状态留在我的会话记忆里**。所有事实下面都带外读坐标或现场读数。

**一、权威线（`mirror/integration-frontend-apple-pass1`）今天的落地序列，尖现在 = `90d29a172e186aab6e6cb138ab4583ccf93bfa68`**
按 ancestry 实读（`GET /repos/Canshu-King/CityNexus/commits?sha=mirror%2Fintegration-frontend-apple-pass1&per_page=5`，09:45 那次输出即下面顺序）：
`45a3d56862fcebd7aa50c16b4a80842320a97856`（收敛安全点）→ `ef277b2da5dfff22ae3f1deaf63b295f5cda678f`（被换到手机的那一代前端）→ `5c4608cede6cb7bd5f3ac7e704bfee379ca47abc`（ORD-0287 re-cut，我自己按 Q40=① 重切的单文件门）→ `6d041dcce11d05f28a55abadd40717f321b4db38`（ORD-0296 写预算）→ **`90d29a172e186aab6e6cb138ab4583ccf93bfa68`（ORD-0280 归因标签）**。
每一笔都是我亲手用 `PATCH force=false` 落的（http 200，落地前后双路由回读，parent 等于落地前一刻实测的尖 ⇒ 纯 fast-forward）。
质检件：`evidence/ord0280-landing/commander_landing_receipt_r1.json` = `b089d6671d563c94eeacc52bc1156702d164df7d`（3,058 B），
仪器 `evidence/ord0280-landing/ord0280_landing_receipt_r1.py` = `d14f73fbfe25e11c7c5481557cf9a8acf14ccaef`（9,114 B），
本块的句子级质检 `evidence/ord0280-landing/q43_ruler_on_commander_block_0943.json` = `f74431fba9c71a9f282ca51ba6aaa7ce40d482bf`（575 B）。

**二、手机可见链：现在仍然是 08:36 那一代，"已落地"≠"看得到"**
现场读数（09:45）：`:4781` vite preview 与 `:4782` Basic-auth 代理都在 LISTENING（pid `12076` / `34324`），`D:/moodle/_qoder_preview_20260920/dist/index.html` 里点名的是 `assets/index-xKIGmoBz.js`。
Q45=①（10:00 前不动用户可见链）⇒ 我**没有**切 index、**没有**重启预览后端、**没有**动 cloudflared。所以：
- ORD-0296（服务端写预算）＝ `LANDED / NOT-YET-DEPLOYED-to-phone`；
- ORD-0280（归因标签只说服务器说的话）＝ `LANDED / NOT-YET-DEPLOYED-to-phone`；
- 手机上能看到的最后一代 = 08:36 那次换代（收据 `receipts/deploy_ef277b2da5dfff22ae3f1deaf63b295f5cda678f_0925_083644.json` = blob `250325c15f1ddff5d2d26c41d3e5c4ed83559d32`，`overall=GREEN`，换机后手机侧字节证明 `evidence/ord0274-landed-generation/deployed_bundle_bytecheck_r1.json` = `62f07fe62934750b57c1ef6a7a227c7c33c91e30`）。

**三、下一班第一分钟该做的两件（都需先解除 Q45 的时间窗，即 10:00 之后）**
1. 让 ORD-0296 真生效 = 重启预览后端（它读的是 `CITYNEXUS_BACKEND_PORT`，起面必须带这个变量；否则 `vite preview` 的 `/api` 代理会指向别人的 8000）：
   先 `python live_checks/deploy_bundle.py --preflight-check` 确认不动产品，再按 `project-mobile-preview-topology` 里那条命令重启，然后跑 `live_checks/bundle_selfreference_check_r2.py --look` 与手机侧探针。
2. 若要 ORD-0280 上手机：`deploy_bundle.py` 正常模式（union→verify→switch），**union 先行**（`DEPLOY_BUNDLE_RETENTION`）；切换前必须重跑 `dist_hardlink_scan.py --serve`（上次 08:15 基线 hits `0`）。备份自清：`ls -d /d/moodle/_qoder_preview_20260920/dist_bak_* | wc -l` 在 09:46 实测读出 **18**（最新两枚 `dist_bak_083634_1790296594717662300`、`dist_bak_051542_1790284542652833400`），各车道按**具名清单**自清、只保留 current+previous，不许按名字形状扫删。

（更正一条我自己刚写错的读数：这份 handoff 的草稿里我把上面那个计数写成 8，那是 `| tail -8` 截出来的显示条数，不是目录里的条数；正文已按 `wc -l` 的实读改成 18。教训与 09-20 那次"分母被 tail 吃掉"同族。）

**四、还欠谁的什么（交接不是关闭）**
- D（红队）：ORD-0278 / ORD-0253 的 `derived_result` 必须署**测量代次**；`90d29a172e186aab6e6cb138ab4583ccf93bfa68` 改过 `frontend/src/features/planning/PlanWithAiSheet.tsx`（blob `c22cf42506a4175db992bde387ed8d9c6f1ffb9d`，47,470 B），凡渲染该组件的臂在 `6d041dcce11d05f28a55abadd40717f321b4db38` 上量到的只能算前一代。
- HJ-P1：ORD-0297（B3/A 臂）在跑，交回时按 Q38 尺子的口径写每格 `why`（尺子 `live_checks/receipt_cell_derivation_check_r2.py`，blob `91ae8b1ec55f5c19122af11bf775df14580955e4`，自带 10 臂 selftest）。
- F：还欠 `evidence/ord0289-ast-census/write_legs_f.json`（写腿机器清单）；那把字面量 key 的**轮换只有用户能做**。
- B：ORD-0288（无幂等键那一腿）代码仍在 hold，等仲裁定归属；不要顺手合。
- 我这一班留下的两处自我更正（别当成别人的缺陷）：09:31 我预告的"第二次切换"在 Q45=① 之后当场作废；08:18 我误叫红队"没动"，实际它 08:01 就交了 ORD-0295，已撤回并改成"叫醒任何车道前先扫 `commander/control` 与 refs"。

**五、只有用户能做的两件事**：轮换那把仍然有效的 key（09-23 复测仍与 `c0d7e3d` 里的字面量精确相等）；如要新开仲裁会话，需要你同意 GitHub 高风险权限。
