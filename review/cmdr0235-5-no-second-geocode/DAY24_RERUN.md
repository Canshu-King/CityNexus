# CMDR 02:35 (5) 反件的线上复跑 · day24 栈（`4fac49f3…`）· 车道 `5a53846b`

派单逐字（账本 `CMDR 01:24` 块第一节第 3 条）：

> `5a53846b`：回退腿已落地，领「回退腿反件的线上复跑」——在 day24 栈上确认锚答后第二问仍是零次。

**0 产品字节**：本包只有读数与一台仪器；比较臂用的是门落地之前的那一代检出。

## 〇、两臂与代次（现读）

| 臂 | 树 | head | `real_city.py` blob | 角色 |
| --- | --- | --- | --- | --- |
| `day24_line_4fac49f3` | `wt_fb549` | `4fac49f371da0820393d038700bddddafd1176d1` | `5bed42608bdfaad1067c50abb11918dfba4710b4` | **线上那一手**（含门） |
| `nogate_491e343b` | `wt543tip` | `491e343bfb3d543b38ab11c9f6f0f0283e66129a` | `e7663564bf47c0fc0923b790f54c429ef4ac4eeb` | 反面对照（门之前） |

解释器 `D:/moodle/CityNexus/.venv/Scripts/python.exe` = Python 3.12.14。

## 一、夹具族在 day24 上逐枚复现（`readouts/day24_mutants_console.txt`）

- 族本身：`1 failed, 6 passed`。那一枚红是本车道具名的尖上存量 `test_a_live_failure_arrives_named_and_carries_the_stage_it_broke_at`（`PROVIDER_SERVER_ERROR != PROVIDER_BAD_RESPONSE`），与这一手无关。
- M1（把门拆开 = 裁语前行为）⇒ `2 failed, 2 passed`，红的正是「锚答 ⇒ 零调用」那两枚：`test_an_answered_anchor_costs_the_fallback_door_nothing`、`test_a_failed_anchor_leg_still_closes_the_second_ask`。
- M2（门焊死 = 收窄过头）⇒ `2 failed, 2 passed`，红的是「锚没答必须仍问」那两枚：`test_when_no_leg_was_asked_the_fallback_door_is_still_asked`、`test_the_default_resolver_was_not_swapped_and_the_replay_fallback_still_answers`。
- 两枚还原后 `sha256[:16] bf91ea87b7a458f0` 与改前逐字节相同（驱动里是断言）；`statement occurrences in product file: 1` 说明这条判据在 day24 那一代仍只有**一处**，没有被上游复制。

## 二、真机那形（Photon 真答 + Overpass 答零）三趟，两趟在形内

`query=cafe`、`radius_m=100`、`provider_timeout_seconds=45`；两臂各自私有后端与一次性私有库，Nominatim 基址指向本机只计数监听（按 `limit` 分别应答：`limit<=1` 回空数组，只让回退那一问拿到合成行）。

| 趟 | 无门臂 实收 / 形状 | day24 臂 实收 / `fallback_geocode` | 在形内？ | 件 blob（字节） |
| --- | --- | --- | --- | --- |
| `day24_rerun_b1` | **1 条**（`limit=8`、`q="cafe, TIANJIN"`），`mode=live`、候选 1 | **0 条**，`NOT_REACHED`（Overpass `PROVIDER_TIMEOUT`，105.64 秒） | 否：day24 臂走的是失败形，零次不是门给的 | 见 `readouts/day24_rerun_b1.json` |
| `day24_rerun_b2` | **1 条**，`mode=live`、候选 1，`overpass=CAPTURED` | **0 条**，`SKIPPED_ANCHOR_GROUNDED_BY_photon_city_anchor`，`mode=replay-fallback`、候选 3、原因 `PROVIDER_NO_RESULTS` | **是** | 见 `readouts/day24_rerun_b2.json` |
| `day24_rerun_b3` | **1 条**，同上 | **0 条**，同 `SKIPPED_ANCHOR_GROUNDED_BY_photon_city_anchor` | **是** | 见 `readouts/day24_rerun_b3.json` |

三趟里两臂的 Photon 腿都是 `attempted=true answered=true http_status=200`、Nominatim 腿 `SKIPPED`、锚 `photon_city_anchor` ⇒ 前置条件（锚由腿落）成立。每臂三证同批：P1 标记行在自己库里读回 1 行、P2 监听 PID 沿父链回到启动 PID、P3 boot log 写着该端口；teardown 后端口都无监听。

**这一手的结论（照派单那句回答）**：**是——day24 栈上锚答之后第二问仍是零次**，在形内的两趟都是 0 次且带具名 `SKIPPED_ANCHOR_GROUNDED_BY_photon_city_anchor`；同一形状下门之前那一代每次都实打实问了 1 次（`limit=8`）。第三趟不算：它的零次来自 Overpass 超时走了失败形（`NOT_REACHED`），不是门的功劳，这一格我不混着说。

## 三、没改善与没测的（具名）

- 旅客可见结果没变：`mode`、候选数、原因在形内两趟逐值稳定（线上 `replay-fallback` / 3 枚 / `PROVIDER_NO_RESULTS`）。省下来的是一枚对该城的外部地理编码。
- 不含时长结论：4.55 / 6.09 / 105.64 秒这种散布在 provider 抖动里不读。
- 真 Nominatim 在本链路能否答出这一问，**仍 NOT_MEASURED_BY_LANE**（我这台监听替它答，行是我造的合成记录，只证通路与形状）。
- day24 前端 :4783 与后端 :4787 我一次也没请求（共享栈，且监听命令行不带 `--app-dir`，工作树无从判定）；"线上那一手"我按**那一代代码**复跑，不是按那台进程复跑。
- ORD-0543 不在这一手射程内：它在 day24 尖上仍未落地（`services.py` 尖上 `f78644842e8ed03bf3b152d4be47b4560dd6d41a`，我的臂文件 0 命中），候选停在 `67bb75ac768a0343d8d4e230e7107cd124ac2741`，`ahead=9 behind=21`，等号令者一句（收 / 让我再搬一次基座 / 就此停）。

## 四、复现

```bash
# 族 + 两枚反件（在 day24 检出上）
cd D:/moodle/_qoder_seed_ord0489/wt_fb549/backend && D:/moodle/CityNexus/.venv/Scripts/python.exe -m pytest -p no:cacheprovider -q --no-header -rf tests/test_qoder_city_failure_reasons.py
cd D:/moodle/_qoder_seed_ord0489/run && MUT_ROOT="D:/moodle/_qoder_seed_ord0489/wt_fb549" D:/moodle/CityNexus/.venv/Scripts/python.exe mutant_fb549_r1.py

# 真机那一对
cd D:/moodle/_qoder_seed_ord0489/run && DOOR_TAG=day24_rerun_b4 \
  DOOR_A_LABEL=nogate_491e343b DOOR_A_TREE="D:/moodle/_qoder_seed_ord0489/wt543tip" \
  DOOR_B_LABEL=day24_line_4fac49f3 DOOR_B_TREE="D:/moodle/_qoder_seed_ord0489/wt_fb549" \
  DOOR_QUERY=cafe DOOR_RADIUS=100 DOOR_TIMEOUT=45 DOOR_STUB=limit_aware \
  D:/moodle/CityNexus/.venv/Scripts/python.exe drive_fb549_door_r1.py
```

一次性私有库（`run/_fb549door_<臂>_<tag>.db`）取完读数由本车道自删；逐值读数都在本包 JSON 里。
