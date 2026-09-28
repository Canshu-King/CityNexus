# ORD-0407 ledger anchors, generated (run `cmdr213805n3`)

## receipts

- `C1` `unlocatable_journey.journey_id` -> review/n3_0407_evidence_r1/cmdr213805n3__C1.json:3281
- `C1` `unlocatable_journey.server_says.city_code` -> review/n3_0407_evidence_r1/cmdr213805n3__C1.json:3283
- `C2` `per_locale.zh-CN.今天.text` -> review/n3_0407_evidence_r1/cmdr213805n3__C2.json:8
- `C2` `per_locale.en.今天.text` -> review/n3_0407_evidence_r1/cmdr213805n3__C2.json:49
- `C3` `denominators.contract_paths_seen_by_this_cell` -> NOT_FOUND denominators.contract_paths_seen_by_this_cell in cmdr213805n3__C3.json
- `C3` `contract_paths_seen_by_this_cell` -> review/n3_0407_evidence_r1/cmdr213805n3__C3.json:5
- `C3` `location_door_http_status` -> review/n3_0407_evidence_r1/cmdr213805n3__C3.json:15
- `C3` `location_row_returned` -> review/n3_0407_evidence_r1/cmdr213805n3__C3.json:29
- `C3` `experience_inputs_unchanged` -> review/n3_0407_evidence_r1/cmdr213805n3__C3.json:28
- `C3` `cell_text_unchanged_after_sharing_location` -> review/n3_0407_evidence_r1/cmdr213805n3__C3.json:31
- `C4` `zh-CN.label` -> review/n3_0407_evidence_r1/cmdr213805n3__C4.json:6
- `C4` `zh-CN.centre` -> review/n3_0407_evidence_r1/cmdr213805n3__C4.json:13
- `C4` `zh-CN.box` -> review/n3_0407_evidence_r1/cmdr213805n3__C4.json:7
- `C4` `en.label` -> review/n3_0407_evidence_r1/cmdr213805n3__C4.json:22
- `C5` `controls` -> review/n3_0407_evidence_r1/cmdr213805n3__C5.json:12
- `C5` `live_controls_above_floor` -> review/n3_0407_evidence_r1/cmdr213805n3__C5.json:16
- `C6` `screens` -> review/n3_0407_evidence_r1/cmdr213805n3__C6.json:7
- `C7` `by_width` -> review/n3_0407_evidence_r1/cmdr213805n3__C7.json:11

## write-door inventory (review/n3_0407_evidence_r1/write_doors_head.json)

- `contract_paths=141` -> write_doors_head.json:5
- `contract_operations=153` -> write_doors_head.json:6
- `contract_write_operations=86` -> write_doors_head.json:7
- `frontend_write_call_sites=62` -> write_doors_head.json:8
- `frontend_write_call_sites_matched_to_a_contract_operation=7` -> write_doors_head.json:9
- `contract_write_paths_containing_activities=5` -> write_doors_head.json:10
- `contract_write_paths_addressing_the_activity_collection=0` -> write_doors_head.json:11
- `contract_write_paths_naming_a_place_or_coordinate_field=2` -> write_doors_head.json:12
- `backend_activity_row_insert_points=6` -> write_doors_head.json:13
- `backend_activity_class_declarations_matched_by_the_same_pattern=2` -> write_doors_head.json:14

## paired-copy check (review/n3_0407_evidence_r1/n3_0407_copy_pair_r1.json)

- `dictionary_pairs=630` -> n3_0407_copy_pair_r1.json:6
- `distinct_keys=520` -> n3_0407_copy_pair_r1.json:7
- `values_checked=630` -> n3_0407_copy_pair_r1.json:8
- `values_not_found=0` -> n3_0407_copy_pair_r1.json:11

## source lines (re-measured by needle, never hand-typed)

- `frontend/src/i18n/mapPanelCopy.ts:67` <- needle `noLocationBody: { zh: "这个行程还没有可信的坐标`
- `frontend/src/components/v8/MapPanel.tsx:501` <- needle `data-cnx-activity-entry`
- `frontend/src/components/v8/MapPanel.tsx:38` <- needle `export function tripHasNoCoordinates`
- `frontend/src/components/v8/MapPanel.tsx:20` <- needle `export function activityCoordinate`
- `frontend/src/components/v8/MapPanel.tsx:134` <- needle `const points = useMemo`
- `frontend/src/app/V8Experience.tsx:4039` <- needle `data-testid="bookings-no-stay-action"`
- `frontend/src/app/V8Experience.tsx:1325` <- needle `const shareForegroundLocation`
- `frontend/src/i18n/LocaleContext.tsx:284` <- needle `"bookings.noStayAction": "Open Stay Explorer`
- `frontend/src/i18n/LocaleContext.tsx:1081` <- needle `"bookings.noStayAction": "到「住宿选择」`
- `frontend/src/i18n/LocaleContext.tsx:11` <- needle `"nav.stay": "Stay Explorer"`
- `frontend/src/i18n/LocaleContext.tsx:838` <- needle `"nav.stay": "住宿选择"`
- `frontend/src/features/execution/LiveRecovery.tsx:423` <- needle `ORD-0407 ③`
- `contracts/openapi.yaml:827` <- needle `/journeys/{journey_id}/activities/{activity_id}/`
- `contracts/openapi.yaml:1194` <- needle `/journeys/{journey_id}/activities/{activity_id}/`
- `contracts/openapi.yaml:1205` <- needle `/journeys/{journey_id}/activities/{activity_id}/`
- `contracts/openapi.yaml:1216` <- needle `/journeys/{journey_id}/activities/{activity_id}/`
- `contracts/openapi.yaml:1285` <- needle `/journeys/{journey_id}/activities/{activity_id}/`
- `backend/app/main.py:4534` <- needle `@app.post("/api/v1/journeys/{journey_id}/locatio`
- `frontend/e2e/qoder-ord0407-empty-state-actions.spec.ts:261` <- needle `test("C2 `
- `frontend/e2e/qoder-ord0407-empty-state-actions.spec.ts:402` <- needle `test("C4 `
- `frontend/e2e/qoder-ord0407-empty-state-actions.spec.ts:502` <- needle `test("C6 `

## instruments and product lines

- review/n3_0407_write_door_inventory_r1.py
- review/n3_0407_baseline_r1.py
- review/n3_0407_mutations_r1.py
- review/n3_0407_copy_pair_check_r1.py
- review/n3_0407_evidence_r1/write_doors_head.json
- review/n3_0407_evidence_r1/controls_before_890b7cfc.json
- review/n3_0407_evidence_r1/mutations_r2.json
- review/n3_0407_evidence_r1/n3_0407_copy_pair_r1.json
