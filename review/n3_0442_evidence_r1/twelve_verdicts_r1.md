# ORD-0442 十二枚具名红 - 逐枚归因（由 review/ord0442/twelve_verdicts_r1.py 从证据件重算，不是手抄）

- 尖：8d038b21f09477b933cff3b1c7b09845c542373b（派单点名）；本轮现读现尖 123fabb637fefe9e1be442b67f2da4be7e95ac74
- 具名导出配方（backend data contracts tools scripts agent-mcp frontend/src frontend/e2e）：12 枚全红，摘要 12 failed, 4 warnings in 16.96s
- 完整树导出（git archive 全量，尖 8d038b21f09477b933cff3b1c7b09845c542373b）：9 枚红 / 3 枚绿，摘要 9 failed, 3 passed, 4 warnings in 14.60s
- 现尖 123fabb637fefe9e1be442b67f2da4be7e95ac74 完整树复跑：9 枚红 / 3 枚绿，摘要 9 failed, 3 passed, 4 warnings in 17.52s
- 三把尺文件里的其余门：22 绿 / 4 红（红的全是本表点名的这几枚）
- 分类计数：{"真缺陷": 1, "仪器缺陷（令中未列这一类，具名报上游）": 2, "尺过期": 5, "ENVIRONMENT_NOT_PRODUCIBLE_ON_LINE": 4}

| 测试 | 具名配方 | 完整树(派单尖) | 现尖完整树 | 点名档 | 判据（实测） | 形状变更归属 |
| --- | --- | --- | --- | --- | --- | --- |
| test_g5_an_ai_run_that_changed_must_say_which_it_was | FAILED | FAILED | FAILED | 真缺陷 | run.outcome=None / run.status=SKIPPED_EXTERNAL_DEPENDENCY / failure_reason='AI is switched off by the operator' (http_status=200) | product: backend/app/agent/runtime.py:645-679 leaves the column null; contracts/openapi-anywhere-draft.yaml names 车道 A/C as the owner |
| test_g9b_provider_http_never_runs_inside_an_open_write_transaction | FAILED | FAILED | FAILED | 仪器缺陷（令中未列这一类，具名报上游） | seam off -> provider calls 0; seam on -> 2 calls, 7 write windows, door reports overlap; SQLite BEGIN IMMEDIATE during the same calls: locked=0/2, controls write=True read=False discriminator_holds=True | ruler: _overlaps() intersects wall-clock windows keyed by id(conn) across every connection, so an ORM transaction that only *later* writes is convicted |
| test_g14a_an_oversized_matrix_fails_closed_and_invents_no_facts | FAILED | FAILED | FAILED | 尺过期 | fixture premise N=11 sends one oversized request; measured cells [100, 1, 36, 36, 36, 36, 100, 1, 36, 36, 36, 36] (max 100, cap 100) -> status CAPTURED, any_oversized=False | product shape 6cb92983 2026-09-22 14:06 (chunked matrix) |
| test_g14c_the_verdict_must_not_depend_on_the_providers_wording | FAILED | FAILED | FAILED | 尺过期 | KeyError 'error_type' because both arms returned status CAPTURED / error_type present=False (keys ['captured_at', 'cost_provenance', 'facts', 'nodes', 'operation_key']...) | product shape 6cb92983 2026-09-22 14:06 (chunked matrix) |
| test_g8a_default_suite_contains_no_live_provider_calls | FAILED | FAILED | FAILED | 尺过期 | both flagged lines make socket connects=0 under a connect guard; mock transport answered status=200 | ruler predates the two mocked-host lines (file added c421d681 09-21 14:12; offenders fed18613 09-21 17:15 and 44e4ea78 09-22 01:12) |
| test_g10_every_normalised_place_carries_a_usable_coordinate_including_nodes | FAILED | FAILED | FAILED | ENVIRONMENT_NOT_PRODUCIBLE_ON_LINE | seam off -> egress 0 and reason_code NO_CANONICAL_IDENTITY; seam on -> photon answered, destination_resolution="provider_no_match", capability=UNAVAILABLE, places_len=0; a city the provider can name (云和县) resolves to OSM:R:3289208 with places_len=0; Beijing -> 8 places, status COMPLETED | opt-in leg: CITYNEXUS_ANYWHERE_RESOLVER defaults to off (app/anywhere_capability.py:223) |
| test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at | FAILED | FAILED | FAILED | 尺过期 | measured mapping 429->PROVIDER_RATE_LIMITED 500->PROVIDER_SERVER_ERROR 502->PROVIDER_SERVER_ERROR KeyError->PROVIDER_BAD_RESPONSE; 5xx differs from a malformed body=True | product shape 6cb92983 2026-09-22 14:06 added PROVIDER_SERVER_ERROR (assertion pinned at d4814644 09-21 14:46) |
| test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation | FAILED | FAILED | FAILED | 仪器缺陷（令中未列这一类，具名报上游） | child self-reports serving and urllib gets status=200 even with a dead proxy exported; the port refuses connects for 0.0-1.5 s (arm B first ok at 1.0 s); the door's _http catches HTTPError only, so its first poll raises | instrument: backend/tests/test_qoder_g3_xproc_http.py:83-90 (no URLError branch) vs :188-195 (readiness loop that assumes it can poll a not-yet-bound port) |
| test_G4_the_lock_wait_is_written_in_exactly_one_place | FAILED | FAILED | FAILED | 尺过期 | inline-copy offenders={} and literal-30000-with-busy_timeout=[]; the extra name is main.py whose only mention is PLAN_CLAIM_LEASE_MS = int(settings.write_deadline_ms) + int(settings.write_busy_timeout_ms) | product shape 5bb04b8f 2026-09-26 08:22 (ORD-0340 lease reads the same settings source) |
| test_C01_the_scanned_set_is_named_and_actually_present | FAILED | PASSED (counts 9+3=12) | PASSED (counts 9+3=12) | ENVIRONMENT_NOT_PRODUCIBLE_ON_LINE | named-recipe export -> FAILED (roots_missing ['qoder-handoff']); complete tree -> PASSED (counts 9+3=12) | export recipe drops the top-level qoder-handoff/ path |
| test_the_existing_list_door_was_not_touched_down_to_its_bytes | FAILED | PASSED (counts 9+3=12) | PASSED (counts 9+3=12) | ENVIRONMENT_NOT_PRODUCIBLE_ON_LINE | named-recipe export -> FAILED (baseline record missing); complete tree -> PASSED (counts 9+3=12) | export recipe drops review/ |
| test_release_metadata_and_map_entrypoint_are_converged | FAILED | PASSED (counts 9+3=12) | PASSED (counts 9+3=12) | ENVIRONMENT_NOT_PRODUCIBLE_ON_LINE | named-recipe export -> FAILED (PACKAGE-MANIFEST.json missing); complete tree -> PASSED (counts 9+3=12) | export recipe drops PACKAGE-MANIFEST.json |

