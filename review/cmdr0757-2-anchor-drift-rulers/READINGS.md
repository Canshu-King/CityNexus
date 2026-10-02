# CMDR 07:57 第 2 条 · 两枚锚点漂移尺改成"锚到具名符号 / 实时重推导"（车道 `5a53846b`，可认领的小单）

裁语（账本 `CMDR 07:57` 块第二节，逐字）：

> 写期限尺与字典键形尺的锚点行号钉死已两次在换代后漂移报红。裁定：改成"锚到具名符号/具名注释串"而非行号，或 exemption 读实时扫描重推导。派给有额度后的任一车道，小单。

我认领了这一条。两枚都是**只改尺、0 改产品字节**。

## 〇、坐标

| 项 | 值 |
| --- | --- |
| 基座 | `00b5f25e9b6b408fba8906ef3ffd49caa5eb84b9` |
| 枝 | `refs/heads/review/newlane-anchor-drift-rulers-r1`（新 ref 名，0 次强推） |
| 交付那一笔 | 见账块（推完从服务器侧回读），产品/门改动面 `git diff --name-status 00b5f25e… HEAD` 只有两枚测试文件 |
| 两枚尺的 blob（改后） | `test_qoder_ord0296_write_deadline.py` = `f402e5759324d071c1ce43409678dbd4f5c3f66c`、`test_qoder_ord0479_dictionary_key_shape.py` = `c1e54505c8355d95dddfa865530651ef1c6ce52f` |
| 解释器 / 树 | `D:/moodle/CityNexus/.venv/Scripts/python.exe`（3.12.14）/ `D:/moodle/_qoder_seed_ord0489/wt543d`（稀疏集合含 `frontend`，所以字典那族能读到前端文件） |

## 一、G4（写期限尺）红的是**尺**，不是产品

尖上的失败读数（本车道现读，命令在 §四）：

```
AssertionError: {'app\\core\\config.py': [...], 'app\\main.py': ['PLAN_CLAIM_LEASE_MS = int(settings.write_deadline_ms) + int(settings.write_busy_timeout_ms)'], ...}
assert ['catalog_hyd..._deadline.py'] == ['catalog_hyd..._deadline.py']
  At index 2 diff: 'main.py' != 'session.py'
```

旧尺除"不许出现第二处内联锁等待数字"（这条真有牙，保留）之外，还把**允许提到 `busy_timeout` 的文件名**钉成一张五行名单。`main.py` 那一行是 ORD-0340 的租约推导（`git log -S"busy_timeout" -- backend/app/main.py` → 提交在 09-26 08:22，笔 `5bb04b8f`），它**读的是那枚具名旋钮**、自己不写任何数——旧尺却因为它不在名单上而报红。这就是"换代后漂移"：被测对象没变坏，尺的名单陈旧了。

改成实时扫描重推导，三条具名类：

1. `KNOB_DECLARATION`：唯一一处**写下锁等待数字**的地方，按符号找（`write_busy_timeout_ms: int = int(os.getenv(` 那一行），并要求它恰好一枚；
2. `WORKER_SHORT_WAIT`：worker 自己那条连接上的短等待，必须同时满足"文件是 `app/**/*_operations.py`"且"值 ∈ {200, 500, 1500}"；
3. 其余每一处提到 `busy_timeout` 的行**不许带数字**（读旋钮、写文案、注释都算）。

任何一处不满足 ⇒ 红，并把三类清单整个打出来（包括被赦免的 `path:line=值`），所以"赦免了什么"是可读的，不是暗中放行。`offenders`（内联抄 `busy_timeout=30000` / `"timeout": 30`）那一格原样保留。

## 二、H01b（字典键形尺）红的是**行号**

尖上的失败读数：

```
assert ('frontend/src/features/shared/SharedJourneyPanel.tsx', 45) in [('...TripPosterPanel.tsx', 34), ('...TripPosterPanel.tsx', 52), ('...SharedJourneyPanel.tsx', 47)]
```

被赦免的那张表在 47 行，旧句钉的是 45——上游 ORD-0512/0513 在表**之上**加过东西，行号自然漂。尺本身报的赦免项是对的（同一循环里逐枚重推导那部分没红）。

改成锚到具名符号：新函数 `_named_table_lines(path, "REFUSAL_KEY")` 在 `export const REFUSAL_KEY: Record<string, string> = {` 处定位，取到 `};` 为止的每一行 `key: "value"`；断言变成"被赦免的行落在这张具名表内"。逐枚赦免的重推导（值必须同时是两本词典的键、同表邻居也必须是键）一字未动。

## 三、牙齿（五枚探针，真跑；`readouts/rulers_teeth_r1.txt`）

| 探针 | 期望 | 实测 |
| --- | --- | --- |
| G4 漂移正控：在旧名单之外的 `main.py` 里插一行**不带数字**的 `busy_timeout` 提及 | green | `1 passed in 44.24s` ⇒ 尺不再因文件名报红 |
| G4 反例：同一文件里写一枚新数 `busy_timeout = 7000` | red | `1 failed` |
| G4 反例（本单原形）：在 worker 里内联抄一份请求路径的等待 `PRAGMA busy_timeout = 30000` | red | `1 failed in 7.78s` |
| H01b 漂移正控：在具名表**之上**插一行（正是上游那种改动） | green | `1 passed in 6.33s` ⇒ 锚跟着符号走 |
| H01b 反例：往那张表里塞一个两本词典都不是键的值 | red | `1 failed in 7.89s` ⇒ 逐枚重推导仍有牙 |

每枚探针都逐字节还原（`restore byte-identical=True`），跑完 `git status --porcelain -- backend frontend` 只剩我这单的两枚测试文件。

## 四、分母（同一棵树、同一命令，两个头）

| 头 | `tests/test_qoder_ord0296_write_deadline.py tests/test_qoder_ord0479_dictionary_key_shape.py` |
| --- | --- |
| 权威尖 `00b5f25e…`（尺未改） | `2 failed, 19 passed, 2 warnings in 72.97s` — 红的正是 `test_G4_…` 与 `test_H01b_…` |
| 我这笔（只改两枚尺） | 分开跑：`11 passed`（0296 一族）+ `10 passed`（0479 一族）= 同一 21 枚，0 红 |

控制那一趟是把两枚尺临时检出成尖上的字节再跑、跑完从我的提交检回（`git checkout <rev> -- <两路径>`，0 stash、不动他人文件），还原后两枚 `git hash-object` 与提交里的 blob 逐字相同（上面那两枚 40 位）。

## 五、没改善 / 没做的（具名）

- 本单**不碰产品字节**，所以旅客能感觉到的东西一件没变；变的只是这两格在换代时不再假红。
- 没有跑全量。这两枚尺在全量里的形状由号令者 07:57 那把尺判（他那趟 `9 failed, 1656 passed`，其中"两枚锚点漂移族"就是这两格）；我这侧给的是同两枚文件的两头对照，不是新基线。
- `offenders` 那三枚 needle 仍是字面串（`busy_timeout=30000` 等），没顺手改成"任何数字"的一般式——那会改变射程，属另一单。
- 字典键形尺的其余八格臂没动；`SITE` 的常量名仍是 `SharedJourneyPanel.tsx` 这一枚路径。若那张表哪天改名，`_named_table_lines` 的 `assert len(head) == 1` 会红并打印路径与符号名——这是有意的失败，不是沉默放行。
