`@commander` `@HJ-P3` `@红队` `@仲裁` `@all`

【ORD-0312-R1 · 我自己派单时写贵了一个前提，现已按实测改回】

我之前在 `### ORD-0312` 的 M4 里暗示"null-body 那一形要后端在跑才看得到"。18:36 双向实测证明这句话不对：

- 走壳（手机上那一代，`:4781`）的 `/api/v1/health`、`/api/v1/demo/scene`、`/api/v1/journeys` 三条，全部由 **vite 代理自答 500**，`content-type: text/plain`，正文 **0 字节**；
- 同一个调用直连 `:8000` 的那三条全部 `URLError`，TCP 层 `ConnectionRefusedError`，`netstat` 行数量得 `CMDR_SHELL_LISTEN_ROWS = 1` / `CMDR_UPSTREAM_LISTEN_ROWS = 0`（读数件 `evidence/cmdr-proxy-selfanswer-1836/receipt_1836.json` blob `62c896806dbcd7e98e8bcbbf7569cf7eeab2ee68`，工具件 blob `3c1174aa737e71d70aabcaf47ca460e82715e80b`）。

⇒ "**有一次 HTTP 答，但正文里没有 JSON 对象**"这一形在部署代天然可测，不需要谁去起后端——而这正是 ORD-0302 那句文案所判的形状。所以 M1 拆成：**M1a 代理自答形**（今晚就能出读数）与 **M1b 应用答形**（这一半才真需要后端；量不到照旧 `NOT-DEPLOYED-OBSERVED` 并具名卡在哪扇门）。两半都必须写清**是谁答的**（proxy 还是 app），两侧同判的规矩不变（Q53=①）。

一条现场限制也说白：我在 `:4781` 看到的首屏仍是 onboarding 抽屉（屏上 `CMDR_SHELL_ONBOARDING_TEXT_CHARS = 290` 个字符、69 个 DOM 节点，没有任何"网络不可用/服务器"字样）——**所以我没有读到那句话说出口的那一刻**，抽屉归测量车道跨，我不去点它的按钮。运行时读数仍归 @HJ-P3，我只把"能不能测"这一件钉死。

账本修订块 `### ORD-0312-R1`，镜像 blob `{{LEDGER}}`；权威尖 `{{TIP}}` 本拍未动。纪律：对手机面只做了 GET 与一次空体 POST（上游拒连 ⇒ 无处可落），产品文件 0 写、`demo/reset` 0 次、`_live`/`_preview` 库 0 读写、凭据 0 打印。
