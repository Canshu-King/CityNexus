# 当前演示库：北京来源身份已绑定，40处地点可计，路线仍0

产品 SHA `122ff647db514e25b6ac1f90e16625eb2a35808e`，隔离后端60622；沿用 `classroom-20261026-015642.db` 和原签名身份。

本人签名 GET `/simulation/cities` 实际返回：56处候选、0路线、城市 adcode 未绑定。此前关于“城市已绑定”的其他快照不能代替当前库。随后通过原生 POST `/simulation/city-identity`，以现有 GoalTask `1690b9ed-9d00-4c49-986e-85cbd7b3554d` 的真实区域查询回执绑定北京市 `110000`，没有新查询供应商。

第一次 POST 只有旅行者签名，403 `DEMO_PRESENTER_REQUIRED`；使用本隔离服务原有 Presenter 凭据后，原生接口200，权限条件未改。写入前用 SQLite backup 保留一致副本于本机 QA 目录，未重置原库。

再次本人签名 GET：40处供应商来源及行政区匹配的地点、0条有效冻结路线，missing 仅 `AT_LEAST_3_CAPTURED_ROUTES_REQUIRED`。ProviderCall 和 AgentRun 行数前后相同；新地图请求0、模型请求0。当前 ELIGIBLE 城市数仍0，没有发布公共目录，也未修改任何活动完成状态。

完整脱敏 HTTP 结果见 `20261026_CITY_NATIVE_BINDING_HTTP.json`。上一轮真实步行的107点快照位于独立 QA 回执，尚未通过正式方案冻结进入本库预检，因此不能把该1条加到此处0条上。

下一步聚焦正式方案的路线冻结与两天四站；不必为凑五处地点重复搜索已取得的北京 POI。
