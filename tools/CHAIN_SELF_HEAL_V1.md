# CHAIN_SELF_HEAL_V1 — 手机预览链的自恢复入口（ORD-0358）

入口：`node tools/chain_self_heal.mjs [参数]`。一辆链四跳：`:8693` 后端 → `:4781` `vite preview` 服发布根 → `:4782` 鉴权代理 → cloudflared 隧道。以前它靠人记得起哪四层、按什么顺序、带什么参数；16:30 那次断链就是四跳都挂在某个会话自己开的窗口下面，会话一停子进程被一起带走。

## 判"活着"的方式

| 跳 | 探测 | 健康判据 |
| --- | --- | --- |
| backend | `GET http://127.0.0.1:8693/api/v1/health` | 200 **且** `content-type` 含 `application/json` **且**正文里有 `"status":` 字段 |
| static | `GET http://127.0.0.1:4781/` | 200 且字节 > 200 **且**真是 HTML（`<!doctype html>`） |
| auth_proxy | `GET http://127.0.0.1:4782/api/v1/health`（带 Basic） | 同 backend（JSON 判据） |
| tunnel | `GET <隧道址>/api/v1/health`（带 Basic） | 同 backend（JSON 判据） |

**为什么状态码不算数**：这条链上栽过一次——对端没有应用层时，静态服会把 `/api/v1/health` 兜成 `200 + index.html`，"200"于是把"没后端"读成了"活着"。API 腿一律要真是 JSON，静态腿反过来要真是 HTML；两形各判各的，收据里每跳带 `shape`（`api-json` / `html` / `other` / `no-answer`）。

**三种判决，只有第一种是绿**：`CHAIN_HEALTHY`（exit 0，四腿俱在且全健康）、`STATIC_SIDE_HEALTHY_API_NOT_CARRIED`（exit 2，只在我这样的隔离实例上出现：隧道指向静态服、这条实例根本没有 API 腿 ⇒ 具名，不许当通过）、`CHAIN_UNHEALTHY`（exit 3）。

**隧道那条腿分三层判**（字段 `tunnel_probe.shape` 与 `verdict_reason.tunnel_edge_state`）：连不上 = `no-answer`；边缘代答（还没绑上连接器，实测过 502/503/530 一形）= `edge_only_or_no_answer`；对端真答 = `origin_answered`。对端真答里还有一形要单独点名：`origin-refused-host` —— vite 自己有 Host 白名单，仓库里 `allowedHosts` 全文 0 命中，所以直接拿隧道域名去敲静态服必然 `403 + Blocked request. This host (…)`。这**不是**隧道断了：`Server: cloudflare` 是 cloudflared 给 origin 应答也盖上的头，拿它判"谁在答"会判错。现网那一腿能过，是因为中间那把鉴权代理丢开来路 Host 并显式改写成 `127.0.0.1:4781`（`raw/preview_auth_proxy.py`、`:127`）。

**就绪等待是有界的**（字段 `tunnel_probe_attempts`、`tunnel_probe_waited_ms`、`tunnel_probe_statuses`）：quick tunnel 打完址还要几秒甚至一分多钟才转发，探不到就等 5 秒再探，最多 24 次；每一次探到的状态都按顺序进收据（`tunnel_probe_statuses`），不靠"多试几次直到绿"。

**探针钉死走法**：每次 HTTP 都用直连（`ProxyHandler({})`），读数里记 `proxy: "bypassed"`。这台机器环境变量 `HTTPS_PROXY` 指着一条无监听的 `:7892`，跟着它走会把「对端拒连」读成「链断了」——实测 17:5x 那趟就是这个假红。

端口在听不算数——必须真 HTTP 拿到状态。另外每次都记**手机那一代的指纹**：首页点名的 `/assets/index-*.js` 的文件名与它的字节数（例：`index-D3j0mgvR.js` / 1,276,676 B）。换代是否落到手机上，读这一枚，不读端口。

**隧道现值只有一个来源**：`run/tunnel_url.txt`。日志只在该文件没有值时才用来兜底，且只做候选——同目录里 `tunnel_0925_0417.err.log` 的 mtime 比什么都新，里面躺着一条早已死掉的 quick tunnel，按 mtime 取日志就会拿到死地址（实测）。权威值与最新日志不一致时，收据里两枚都列（`from_newest_log`）。

## 起进程的方式与被判定项

