### 11.7 本代尖上的门禁读数（逐步骤，不是"作业绿"）

最终尖 `83a4ab4e9f`（本节的账在 `c48b190aa7` 之后一笔交付件修订）触发的 run `40745173400`：
三枚作业全 `success`，测量作业逐步出声——`Scan every screen setter for a raw client error string:success`、
`Prove the ruler still catches the leak that really reached a traveller:success`、
**`Prove no two walk arms drive one browser or write one receipt:success`**，其余为 setup / Post / Complete 步。
`Backend signed journey and classroom integration` 与 `Frontend typecheck and Vite build` 同代 `success`。

要写清的两笔：`e351f5089c`（半条改动）与 `5182018dab`（修全）各自的 run 都被顶掉——
`40744442663`、`40744646043` 结论 `cancelled`，这是顶部 `concurrency` + `cancel-in-progress: true` 的正常行为，
不是红；因此"修复后的那一代有没有过闸"这个问题，答案要靠最后这趟 `40745173400` 才算证到，
而它在 `trial/**` 已进 `paths` 之后才会被一次纯文档/纯臂的推送触发（本笔正是纯 `trial/**` 的推送，
所以这条触发路径也顺带验到了第二次）。

窄配置那把看不见这两枚文件的类型闸（§11.5、交付件第 8 条）仍在原处，本代没有替它做主：
`Frontend typecheck and Vite build` 里的 `Typecheck current V3 product` 步骤跑的还是 5 枚具名文件那份清单，
它对 `DraftDepartureCard.tsx` 的引用错误依然会绿。这条要扩不扩，等主人点头或由那枚配置的写者自己动。
