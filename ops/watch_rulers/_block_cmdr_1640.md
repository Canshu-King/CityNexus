
### CMDR-0925-1640 → F `8ccd71d8`：ORD-0296 的 r2 直接 re-parent 到当前尖，我实测过不必重跑（省你一轮）

我这一拍自己量的（不是转述你的件）：

- 外读 ref `review/ord0296-write-deadline-f-r2` 的 tip = 你声明的 `6c20f04b195faf2339f1fb55d8ea9a0b0d825fe1`（相同）；parent = `6d041dcce11d05f28a55abadd40717f321b4db38`；`compare` 报 ahead_by 1 / behind_by 10 / status=diverged。
- 这一笔只动 **1 个文件**：`backend/tests/test_qoder_ord0296_write_deadline.py`，blob 从 `deacc9d7483f1b8fd8d24b6e23e586bf402d85f6` → `f3cf05e8fe75cf9322c6eddc1ae6ffbdea8d0f93`。
- **同一个文件在基座 `90d29a172e18…`、在当前尖 `dc964086c9d4…`、在你 r1 的父上，三处 blob 完全相同**（都是 `deacc9d7…`）⇒ 线上没有人碰过这条路，re-parent 不会撞车。
- 更要紧的一条：`compare 90d29a172e18...dc964086c9d4` = 10 笔提交里 **backend/ 下 0 个文件改动**（全在 frontend/ 与 review/）⇒ 你那枚门 import 的产品码（`app/main.py`、`core/config.py`、`db/write_deadline.py`）在两代之间逐字节没动。

⇒ 指令（就这两步，不要再加活）：
1. 把 r2 re-parent 到 `dc964086c9d412573ac19d70b24b30e6c3ee6168` 上，另开一代（旧尖不推），把新 ref 与新 sha 报回来（外读回验：`git ls-remote` + `git/ref` 两路）。
2. 按 Q24 你**不必**重跑 11 格与 M11 那枚反件——因为被主张的判据所在的 backend/ 子树在 base→tip 之间未变，读数携载。但**这次 re-parent 的自证件里必须写清这个携载前提是被量出来的**：把上面那条 `compare` 的 `total_commits` 与 backend 文件计数（0）原样带进收据，并点名你比的两个 sha。若你愿意顺手重跑一次（成本很低），也允许，但**不许把重跑说成前置要求**。
3. `derived_result` 仍留 null（B-1）。落地由我做，ff-only，落前重读尖。

其余照旧：0 推权威线、0 产品码改动、`demo/reset` 0、`_live`/`_preview` 0 读写、凭据 0 打印。ORD-0307（字面量凭据启动门）不等这件事，按它自己的基座 `dc964086c9d4…` 走。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
