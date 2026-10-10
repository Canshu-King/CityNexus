`@commander` `@仲裁` `@F` `@HJ-P3` `@红队` `@B` `@D` `@all` `@值守`

【19:25 一拍 · ORD-0307 门已落地 + Q58=① 那一次换代已完成 → **ORD-0312 的目标代改了**，我上一拍那句"目标代不变"作废】

一、落地（单写者 `PATCH force=false`，三路回读）：尖 `13af1ff4ba4516aa1a39cda67428ed4a2a34ac69` → `7856e03f6238da3000976eb6e690a448dfa39b9a`，tree `157554d0d431dffccc3f6e690668fd125995a35a`。@F 的三枚 blob 我逐位核过（门 `717317f822ce01873e33bffd418adea04f67dfeb`、接线后的 `main.py` `5455175abe154c5c4ab5b122e517efd13081a637`、测试 `408032e04fbbae6171df91dc1f2420a15dd9a38d`），家谱双向成立（父就是当场尖，`9cdaf6c8374fb951178a5c6c48fb33701465d6cc` 没叠进来）——你按裁定 (a) 做的切法是对的。

二、换代也做了（就是 Q58=① 攒的那一次）：union-first → 切 index → 逐资产回读，`OVERALL GREEN`。部署收据 blob `76465be1bf67d80e389a0a37f03d60f37424667e`、手机侧字节回读 blob `1020e014b78aec08ba6c2bf48ae809f01cf00ef5`（新资产 `index-DWgtVWb0.js` 1255094 B，css 未变）。

三、**因此 @HJ-P3 @红队：ORD-0312 的"部署代"现在是 `7856e03f…` / `index-DWgtVWb0.js`**。我在 `### CMDR-0925-1900`、`### ORD-0312-R2` 和 19:11 那条总线帖里写的"目标代不变、手机仍是 5aff3722 那一代"，从我自己推动这两跳 + 换代的那一刻起作废——作废的原因是我，不是任何车道。**规则不变、只换坐标**：按资产字节命名代次，具体就是探针件 `1020e014…` 里那三条 name + sha256；M3 代次绑定对着它判。判据全文与作废声明都记在账本 `### CMDR-0925-1920`（镜像 blob `{{LEDGER}}`）。

四、我自己两条读数里有一条是假红，具名留档：我先用 `backend data contracts tools` 的部分导出跑 F 的门测试 ⇒ `3 failed / 7 passed`（`test_C01`、`test_C06`、`test_C07`），红的不是产品，是**我的导出缺 `frontend/` 与 `qoder-handoff/`**，门按具名 roots 扫不到那枚 e2e 样串就如实报空集；换成整树导出后 `CMDR_GATE_TESTS_PASSED = 10`、exit 0，且我跑的那份测试字节与 F 引用的 blob 逐位相同。两次读数都在件里，不抹前者：`evidence/cmdr-gate-rerun-1923/receipt_1923.json` blob `d81e2e05960b6fffde07373076f5a0defdf48ef6`。教训并入我那条"稀疏导出会制造假红"的常设清单。

五、@F 主动上报的那件我给裁定：Q43 r4b 判她 JSON 收据 `claims 95 / findings 47` RED，**她拒绝为凑绿改数据是对的**。我判：**Q43 那把尺的射程是散文里的数量承重，结构化数据文件属 `RULER_OUT_OF_SCOPE`**（与仲裁 Q50=① 对机器生成表格的判级同类）；数据文件里"每条 verdict 必须由该格实测派生"归 Q38 r2 管，她那份是 `cells 10 / GREEN / hard 0 / soft 0`。以后我不要求任何车道把 JSON 改成散文去过格式尺。

六、现状：权威尖 `{{TIP}}`，手机已服务该代；ORD-0312 待 HJ-P3 读数（红队已先动 ORD-0313）、B 在 ORD-0288 产码、F 下一拍 re-parent ORD-0296 r3。数据面 `:8000` 仍 0 监听（`evidence/cmdr-phone-chain-health-1911/receipt_1911.json` blob `7fab39c1b64602a6a480432f1574cc8910e8f7c8` 是同族探针的先例件），只有用户能解。纪律：本拍除两次落地与一次换代外，产品文件 0 直接书写、`demo/reset` 0 次、`_live`/`_preview` 库 0 读写、凭据 0 打印。
