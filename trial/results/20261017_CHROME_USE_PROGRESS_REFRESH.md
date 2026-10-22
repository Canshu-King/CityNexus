# Chrome-use 真人式复测：第一站完成后的刷新恢复

- 时间：2026-10-17 21:16–21:20（Asia/Shanghai）
- PR：#23，测试时分支 head 为 `869a1c9e2c5291e913ced247e6381837ce186092`；产品代码来自 `bf00dc739ef6e9b5ea6690a3416534fc8b2a995f`。
- 环境：现有隔离演示页 `http://127.0.0.1:14176/revolution`，Chrome-use 真实 Chrome 会话，390×844 手机布局。
- 范围：复测已保存 Pocket Walk 的 GO 进度更新与刷新恢复；未重发城市地点、模型或其他外部请求。

## 操作与结果

1. 打开已有两站 GO 路线：A Giraffe Coffee&Cacao、Puzzle Coffee。见 [操作前截图](assets/chrome-use-20261017/step-00-go-before.png)。
2. 聚焦“我完成了第一站 →”后按 Enter。Chrome-use 的语义 click RPC 返回 EOF，页面没有变化；键盘激活后页面显示“进度已保存”，并改为“前往第二站 →”。见 [保存进度截图](assets/chrome-use-20261017/step-01-first-stop-complete.png)。
3. 刷新页面。页面没有恢复路线，转回探索页并显示“旧行程无法恢复，原记录仍保存在服务器。”
4. 打开“行程”页，看到空列表；回到“探索”仍显示恢复失败。失败页见 [刷新后截图](assets/chrome-use-20261017/step-02-refresh-restore-failed.png)，完整操作见 [Chrome 录像](assets/chrome-use-20261017/p0-progress-retest.webm)。

## 持久化核对

对本次隔离 SQLite 数据库执行只读计数：存在 2 条未删除 DRAFT 行程、1 条 member draft Pocket Walk，且有 1 条 `FIRST_STOP_DONE_SELF_REPORTED / USER_REPORTED_PROGRESS` 进度记录。服务端进度已保存，页面恢复链路仍失败；没有删除或新建行程。

## 结论

**失败：** 用户完成第一站后，进度显示已保存；刷新后路线未恢复，行程页也未显示这条草稿散步。当前证据定位到手机端草稿路线的刷新恢复链路，根因尚未确认。重新打开页面没有发起重复地点或模型请求。

本次只覆盖 Chrome 桌面上的 390×844 手机布局，不是 Android 真机验收；行程仍为 DRAFT，未产生 ACTIVE Journey 或 AgentRun。

## 证据 SHA-256

- `step-00-go-before.png`: `F368ED20D04650EA27B45CC3D469B836C56A78E27373ED1CE2EC656EBEA3B077`
- `step-01-first-stop-complete.png`: `B1219B5500AC9416BB871D5D8F787AE8044E9F190E0B1269E447416902585306`
- `step-02-refresh-restore-failed.png`: `8538A15F08EF45945636B48E9542784F34157270E79059303A6CA9197148261E`
- `p0-progress-retest.webm`: `F4B2A3BF130E795D252B1ED82B81D039A4D37B139B9CE61791C4CDB46F3D6013`