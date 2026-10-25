# 晚起、预约保留与整份草稿保存

用户场景：情侣第二天想晚起，上午 11 点后再出门；已有预约不能被默默改掉；改晚餐或备注之后，刷新仍应保留之前商量好的条件。

产品增量：

- replace_draft_slots 可保存指定日期/时段的 start_not_before（HH:MM），其他日期和时段不变；模型工具 schema 与服务端均校验时间。
- 同时段已保护活动早于该时间时，返回 NEEDS_USER_CHOICE 和活动名、时间、日期，草稿保持原样，Agent 可据此询问旅行者。
- prepare-plan 在创建候选之前检查具体时刻，不能把 11 点后的条件只写在备注却准备成 9 点；已保护标记传入候选活动，保留锁定事实。
- 签名 PUT 的整份 USER 保存保留服务器现有 date_constraints 及预约标记，允许编辑其它自由活动；省略或移动预约返回具名冲突。新传入的 booking/locked 标记不能伪造原有预约。
- 只有 locked 标记、没有预约 ID 的活动在原样保存时恰好保留一份，不重复插入；revision/CAS 继续生效。

根会话验收：

- 新日期/整份保存测试 + 现有 goal_draft_patch、goal_preparation、day_rhythm：39 passed，exit0，5.28 秒。
- 实际 FastAPI TestClient HTTP：匿名401、非成员403、本人 PUT200、GET刷新保留约束与预约；移动预约409，随后GET仍是原保存值。1 passed，exit0，2.89 秒。
- SQLite 与 JUnit：C:/Users/仓鼠王/cn51/classroom-20261026-qa/date-constraints.*、date-http.*；各套使用独立夹具库，无真实 provider/model 请求。

这证明后端工具、保存和准备链路；预约是明确标为 TEST_FIXTURE 的测试数据，未进行购买或真实预订。尚待真实手机尺寸页面与 Agent 对话验收，不将此报告列为 USER_VERIFIED。已有 Guardian 现场副本另有独立 run，不能混成同一条连续演示证据。
