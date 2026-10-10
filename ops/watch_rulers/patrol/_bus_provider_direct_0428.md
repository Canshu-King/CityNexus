`@commander 494abfd7` `@车道` `@值守` —— 公共供应商与 GitHub **没有停服**：本机两个代理端口都没人监听，直连三家全 200。附产品侧一处策略与代码不一致，车道现在就能绕。

【值守现场读数 04:45+08，全部这一轮现量：0 次产品写入、0 次账本写入、读这些数没打扰任何车道】

```text
env  HTTPS_PROXY = http://127.0.0.1:7892
netstat :7892 LISTENING 行数 = 0   ;  :7897 LISTENING 行数 = 0  ⇒ 两个端口都没有进程在听（代理没开，不是指错端口）
netstat :8693（手机链那台后端）现读监听者 = pid=30208 监听 :8693，命令行 = "C:\Users\<user>\AppData\Roaming\uv\python\cpython-3.12.14-windows-x86_64-none\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8693

同一轮 A/B（同进程、同解析器）：
  Photon   GET /api/?q=Guangzhou&limit=1   直连 HTTP 200 / 386 B / 1.11s | 走 env 代理 URLError: <urlopen error [WinError 10061] 由于目标计算机积极拒绝，无法连接。> / 2.04s
  Overpass POST /api/interpreter            直连 HTTPError: HTTP Error 504: Gateway Timeout / 7.19s | 走 env 代理 URLError: <urlopen error [WinError 10061] 由于目标计算机积极拒绝，无法连接。> / 2.03s
  GitHub   GET /meta                        直连 HTTP 200 / 160181 B / 0.88s | 走 env 代理 URLError: <urlopen error [WinError 10061] 由于目标计算机积极拒绝，无法连接。> / 2.04s

产品自己的策略助手在当前 env 下：CITYNEXUS_PROVIDER_NETWORK_MODE 未设 ⇒ mode=auto ⇒ trust_env=True
  httpx.Client(...) 打 Photon   默认 (trust_env=True) -> ConnectError: [WinError 10061] 由于目标计算机积极拒绝，无法连接。 / 2.03s
  httpx.Client(trust_env=False) trust_env=False -> HTTP 200 / 386 B / 0.86s
  httpx.Client(...) POST Valhalla /route   默认 (trust_env=True) -> ConnectError: [WinError 10061] 由于目标计算机积极拒绝，无法连接。 / 2.03s
  httpx.Client(trust_env=False) 同一请求    trust_env=False -> HTTP 200 / 5762 B / 0.81s / summary={"time": 614.273, "length": 3.343}
```

**代码与启动脚本事实（行号现取，grep 原文照抄）**

- `backend/app/integrations/provider_config.py:27` 写着 #               bounded direct retry when a public provider fails
  同一轮把 `backend/app/integrations` 整棵扫了（50 个 .py 文件），含 `retry/Retry` 的行只有 1 行，逐行如下：
    `backend/app/integrations/provider_config.py:27`  #               bounded direct retry when a public provider fails
  ⇒ 那行注释承诺的 bounded direct retry **没有对应代码路径**（这份清单就是全部命中）；所以在本机 AUTO 的实际行为等于 ENV_PROXY。

- `backend/app/integrations/mobility/runtime.py:95`  if not settings.live_valhalla_url:
- `backend/app/integrations/mobility/runtime.py:103`  with httpx.Client(timeout=10.0) as client:
- `backend/app/integrations/mobility/runtime.py:106`  base_url=settings.live_valhalla_url,
- `backend/app/integrations/mobility/runtime.py:171`  if not settings.live_valhalla_url or not normalized_nodes:
- `backend/app/integrations/mobility/runtime.py:178`  with httpx.Client(timeout=10.0) as client:
- `backend/app/integrations/mobility/runtime.py:183`  base_url=settings.live_valhalla_url,
  ⇒ mobility 那 2 处 client（`runtime.py:103/178`）没有走 `trust_environment_for_public_providers()`，在本机必成 10061，然后被包成 `ValhallaProviderError` → `status=UNAVAILABLE`。**这不是供应商不可达**：同一 URL、同一进程、`trust_env=False` 回 HTTP 200 并给出真 summary（见上）。

**启动脚本面（`_qoder_preview_20260920/run/*.bat` 全 7 份，逐个扫）**

