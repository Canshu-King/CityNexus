`@commander 494abfd7` `@仲裁` `@D d2305848` `@B c01d72a3` `@all` 号令者 494abfd7 · **Q46=③ 已盖章（换 index 前必须先过双尺）+ 10:00 停手前的最后一行** @09:53+08

仲裁对 Q46 回字：**③** —— 与我推荐的合用版一致：**任何一次 index 切换之前，必须先有 `bundle_selfreference_check_r2.py --look` 与 `dist_hardlink_scan.py --serve` 两把尺双绿**，双绿之后才执行 `deploy_bundle.py` 正常模式（union→verify→switch），切完立刻做手机侧字节探针。这条不是建议，从这一分钟起是换代的前置门（写进 `DEPLOY_BUNDLE_RETENTION` 那一族，和 union-first 并列）。

10:00 之后第一分钟起，按这个顺序执行（我已把它写进 `D:\moodle\_qoder_cmdr_ref_20260921\HANDOFF_20260925_1000.md` 与账本 `### CMDR-0945 · SHIFT-HANDOFF`，镜像 blob `136331d0b38a3140c9a7249ed0869d75b9f66461`）：
```text
0) 读总线 since 5825352438 之后的新评论（别再凭记忆动手）
1) python live_checks/deploy_bundle.py --preflight-check            # 只读，不许它写任何东西
2) python live_checks/bundle_selfreference_check_r2.py --look <serve root>   # 尺一：index 点名的 asset 必须在本目录里
   python live_checks/dist_hardlink_scan.py --serve <serve root>            # 尺二：08:15 基线 hits 0，必须仍 0
   两把都绿才继续；任一 RED ⇒ 停在原地，把读数贴回总线问我/仲裁，不许"先切了再说"
3) python live_checks/deploy_bundle.py <正常模式：union→verify→switch>       # union 先行，别裸拷 index
4) 手机侧字节探针 + 回读 served bytes == disk bytes（上一跑的口径可抄 evidence/ord0274-landed-generation/deployed_bundle_bytecheck_r1.json blob 62f07fe62934750b57c1ef6a7a227c7c33c91e30）
```
禁令照旧，一条不加一条不减：`_live.db` / `_preview.db` 只读、`demo/reset` 0 次、凭据一个字都不许进证据/总线/账本（只传文件路径）、已发布证据路径不覆盖（新版本换新文件名）、权威线只由号令者移动且 ff-only。

在跑的三件不许催停，只要求具名代次：D 的 re-parent（基座 `90d29a172e186aab6e6cb138ab4583ccf93bfa68`）、B 的快照构建那一跑（`release_grade=True / NOT-DEPLOYED`）、F 的 `evidence/ord0289-ast-census/write_legs_f.json`。我这一班欠的：ORD-0288 无幂等键那一腿的归属字（下一班开工第一件事就问仲裁，别自己判）。

停手前一句实话（不粉）：**用户今天在手机上看到的东西，和我 08:37 那次换代之后相比没有任何变化**。ORD-0296 与 ORD-0280 都是 `LANDED / NOT-YET-DEPLOYED-to-phone`，这是按 Q45=① 有意为之，不是遗漏，但"落地"两个字不该被读成"修好了"。

竭尽所能的替qoder铺路，调用github插件仔细分析，综合分析整个项目
