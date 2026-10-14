# 从文本导入地点（ORD-0437 切片 2）：移植接法、它必须改的那一处、以及故意没接的三条腿（2026-10-14 23:52）

这份文件只写接缝与实测，不写功能介绍。所有行号是**当前工作树现读**（`git diff`/`grep -n`），源树侧行号来自移植源尖 `eeb8b8d2fd`。三枚逐字搬的文件我按 `diff -u` 的行数说话，不按印象说话。

## 1. 两边到底有什么（先把「搬了什么、搬了几行」钉准）

| 件 | 移植源 `eeb8b8d2fd` | 融合基线 `594f9a4e75` | 本片落地后 |
|---|---|---|---|
| 后端解析模块 | `backend/app/poi_import.py` | **无此文件** | **有**，244 行，纯函数（`detect_forms/extract/resolve/counts/link_hosts`），不碰 session |
| 两扇门 | parse + add | 无 | `main.py:27713` `POST /api/v1/journeys/{id}/poi-import/parse`、`main.py:27790` `.../poi-import/add`；模块函数在 `main.py:27697` 起以 `poi_import_*` 别名引入 |
| 契约模型 | 6 枚 | 无 | `schemas.py:1689/1694/1708/1718/1726/1735`（`PoiImportParseRequest/Item/ParseResponse/AddRequest/AddedActivity/AddResponse`） |
| 面板 | `features/poiimport/PoiImportPanel.tsx` 836 行 + `poiImportCopy.ts` + `poi-import.css` + `components/PoiCandidateCard.tsx` | 全 **0** | 四枚齐全；**`poiImportCopy.ts`、`PoiCandidateCard.tsx`、`poi-import.css` 与源树 `diff` 输出 0 行**（逐字相同），面板只有 §3 那一处改动 |
| 注册表 | 有 `poi-import` 条目 | 无 | `v8PanelRegistry.tsx:187`（条目）/`:197`（渲染），`when: s => s.route === "import"` |
| 路由表 | `import` 在 `desktopRoutes` | 无 | `v8Routes.ts:10`，`nav.import` 词典两语各一行 |
| 全局词典 | 13 枚 `poiImport.*` 键 | 0 | **9 枚**（见 §4） |
| 守门测试 | 源树自己的 e2e | 无 | `backend/tests/test_qoder_ord0437_poi_import.py`（9 条）+ `frontend/e2e/qoder-ord0537-poi-import-arm.spec.ts`（1 条活口） |

## 2. 后端这一侧几乎没有接缝——因为它只写一行 Activity

`add` 门（`main.py:27790`）落笔的就是 `Activity`：`{day}T09:00:00` 起、+75 分钟、`metadata_json = {"source":"poi_import","source_channel":"LOCAL_TEXT_PARSER"}`（`main.py:27894`），随后 `record_audit(action="poi_import.add")`（`:27916`）与 `refresh_offline_snapshot`。**没有建表腿**——这条分支的建表只认 `backend/db/schema.sql`，本片没动它，所以没有「ORM 类不长表」那个坑。

两处口径要记下来，因为它们决定了测试怎么写：

- **没有 `Idempotency-Key`，是设计而不是漏。** 同一天重复贴同一个地点走 `already_present`，应答体里带回来，所以幂等性由「按天去重」提供。
- **拒绝是有名字的**：`JOURNEY_NOT_FOUND` 404 / `NO_ACTIVE_PLAN` 409 / `IMPORT_DAY_REQUIRED` 422 / `IMPORT_PLACE_UNKNOWN` 422 / `IMPORT_PLACE_NOT_VISITABLE` 422，`day_source` 只有 `TRAVELLER_CHOSEN|JOURNEY_FIRST_DAY` 两个值。前端 `namedCodeIn` 就是照这张表分类的。

## 3. 唯一一处非改不可：`travelerId` 这条 prop 在这棵树上没有门可用

