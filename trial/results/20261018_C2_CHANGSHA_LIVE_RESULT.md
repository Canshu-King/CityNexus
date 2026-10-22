# C2 长沙真实地点搜索结果

- 日期：2026-10-18（本地时间）
- 产品仓库：`Canshu-King/CityNexus`
- 分支：`design/revolution-mobile-first-v1`
- 验收代码 HEAD：`16652d32ca53fe0c07dc9330727aa0c7f7808f2c`
- 客户端：Chrome-use，390 × 844 浏览器视口
- 判定：`PARTIAL`；长沙本轮未完成双站保存和 GO。

## 实际操作

1. 从 Revolution 页面提交“长沙市”，服务器创建签名旅客会话和 DRAFT 行程，两个创建请求均返回 HTTP 201。
2. Nominatim 本轮不可用一次；页面提供 Photon 备用城市搜索。Photon 返回长沙市候选，选择城市后继续。
3. 搜索“公园和绿地”，Photon 返回 HTTP 200，但原始 `features` 数量为 0。
4. 改搜“咖啡馆”，Photon 返回 HTTP 200，原始 `features` 数量仍为 0。
5. 两次 POI 响应的返回数和本地拒绝数均为 0。没有候选地点可供选择，因此本轮没有保存双站 Pocket Walk、执行 GO 或验证刷新恢复。

## AI 与服务器行程轨迹

本轮没有发送 AI 请求。隔离服务健康状态显示 `ai=disabled`、`AI_STATE=CONFIGURED_UNVERIFIED`；隔离数据库中没有可用于这轮验收的签名 ACTIVE 行程或 AgentRun。因此没有 Hermes 工具调用或服务端持久化轨迹可报告。

此前宁波的真实地点闭环属于另一轮独立会话，不计入本轮长沙结果。旧 Overpass 502、其他城市或测试夹具也不计入本轮。

## 代码变更与测试

将 Photon 请求默认超时从 3 秒提高到 5 秒，与适配器的最大超时保持一致。聚焦测试 `uv run --project . pytest tests/test_photon_poi_adapter.py -q` 为 24 项通过。长沙两次真实响应约 0.6 秒即返回空结果；因此这个超时调整没有解决本轮空结果，也不作为空结果原因的证据。

## 结论

长沙城市解析和签名 DRAFT 创建已实测；Photon 的两类 POI 查询都拿到 HTTP 200，但服务端原始响应没有地点。当前证据无法判断该地点中心或公共数据源为何返回空结果。本轮停止继续外部查询，没有用模拟地点补足结果。

下一次要完成 P0，需要在新的真实城市或地点类别上取得两个合格 POI，再按双站保存 → GO → 刷新恢复继续；AI 轨迹应在真实签名 ACTIVE 行程存在后单独验证。
