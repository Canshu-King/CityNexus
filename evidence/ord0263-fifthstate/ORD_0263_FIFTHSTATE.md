# ORD-0263 第五态 · before 读数：源站答了 200，屏上说"没人回答"——第五臂红了，前四臂一个没动

尺：`tools/ord0263_verifier_v3.py`（v2 的前四臂逐字节搬过来 ＋ 第五臂；搬运由尺自己在自检里比对，不靠我说）。
被测：盘上这一代 `/assets/index-Cpy_jhEg.js`（1,242,399 B / sha256 `5d674a44…d7b2d7`）、
`/assets/index-I45CQek8.css`（sha256 `1b363278…f6a58f`）。
结论一句话：**`derived_result: RED_CELLS: V5_origin_invalid_response` —— 前五格那张表里只有第五格红，
而且三形（200+HTML / 200+空体 / 200+非 JSON）各自红在同样五条上。**

## 1. 代次先钉住（23:2x 换过代，我量的是哪一枚必须说清）

23:21 那次换代（`ORDERS` 顶 `@22:5x` 块 §③ 里 B 的 `fix(build): let Workbox keep the single content-derived
shell entry`）改了 dist 根的 tree：我 22:5x 起面复制时是 `074267d90c499b71…` / 32 文件 / 16,818,701 B，
现在盘上是 `7a76b74339713092…` / 32 文件 / **16,818,660 B**（差 41 B）。所以收尾脚本回读
`byte_identical_to_before: false` —— 那是**真的换了代**，不是我的副本被谁动过。

差异落在哪：被量的那两枚资产逐位未变（我拿自己起面时写进收据的 per-file sha256 与当前盘上重算比对，
`same_now=True` × 2），变的是 sw 侧 —— 用你给的标记核：`v10-sw.js` 2,055 B / sha256 前缀
**`e63d7421eda34093`** ✓ 对得上，`sw.js` 7,178 B / `1fc94905…`，`index.html` 现 mtime 23:07:28 仍引用同一枚
js/css。⇒ **我这份 before 读数所指的那一枚 bundle，与 23:2x 这一代正在服的那一枚是同一枚字节**，
结论直接适用于新代；被换掉的只有 sw 外壳。

## 2. 第五臂怎么判（照仲裁的最低验收，不锁 B 的措辞）

`judge_v5` 只吃实测字段，五条件全过才绿：

| 条件 | 读法 | 这一代实测 |
| --- | --- | --- |
| `evidence_kind` 保住 HTTP 事实 | 屏上展开「归因详情」后渲染出来的 `evidence_kind=` | `TRANSPORT` ❌ |
| `http_status` 仍带得上 | 同一行 `http_status=` | `none` ❌（而仪器侧同一发是 **200**） |
| reason 不落网络 | `attribution_reason=` ∉ {NETWORK_UNAVAILABLE, NO_REPLY} | `NETWORK_UNAVAILABLE` ❌ |
| 层不落 TRANSPORT | `source_layer=` | `TRANSPORT` ❌ |
| 句子不许否认收到过回答 | 主句正则 | 「这一发请求没能出去，也没有收到任何回答」❌ |
| 快照那一列跟测量走 | `cached_copy_present=` vs IndexedDB 实读行数 | `true` vs 1 行 ✓（这一条它是对的） |

**命名不锁死**：仲裁写的是"名字可再定"，所以判据里没有 `== "ORIGIN_INVALID_RESPONSE"` 这种字符串断言——
B 换成别的词也不会被我的尺卡住，卡他的是"HTTP 有回答这件事不能丢"。这条我写进 `fifth_state_acceptance_used`。

三形是三次独立读数聚合，**一枚绿不能带两枚红**（`aggregate_v5`）：

```text
200_html      answered 200  1200 B text/html; charset=utf-8   -> reason=NETWORK_UNAVAILABLE kind=TRANSPORT http_status=none
200_empty     answered 200     0 B application/json           -> 同
200_not_json  answered 200    33 B text/plain; charset=utf-8  -> 同
每形 failed_conditions = [evidence_kind_lost_HTTP, http_status_not_carried, reason_collapsed,
                          layer_collapsed_to_TRANSPORT, sentence_claims_no_answer]
```
仪器侧原文度（`origin_answer` 的 status/content_type/body_bytes）不是我打的字，是 builder 从
`ord0263_junk_{html,empty,nonjson}.log` 里读出来的 answered 行；三份日志原件一起发布。
页面上的 `duration_ms`（4–6 ms）与 `responseStatus: 200` 来自浏览器自己的 Resource Timing。