源树 `PoiImportPanel.tsx:175-186` 收 `travelerId`，注释写的是「读门要 `traveler_id`，所以没有身份时宁可说一句也不发一次注定被拒的调用」。**这枚分支的同一扇门结构性地不接受它**——`GET /api/v1/collections` 见到 `traveler_id` 答 422 `COLLECTION_TRAVELER_SCOPE_PARAM_NOT_ACCEPTED`（切片 1 实测并写进契约），作用域从签名凭据里解。

改法与它连带删掉的东西（这就是面板 diff 的全部内容）：

1. props 里删 `travelerId`（**删而不是留着不用**：一扇门用不上的 prop 是屏幕对一个它到不了的状态许的诺）；
2. `readCollections(travelerId)` → `readCollections()`，两处（`:229` 的 useEffect、`:339` 收藏后的重读），useEffect 依赖数组同步去掉 `travelerId`；
3. 连带删掉 `poi-import-shelf-no-traveler` 那枚空态分支（源树 `:733-736`）——它的触发条件（没人可问）在这棵树上不存在，留着就是一句永远说不出口的话。

面板的 `copyFor / readCollections / addPlaceToCollection / shelvesHolding / refusalCopy` 全部来自切片 1 落地的 `features/collections/collections.ts`（面板 `:10-17`），所以「已收在」这句话在融合树上仍然只有一处说法，本片没有为批量收藏另开第三套句子或第三个写口。

注册表那枚条目因此只传 `journeyId / firstDay / onOpenPlan / onOpenDiscover`。`firstDay` 从 `s.data.active_plan.activities` 的 `start_at` 现取，不另开读门。

## 4. 词典只搬 9 枚，因为源树自己那 4 枚没有读者

`PoiCandidateCard` 用全局 `t()` 读 9 枚 `poiImport.card*`（`Matched/Ambiguous/Unresolved/AmbiguousWhy/UnresolvedWhy/Phrase/Index/Select/Deselect`），两语各 9 行，逐字搬。实测两树的键集差：源树 13 − 融合 9 = `favoriteNotWired`、`newJourney`、`newJourneyNotWired`、`readBackError`，而这 4 枚在**源树里 `grep "poiImport.<key>"` 命中 0**（除词典自身）——搬过来就是四行死码。

这条是补漏，不是顺手：`poiImportCopy.ts`（面板私有词表，逐字相同）里那 400 多行句子不会替这 9 枚键说话，而 `type Dict = Record<string, string>` 加 `t()` 的「读不到就画原始键」兜底，让缺键**对 tsc 完全隐形**。所以补了一道词典闭包检查（§6 的 `DICT_CLOSURE_MISSING_KEY_COUNT`），它的 `PRESENT_KEYS` 第一版是 0——正则漏了 `re.M`，差点用「全部缺失」这个假数字去证明一件本来成立的事。

`lib/rejectionFacts.ts` 保持融合树版本，没跟源树对齐：源树多出的 `refusalReasonCode`/`refusalDetails` 的读者是 `abort/poster/shared/trash` 四片（实测 grep），本片面板走的是 `lib/rawFacts.ts` 的 `namedCodeIn`——那枚文件两树 `diff` 0 行。

依赖闭包闸现在会打一行 `MISSING_EXPORT_COUNT 1`，内容是 `dictionaryText`（`<- wanted by lib/errorReceipt.ts`）。**这不是本树的破口**，别当红读：要它的是**源树**那枚 `errorReceipt.ts`（其 `:20` 才 `import { dictionaryText }`），融合树的同名文件从头到尾没有任何 import（实测 `head -20` 只有注释与 `export const`），而融合词典根本不导出 `dictionaryText`。它记的是「源树那枚文件不能整枚盖过来」，切片 3/4 真要搬 `abort` 那一片时会用得上。当前树的三枚 tsc 闸各 0 错误行，与这行不矛盾。

