# 从真实高德折线到移动快照

## 已实现的产品路径

高德步行/公交结果 → 研究路线保存 → 路线冻结 → `StoredAmapRoutes.estimate()` → 原生 MobilitySnapshot 的 WGS84 `route_geometry`。来源调用 ID、原始 GCJ02 分段、采集时间、字段路径、转换与反向复用标记都保留。旧记录没有几何时仍为空；城市 preflight 的来源门槛未修改。

真实 v5 公交响应的 `polyline` 是 `{polyline:"坐标串"}`，旧 parser 只认字符串，导致有折线却解析为零段。现兼容 v5 对象与原字符串形式；同一公交段中的多条 buslines 是替代线路，选第一条供应商返回线路并保留替代元数据，不串成环。高德官方文档的可选字段说明见[路径规划2.0](https://developer.amap.com/api/webservice/guide/api/newroute)。

实测步行相邻段坐标有最多 0.7007 米接缝差；按明确 `PROVIDER_SEGMENT_JUNCTION_WITHIN_1M` 规则接续，保留原采样点，仅去掉完全重复的端点，并记录最大接缝距离与 `inserted_coordinate_count=0`。超过一米的缺段不补直线，公交约28米断口仍 BLOCKED。该处理不等于拿起终点连线替代路线。

## 本轮三个真实请求与离线回放

1. 天安门广场→天坛，公交，单次 HTTP200，3237秒/4179米，调用 `cf822bd9-3170-4f20-9328-e31c5b28e4de`。当时 parser 只认字符串，未保留原 segments，不能从这条投影断言供应商没给；失败收据保留，没有重试。
2. 故宫→天安门，另一个地点对的公交单次 HTTP200，3849秒/3477米，调用 `d7aa61d8-80cd-417e-832e-3ef325f6442a`。本次保存公开响应 segments；修复后的离线回放提取25段/125点，仍有真实断口，`BLOCKED_GEOMETRY_DISCONNECTED`。没有重发此请求。
3. 天安门→故宫，步行单次 HTTP200，2708秒/3385米，调用 `eca5e4c6-01f5-432c-ad76-011528661c55`。28个供应商分段、114个分段采样点经已说明的接缝处理与 GCJ02→WGS84 转换，原生快照捕获107个路线点、`geometry_provider=amap-web-service`、`fact_quality=LIVE_PROVIDER_CAPTURE`。快照创建来自保存的真实响应的离线回放，不是又一次 HTTP 请求。

这证明原生可捕获真实几何事实从0到1。**尚未把这份新事实发布到课堂城市目录**，因此不能称北京已 ELIGIBLE，更不代表三城/两 seed 或两天四站已完成。三次请求只发送公开坐标/城市和所需出行时间，key 只在授权隔离进程读取，未进入源码/回执。

附件：

- [第一次公交投影](20261026_TRANSIT_GEOMETRY_FIRST.json)、[第二次公交投影](20261026_TRANSIT_GEOMETRY_SECOND.json)
- [第二次原始公开分段](20261026_TRANSIT_PUBLIC_SEGMENTS.json)、[公交离线回放](20261026_TRANSIT_GEOMETRY_REPLAY.json)
- [步行回放说明](20261026_WALKING_GEOMETRY_REPLAY.json)、[原生快照](20261026_WALKING_GEOMETRY_SNAPSHOT.json)
- [已接受真实链的只读新投影](20261026_ACCEPTED_REAL_CHAIN_PROJECTION.json)，守护产品SHA `96ffe4649463e64f878706380f147339ecfe86a7`

## 根串行验证

`test_issue49_amap_transit_geometry.py`、`test_issue49_goal_route_geometry.py`、`test_mobile_amap_provider.py`、`test_goal_amap.py`、`test_qoder_amap_transit_provider_r1.py`：**34/34，exit0**，JUnit `C:/Users/仓鼠王/cn51/classroom-20261026-qa/route-geometry-final.xml`。

冻结链另运行 `test_goal_route_freeze.py` 加两新增几何文件：**23/23，exit0**，JUnit `route-freeze-geometry-verified.xml`。其首次有1项测试将“未配置key”误当“已配置但无路线”；为该已有测量替身显式配置无效测试占位值，网络入口仍完全替换，原业务断言保留。两组包含重叠用例，不相加。CI加入原高德 parser、GoalTask 与冻结链回归。

下一步：将新真实路线走既有原生冻结/目录发布路径，补足本 Journey 的至少五处来源地点和三条可计边；保留第四地点与活动的真实缺口。没有直接写 ACTIVE、没有复制北京成三城、没有替 Qoder 修改界面或启动器。
