## commander 冻结行更新 @2026-09-22T13:3x+08 —— 仲裁改口：**`CURRENT_INTEGRATION_REFERENCE_TIP = c0d7e3d`**；另补第二把全量（11 条逐 nodeid 不变）

### ① 仲裁原话（总线 `5771623368` @ 13:24:58+08，全文 127 字，我不转述成别的意思）

> 改：`CURRENT_INTEGRATION_REFERENCE_TIP = c0d7e3d`；`e0fc697` 保留为上一比较锚点，
> 不升级为稳定 baseline，P7=false 与 P0 冻结均不变。

⇒ **全体车道以 `c0d7e3d` 为参考尖**（它＝我的合并：`ebb4b3f` 你的改名 + `7167ef6` B 的 reply-level 计数）；
`e0fc697` 只是比较锚点，**谁都不许把这两把全量报成"基线"**。P7 仍 false，P0 冻结不变。

### ② 第二把全量（干净导出树 `v_c0d7e3d`、`.venv` 3.12.14、`DEEPSEEK_API_KEY`/`AI_ENABLED`/`DEMO_MODE` 全 unset）

```
CMD  python -m pytest -q --tb=line -p no:randomly        （整棵 backend）
SHA  c0d7e3d   TREE D:\moodle\_qoder_cmdr_ref_20260921\v_c0d7e3d（git archive 导出，无 .git）
RESULT  11 failed / 1151 passed / 15 skipped / 1 xfailed in 127.77s，exit=1
        collected 1178（与 `ebb4b3f`、`e0fc697` 逐数相同）
```

**红集合逐 nodeid 与 `e0fc697` 那 11 条完全相同**（我按 nodeid 排序对过，不是我"看起来一样"）：
`discovery_truth g16b/g17a/g18a/g18b`、`gates g5`、`lock_duration g9b`、`matrix_truth g13d/g14b`、
`provider_independence g8a`、`provider_truth g10/g11`。

⇒ 这一把的价值不是"更绿"，而是**回归对照**：改名（enum＋两份契约＋发射点＋retryable 联动）＋ 合并（新增两列计数）
之后，产品红一条没多、一条没少。仍按仲裁口径标 `observation`，**不叫 baseline**——要 baseline 得在同一尖上 ≥3 次可比跑＋区间＋游名。

### ③ 现在各单状态（我名下、带证据的收口）

- **ORD-0200（F）＝ `ACCEPTED`**：`c79304d` 6 passed → `adf0a3a` **8 passed**，第二步已把 `return {}` 换成双向判据
  （`applicable && {} ⇒ RED`／`not applicable && 仍给 attribution ⇒ RED`）。F 现接我 13:1x 派下的三件量具修复（g5/g9b/g8a）。
- **ORD-0202 第一步（C）＝ 收讫**：11 条 triage ＝ **9 具名产品缺口 + 2 量具缺陷**，含实测行号（它自己发现门报的行号漂了两处并改正）。
  第二步（消费 B 的计数）此前被"B 未合并"挡住——**现在 `c0d7e3d` 已含那两个字段**，路通了。
- **ORD-0204（E）＝ 收讫、我核过形状**：自己的干净副本 `tree7`，基线 collected 29/29 passed；
  四个新发射器 **a/c/d KILLED**，(b) 与契约里已登记的**预期幸存者 M17 一致地 SURVIVED**，并补第三臂让"只是冗余"变可证伪。
  ⚠ 它跑的是 `e0fc697`；我已让它在新参考尖 `c0d7e3d` 上重钉一遍再算终态。
- **ORD-0190（HERMES）第一步＝ 收讫**：冻结（0 监听 / 0 进程 / 三库 checkpoint 无 `-wal` 残留）→ 重出 manifest
  `generated 2026-09-22T12:44:08+0800`、182 条含 sha256 → 覆盖检查。按用户令 §3 转入 H4–H10 并行。

### ④ 环境：盘已宽

我 13:0x 清出 2.0 GB（自己的导出与 `node_modules`/`dist`）之后 D: 3.43 GiB；用户又腾出空间，13:27 实测
**D: 剩 15.47 GiB / C: 剩 12.42 GiB**。我不再为省盘复用旧导出树，但保留两条纪律：
一份尖只留一份导出、被空间失败中断过的树**必须重导**（`tar` 半棵树写出来会伪装成干净基线）。
