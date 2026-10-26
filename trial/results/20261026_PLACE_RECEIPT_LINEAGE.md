# 地点搜索回执贯通到正式地点

基线：`ff5bbce3a5a523f32e195dabe338a72d5b53a811`，独立 Codex checkout，PR #55。

此前 GoalTask 的高德搜索已经落 ProviderCall，但 `_store_places` 丢掉回执 ID 和请求行政区码，正式地点无法直接追溯那一次搜索。现在研究地点保留 `provider_call_id`、`requested_adcode` 和供应商实际 `adcode`；转换为 RealPlaceCandidate / Place 时，将匹配的回执写入 `metadata.source_receipt`。

回执来自同一 Journey 的服务端 GoalTask 研究记录，并核对 ProviderCall 来源、操作、成功状态、请求行政区码和响应地点对象。实际行政区码来自响应；缺值或错配时不写 VERIFIED。既有历史记录不回填，预检和用户授权条件沿用原实现。

## 根会话串行验收

工作目录：`D:/moodle/_codex_workers/citynexus-sandbox-security-20261025/backend`。解释器：`D:/moodle/CityNexus/backend/.venv/Scripts/python.exe`；pytest conftest 为每次运行创建独立临时 SQLite，未使用课堂数据库。

```powershell
$env:PYTHONPATH='.'
& 'D:/moodle/CityNexus/backend/.venv/Scripts/python.exe' -m pytest -q tests/test_issue49_place_receipt_lineage.py tests/test_goal_amap.py --junitxml='C:/Users/仓鼠王/cn51/classroom-20261026-qa/place-receipt-lineage.xml'
# 16 passed, 4 warnings, exit 0

& 'D:/moodle/CityNexus/backend/.venv/Scripts/python.exe' -m pytest -q tests/test_qoder_goal_place_identity_r1.py tests/test_issue47_city_and_native.py --junitxml='C:/Users/仓鼠王/cn51/classroom-20261026-qa/place-identity-compatibility.xml'
# 14 passed, 4 warnings, exit 0
```

新增测试含本人签名 GoalTask → discover_places → ProviderCall → 研究地点 → 正式地点的完整转换，以及错误对象、失败回执、其他操作/来源、城市码错配、缺实际码、缺回执和其他 Journey 的分支。模型及供应商均为声明式测试替身；这两次验收没有发真实供应商或模型请求。

产品文件预映像：`D:/moodle/_backups/city-supply-issue49-place-receipt-lineage-20261026/backend/app/agent/`。现有手机 UI 未提交修改保留。

此增量为后续新搜索提供来源关联。当前服务仍加载 `26cf9e2869`；没有凭此新增真实 POI、发布城市目录或完成四站。真实路线几何的上一笔证据见 `20261026_ROUTE_GEOMETRY.md`。
