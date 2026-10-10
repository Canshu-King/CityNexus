## commander 重启恢复 @2026-09-22T16:50+08 —— 电脑重启：预览链按序重建并端到端验证；用户数据零变化；**12 条车道全部被重启打成 cold，正在逐个唤醒**

### ① 现场勘查（重启后第一手读数，不是回忆）

```text
16:47:46 +0800   本机钟
监听端口          :4781 / :4782 / :8693 全部无监听（重启清空了整条链）
进程              cloudflared 0 个；uvicorn 0 个；只剩 Qoder/Codex/Playwright 自己的 node
产物              线上 dist 还在，index.html 仍引用 assets/index-BCF4ptyk.js（8 个 asset 文件＝新包＋上一代，没被重启吃掉）
用户库(只读)      journeys 3 / travelers 3 / plan_versions 19 / commitments 1 / bookings 1  ← 与重启前 16:29 读数逐项相同
```

### ② 重建（严格按 09-21 定下的顺序，一步一验）

| 步 | 动作 | 验证读数 |
|---|---|---|
| 1 | `:8693` uvicorn（gate 树，`_live.db`，`CITYNEXUS_DEMO_MODE=true`，`CITYNEXUS_AI_ENABLED=true`） | `/api/v1/health` **200**，`status=ok / database=ok / ai=enabled` |
| 2 | `:4781` vite preview（`--outDir _qoder_preview_20260920/dist`，`CITYNEXUS_BACKEND_PORT=8693`） | `/` **200**，bundle = `assets/index-BCF4ptyk.js` |
| 3 | `:4782` auth proxy（`_qoder_recovery_20260919/raw/preview_auth_proxy.py`） | 监听成立，日志 `listening 127.0.0.1:4782 -> http://127.0.0.1:4781` |
| 4 | cloudflared quick tunnel | 新 URL `https://buyer-festivals-jeans-photographers.trycloudflare.com`（旧 URL 随重启死，已写 `tunnel_url.txt.dead_1648`） |

**端到端（走新隧道，不是走 localhost）**：

```text
鉴权 GET /api/v1/health   -> 200  {"status":"ok","database":"ok","ai":"enabled"}
鉴权 GET /                -> 200  bundle = assets/index-BCF4ptyk.js
匿名 GET /api/v1/demo/scene -> 401 Basic realm="CityNexus preview"   （护栏在位）
匿名 GET /                -> 401（两次复测同）
鉴权 POST /api/v1/demo/reset -> 403 PREVIEW_GUARDED                  （R13 护栏在位）
```

⚠ 一条**我自己量具的错**，先报免得别人跟着踩：第一次匿名探测拿到 **502**，我差点写成"护栏异常"；原因是那一刻隧道刚起、回源还没就绪，**502 是 Cloudflare 侧的上游未就绪，不是我们代理的判定**。复测两次都稳定 401。⇒ 规则：**隧道刚建好的头 30 秒内不要拿状态码下结论**，等两次一致再说。

### ③ 车道现状（16:49 `list_chat_sessions`）

**重启把 12 条车道全部打成 cold**（除我 `494abfd7` 与一个无关会话 `23656ce5` 是 running）。全部需要唤醒，我按"重启后第一条消息"逐条发窄定位（各一行、不含任务正文，遵守 LANE_PROTOCOL）：
`8c66aa92` C（欠 ORD-0217 与 ORD-0213）｜`8ccd71d8` F（ORD-0210 机制）｜`c01d72a3` B（四条红＋g10）｜`e345b9d6` D（ORD-0216 四件）｜`d2305848` 红队｜`d291c9dc` HARNESS｜`1a986a24` HJ-P1｜`4e974ae5` HJ-P4｜`aad2d1f2` HJ-P3｜`d4b04a0f` HJ-P2｜`9baacb24` HERMES｜`5ea3bedc` LAB。

### ④ 现场冻结

working tip `56d20ec`；`c8472fd`（F 的 ORD-0214 门）在 F 分支未合；reference tip `c0d7e3d`；`P7=false`；`demo/reset` 从未触发；0 次 provider 出网；那把 key 仍未轮换（只有用户能做）。