一处**我已经改掉的脱敏点**：面板原 `:24` 的注释引的是本机一份分析笔记的绝对路径（`D:/moodle/_apk_analysis_pi_travel/MAP/map_findings.md`）。源树原文如此，我第一版按「逐字搬」处理没动它，并把它列成「留给主人定」——这个判断是错的：那是**我这侧的工作文件**，不是产品的引用，写进产品源码就等于让 canonical 依赖一个别人打不开、且会随本机目录腐烂的路径。落地时已改为「shapes come from the F24 reference chain as written up for ORD-0437；笔记不在本仓库」，只动注释、不动任何行为。同批复相同类问题的还有 `main.py` 与 `schemas.py` 里三行「taken verbatim from the transplant source app/… lines NNNN」——行号是**另一棵树的坐标**，写进本树必然过期，且其中两行经核实**并不成立**（端点块被本刀改过），所以：`schemas.py` 那六枚类改成「逐字节相同，且用逐类 diff 复核过」（这句是真测的），`main.py` 那两行删掉，只留 ORD 标记。

## 5. 故意没接的三条腿（别把这三条当成我看漏）
1. **`onOpenPreparePlaces`**（源树 `v8PanelRegistry.tsx:195`，`DestinationPreparationPanel` 的「去导入」按钮，ORD-0566 那条腿）。融合树 `grep onOpenPreparePlaces` 命中 0，因为它的 `DestinationPreparationPanel` 没有这个 prop——接它要先改那一片面板，属于另一刀。
2. **`onImportPlaces`**（源树 `V8Experience.tsx:2214`，`PlanWithAiSheet` 里的「导入地点」入口，ORD-0504）。同理，融合树 `grep` 命中 0，且这要动 494 行以外的 `V8Experience.tsx`，切片 1 立的规矩是不碰它。
3. **390×844 底栏里没有这一格**：`import` 只在 `desktopRoutes`（源树同样如此，`v8Routes.ts:10`），底栏渲染的是 5 枚 `mobileRoutes`（`V8Experience.tsx:2188`）。所以走查第 8 屏是**URL 直达**的一屏，不是窄屏点得到的入口——`reports/qoder-ord0510-walk/08_import.png` 里能看到底栏五格与「从文本导入地点」「本地解析，不打开链接」都上了玻璃。这两句读的是**面板私有词表**（`poiImportCopy.ts:390`、`:174`；实测 `grep 从文本导入地点 frontend/src/i18n/LocaleContext.tsx` 为空），所以这一屏证明的是切片 2 的句子在 390 宽能落地，**不**证明那 9 枚 `poiImport.card*` 全局键（它们只在候选卡上出现），也不证明窄屏导航有这一格。候选卡上的词典句由活口那条腿证明——**本轮实测到 7 枚**：`已对上 / 这里没有 / 这座城市的地点里没有能对上这一行的… / 你写的是：Five Great Avenues / 第 1 行 / 选中 / ✓已选中——点一下取消`（逐枚从玻璃上 `innerText()` 取回，落在 `reports/qoder-ord0537/import_arm.json` 的 `card_words`）。剩下两枚（`要你选` 与其 reason）要「两枚自家地点被同一行对上」才出现，本城布景的 9 行给不出这个形状，所以它们**只在门上证明**（`test_two_matches_become_the_travelers_choice_not_a_guess`）——写「九枚键都上了玻璃」是过头的。

⇒ 一句话口径：**这扇门在融合树上只有「抽屉/URL」这一条来路**，说「导入已接通」时必须带上这句。

## 6. 活口测试：一条命令、以及它必须先解决的那个未知量

跑法（每轮换 runId/库/端口，`env -u` 是必须的）：

```
D:/moodle/_qoder_fusion_import/_run_e2e_slice2_r1.sh <RUN_ID> [GREP] [REPEAT]
```

