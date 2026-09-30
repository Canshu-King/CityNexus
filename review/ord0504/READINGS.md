# ORD-0504 readings, computed from the drivers' own JSON (every line carries its own number)

lane_backend_port=:8790 lane_patched_frontend_port=:8793 lane_base_frontend_port=:8794

## refusal screen, base generation (mutant A)
base_sheet_button_count=4 -> ["×", "换一座有数据的城市", "稍后", "开始规划"]
base_import_entry_present=0
base_catalogue_count_present=0
base_desktop_import_entry_present=0

## refusal screen, patched generation (the entry)
patched_import_entry_present=1
patched_catalogue_count_present=1
patched_count_sentence=服务器回读：这座城我们现在一个地点都还没有。
patched_entry_label=粘贴你自己的地点，导入这趟行程
patched_entry_classes=v8-outline-button plan-ai-import-entry
patched_visible_primary_buttons_page_wide=3
after_press_url=http://127.0.0.1:8793/v8/import
after_press_poi_import_panel_mounted=1
desktop_after_press_url=http://127.0.0.1:8793/v8/import
desktop_poi_import_panel_mounted=1

## the count follows the store, not the device
xiamen_door_before=0
xiamen_sentence_before=服务器回读：这座城我们现在一个地点都还没有。
discover_limit_1_status=200 candidates=1 provenance=LIVE_PROVIDER
xiamen_door_after=1
xiamen_sentence_after=服务器回读：这座城我们现在有 1 个地点，可以排进行程。
sentence_equals_door_count=true
fuzhou_door_count=0

## zero-row paste (mutant B) and the unreadable door
paste_counts_sentence=读出 1 行 · 对上 0 个 · 0 个要你选 · 1 个没找到
paste_cards=1 add_button=1
paste_sentence_after_zero_rows=服务器回读：这座城我们现在一个地点都还没有。
unreadable_line_present_when_run_stops_early=0
unreadable_shape_claims_no_count=true next_step=照原话再试一次

## no identifiers painted
A_base_phone_uuid_matches=0 place_key_matches=0 internal_code_matches=0
B_patched_refusal_phone_uuid_matches=0 place_key_matches=0 internal_code_matches=0
A_base_desktop_uuid_matches=0 place_key_matches=0 internal_code_matches=0
B_patched_refusal_desktop_uuid_matches=0 place_key_matches=0 internal_code_matches=0
r1_verdict_D_no_identifier_painted=true

## earlier supply attempts that failed, kept (r2 first pass)
r2_attempt city=CN-GUANGZHOU query=museum status=200 candidates=0 rows_after=0 anchor_source=None
r2_attempt city=CN-GUANGZHOU query=cafe status=200 candidates=8 rows_after=8 anchor_source=nominatim_city_anchor
r2_first_pass_cities_burst_count=2 chosen_after_pacing=CN-GUANGZHOU
r2_first_pass_rows_total=0 provenance_was_live_provider=1

evidence_files=31
