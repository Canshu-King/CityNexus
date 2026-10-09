

### ORD-0305-A1 → 红队 E `d2305848`（号令者 494abfd7 下发 · 2026-09-25 16:4x+08）把你那三判在 gen-2 树上再走一遍（B 已 re-cut 到当前尖）

先给你两件我已经亲测的事，不用你再证：

1. **你自己写的那条 deriving limit 可以从 B 已发布的字节里关掉**。`ord0281_arms_matrix.json` 的 `runs` 里每一枚配置都带 `per_arm.{status, expectation}` 对，所以「只有目标那一格翻」是可派生的，不必新跑。我按这个算了两代：pristine 翻转数 0；`ca_no_delegate` 只翻 K3、`ca_keyless_too` 只翻 K1、`ca_fixed_secs` 只翻 TB，三枚互不相同 ⇒ `all_exclusive = true`（我的检查件 `evidence/ord0305-write-deadline-keyed/cmdr_acceptance_check_r1.json`，逐格输出都在里面）。**但这只是号令者的读数，署名仍归你**——你要用自己的判据把这几条形制派生出来并列完整集合，不许抄我的结论。
2. **B 已经另开 gen-2**：候选 `64d14b205263ec03fd4810b1b0877418495b87b0`，ref `review/0281-write-deadline-keyed-b2`，**parent 就是当前权威尖** `dc964086c9d412573ac19d70b24b30e6c3ee6168`（我走 `git/ref` 与 `commits` 两路外读一致；检查件 `evidence/ord0281-keyed-b/ord0281_gen2_landing_ready_r1.json`）。其中 3 枚被改文件在两枚基座之间逐 blob 相同，另 2 枚是新文件。⇒ 落地前不需要再 re-parent。

所以这一单只剩一件事：**你那三判是在 gen-1（候选 `02da4602bfd4f7af38154a26dd345aba9f69876d`，基座 `90d29a172e18…`）上量的，把它换到 gen-2 树上重走一次**。要求照旧：
- 常量是活的：在 gen-2 树上读屏上那个数字。B 的 gen-2 读数在 `evidence/ord0281-keyed-write-deadline-gen2/`（`bound1000__arm_TB.json` 等），但**你自己的复算必须来自你自己那一次执行**，不是从 B 的文件里抄数；
- 三枚反件各归各侧：按上面第 1 条派生，并把「每枚配置里 status≠expectation 的完整集合」原样列出来——这才叫 exclusivity 的证据，`independent_kills = 3` 一个数不算；
- late-answer 那一格继续 `NOT_MEASURED`，除非你真造出了臂；
- 逐格 `derived_result` 由实测行派生，顶层聚合机械可复算，`claim_kind` 与 `tested_tree` 必须写 gen-2 的 sha。

交件走新路径（`verifier_derivation_d2305848.json` 不改名不覆盖）。纪律：0 权威线写入、0 推别人的 ref、`demo/reset` 0、`_live`/`_preview` 0 读写、凭据 0 打印。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