## 下一步（每条一枚）
- test_g5_an_ai_run_that_changed_must_say_which_it_was：结构化 run.outcome 要同时改 4 条形（COMPLETED/PARTIAL/FAILED_EXTERNAL/SKIPPED）与 frontend/src/api/citynexus.ts 的 outcome: string | null 两处类型，属跨车道契约改动
- test_g9b_provider_http_never_runs_inside_an_open_write_transaction：g9a/g9c 在同一条 arm 下都绿（1 failed, 2 passed）⇒ 报上游：判据要落到锁视图或并发饥饿，不是事件簿记
- test_g14a_an_oversized_matrix_fails_closed_and_invents_no_facts：报上游：这条门要量「越界请求必须失败关闭」，今天产品已不再发出越界请求 (N=20 -> 20 片 / cells_max 100 / 760 facts)，需要一个能真造出越界片的形状才能判
- test_g14c_the_verdict_must_not_depend_on_the_providers_wording：报上游：与 g14a 同一根因，错误字段只在真失败时才存在
- test_g8a_default_suite_contains_no_live_provider_calls：报上游：同行文法判不出 MockTransport / 被 monkeypatch 的 transport，需要出网自证那一档
- test_g10_every_normalised_place_carries_a_usable_coordinate_including_nodes：报上游：这条门要 live provider 且要一个 provider 认得的目的地；默认套件按 §17C 不许出网
- test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at：报上游：产品现在把 5xx 与畸形 2xx 分开命名，正是这条门自己文件写的「六形五码」诉求；断言钉的是塌缩前的旧码
- test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation：报上游：门的就绪循环扛不过 1.0-1.5 s 的绑定窗口，硬约束不许我为跑绿改测试，故本轮不动
- test_G4_the_lock_wait_is_written_in_exactly_one_place：报上游：门的第一条断言（内联第二份拷贝）仍然绿，红的只是它抄死的模块名清单
- test_C01_the_scanned_set_is_named_and_actually_present：把 qoder-handoff/ 加进入档清单（本轮已证：完整树 3 枚转绿）
- test_the_existing_list_door_was_not_touched_down_to_its_bytes：把 review/ 加进入档清单
- test_release_metadata_and_map_entrypoint_are_converged：把 PACKAGE-MANIFEST.json 加进入档清单