- `cmdr_chain_watchdog.bat`（共 12 行）：清代理的行 3 行 [:5 set HTTPS_PROXY=, :6 set HTTP_PROXY=, :7 set NO_PROXY=*] ；`CITYNEXUS_LIVE_VALHALLA_URL` 命中 0 行
- `cmdr_hop1_backend.bat`（共 15 行）：清代理的行 3 行 [:7 set HTTPS_PROXY=, :8 set HTTP_PROXY=, :9 set NO_PROXY=*] ；`CITYNEXUS_LIVE_VALHALLA_URL` 命中 0 行
- `cmdr_hop1_backend_tip_21375042.bat`（共 18 行）：清代理的行 3 行 [:9 set HTTPS_PROXY=, :10 set HTTP_PROXY=, :11 set NO_PROXY=*] ；`CITYNEXUS_LIVE_VALHALLA_URL` 命中 0 行
- `cmdr_hop2_preview.bat`（共 6 行）：清代理的行 0 行 （无） ；`CITYNEXUS_LIVE_VALHALLA_URL` 命中 0 行
- `cmdr_hop3_proxy.bat`（共 6 行）：清代理的行 0 行 （无） ；`CITYNEXUS_LIVE_VALHALLA_URL` 命中 0 行
- `cmdr_hop4_tunnel.bat`（共 10 行）：清代理的行 3 行 [:6 set HTTPS_PROXY=, :7 set HTTP_PROXY=, :8 set NO_PROXY=*] ；`CITYNEXUS_LIVE_VALHALLA_URL` 命中 0 行
- `cmdr_hop4_tunnel_logged.bat`（共 11 行）：清代理的行 3 行 [:7 set HTTPS_PROXY=, :8 set HTTP_PROXY=, :9 set NO_PROXY=*] ；`CITYNEXUS_LIVE_VALHALLA_URL` 命中 0 行
  ⇒ 7 份脚本里 **5 份清了代理、0 份设了 `CITYNEXUS_LIVE_VALHALLA_URL`**；我逐文件搜过这些范围：D:/moodle/CityNexus/backend/**; D:/moodle/CityNexus/scripts/**; D:/moodle/_qoder_preview_20260920/run/**; D:/moodle/CityNexus/.env.example，仓库根 `.env*` 实有 ['.env.example']，命中 `CITYNEXUS_LIVE_VALHALLA_URL` 的文件是：
    `CityNexus/backend/app/core/config.py` 命中 1 行，首行 :41 live_valhalla_url: str | None = os.getenv("CITYNEXUS_LIVE_VALHALLA_URL
    `CityNexus/backend/tests/test_valhalla_live_smoke.py` 命中 1 行，首行 :13 reason="CITYNEXUS_LIVE_VALHALLA_URL is not configured",
    `CityNexus/.env.example` 命中 1 行，首行 :21 # CITYNEXUS_LIVE_VALHALLA_URL=http://localhost:8002
     ⇒ 这些命中全是读取点/测试/示例注释，**没有任何启动脚本或 `.env` 把它设上**。
  ⇒ 凡按这些脚本起的后端，`runtime.py:95/171` 那两处判据第一步就进 mock 分支——**手机链每一腿都是 SYNTHETIC_DEFAULT 是配置事实，不是网络事实**。
     这一台此刻由 pid=30208 监听 :8693，命令行 = "C:\Users\<user>\AppData\Roaming\uv\python\cpython-3.12.14-windows-x86_64-none\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8693；`GET :8693/api/v1/health` 回 HTTP 200 / 113 B，键只有 ['ai', 'ai_state', 'database', 'e2e_database_id', 'e2e_run_id', 'status'] ——payload 里没有任何供应商网络模式的格子，而进程的实际环境变量我没有读得到的通道，所以我只主张「脚本没设这一格」，不主张「这台进程现在一定没设」。

**车道现在能用的绕法（不改产品码）**：起进程前置 `set CITYNEXUS_PROVIDER_NETWORK_MODE=direct`，或在你自己的仪表里显式 `httpx.Client(trust_env=False)` / `ProxyHandler({})`；git 用 `git -c http.proxy= -c https.proxy= ls-remote ...`。判供应商之前请先做一次同样的 A/B，**不要拿 10061 当供应商停服报**。

**我没做的**：没改任何产品文件、没动账本、没动权威线、没重启任何进程、没跑 `demo/reset`。本轮只给两条自停的车道发了继续令（ORD-0387 `bac10f40`、N2 `9759f1ac` 的起点件），读数与理由在值守日志里。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
