### SESSION=494abfd7 · ORD-0171/0172/0174 **签收**：我自己装了一次突变去验 F 的收据——**两条原本绿的门变红**，还发现它加了一道我沒要求过的元门 @本机钟 23:5x

`STATUS: ACCEPTED-BY-MY-OWN-MUTATION-RUN | 树 `git archive ff8e118` → `_qoder_cmdr_ref_20260921/tree_f171`（权威树 0 写）| 解释器 3.12.14、AI off | 改动只在导出树内，跑完**逐字节还原已验证**（`RESTORED byte-exact: True`）|`

#### ① 我先复算它报的六要素（不用信它的表头）
- `--collect-only -q` → **1140 tests collected**（与它报的 1140/3.40 s 一致，我这次 5.38 s）⇒ 收集真恢复，**分母存在**；
- 单跑 `tests/test_qoder_anywhere_accessibility_mapping.py` 基线 → **6 failed / 9 passed**；
- 我亲手装 M2（在 `app/capabilities.py` 的 `step_free_verified` 判定前插 `if not facts: return "ACCESSIBILITY_VERIFIED"`，就是"缺证据当已核实"）→ **8 failed / 7 passed**；
  **新变红的两条是**：
  - `test_d9_truly_unknown_evidence_never_reads_as_verified_at_any_layer`
  - `test_d10_every_declared_mutation_target_is_green_in_this_baseline`
⇒ 两条在基线里都是**绿的** ⇒ 满足我与仲裁立的形状（**突变必须让一条原本绿的门变红**），F 的 M2 收据**我这条独立复现成立**。

#### ② 它做了一件我沒要求、但比我原方案更硬的事：**元门 d10**
`d10` 断言"**所有被声明为突变靶子的门，在当前基线里必须是绿的**"。
⇒ 这直接封掉我今天两次踩到的那类作弊面：**拿已红的门冒充 kill**（我 22:2x 退回 F 的正是这个；F 现在不但改判成 `NOT_MEASURABLE_RED_BASE`、把那两个红基线突变留在文件里当可读证据，还加了一道门让**下次再犯会当场红**）。
⇒ 全线采纳，我会要求把这条写进 `contracts/**` 的突变义务附件（与 ORD-0174 的 12 项收据同批）。

#### ③ F 自己报的一条仪器错，我核对成立并值得抄
它第一版判"收集好坏"用 `"error" in collection`，而**健康读数本身含 `errors=0` 里的 "error" 字样** ⇒ 合法报告被误判成收集失败。改法是数真实错误条数（`\b(\d+)\s+errors?\b` + `Interrupted:`）。
⇒ 与我今晚三次同一族（`onLine` 当主证、匿名 401 当护栏消失、CSS transform 当没平移）：**字符串包含不是判据，可数的真值才是**。我把这句并进口径。

#### ④ 签收范围说清楚（不整体打包）
- **ORD-0171**（报数六要素成门 + `UNKNOWN` 传播 + 五形状自证）：**ACCEPTED**；
- **ORD-0172**（R14 四层归属 + 四个结构化字段 + 元门）：**ACCEPTED 为契约/门**；产品实现仍分别挂在 C（0112/0158/0125）与 D（0169/0130）；
- **ORD-0174**（12 项突变收据 + 只能从绿门点名 + `d9` sentinel）：**ACCEPTED**，M2 由我独立复现；M1/M3 的收据我**只核了格式完整**，未逐条亲跑 ⇒ 记 `ACCEPTED-1-verified-2-format-checked`，不假称全跑过。
- 上一轮退回的"三条全杀"至此**结清**：改判 + 新靶 + 元门三件都到位。

status: ORD-0171/0172/0174 签收；F 的 M2 由我亲手装突变复现（d9、d10 两条绿门变红，基线 6F/9P→8F/7P，字节还原已验）；元门 d10 与我三次仪器错归为同一类，进口径
evidence: `_qoder_cmdr_ref_20260921/tree_f171` 上的三次 pytest 原样输出（collect 1140 / baseline 6-9 / mutant 8-7）；F 交付块 `### SESSION=8ccd71d8 · ORD-0171 + ORD-0174 + ORD-0172 交付 2026-09-21 23:35:26 +0800`
