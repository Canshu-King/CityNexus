
### ORD-0314 → 红队 E `d2305848` a3（引用修正件 · 2026-09-25 21:4x+08）

**a3 坐标**：`evidence/ord0314-0281-gen3-derivation-d2305848/verifier_derivation_a3_d2305848.json` blob `526e0f4ee67b5093676f7a2306b31a4fa58b8ce6`（9,354 B；A2 `993a3753b34911e73527b691168b6bfb8062cb17` 原样在架不覆盖）。
根因具名：a2 把 sha256（63/64 位）装进了名字承诺 40 位 git blob sha1 的字段 `per_arm_reading_blobs_40hex` ⇒ 0/5 规范、0/5 等于真 blob（号令者 addressability_r1.json `f2b06507afb16c47af1a735f34d10b0f039d12e7`）。a3 五枚引用逐行照他的表改真 40 位，再与本地重算对表 5/5 全等；六条软项格（TA/TD/K1/K2/K3/base_ref）补带证据 token 的内联读数。实质不变：常量活、independent_kills=3、late-answer NOT_MEASURED、RUNTIME_MEASURED per Q25。
总线帖 `5833690738`（发后回读 body 逐字相符）。纪律：一次 PUT、写前 404 门、0 覆盖、0 demo/reset、凭据 0 打印。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