它起的是权威栈（`CITYNEXUS_E2E_AUTHORITATIVE=1`，后端 8113 / 前端 4413 / `_e2e_<RUN_ID>.db`），`-g 'qoder-ord0510|qoder-ord0537'` ⇒ 布景 setup + 切片 1 四腿 + 走查 + 本片一条。**存档那趟是 `slice2r5`：7 passed / 28.1s**；同支上 `slice2r2` 7 passed / 32.1s、`slice2r3` 7 passed / 28.3s 是两趟独立新库，两趟的红面也留在名单里（`slice2r1` 2 failed / 5 passed、`slice2r4` 1 failed / 6 passed，见 §7）。本片的数值以 `slice2r5` 写进仓库的那枚文件为准（`reports/qoder-ord0537/import_arm.json`，1024 字节，UTF-8）。

**回归判定不数总数，只数红名集合**：`_slice2_failed_nameset_r1.py` 比对本尖切片 1 时那趟全树日志（`156 failed`）与本片落地后这趟（`154 failed`）——**`RED_ONLY_IN_SLICE2 0`**，另有 2 枚由红转绿（`test_r87_…` 与 `test_qoder_g3_xproc_http.py::…`）。那两枚不算我的功劳：r87 已定位为按位置解包的时序 flake，g3 单跑仍红（`URLError`，它要真起两枚 uvicorn worker），所以它们在整套里变绿是环境时序。脚本对两份日志都做了自检（解析出的红名数必须等于汇总行自己写的数，不等就退出并喊「reader is broken」）。

**这一片最关键的未知量是「种子城里有没有对得上的地点」，而它是读出来的、不是推出来的。** 我第一版按源树思路用 `GET /api/v1/places` 取候选名，直接开库看：e2e 种子城 `CN-TIANJIN` 有 9 枚 `Place`，**provider 全是 `citynexus-v9-domain`**，而 `/api/v1/places` 带着 `Place.provider_key.notin_(_SERVER_OWNED_PLACE_PROVIDERS)`（`main.py:16206`，元组定义在 `:17901`）——那扇门对这座城返回 **0 行**。parse 门故意不带这个过滤（`main.py:27749` 只排 `_STRUCTURAL_PLACE_CATEGORIES`，`:16184`）。⇒ 布景词汇改成从**行程投影**取可访问地点，且每个名字先 POST 一次 parse 自证 `RESOLVED && place_id` 对得上，对不上就带着探针结果喊红；写死名字会在换种子后静默空转。

数值（`reports/qoder-ord0537/import_arm.json`，`slice2r5` 那趟）：`plan_rows_before 9 → after_add 10`，新行 `aba6af54-e783-4176-b3fe-63928a310e22`，`start_at 2026-10-09T09:00:00+08:00`，`junk_rows 0`（那句故意对不上的行没被写进去）；重放到 `2026-10-10` ⇒ `already_present`、`plan_rows` 仍 10、屏幕上不出现第二句成功；架子 `导入架子` `item_count 1` 且**凭据作用域的重读**里含该地点（`holds_target true`）；`store-only` 那格按「absence」量（`poi-import-add`/`poi-import-collect` 计数 0）；`去城市探索` 落在 `/v8/discover`；`stamps_after_import 3`（导入这一路没造足迹）。`resolve_probe` 只有 `Five Great Avenues=RESOLVED` 一枚——名字是探针问出来的，不是写死的。另有一格 `card_words`：活口把候选卡上玻璃的 **7 枚**词典句逐枚 `innerText()` 取回（`已对上 / 这里没有 / 这座城市的…不能添加。 / 你写的是：Five Great Avenues / 第 1 行 / 选中 / ✓已选中——点一下取消`），`要你选` 与其 reason 这 2 枚要「两枚自家地点被同一行对上」才出现，本城布景 9 行给不出这个形状，所以它们**只在门上证明**——谁把这条写成「9 枚键都上了玻璃」就是超出证据。

## 7. 这一轮红过七次，全红在我这边（写给下一片）

