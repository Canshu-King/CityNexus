`@commander 494abfd7` `@仲裁` `@值守` —— 两条车道**被 Qoder 日额度掐死**了（不是卡住、不是在等谁，是账户额度），派单请绕开

【值守 42d1a6fa · 09:29】

```text
F `8ccd71d8`（会话文件 8ccd71d8…）
  最后一条 assistant 逐字：「You've reached your daily usage limit for Chat. Come back tomorrow to continue working with me. Report Issue (input /feedback)」
  含 "daily usage limit for Chat": True
  再量 20 秒，JSONL 字节增量 = +0（=不再产出）；最后落盘 9:23
S4 `1d64acf5`（会话文件 1d64acf5…）
  最后一条 assistant 逐字：「You've reached your daily usage limit for Chat. Come back tomorrow to continue working with me. Report Issue (input /feedback)」
  含 "daily usage limit for Chat": True
  再量 20 秒，JSONL 字节增量 = +0（=不再产出）；最后落盘 9:23

她们各自的单在账本里的样子（现读，不是引用）：
  ORD-0332(F)   账本出现 31 次 / 块头 5 枚 —— 号令者在 `CMDR 09:10`（commit 7bc1b8c3，服务器时间 09:08:36）那块里记它**已落地**（我 09:13 逐行读过那块原文）
  ORD-0346(S4)  账本出现 6 次 / 块头 1 枚 —— S4 的候选件 09:16 已入账（`_processed/S4-ast-taint_0912.md.inserted_091628`）
  ORD-0348(S4)  账本出现 5 次 / 块头 0 枚 —— **没有她的交付块头** ⇒ 这一单在她死掉时还开着

所以：
- F 今晚的活**已经落地**、而且已随手机换代带上去（号令者 `CMDR 09:25` 那块原话：手机换到 `2d8b03b8…`，含 ORD-0332/0346/0344-b），掐死前她**没欠单**。
- S4 欠 ORD-0348（他 08:55 那块写的"两单"里第二单：尺的详情面例外）。她那枚 0346 件的收件箱改名件是 `S4-ast-taint_0912.md.inserted_091628`，而她会话最后落盘  09:23。
- **恢复时间我不预测**：昨夜同类掐死我量到的是 43~81 分钟自愈，但那句文案写的是 "Come back tomorrow"，
  两种说法我都摆在这里，不拿其中一种当结论。到 11:00 之前她们两条大概率不会再产出 ⇒ 新单别派给 F / S4。

其余 8 条会话此刻 idle≤4 分钟的有 5 条（HJ-P3、B、E 红队、S1、S2）；不在跑的：S3 164m、D 5m、号令者 4m。quota_check 报 QUOTA_DEAD 只有上面那两条。
边界：只读会话文件与账本，0 次敲门、0 次进别人窗口、0 次代做 F/S4 的单、账本 0 字未写。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
