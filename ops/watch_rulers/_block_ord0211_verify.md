### commander 亲测 @2026-09-22T15:2x+08 —— ORD-0211 验收（`0a4cb23`）＋ g3 的 14 次独立进程读数 ＋ ORD-0213 下发（C）

**① ORD-0211 = ACCEPTED（只签机制层，不签"隔离已解决"，边界照仲裁原文）。** 全部在 `git archive` 干净导出树上跑，解释器 `D:/moodle/CityNexus/.venv/Scripts/python.exe`（3.12.14），收据落 `live_checks/ord0211/receipt.json`：

- **M1 对照（父提交 `0cd697b`，没有钉）**：在 `backend/` 植入一个带 canary 行的 `citynexus.db`，跑一道会写库的门，植入文件 sha256[:16] 由 `7c8c09284dffd5ba` 变成 `73aa25d9bd451015` ⇒ 泄漏是真的，M2 不是空判定（非空性＝`plant_mutated=true`）。
- **M2 交付（`0a4cb23`）**：同一个植入文件跑完**逐字节不变**（`7c8c09284dffd5ba` → `7c8c09284dffd5ba`，`plant_untouched=true`），且收集期收据原文打印了解析后的绝对路径：`ORD-0211 test database: resolved=C:\Users\…\AppData\Local\Temp\cnx_pytest_rko0g_8g\suite.db | exists=False | declared_by=conftest temp dir`。跑完目录里只剩植入的那一个 `citynexus.db`，没有多出 WAL/sidecar。
- **M3 拒绝分支（双向都试）**：把 `CITYNEXUS_DATABASE_URL` 声明成 `sqlite:///<一个不存在的临时目录>/_live.db`，pytest 退出码 4，conftest 抛 `RuntimeError: ORD-0211 boundary: the test suite must never open '_live.db' (preview/live target)`，而且那个路径跑完之后仍然不存在（`declared_path_exists_after=false`）⇒ 它是**先拒绝再谈打开**，不是打开之后再道歉。
- 我这边的一处仪器错先自纠：第一版脚本用 `pytest -q`，而 `-q` 会把打印收据的 header 段一起压掉，于是把 `receipt_names_temp_dir` 误判成 false。去掉 `-q` 后收据照原样出现。这条红是我的量具，不是 C 的交付。

**② g3（`gates::test_g3_five_concurrent_hydrations…`）的 14 次独立进程读数——请 ORD-0210 改验收口径。** 每次都是新进程、新的 `cnx_pytest_*` 临时库（14 次共 14 个不同临时目录），全在钉住树里：

| 时段 | 进程数 | 红 | 绿 |
|---|---|---|---|
| 15:15（M2 那次） | 1 | 1 | 0 |
| 15:16 手工三次 | 3 | 1 | 2 |
| 15:18–15:20 burst | 8 | 8 | 0 |
| 15:24 同树"预热后" burst | 4 | 4 | 0 |
| 合计 | **14** | **12** | **2** |

- 红的时候门自己报出 **2–4 枚**不同的 operation_id（例：`3a9c8765… / 978dd186… / d1957ab3…`），不是 1 枚。
- 我试过并**反证**了一个解释：冷导出树 vs 已经跑过 12 次的同一棵树，两边都全红；两边文件差异只有 `.pytest_cache/**` 和那个植入诱饵。所以"热了就好了"不成立。
- 对分类的一条更正（附读数，不是意见）：`ISOLATION_BREACH / dirty-db false-green` 只解释了"脏库能绿"那一半——**干净临时库同样绿过 2 次**，所以单次绿不能当修复证明。请 ORD-0210 的验收从"跑一次不红"改成**独立进程连跑 10 次全绿**，并把每次的 `exit` 与临时库绝对路径逐条列进收据。

**③ ORD-0213 → C（只限这一道门）。** 靶子＝②里那个竞态本体：为什么五个并发请求会拿到 2–4 枚 operation_id。要求顺序是先给**机制判定**（先查后插？拿锁顺序？唯一约束缺位？）再谈修法；复现命令逐字可复放：

```text
cd <git archive 0a4cb23 导出树>\backend
D:/moodle/CityNexus/.venv/Scripts/python.exe -m pytest \
  tests/test_qoder_anywhere_gates.py::test_g3_five_concurrent_hydrations_of_one_county_converge_on_one_operation \
  -p no:randomly --tb=line -rA
```

验收＝10 次独立进程全绿 ＋ 一条反例（把收敛点故意拆掉必须变红，用 `mutation_anchor_guard.py`）。**不许用 sleep/加重试把门哄绿**，那只会把 12/14 换成 0/10 而问题原样留在产品里。
顺带一条小尾巴（HARNESS 15:1x 已量到 `%TEMP%` 里 22 个目录 / 22 MB 堆积，我不重复计数）：conftest 的 `mkdtemp(prefix="cnx_pytest_")` 没有进程退出清理，请在 ORD-0213 里一并收尾，或者至少把目录名落进收据好核对归属。

**④ 车道规则（采纳 HJ-P1 15:04 的现场，全体适用）**：验证、构建、跑门一律从 `git archive <sha>` 的导出树做，不从活树构建——活树随时带着别人未提交的编辑（HJ-P1 撞上了，我这两棵树也照此办理）。

**⑤ tip 与 P0。** working tip 现在是 `952ec40`（D 的 ORD-0209，15:08：demo 入口改为寻址已封存行程）。我只读了提交与代码，**没有跑 3 击 0 POST 的运行时复验**——HARNESS 15:1x 已声明用同一支 `harness_sealed_entry_audit.py` 复验，我不重复开枪、也不替它签。P0：本轮我 0 次触碰 `_live.db` / `_preview.db`，0 次 `demo/reset`，0 次 provider 出网，没读过也没写过用户库；我造的两个 `citynexus.db` 诱饵只存在于我自己的导出树里。
