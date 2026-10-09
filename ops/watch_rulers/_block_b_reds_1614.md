## commander 读数 @2026-09-22T16:1x+08 —— **B 那四条红在今天的尖上仍全红**（`56d20ec` 干净导出树，一次跑，分母写全）

B `c01d72a3`：16:07 我叫醒你时你已经从 14:52 静默了 75 分钟。下面这把不是复述谁的话，是我自己在 `git archive 56d20ec` 导出树里跑的（`:8693` 未动，临时库由 ORD-0211 的 conftest 自己解析）：

```text
命令  python -m pytest -k "g14a or g14c or g10 or city_failure" -p no:randomly --tb=line -rA --no-header -q
结果  4 failed, 6 passed, 1168 deselected  ⇒ collected 总数 1178（与 HARNESS 15:07 那把 `1178 tests collected` 同分母）

仍红 4 条（具名）：
  test_qoder_anywhere_matrix_truth.py::test_g14a_an_oversized_matrix_fails_closed_and_invents_no_facts
  test_qoder_anywhere_matrix_truth.py::test_g14c_the_verdict_must_not_depend_on_the_providers_wording
  test_qoder_anywhere_provider_truth.py::test_g10_every_normalised_place_carries_a_usable_coordinate_including_nodes
  test_qoder_city_failure_reasons.py::test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at
同文件已过 6 条：city_failure_reasons 另外 4 条 + pending_identity::g10_legacy_rows + provider_identity_leg::g10_one_place_two_index_entries
```

⇒ 结论只有一句：**`NEW_REGRESSIONS=3` 加上你未闭的 g10，在 working tip 上 0 条恢复**。仲裁 15:58 之后这类门的验收是 `GATE_ACCEPTANCE_STREAK`（八条，量具＝我 16:1x 的 `gate_streak.py`，两向自检过）；**g14a/g14c/city_failure 要在同一个 exact SHA 上一次报齐**，别交三把不同 SHA 的截图。
另外那把日志里有一条我自己撞见的线索（不算结论，供你判）：跑这一族时 `real_city.py:1451` 打了 `real-city live discovery failed (RESOLVER_LABEL_CARRIES_INTERNAL_CODE) at anchor_geoco…` ⇒ 与 `test_a_live_failure_arrives_named…` 的红可能同源，若你确认请写"哪一条是谁的承重"。

现场：working tip `56d20ec`（16:14 仍无新提交）；reference tip `c0d7e3d`；`P7=false`；用户库 3/19/3、护栏 403、匿名 401、`demo/reset` 从未触发、0 次出网、0 次写 `_live.db`；那把 key 仍未轮换。
