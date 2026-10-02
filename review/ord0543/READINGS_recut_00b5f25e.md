# ORD-0543 追尖件（recut on `00b5f25e…`）· 日序腿加宽 · 车道 `5a53846b`

这块只说一件事：**产品字节一枚没动，基座从 `5a4cdbd2…` 搬到 `00b5f25e…`，在新代把臂、反件、门读数重跑了一遍**。旧件（`READINGS.md`、`mutants_M1_M2.json`、`door__r3543.json` 等）一字未改，本件是新增。

## 〇、坐标（现读）

| 项 | 值 |
| --- | --- |
| 基座 | `00b5f25e9b6b408fba8906ef3ffd49caa5eb84b9`（`git ls-remote --refs origin refs/heads/mirror/integration-frontend-apple-pass1` 回读同值；命令里逐字带 `NO_PROXY="*"` 形制，避开注册表代理把 Authorization 弄坏那一格） |
| 枝 | `refs/heads/review/newlane-ord0543-day-sequence-leg-r1`（号令者 23:16 那块写的是"把真活推上同一枝名即可"，所以沿用同名；同名重推对本枝是一次非快进更新，用的是 `--force-with-lease=<枝>:<旧 head>`，旧 head `9bc7c724806f25cf38f2e3e94e5361de6f4cc975` 对象仍在库里、账本 17353 行那处引用仍可 `git cat-file -t`） |
| 交付 head（新代） | 见账块，推完从服务器侧回读，不写本地记忆 |
| 五笔链 | `a0cb0e3d`（产品+臂）→ `c3dddb1c` → `9976716a` → `3e1cd03e` → `f75c1801`，全部线性坐在 `00b5f25e…` 上；对应旧代 `370025c2` → `a0a7a993` → `c314dde9` → `3367787e` → `9bc7c724` |
| **产品 blob 跨代逐枚不变** | `backend/app/services.py` = `564bb4a9cfb6e04f114f04d926bfaf0a5ccef895`；`backend/tests/test_ord0543_day_sequence_leg_r1.py` = `bb7d166b9f4fabe848340e4a04be6b1a0921ea96`（`git rev-parse <代>:<路径>` 两侧同值 ⇒ 这一跳是搬基座，不是重做） |
| 上游这 9 笔动了什么 | `git diff --name-only 5a4cdbd2… 00b5f25e…` 里 `backend/app/services.py` 与 `backend/tests/test_ord0543_day_sequence_leg_r1.py` **都不在列**（动的是 `main.py`、`schemas.py` 与 ORD-0531/0512 那族） |
| 树 / 解释器 | `D:/moodle/_qoder_seed_ord0489/wt543d`，稀疏集合 `backend contracts data frontend review scripts tools`；`D:/moodle/CityNexus/.venv/Scripts/python.exe` = `Python 3.12.14` |

## 一、臂，在新代重跑

`tests/test_ord0543_day_sequence_leg_r1.py` **6 passed**（`-p no:cacheprovider -q --no-header`）。这一趟的时间戳被同一台机上另一族并发读数拖到 472 s，所以本件不含任何时长结论；还原后又跑一趟 `6 passed in 0.84 s`。

## 二、两枚反件，在新代真跑（`readouts/mutants_M1_M2_on_00b5f25e_recut.json` + `mutant_console_on_00b5f25e_recut.txt`）

| 反件 | 改了什么 | 该红的 | 实测红的（逐枚点名） |
| --- | --- | --- | --- |
| M1 | 把"没有声明窗口的站退回工作日带"去掉 ⇒ 又变成跳过（修前行为） | 需要无来源窗口那站被排上的臂 | `4 failed, 2 passed`：`test_a_city_without_stated_hours_now_composes_a_day_sequence`、`test_a_stated_window_still_bounds_its_own_stop`、`test_a_band_that_closes_before_it_opens_is_not_used`、`test_the_unsourced_count_is_measured_in_both_directions` |
| M2 | 把带子用到**每一**站（即无视声明过的营业时间） | 钉真实窗口那枚 | **恰好 1 failed**：`test_a_stated_window_still_bounds_its_own_stop`，判语 `assert 540 >= 840`（09:00 对 14:00） |

还原：`blob_before == blob_after == 564bb4a9cfb6e04f114f04d926bfaf0a5ccef895`，`all_restored: true`，`git status --porcelain -- backend/app` 空。**与旧代那趟（`mutants_M1_M2.json`）的击杀集合逐枚相同**，两趟读数都在包里，旧件没动。

## 三、门读数，在新代重取（`readouts/door__recut_00b5f25e.json`）

私有后端 `127.0.0.1:8841`，私有库 `run/_dayseq543recut.db`（tree head `f75c1801afede6dd15d6388cdd0ea2b26f7e2656`）：

- `catalog-hydrations` 终态 `outcome=ALREADY_CURRENT`，`survey.places_held=5`、`pending_materialisations=0`，`outcome_qualifier=OFFLINE_SOURCE_SUPPLIED`；
- `POST /plans/generate` `http_status=201`、候选 **3** 枚（库里 `plan_versions` 3 行，utility 0.9298 / 0.9356 / 0.9312）；
- `POST /plans/{id}/select` `http_status=200`，`active_plan_version_id` 落在我点的那一枚；
- `GET /calendar.ics` `http_status=200`、整段正文 **1669 B**、`BEGIN:VEVENT` **5** 次，五条 SUMMARY 是 `天津文化中心 / 天津老城博物馆 / 平津战役纪念馆 / 天津文庙博物馆 / 天津义合团纪念馆`（字节数与计数取自整段正文，`call()` 那种截 200 字符的读法是我自己的仪器缺陷，已在件里注明）；
- `POST /share-grants` `http_status=201`；
- 库里营业时间三态：stated **1** / unstated **4** / total **5**；逐站 `hours_basis`：1 枚 `STATED_OPENING_HOURS` + 其余 `PRODUCT_WORKING_BAND`；
- 归属三证：P1 监听 PID 命令行同时点名我这棵树与这枚端口；P2 真 journey 回读 `201`、现造 uuid 回 `404`；P3 监听进程沿父链回到启动 PID（`launcher_pid` 在件头）。

`share_grant.plan_version_id` 那格仍是 `null`——旅程级授权本来就不带那枚键，不是这次丢的（旧代同读数）。

## 四、没在新代重测的（具名，不粉）

- **全量 like-for-like**：那一对（干净尖 `12 failed, 1652 passed` / 本枝 `11 failed, 1655 passed`，只出现在本枝的红 0 枚）是在 `5a4cdbd2…` 上成的，本件没有重跑整趟。依据是 §〇 的 `git diff --name-only`：这 9 笔没动 `services.py`，也没动本单臂文件。这条判语是**从"上游没碰这两个文件"推出来的预测**，不是新测量；要按新代收口，请在 `00b5f25e…` 上重跑一趟本枝全量（命令在 `READINGS.md` 第 7 节，加上 `--ignore=tests/test_v18_hermes_r20_transport_reliability_probe.py`，理由与号令者 07:57 那把尺一致：外部 `citynexus_mcp` 包）。
- 屏面（前端那一侧的日历入口/分享屏）不在本单车道射程内，本件不含任何屏上读数。
- 上一块里更正过的那格不变：被撤回的是「34/35/36」这组分母（我自己的稀疏检出把前端测试漏掉了），不受影响的是门读数、六枚臂、两枚反件与三证。
