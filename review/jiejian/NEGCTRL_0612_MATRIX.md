# ORD-0612 负对照矩阵读数（一次跑批的原始判定，逐枚照抄）

- 权威尖 `2899f86fb08cd85602b713c9d5597ddfd7cb0871`（跑这一拍 ls-remote 现取）
- 被测模块 `backend/app/execution/shared_walk.py`，blob 逐字节取自代表枝 `a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9`
- 对照测试 `backend/tests/test_jiejian_0612_shared_walk_contract_r1.py`，17 枚用例
- 解释器 CPython 3.12.14 + pytest（`-X utf8 -p no:cacheprovider`）；整棵尖导出后只加这两枚文件，未起服务、未开库
- 跑法：每次只改坏模块里的一条规则 → 从磁盘重读确认改动确实落盘 → 清 `__pycache__` → 只跑认领那条规则的用例 → 恢复原文。改动没落盘就记 `PATCH-NOT-PERSISTED` 而不是给判语（上一版矩阵就是这么骗过我的，见文末）。

| 改坏的那条规则 | 认领它的用例 | 判定 |
|---|---|---|
| 前导零只在 URL 路径那一门放宽 | `leading_zero_identity_is_refused_not_repaired` | GREEN-by-defence-in-depth（预期：身份构造器那第二门仍拒） |
| 前导零两门一起放宽 | 同上 | RED-as-expected |
| 超长/空文本闸门 | `empty_and_oversized_pastes_are_refused_without_scan` | RED-as-expected |
| 控制字符与尖括号闸门 | `control_characters_and_angle_brackets_are_refused` | RED-as-expected |
| 凭据关键词闸门 | `credential_shaped_text_is_refused_before_parsing` | RED-as-expected |
| token 形状串闸门 | `a_token_shaped_run_is_refused_even_without_a_keyword` | RED-as-expected |
| OSM kind 白名单 | `leading_zero_identity_is_refused_not_repaired` | RED-as-expected |
| host 白名单 | `non_https_and_delegated_hosts_are_refused` | RED-as-expected |
| 端口/凭据/query/fragment 闸门 | `port_credentials_query_and_fragment_cannot_ride_the_link` | RED-as-expected |
| 浏览器夹带换身份闸门 | `a_browser_relabelled_identity_is_refused` | RED-as-expected |
| 「恰好两枚」上界 | `three_links_are_not_a_walk_either` | RED-as-expected |
| 「恰好两枚」下界 | `one_link_is_not_a_walk` | RED-as-expected |
| 校验列表的数量闸门 | `the_validated_list_must_hold_exactly_two_objects` | RED-as-expected |
| 两枚不得相同 | `two_identical_objects_are_refused_as_not_a_walk` | RED-as-expected |
| 路径必须点出一个对象 | `a_non_object_name_in_an_otherwise_clean_url_is_refused` | RED-as-expected |
| 拒语不回显粘贴原文 | `a_refusal_never_reflects_the_pasted_text_back` | RED-as-expected |
| 句尾句号不算进 URL | `sentence_punctuation_after_a_link_is_not_part_of_the_url` | RED-as-expected |

合计：17 次判定 = 16 次「按预期变红」+ 1 次「纵深防御下预期仍绿」；`STILL-GREEN`（规则没被锁住）为 0。恢复原文后全量再跑：17 passed。

## 这轮矩阵自己先错过一次

第一版矩阵把 3 条规则报成「测试仍绿」。其中 **1 条是尺在说谎**：它写完 mutant 就去跑测试，却没验证字节有没有真落到磁盘，于是那条用例其实是对旧代码跑的。第二版给每一步装了自检（写后回读比对、清 `__pycache__`、并区分「没选中用例」与「仍绿」），剩下 **2 条才是我的测试真虚**：

- `leading_zero_identity_is_refused_not_repaired` 三句全走身份构造器，没测 URL 路径那一门 → 补了走 `normalize_osm_object_url` 与整串粘贴各一句
- `the_validated_list_must_hold_exactly_two_objects` 只测了「少一枚」，把 `!= 2` 改成 `< 2` 它照样通过 → 补了「多一枚也必须拒」

两条都是**把断言加严**修好的，没有改任何既有断言换绿。
