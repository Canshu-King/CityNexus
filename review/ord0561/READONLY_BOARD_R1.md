# ORD-0561 · 只读派单板：每行写清「哪一屏、还剩什么、修完怎么复量」

## 〇、它和上一张板差在哪

`review/ord0561/CONTROL_SET_BOARD_GATED_R1.md` 回答「还剩多少」；本件回答「**在哪一屏、还是不是真控件、修完怎么用同一把尺复量**」——车道要的是这三件事。件内每一行的数字都由脚本从扫描件**重新推导**，并与带已装进尺的板**逐格对账**，两者不一致就整件拒收，所以板与读数不会悄悄走开。

## 一、代次与只读边界

- 读数代次 `79daa3c4ff8f37304d352177b456133d4b9c2a45`（写件时现尖 `ff7f62011821240835572bf4effe2e139ee2bada`）；入口资产 `index-ay8Jsqaq.js`、1624284 字节 B；两档各 136 趟、全挂载 136 趟。
- **只读**：产品字节 0 枚改动、账本 0 次直写、别人的树与进程 0 次触碰。本件只读两份扫描件、写一份 JSON。

## 二、还剩什么：可动手的屏只有 6 块

可动手的屏：/v8/agent、/v8/bookings、/v8/hub、/v8/live、/v8/map、/v8/trips。其余十一屏在两条闸（名牌、带）之后都收到零——零是量出来的。

| 屏 | 形 | covered 树内 | below 带内 | 其中地图针 | 其中其它真控件 | 被正文盖 | 带不适用剔出 |
|---|---|---|---|---|---|---|---|
| /v8/agent | 390x844 | 8 | 8 | 0 | 16 | 0 | 0 |
| /v8/bookings | 1280x900 | 4 | 0 | 0 | 4 | 0 | 14 |
| /v8/hub | 1280x900 | 2 | 0 | 2 | 0 | 0 | 12 |
| /v8/hub | 390x844 | 28 | 24 | 46 | 6 | 0 | 0 |
| /v8/live | 390x844 | 12 | 4 | 8 | 8 | 0 | 0 |
| /v8/map | 1280x900 | 8 | 0 | 4 | 4 | 0 | 10 |
| /v8/map | 390x844 | 4 | 0 | 4 | 0 | 0 | 0 |
| /v8/trips | 1280x900 | 4 | 0 | 0 | 4 | 0 | 16 |
| /v8/trips | 390x844 | 8 | 4 | 0 | 12 | 4 | 0 |

读法：**地图针**是有意落在带里的地图控件，不是缺陷（「其它真控件」与「被正文盖」那两列才是缺陷候选）；「带不适用剔出」是宽形上底栏不在场、那条带无前提而单列的读数，保留可见、不算缺陷。

## 三、修完怎么复量（同一把尺，逐行附一份）

- stack：`python start_stack_r5.py <label> dist_<dist> <own-token>   # ports 4891/4892, own db file`
- sweep：`TIERS=light,dark SHAPES=390x844,1280x900 LOCALES=zh-CN,en ENTER=url node sweep_ink_r1.cjs <label> sweep_<label>light.json <journey> <token>`
- summarise：`LBL=<label>light SWEEP=sweep_<label>light.json OUT=reach_summary_<label>light.json python sum_reach_r1.py   # and the dark pair`
- board：`SWEEP_PREFIX=<label> python chip_board_gated_r1.py && SWEEP_PREFIX=<label> python chip_readonly_board_r1.py`

复量的规矩：两档腿都必须**拒收 0 条**才算数——汇总脚本对任何一条拒收都整腿拒收（不是忽略）。跑完再出一次本件表格，逐格与本表对账。

## 四、没做的，具名

- 本件是只读重算，没有新起浏览器；`C4` 那格的漂移复量另起一格单独交。
- 前端 e2e 整套没跑（`NOT_EXECUTED_BY_CMDR`）；共享预览口这手没读没写；权威尖我没移动过、已发布 ref 覆盖 0 次（force-push 没用过）。
- 归属我不派：这些屏各归哪个车道，仍等号令者定；我这里只给「哪一屏、是不是真控件、怎么复量」。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