## 3. 前四臂"一字未改"是尺自己比的，不是我声明的

`legacy_arms_unchanged()` 在运行时把 v2 与本文件里 `answered / no_answer / judge_v1 / judge_v1_vacuity /
judge_v2 / judge_v3 / judge_v4` 七段源码切出来逐字节比，自检里作为一枚臂：

```text
[OK] V0-legacy:four_old_arms_and_two_helpers_are_byte-identical_to_v2 expect=True got=True
     {"answered": true, "no_answer": true, "judge_v1": true, "judge_v1_vacuity": true,
      "judge_v2": true, "judge_v3": true, "judge_v4": true}
```
搬运也是脚本切源码插进去的（`tools/splice_v3_arms.py`），我一行都没重打。
`cell()` 组装同样没动：第五格的四个旧格是 builder **从已发布的 `ord0263_capture_landedgen.json` 读回来的**
（capture 里记了那份文件的 sha256 与"retyped: false"），所以加第五格这个动作本身不可能悄悄改掉前四格。

尺的自检 `SELFTEST GREEN (10/10)`：一枚正控（修好后应有的形状必须绿）＋ 五枚 killer
（reason 仍网络 / http_status 丢 / 层落 TRANSPORT / 句子否认回答 / 快照列不跟测量）＋ 一枚 NOT_MEASURED
（源压根没答，不是这一态）＋ 一枚聚合 killer ＋ 上面那枚 V0-legacy。

## 4. 我自己这一轮被抓出来的两处错（都留下了痕迹）

* **链式比较把正控读成红**：`measured_copy == x in ("1","true","yes")` 在 Python 里是链式比较
  （`(a==b) and (b in tuple)`），我那句意图是 `a == (b in tuple)`。后果是"修好后应该绿"的正控一度被判红
  ——一个假红，方向正好反过来。已拆成两行先算 `declared_copy` 再比，正控才绿。
  教训：`in` 和 `==` 挨着写等于埋雷，判据里不许再出现这种连写。
* **切块边界让我误报"前四臂有差异"**：第一版比较用 `def selftest` 当 v3 里 `judge_v4` 的终点，
  于是把比较代码自己也切了进去 ⇒ 报 `judge_v4: false`。那是**我的文件布局**，不是老臂被改。
  现在改成每块显式给 `(stop_v2, stop_v3)`，v3 那侧用 `# ---- end legacy arms ----` 哨兵收口。

## 5. A3 那一格我**没验**，按具名未验交

号令里"写腿永挂时屏幕会不会也说谎"这一格，我这次没跑，所以既不写红也不写绿。要跑它需要一次**写操作**
（replan/generate 一类 POST）在写腿挂住时读屏，那是写路径、且会往库里落东西，不属这一格的授权范围。
如果它也说"网络不可用/没有回答"，按仲裁与你的口径是 A1 同族、并进本单不另开——这一句我原样记着，不动手。

## 6. 下一步与边界

* **闭单条件**：等 B 修完换代，我用**同一枚 v3 尺、同一张五格表**再跑一次；`derived_result` 里
  第五格转 GREEN（三形各自五条都过）才算这单能写 CLOSED。尺在此之后不再动，动它就等于改验收。
* 我这一轮仍然只测不改：产品码 0 改动、v2 尺源码 0 改动（v3 是新文件、老臂逐字节搬运）、没有进程内替换 BASE；
  `:4781/:4782`/隧道/cnx proxy/`_live.db`/`_preview.db` 一个没碰，无 `demo/reset`。
* 仪器踩到的坑记一条：`socketserver` 不起 `serve_forever` 时会"接了 TCP 但不答"，症状与静默源一模一样 ——
  我第一版就这样，直连 curl 8 s 超时才发现是自己的仪器没起 loop。
* 现场：`:4415` 与 `:8411` 按端口具名停、netstat 回读为空；副本按具名清单删（释放 16,818,836 B）；
  克隆仍在 `compat/ord0254` = `6a39c527f2aa…`，`git status --porcelain -- frontend` **0 行**。
* 坐标走新路径 `evidence/ord0263-fifthstate/`（`ord0263/`、`ord0254/`、`ord0263-livegen/`、
  `ord0263-landedgen/` 四条旧路径一件未动），每件 PUT 后独立 GET 回读满 40 位。
