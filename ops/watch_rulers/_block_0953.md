### CMDR-0953 · Q46 已回字并盖章：换 index 之前必须先过双尺（③）— 交接指令定稿

仲裁 09:52 对 Q46 回 **③**（窗口原话只有一个符号"③"）。**这条回字目前的 durable 等级 = `COMMANDER_RELAYED`**：仲裁自己还没在总线上给 Q46 盖章，所以按 Q43 的口径我不写"仲裁在总线说"，只写"我在窗口读到 ③、我盖章转发"， durable 坐标是 `Canshu-King/CityNexus-Workspace` Issue #1 的 `issuecomment-5825382870`。下一班开工先确认仲裁有没有补它自己那条章；补上了就把等级升成 `ARBITER_STAMPED`，**没补也不要停手**——门的内容不依赖署名。
我把这条当**换代前置门**执行并盖章：
**任何 `dist/index.html` 切换之前，必须先有两把尺的绿读数** ——
`live_checks/bundle_selfreference_check_r2.py --look <serve root>`（blob `fb6497edd2075b3842377804863df95cf5cbd350`：index 点名的 asset 必须在自己目录里存在且字节相同；r1 曾在 0 roots 上打印 `ALL_SELF_REFERENTIAL` 并退出 0，r2 才把这种空转改成 `roots_actually_measured=0` + 退出 6，见 `evidence/swap-rulers-fix/r1_zero_root_false_green.txt` = `044595aff49a2d236c3fcd45538cff66e0e00529` 与 `r2_zero_root_not_measured_rc6.txt` = `b81844e9d5e79cf2dace72ee2213e88992ad2c7a`）
`live_checks/dist_hardlink_scan.py --serve <serve root>`（blob `ec3a3814bfb794e423e8fe27efe8b0671722de94`；08:15 对当时 serve 根 hits 0）。
双绿之后才允许 `deploy_bundle.py` 正常模式（union→verify→switch，`DEPLOY_BUNDLE_RETENTION` 不动），切完立刻手机侧字节探针（口径同 `evidence/ord0274-landed-generation/deployed_bundle_bytecheck_r1.json` = `62f07fe62934750b57c1ef6a7a227c7c33c91e30`）。
任一尺 RED ⇒ **停在原地**，把读数贴回总线，不许"先切了再说"。

我这一班到此停手。停手时的权威线尖 = `90d29a172e186aab6e6cb138ab4583ccf93bfa68`（ORD-0280，见 `### CMDR-0943`）；手机仍是 `assets/index-xKIGmoBz.js` 那一代（`LANDED / NOT-YET-DEPLOYED-to-phone` 两笔：ORD-0296、ORD-0280）。
在跑不许催停、只要求具名代次：D 的 ORD-0278 / ORD-0253 re-parent（基座 `90d29a172e186aab6e6cb138ab4583ccf93bfa68`）、B 的快照构建那一跑（`release_grade=True / NOT-DEPLOYED`）、F 的 `evidence/ord0289-ast-census/write_legs_f.json`。
欠账：ORD-0288 无幂等键那一腿的归属字（下一班开工第一件事问仲裁）。
盖章条（总线 = `Canshu-King/CityNexus-Workspace` Issue #1）：`issuecomment-5825352438`（落地与点字）、`issuecomment-5825382870`（Q46=③ 与换代流程）。交接正文另有本机文件 `D:\moodle\_qoder_cmdr_ref_20260921\HANDOFF_20260925_1000.md`。
停手前一句不粉的话：**用户今天在手机上看到的东西与 08:37 那次换代之后相比没有任何变化**——这是按 Q45=① 有意为之，但"落地"两个字不该被读成"修好了"。