每一跳落成一份 `run/hop_<跳名>_<HHMM>.bat`（`HHMM` 是本地时间），再用 `cmd /c start "" /min <那份 bat>` 起——子进程自立控制台，不挂在调用方的会话上。收据里对每个被起的 pid 记：pid、父 pid、父进程是否还活着、父进程镜像名，并判**父进程不得是任何 agent 会话的 shell**（`bash.exe`/`sh.exe`/`zsh.exe`/`qoder.exe`/`codex.exe`）。真正的行为证明是臂：工具进程退出之后，那些跳必须还活着（`recover` 臂）。

## 三条硬边界（写在代码里，不是写在注释里）

1. **数据库**：只允许 `D:/moodle/_qoder_preview_20260920/_preview.db`。解析出的路径不等于它 —— 在任何一次 spawn 之前 `exit 4`（`--arm db-guard` 就是演这一出，换成 `_live.db` 必须拒）。不修、不猜、不"顺手对齐"。
2. **凭据**：`run/preview_auth.txt` 只按路径取用（TAB 分隔，运行时读一次拼一个 header），值不进日志、不进收据、不打印。
3. **地址与留言只追加**：隧道每次换址，旧值归档为 `run/tunnel_url.txt.dead_<HHMM>`，新值写 `run/tunnel_url.txt`，桌面留言只在**顶部插一个新块**；写完立刻校验旧字节仍完整地位于末尾，不满足就抛 `DESK_NOTE_REFUSE` 而不是覆盖。

## 实例参数（不碰别人那条链）

`--static-port/--auth-port/--backend-port`、`--run-dir`、`--dist-dir`、`--desk-note`、`--only <跳,...>`、`--fresh-tunnel`（本实例自己起一条隧道并公布新址，别把现网那条址当成"我这层已经活着"）、`--detect-only`（只读：0 spawn、0 写，可以对任何人的链跑）。

## 四臂

```
node tools/chain_self_heal.mjs --detect-only                       # 现网只读：三跳 + 资产指纹 + 隧道址
node tools/chain_self_heal.mjs --arm db-guard                      # 必须 exit 4，一条进程都不起
node tools/chain_self_heal.mjs --arm note-append                   # 临时副本上证明"只追加、旧字节在末尾"
node tools/chain_self_heal.mjs --only static,tunnel --static-port 4792 --auth-port 4792 \
     --fresh-tunnel --run-dir <我的目录> --desk-note <副本>        # 起→杀→再跑；这一台该拿 exit 2，不是 0
```

`recover` 臂的"杀"必须回验：`taskkill` 发了不算，要 `netstat` 读到那个端口真的空了（实测有 pid 被"杀"过、下一趟还在听，于是那一趟复用了残留的 vite，等于没演）。空不了就带着 pid 与命令行 ABORT，不许继续往下判绿。

## 已量到的三条形状事实（写在这里，省得下一个人重踩）

- 那把鉴权代理尺把自己钉死在 `:4782`、静态上游钉死在 `:4781`（`raw/preview_auth_proxy.py` 与 `:31`），只有 API 上游可由 `CNX_PROXY_API_UPSTREAM` 改（`:30`）⇒ 它不能挪端口做实验，只能整条一起起。
- `vite preview` 的 /api 目标是 `CITYNEXUS_BACKEND_PORT ?? 8000`（`frontend/vite.config.ts`、`:143`）⇒ 后端在 `:8693` 时，代理会自己答 500/0 字节（14:34 那批 `ECONNREFUSED 127.0.0.1:8000` 就是这个）。这一形状是 ORD-0352 的题，不是本单的题。
- quick tunnel 把新址打成 `... INF |  https://xxx.trycloudflare.com  |`，**行首不是 URL** ⇒ 提取地址的 regex 不能带 `^` 锚。
- 在这台机器上 `cloudflared tunnel --url … `（默认 QUIC）会停在 `precheck complete` 之后不再打印地址（实测 5 分钟没吐）；现网那条自己带 `--protocol http2`。本工具起的隧道同样带 `--protocol http2`，吐址只要几秒。
- `cmd /c start "" /min 某.bat` 起的是 `cmd /K 某.bat`：那个 cmd **一直握着从调用方继承的 stdout 管道写端**且不退出 ⇒ `spawnSync` 永远不返回（实测把一整趟 recover 挂死）。所有 start 调用一律 `stdio: "ignore"` + `timeout: 30000`。
