# ORD-0543 · 更正：先前那串「整套 34-36 红」是稀疏树缺 `frontend/` 造的假红

写这块的原因：我在 00:41 那块里报「三遍都红的稳定集合 = 34 枚」，并把「干净树 35 / 本枝 36」当成存量债与我的差。
那三趟都在一棵**没有检出 `frontend/`** 的稀疏工作树里跑（集合是 `backend contracts data tools scripts review`）。
账上大量臂（`test_the_generated_client_carries_*`、`test_contract_and_generated_client_*`、
`test_release_metadata_and_map_entrypoint_are_converged` 等）读的是
`frontend/src/generated/api.ts` 与前端源码；文件根本不在树上时它们必红，与产品无关。
我 09-30 就为同一族坑立过条（排除根目录会让门造出假红），这次是我自己又踩了一遍，而且是在**已经注意到
_CMDR 01:08 那块数是 10 红_**之后没有立刻把两边形制对齐——看见了不一致还继续往下报，是这格真正要改的习惯。

更正后的配对（两棵树都把 `frontend` 检出；命令取号令者那形制
`pytest tests/ -q --no-header -p no:cacheprovider --ignore=tests/test_v18_hermes_r20_transport_reliability_probe.py --tb=no -rf`，
并摘掉 `HTTP(S)_PROXY`、`NO_PROXY=*`）：

| 树 | 读数 |
| --- | --- |
| 干净尖 `5a4cdbd26d4a58d6ed6b277480e766ac08b15ded`（`wt543tip`） | `14 failed, 1650 passed, 16 skipped, 1 xfailed` |
| 本枝（`wt543d`，head 见交付 ref） | `12 failed, 1658 passed, 16 skipped, 1 xfailed` |

红名逐枚对：**只出现在本枝的红 = 0 枚**；只出现在干净尖的是 2 枚
（`test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation`、
`test_acceptance_answers_while_the_provider_is_still_being_asked`，都是跨模块状态敏感那一族的成员）。
两份清单全文在 `readouts/full_suite_clean_tip_5a4cdbd2.txt` 与
`readouts/full_suite_branch_withfrontend.txt`。

**哪些已发布读数受影响、判据变不变**：

- 受影响：00:41 那块里「34 / 35 / 36」这一组**分母**，以及从它们推出的「本枝多 1 枚红」这句话——
  形制对齐后本枝一枚不多。
- 不受影响（都不依赖前端检出）：门读数（`plans/generate` 201 / 3 枚候选、`select` 200、
  `calendar.ics` 200 与整正文 1669 B / 5 条 `BEGIN:VEVENT`、`share-grants` 201、
  逐站 `hours_basis` 1 : 4）、六枚臂、两枚反件（M1 四红点名、M2 恰一红）、三证归属、
  以及「干净树上 `day_sequences_available` 0 ⇒ 日历 409」这条根因。产品结论一字不改。
- 与号令者 01:08 的 `10 failed` 相比我现在这形制是 14：中间落了 ORD-0541/0545/0539，且我仍不是一棵
  整树导出（缺 `agent-mcp/` 等根目录），所以那 4 枚差我不解释、只把两份清单摊在这里，请他以自己那条
  基线为准做差。
- 顺带仍然成立的一枚：`test_qoder_city_failure_reasons.py::test_the_bounded_fallback_asks_with_the_same_label_as_the_anchor`
  在干净尖上红（我上一单报过、等裁语的那一枚），这次是**独立第二次读到**。