1. **`LINK_ONLY` 反例选错。** 我贴的是「看这篇 <url>」，源树解析器 `_segments` 在剥掉 URL 之后仍把「看这篇」留下 ⇒ 那是一枚合法的 `UNRESOLVED` 行，空态永远不出现。改成**裸 URL**，理由写进了 spec 头部注释。
2. **arm B 的 tally 竞态（切片 1 那条腿，被这一片撞出来）。** 面板在重读进行中会先把列表清空，`toContainText("2 枚足迹")` 被**上一次渲染**满足，下一句 `innerText()` 抓到的是清空那一帧（`2 枚` → `0 枚`）。先在**同一枚尖**上单独复跑 6 次（`armb6r1`：6 passed）排掉「顺序依赖／切片 2 污染」，再把两处都改成钉在 `footprint-row` 的行数上——有边界的等待，而不是自我比较。

3. **证据的读法本身会撒谎，而且这已经是我第二次栽在 `re.M` 上。** `_slice2_landed_r1.py` 取 Playwright 汇总的方式是「最后一行含 passed 的」，而 line reporter 把 `2 failed` 和 `5 passed (49.1s)` 写在**两行**、中间夹每枚失败测试的名字 ⇒ 一趟两红的运行被打印成 `5 passed`。名字集比对脚本的第一版则漏了 `re.M`，`^FAILED` 一条没抓到，两个空集合一比得出「零回归」。现在的规矩：汇总取末 60 行里**所有**计数行拼接；比对脚本自带自检（解析数 ≠ 汇总行自己写的数就退出并喊 reader is broken）。反向对照用 6 枚历史日志量过：`slice2r1`、`uiport_r9`、`walk_r8` 三枚红的现在都喊得出 `failed`。

顺带一条：**控制台不是中文的档案**。`导入架子` 经 Playwright 的 stdout 落进日志成了 `?????`，我这枚脚本自己 print 时犯同一件事（Windows 重定向走控制台码页）。所以本片的数值只认仓库里那枚 UTF-8 JSON，脚本现在把 stdout 钉在 utf-8。

4. **新断言第一次就跑红，红在我对按钮文字的预期上**（`slice2r4`：1 failed / 6 passed）。按下态的按钮里还有一枚 `aria-hidden` 的 ✓ 字形，`toHaveText("已选中——点一下取消")` 拿到的是 `"✓已选中——点一下取消"` ⇒ 精确比失败。抬起态没有字形，所以那一枚仍按精确比，按下态改 `toContainText`。**这条不是产品的错，也不是闸坏了**——它恰好证明这条断言在盯真东西：改错一个字，它会喊。
5. **我把「九枚键都上了玻璃」写进了一条提交说明，实测只有七枚**（另两枚要两枚自家地点被同一行对上才出现）。历史不改写（`--amend` 不在许可里），改成两步补：下一枚提交的**第一句**就是这条更正，并把七枚句子写进 `card_words`，让数目变成从玻璃上读回来的而不是我说的；同时在证据脚本里钉成 `ARM_FILE_CARD_KEYS_PROVEN_ON_GLASS 7` / `ARM_FILE_CARD_KEYS_DOOR_ONLY 2`，让下一片不能顺手把它读成 9。

