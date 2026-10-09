### SESSION=494abfd7 · 晨报骨架已建立（`D:\moodle\MORNING_ANYWHERE_SUNRISE_REPORT.md`，15 项 + 每格三档标注）；复现协议已拉回备用；**并记下一条容易冲昏头的收窄：贡山复现成功 ≠ P7 成立** @02:2x

`STATUS: REPORT-SPINE-CREATED | 协议 `ORD_0192_REPRODUCTION_PROTOCOL.md`（`cab91a25`，4,839 B，blob 与磁盘一致，存 `live_checks/`）| 仲裁 5765348482 ①②③⑤⑦ 全部执行 |`

**报告里现在就有的一刀**：第 5 项与第 9 项各拆两格——
- `树内已改（我复跑：19/19、四类 typed 24/24）`
- `用户可见未改（部署后端仍 53fe8e8；我对部署侧直接 GET 到 `unresolved:8fccf2bbf123e3df` + `CHOOSE_ANOTHER_DESTINATION`）`
⇒ 明早任何人看这份报告，**不可能把"测试绿"误读成"手机好了"**。

**仲裁 ③ 的收窄已写进报告第 11/12 项与唤醒流程**：
```text
ORD-0192_GONGSHAN = REPRODUCED   与   P7_RESOLVER_INTEGRATED = false
```
两者**同时成立并不矛盾**：B 的 E2E 可以证明某条 provider→hydration→planner 链真跑到 mobility blocker，
但权威产品路径仍未完成 `B typed result → C product truth` 的正式接线。
⇒ 所以：**不因贡山复现而提前唤醒 Harness / P1–P4**；**不因 step 13 达成而说用户可见 Anywhere 已打通**；
   P7 只由 C 的**七条件 + exact-SHA 行为复验**决定（口径 v2，grep/import 只算辅助证据）。

**报告目前标注**（会随车道交付继续更新）：`REPRODUCED` 7 格 · `FORMAT_CHECKED` 2 格 · `SELF_REPORTED` 4 格 · `PENDING` 6 处（含最终候选那一次全量，夜里不提前跑）。
**最后一节专门记我自己今夜的工具类错误**（6 类，含"按名字找→假缺失"三次、单次读数当稳定、总线回读 URL 写错、写入器查重缺陷、注记被重写吞掉、探针污染自己的档案）——统一归到仲裁那句：**观察失败 ≠ 目标不存在**。

status: 晨报骨架 + 复现协议到位；P7 与 Mission A 解耦已写死（复现成功不解锁唤醒）；今夜工具类错误单独成节，避免被好结果掩盖
