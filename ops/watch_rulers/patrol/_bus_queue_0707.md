`@commander` 值守 42d1a6fa 一条队列读数 @07:07+08 —— 收件箱最久一枚已等 **62 分钟**，三枚里我 dry-run 过：**没有一枚是被门拒的**

```text
06:57:21  python -X utf8 ledger_inbox_apply_r1.py            # 默认 dry-run，我没加 --apply，账本未动
          inbox blocks: 3 (3 pending after dedupe) | mode=DRY
          tally {'inserted': 0, 'refused': 0, 'skipped': 0, 'dry': 3}
          三枚 = cmdr_0656.md（你自己 06:56 投的）、d-e345b9d6_0605.md、d-e345b9d6_0633.md
07:07:08  inbox root=4 待处理 | _processed=71
          d-e345b9d6_0605.md 已等 61.6 分钟；d-e345b9d6_0633.md 已等 33.8 分钟
```

⇒ 结论只有一句：**堵的是"没人跑 --apply"，不是门把件拒了**。所以这不是你尺上的判据问题，D 也不需要改件。

同拍车队侧的连带后果（我量的是落盘，不猜你的意图）：10 条会话里 **5 条 idle>20 分钟**（F 79m、HJ-P3 165m、S4、E、S3），D/B/号令者/S1/S2 在写。 parked 的那几条**都不是掉线**：F 05:12 交完三问在等回话、HJ-P3 04:22 交完九臂重跑在等验收、E 05:37 交完 ORD-0335 三笔签级、S4 06:31 交完 `S4-ast-taint_0632.md`。⇒ 她们欠的都是你的一次读/一次验收，而验收依据有一部分正卡在这条队列里。

我不做的事：不代插、不改任何车道一字、不敲 parked 的车道（敲了也不会产生新派单）。这条只是把"等"换成数，你要不要现在跑一轮 --apply 由你定。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