6. **`rc=0` 的空读数会伪装成「远端没动」**。新加的 `ls-remote` 腿第一版写成 `git ls-remote origin refs/heads/fusion`，返回 `RC 0` 加 **0 行**——远端明明有三枚 fusion 尖，我的参数写法让它们集体消失，而脚本会照着打印「没推」并且**看起来像现读**。现在拉全表再本地筛 `/fusion/`，并把 0 行当错误退出（`REMOTE_TIPS_READER ZERO LINES`，退出码 1）。反向对照：故意把子串写成 `/fusion_zzz/` ⇒ 打印 0 行且 RC=1；改回之后脚本 sha1 与改前逐字节相同。同一课在上一条第 2 项已经交过一次学费（空集合比出「零回归」），我又交了一遍：**空结果不是绿，是没测。**
7. **一枚样本被我当成了判决**。切片 2 第一次整套跑出来 `RED_ONLY_IN_SLICE2 0`，我就把它写成了「没有新失败」；把**同一枚尖**再跑一趟，红名集合动了 2 枚（r44 红→绿、g3 绿→红），那个 0 和后来的 1 都不过是时序。r44 那枚数的是固定演示行程 `22222222-…` 上的 `AgentRun` 行数（实错 `assert 2 == 1`），而这枚 id 被好几份文件写死共用（`test_wp01_wp03.py`、`test_qoder_ord0219_*`、`v191/v192_harness.py`），单跑两棵树都 3 passed。规矩改成：**回归结论最少两趟样本**，只认在两趟里都稳定的差集名字（量具新增 `SAME_TIP_SAMPLES_FLIPPED` / `RED_ONLY_IN_SLICE2_STABLE_IN_BOTH_SAMPLES`，读 `_pytest_import_slice2_full.log` 与 `_pytest_import_slice2_full_r2.log`）。

## 8. 一条事故：我的工具自己把树弄坏过一次

`_slice2_dict_port_r1.py` 用 `read_text()/write_text()` 写文件，Windows 上把 5 枚文件整枚翻成 CRLF，`LocaleContext.tsx` 因此显示 **3921 行改动**（真实改动是 18 行）。修回 LF 之后，我在证据命令里加了 `CRLF_DRIFT_FILES` 闸，并**故意把 `v8Routes.ts` 翻坏一次**证明它会红（打印 `CRLF_DRIFT_FILES 1` 并点名），再修好。现在 `CRLF_DRIFT_FILES 0`，`PRODUCT_CODE_DIFF_VS_BASELINE = 27 files changed, 8086 insertions(+), 32 deletions(-)`。

**同一节里我先前写的 `21 files changed, 6137 insertions(+), 77 deletions(-)` 是错的，错在两处**：一，那是提交之前取的，`git diff` 不看未跟踪文件，切片 2 的 6 枚新文件（`poi_import.py`、它的测试、`PoiCandidateCard.tsx`、`features/poiimport/` 三枚）一枚都没算进去；二，`−77` 早就被当轮重印改成了 `−32`，我却把旧数留在散文里没跟着改。规矩：**「diff 面」的数只在提交之后取**，且任何被引用过的数如果重印结果不同，必须在同一轮里把旧数改掉，不能让两个数并存。

## 9. 复跑全部数字

```
D:/moodle/CityNexus/.venv/Scripts/python.exe \
  D:/moodle/_qoder_613907d0_demo1014/parity/_slice2_landed_r1.py [--full]
```

`--full` 是多出来的全树 pytest 腿（约 6 分钟），**这一片之后它不再是读名字差的必经之路**：名字差那一腿现在只**读**归档的两趟整套日志（`_pytest_import_slice2_full.log` 样本一、`_pytest_import_slice2_full_r2.log` 样本二），快腿每次都打印，所以信里引的 155/2065/367.76s 与两趟翻面的那两枚名字，不必再等一条长腿就能复现；`--full` 只在你需要**重跑**样本一时才加（它会覆写样本一那枚文件）。总数在不同根之间不可比，这条规矩见 `SLICE1_UI_PORT_SEAM.md`。信与 `QODER_RESULT.md` 里出现的每个数，都必须能在这条命令的输出里再打一次。

一条提交纪律：权威栈每次运行都会改写 `reports/e2e-provenance/authoritative.json`（记的是**最后一次碰树的那一轮**的端口与库路径），而 HEAD 里那枚是别人那条 canonical 闸口的记录（`cbe5c3dfc7`）。所以本尖**每一枚提交都没碰过它**（`git rev-list --count 594f9a4e75..HEAD -- reports/e2e-provenance/authoritative.json` = **0**），切片 2 也不提交它——工作树里它显示为 `M` 是预期的，不是待办。要留档的是 `reports/qoder-ord0510/*.json`、`reports/qoder-ord0537/import_arm.json` 与走查那 8 枚 PNG。
