# CHAIN_SELF_HEAL_V1 — 手机预览链的自恢复入口（ORD-0358）

入口：`node tools/chain_self_heal.mjs [参数]`。一辆链四跳：`:8693` 后端 → `:4781` `vite preview` 服发布根 → `:4782` 鉴权代理 → cloudflared 隧道。以前它靠人记得起哪四层、按什么顺序、带什么参数；16:30 那次断链就是四跳都挂在某个会话自己开的窗口下面，会话一停子进程被一起带走。

## 判"活着"的方式

| 跳 | 探测 | 健康判据 |
| --- | --- | --- |
| backend | `GET http://127.0.0.1:8693/api/v1/health` | 200 |
| static | `GET http://127.0.0.1:4781/` | 200 且字节 > 200 |
| auth_proxy | `GET http://127.0.0.1:4782/api/v1/health`（带 Basic） | 200 |
| tunnel | `GET <隧道址>/api/v1/health`（带 Basic） | 2xx |

端口在听不算数——必须真 HTTP 拿到状态。另外每次都记**手机那一代的指纹**：首页点名的 `/assets/index-*.js` 的文件名与它的字节数（例：`index-BOIAHTWw.js` / 1,271,252 B）。换代是否落到手机上，读这一枚，不读端口。

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
     --fresh-tunnel --run-dir <我的目录> --desk-note <副本>        # 起→杀→再跑，回到 CHAIN_HEALTHY
```

## 已量到的三条形状事实（写在这里，省得下一个人重踩）

- 那把鉴权代理尺把自己钉死在 `:4782`、静态上游钉死在 `:4781`（`raw/preview_auth_proxy.py:25` 与 `:31`），只有 API 上游可由 `CNX_PROXY_API_UPSTREAM` 改（`:30`）⇒ 它不能挪端口做实验，只能整条一起起。
- `vite preview` 的 /api 目标是 `CITYNEXUS_BACKEND_PORT ?? 8000`（`frontend/vite.config.ts:132`、`:143`）⇒ 后端在 `:8693` 时，代理会自己答 500/0 字节（14:34 那批 `ECONNREFUSED 127.0.0.1:8000` 就是这个）。这一形状是 ORD-0352 的题，不是本单的题。
- quick tunnel 把新址打成 `... INF |  https://xxx.trycloudflare.com  |`，**行首不是 URL** ⇒ 提取地址的 regex 不能带 `^` 锚。
