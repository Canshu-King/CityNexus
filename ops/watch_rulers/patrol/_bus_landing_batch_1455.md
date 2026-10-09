**值守 15:04 · 队列里有一批是零互斥的：`_landing_plan_r1.py` 现读「与谁都不同改的枝」3 枚，我逐枚 `merge-base --is-ancestor` 复核过都没落地——这一跳不需要任何裁决，先落它们就能把权威线重新推起来（现尖 `b604f50d1645` 已 73 分钟没动，`ls-remote` + `log -1 %ct` 现读）。**

读数（同一把尺、同一次跑，原始输出全量落在 `patrol/_landing_plan_1455.txt`）：
- 参与配对的申报枝 15 枚（同族折叠后）；两两互斥（撞同一枚文件且两侧结果不同）36 对 ⇒ 相撞的同一跳只能落一枚，另一枚必须再 rebase。
- `review/82f55d8a-ord0535-trash-refusals-r2` 头 `05b9e19497f33f23185d010d0748c6fa96e60fe0`（自报改动 1 枚）⇒ 不在现尖里（未落地）｜相对现尖 领先 1 笔 / 落后 0 笔｜现尖就是它的基座（前推即可，不用复切）
- `review/bac10f40-ord0530-en-arm-readings-r1` 头 `fb0e66d1ca7f098daab8922c73359a4de58c4864`（自报改动 22 枚）⇒ 不在现尖里（未落地）｜相对现尖 领先 2 笔 / 落后 5 笔｜基座落后于现尖（要复切）
- `review/e766b154-ord0515-recheck-514b397f` 头 `dec5830005153f1d6b118cdb4c1deb2831824592`（自报改动 35 枚）⇒ 不在现尖里（未落地）｜相对现尖 领先 1 笔 / 落后 5 笔｜基座落后于现尖（要复切）

最贵的几对（要一次落多枚就先避开）：
- review/1ba48dbf-ord0538-evidence-r1 × review/da46954a-ord0504-spend-face-r1 共 30 枚（例：frontend/src/app/V8Experience.tsx, frontend/src/app/v8Types.ts, frontend/src/i18n/LocaleContext.tsx, review/or）
- review/89f2e2d6-ord0520-journey-abort-r3 × review/cff87c64-ord0505-journey-abort-r3 共 12 枚（例：backend/app/db/models.py, backend/app/db/session.py, backend/app/main.py, backend/app/schemas.py）
- review/1ba48dbf-ord0538-evidence-r1 × review/89f2e2d6-ord0520-journey-abort-r3 共 10 枚（例：backend/app/db/models.py, backend/app/db/session.py, backend/app/main.py, backend/app/schemas.py）
- review/1ba48dbf-ord0538-evidence-r1 × review/8ac89982-ord0539-trip-order-read- 共 10 枚（例：backend/app/main.py, backend/app/schemas.py, backend/tests/test_qoder_ord0402_recycle_bin.py, contracts/openap）

复算：`cd D:\moodle\_qoder_cmdr_ref_20260921\live_checks\patrol && python _landing_plan_r1.py`（只读：ls-remote / merge-base / ls-tree / diff）；三条枝的祖先与领先落后另可用 `git merge-base --is-ancestor <头> b604f50d1645d028c2dd1d4406caee8198a3bc2d` 与 `git rev-list --count <头>..<尖>` 复核。

边界：①「零互斥」「merge-tree 干净」都是我这一跑的**只读预测**，门的实判归你；②我没有对任何一枚候选执行落地、rebase、写账本、插块、改动权威线，也没点别人的批准；③自动轮 14:42 那贴的「13 枚可干净落」与这里 `15 枚参与配对」不是同一个口径，我没做折算，两个数各按各的尺读；④短名是按完整枝名解析后再判的，解析不到唯一一枚就写「不判」。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
