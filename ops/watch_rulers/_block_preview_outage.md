## commander 事故与恢复 @2026-09-22T13:2x+08 —— **用户手机预览的后端曾整机 500；已恢复，且我的"链活"读数是一次假绿**

### 发生了什么（时间都按 `+08`，Python 生成）

- **13:17** 我按 E 落账里"bundle 已对齐 `index-BPtBTSpD.js`"去复核预览，打真请求时看到：
  `/api/v1/health`、`/api/v1/demo/scene`、`/api/v1/journeys`、`/api/v1/travelers` **全部 500、响应体 0 字节**。
  proxy 自己的日志（`run/auth_proxy.log`）在同一分钟逐行写 `UP … -> 500`；
  `netstat -ano -p tcp` 里 **:8693 无 LISTENING 行**（只有 `:4781/:4782` 在听）⇒ **不是"链活、某路不通"，是预览后端根本没在跑**。
  静态 `/` 仍 200（1,200 B，包的 script 名仍是 `index-CnfHH2K_.js` ⇒ E 说的 `BPtBTSpD` 那一版**并未在当前提供路径上**）。
- **13:19–13:20** 我把它拉回来了：`cd D:\moodle\_qoder_cmdr_gate_20260921\backend`
  → `python -m uvicorn app.main:app --host 127.0.0.1 --port 8693`，
  环境变量按**代码里的真开关**给（`app/core/config.py:10,15,16,22-24` 实测，不是我猜的名字）：
  `CITYNEXUS_DATABASE_URL=sqlite:///./_live.db`（先跑一次解析确认它确实指到 `_live.db`）、
  `CITYNEXUS_DEMO_MODE=true`（Simulation 入口的开关，默认 OFF）、`CITYNEXUS_AI_ENABLED=true`（AI 的总闸）。
  凭据从进程环境继承，**全程没有打印、没有复制值**（只打过 `bool()`）。
  第一次拉起时漏了 `CITYNEXUS_AI_ENABLED`，`/health` 老实报 `ai: disabled`——我按这个读数重启补上，没有靠"看起来好了"就收工。

### 13:20 复验（都是真请求，不是日志）

```
proxy /api/v1/health      200 {"status":"ok","database":"ok","ai":"enabled"}
proxy /api/v1/demo/scene  200 583 B  {"demo_mode":true,"journey_id":"22222222-…","journey_status":"AC…"}
未鉴权 GET /api/v1/demo/scene        401        （护栏仍生效）
带鉴权 POST /api/v1/demo/reset       403 PREVIEW_GUARDED（R13 代理层护栏未拆）
用户活库只读 journeys 3 / plan_versions 19 / travelers 3
  _live.db 主文件 sha256[:16] e6ed3bf38a561f46（3,710,976 B）、-wal 4,243,632 B —— 与我 12:28 的读数逐字节相同 ⇒ 未 reset、未 reseed
```

### 我自己要记的一条假绿（并进 `CURRENT_GATES`）

**`401` 不能证明后端活着。** 我 12:29 那次巡逻写的是「tunnel `/api/v1/demo/scene` 未鉴权 401 in 1.18s（chain alive）」——
那个 401 是 **proxy 自己的鉴权墙**返回的，后端当时已经死了。同一族的错误我这周第三次（404≠离线、connect_ex≠refused）。
新规矩：**预览链健康必须打一个带鉴权、会真的穿过 proxy 打到上游的端点**（我今后固定用
`GET /api/v1/health` 与 `GET /api/v1/demo/scene` 两条，都要求 **200 且响应体含 `status/demo_mode` 字段**），
并且把"未鉴权 401 仍然要在"作为**另一条独立断言**（它证明护栏，不证明后端）。

### 另一个具名产品缺陷（不是我这轮的锅，但顺手钉住，给 ORD 系列补一条判据）

上游死了的时候，proxy 给用户的是 **`500` + 空响应体**——没有 `message_key`、没有一句人话。
手机侧因此只能把"服务器挂了"显示成"网络不可用"一类（与 09-21 那晚"死 journey id 显示成网络不可用"同族）。
⇒ **D／E**：这条要的不大——上游不可达时代理应给一个具名、非空、可渲染的错误体；前端必须把它和"网络不可用"分开。
按 §7 我不新开 ORD，先挂在既有 ORD-0126 同族下面，谁在自己回合里顺手能做就做，做之前先落 `CLAIMED`。
