# ORD-0464 · 丢弃前问一次 · 屏上读数与没做到的部分

分支 `review/Q-ord0464-abort-reason`；本文件与规格同一笔提交（那笔的 40 位在账本块里，写这里时还不存在）。
父尖（命令者 13:55 那块所记现读）`4037cb331ea00b83124316d40329762fa1131689`。

## 三态在屏上的原话（zh-CN，390x844 无头 Chrome，页面是本车道自己的 `vite preview :4192` 构建产物）

逐字取自本目录 `SCREEN_READINGS_R1.json`；三张截图 `screen_declared_r1.png`、`screen_skipped_r1.png`、
`screen_silent_r1.png` 同批。

- **declared** 行程 `journeys.id=14d9be0c-41ad-4199-b581-4fb0a7bcc3db`
  - 触发钮：把这趟丢进回收站
  - 问句：方便说说为什么不需要这趟了吗？
  - 八条说明句：安排不合用（活动、顺序或节奏）／预算兜不住／日期或目的地变了／关键信息拿不到（路况、住宿没有可信答案）／被保护的安排被排掉了／已经用别的方式安排好了／这是测试或演示数据／其他
  - 主按钮：丢进回收站（未勾时 disabled=True）· 跳过：暂不说明，直接丢进回收站
  - 补充说明框 maxLength=200，方框数 8
  - 落定那格：data-cnx-state=DECLARED → 这趟已经在回收站里。服务器记下的原因是：预算兜不住、被保护的安排被排掉了。
  - 服务器那一行：event_type=JOURNEY_DELETED payload={"codes": ["BUDGET_DOES_NOT_FIT", "PROTECTED_ITEM_DROPPED"], "note": "住的那一晚超出了预算", "reason_state": "DECLARED"}

- **skipped** 行程 `journeys.id=f35edb1e-d665-44c7-8f2d-b281abaff0f5`
  - 触发钮：把这趟丢进回收站
  - 问句：方便说说为什么不需要这趟了吗？
  - 八条说明句：安排不合用（活动、顺序或节奏）／预算兜不住／日期或目的地变了／关键信息拿不到（路况、住宿没有可信答案）／被保护的安排被排掉了／已经用别的方式安排好了／这是测试或演示数据／其他
  - 主按钮：丢进回收站（未勾时 disabled=True）· 跳过：暂不说明，直接丢进回收站
  - 补充说明框 maxLength=200，方框数 8
  - 落定那格：data-cnx-state=SKIPPED_BY_TRAVELER → 这趟已经在回收站里。当时你选了不说明原因，我们也不会替你编一个。
  - 服务器那一行：event_type=JOURNEY_DELETED payload={"codes": [], "note": null, "reason_state": "SKIPPED_BY_TRAVELER"}

- **silent** 行程 `journeys.id=2ee3b691-b07a-40df-8351-4f58b91b631f`
  - 触发钮：（这趟已在回收站，屏上不再端出触发钮）
  - 落定那格：data-cnx-state=NOT_ASKED → 这趟已经在回收站里。这台服务器没有收到过这个问题，所以也没有原因可记。
  - 服务器那一行：event_type=JOURNEY_DELETED payload={"codes": [], "note": null, "reason_state": "NOT_ASKED"}

## 这一屏刻意做成什么样

- 两个出口都写真实动作：`丢进回收站` / `暂不说明，直接丢进回收站`。没有一枚按钮写「提交」「确认」。
- 「已丢弃」那句是读服务器得来的（`GET .../outcomes`），不是 React 里记得按下过什么，所以刷新与第一次走同一格代码。
- 机器词面只待在 `data-cnx-code` 属性里给门禁读，标签上是中文句子。
- 词表八枚对着本产品已有的面拟：没有一枚提到供应商名字、离线模式或本产品没有的功能。

## 没改善的部分

1. 「中止」那一半没做：`journeys.status` 的 `CANCELLED` 到现尖仍无任何路由写入，屏上也没有中止动词，所以词表里没有中止专用码。
2. 原因没有回读的门：回收站列表那屏的行里没有原因字段；契约声明了 `JourneyAbortRecorded` 的形状，但现尖没有响应把它发出来。
3. 找回后再丢弃会留第二枚行，屏上取最后一枚，没有「哪一次」的选择器。
4. 并发未测：同一趟两个 tap 同时丢，本单没加新防护。
5. 手机链真机未走：A7 是无头视口的命中测试。
6. `playwright.config.ts` 只被收集、未经它执行。
7. 八枚词是我拟的产品面语言，没做用户研究；改词必须同批改 `journeyAbortCopy.ts` 与契约枚举，否则 `test_r12` 判红。
8. 面板第一版把「正在读取」写成「正在丢进回收站…」，是描述错动作；已新增 `abort.loading` 修掉，记在这里因为它是交付第 4 笔的内容而不是原样。
