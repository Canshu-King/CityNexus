# CMDR 02:35 (5) follow-up · what the narrowing gives up, measured on the real path

The ruling landed as `e49bd2c62b0f94f50fea0015660e1b977ae87870` (line tip at the time
`c4da40beda5940ec9ef3d5c43223356cd2ff7d10`). Its acceptance said "self-declare when done", which I did,
and one cell was left `NOT_MEASURED_BY_LANE`: **if the second bounded ask would have answered, does the
narrowing cost the traveller supply?** This package answers it with the same door instrument, run against
the pre-gate generation, and names what the instrument itself contributed.

## 〇、形制

| 项 | 值 |
| --- | --- |
| 无门臂（比较代） | `491e343bfb3d543b38ab11c9f6f0f0283e66129a`，树 `wt543tip`，其 `backend/app/integrations/discovery/real_city.py` blob = `e7663564bf47c0fc0923b790f54c429ef4ac4eeb` |
| 有门臂（已落代） | `c4da40beda5940ec9ef3d5c43223356cd2ff7d10`，树 `wt_fb549`，同路径 blob = `5bed42608bdfaad1067c50abb11918dfba4710b4` |
| 本枝 | `refs/heads/review/newlane-fallback-supply-consequence-r1`（新 ref 名，0 次强推；**只交证据，0 产品字节**） |
| 仪器 | `readouts/supply/drive_fb549_door_r1.py`，两臂各起私有后端与一次性私有库，`CITYNEXUS_NOMINATIM_URL` 指向本机只计数监听 |
| 解释器 | `D:/moodle/CityNexus/.venv/Scripts/python.exe` = Python 3.12.14 |

## 一、五趟里只有一趟走到那一形（逐趟原因在 JSON 里，不挑好的说）

| tag | 走到了哪一形 | 为什么不算 |
| --- | --- | --- |
| `cafe100_one` | 两臂 Overpass 皆 `PROVIDER_TIMEOUT` | 门没被走到 |
| `supply_one_a` | 同上 | 同上 |
| `supply_one_try1` | Photon `NOT_ANSWERED_ConnectError`，**我的 stub 替它落了锚** | 仪器决定了哪条腿答，形状被污染 |
| `supply_one_try2` | 无门臂同上；有门臂 Photon 答了但 Overpass 超时 | 只有一臂在形内 |
| `aware_b1` | **三件事齐**：Photon `http_status=200` / `bytes=344`、Overpass 答零、回退那一问按 `limit` 答得出 | 这一趟是本包结论唯一依据 |

## 二、`aware_b1` 的两臂读数（同一形状，两代）

| | 无门 `491e343b` | 有门 `c4da40be` |
| --- | --- | --- |
| `http_status` | `200` | `200` |
| `mode` | **`live`** | `replay-fallback` |
| 候选 | 1 枚（来自那第二问） | 3 枚（来自封存 replay） |
| Nominatim 实收 | **1 条**（`limit=8`、`q="cafe, TIANJIN"`） | **0 条** |
| `fallback_geocode` | 该键不存在（此代无此字段） | `SKIPPED_ANCHOR_GROUNDED_BY_photon_city_anchor` |
| `overpass` | `CAPTURED`（=有 attempt 答过，不代表留下候选） | `REPLAY_FALLBACK` |
| `fallback_reason` | `null` | `PROVIDER_NO_RESULTS` |

代码条件是硬的：无门代 `real_city.py:1642` 的 `if not candidates:` 之后才有那一问，`overpass` 的
`CAPTURED` 由 `:1670` 的 `any(a.get("answered") …)` 决定——答过≠留下。所以那一枚候选确实来自被裁语关掉的门。

**结论（这格现在才有句子）**：裁语确实让掉一条通路——在“腿已答而类别答零”那一格里，若第二次问能答出东西，
无门代会把它作为 live 供给交出去，有门代不会；旅客在两代都拿到东西（1 vs 3），但**来源类别不同**
（供应商形状的一手 vs 封存 replay），两枚候选数不可加、也不构成“谁更多”。

## 三、必须具名的三处

1. **那一行是我造的**：`_SYNTHETIC_ROW`（`display_name` 里就写着 `SYNTHETIC-NOMINATIM-ROW not product data`），
   只进一次性私有库，从未进共享库；它证明的是**通路与形状**，不是“今天真 Nominatim 能不能答”——后者这一格仍然
   `NOT_MEASURED_BY_LANE`，因为本校园链路上 Nominatim 不可达，而我不能拿仪器代它答。
2. **我这轮又改掉一处自己仪器的缺陷**：`DOOR_STUB=one` 会连锚腿（`limit=1`）一起答，于是仪器替产品决定了落锚的腿
   （`supply_one_try1` 两臂都 `nominatim_city_anchor` 是现场证据）；已改成按 `limit` 分别应答
   （`limit<=1` 回空数组）。这是仪器的，不是产品的。
3. **件头一处申报缺陷**：驱动里 `stub_row_declared_synthetic` 只在 `stub == "one"` 时写值，
   对 `limit_aware` 写成 `null`——所以上面第 1 条那句“这行是合成的”在 `aware_b1.json` 的字段里读不到，
   只能读本文件。数据性质不变，申报面有此一格，我不遮。

## 四、复现

```bash
cd D:/moodle/_qoder_seed_ord0489/run && DOOR_TAG=aware_b1 \
  DOOR_A_LABEL=nogate_491e343b DOOR_A_TREE="D:/moodle/_qoder_seed_ord0489/wt543tip" \
  DOOR_B_LABEL=gated_c4da40be  DOOR_B_TREE="D:/moodle/_qoder_seed_ord0489/wt_fb549" \
  DOOR_QUERY=cafe DOOR_RADIUS=100 DOOR_TIMEOUT=45 DOOR_STUB=limit_aware \
  D:/moodle/CityNexus/.venv/Scripts/python.exe drive_fb549_door_r1.py
```

一次性私有库（`run/_fb549door_<臂>_<tag>.db`）取完读数由本车道自删；逐值读数都在本包 JSON 里。
