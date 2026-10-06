## commander 亲测 @2026-09-23T03:27+08 —— 在**用户那条链**上独立抽验 HJ-P4 的矩阵（place 轴成立）；并补一条仪器口径

### ① 抽验（走真隧道、用户面后端 pinned 那棵、preview 库）

```text
GET /api/v1/places?city_code=CN-BEIJING   -> 200  8 条
GET /api/v1/places?city_code=CNX-DEMO     -> 200  8 条（place-city-park …）
GET /api/v1/places?city_code=CN-HANGZHOU  -> 200  0 条
GET /api/v1/places?city_code=CN-TOKYO     -> 200  0 条
GET /api/v1/places?city_code=CN-FUZHOU    -> 200  0 条
GET /api/v1/places?city_code=CN-苏州       -> 200  0 条
GET /api/v1/places?city_code=CN-SUZHOU    -> 200  0 条
```
⇒ **HJ-P4 的矩阵在"place 行数"这根轴上，于用户面成立**：只有北京与演示城有行，其余为 0。
### ② 我只验了一半，说清哪一半
`4e974ae5` 另报的"3 座城服务器连身份都给不出（`NO_CANONICAL_IDENTITY` / `UNAVAILABLE`）"走的是**另一根轴**（capability 路由），**我这轮没有探**，所以那句仍只算它一侧的读数。⇒ 抽验结论限定为：**place 轴＝已独立确认；capability 身份轴＝未复核**。
### ③ 一条仪器口径
`GET /places?city_code=<未知码>` **返回 200 + 空列表**，不是 404/422 ⇒ **"拿不到数据"在这条路由上表现为 200-empty，排查时别把 200 当"有数据"**。
