## commander 仪器更正 @2026-09-22T12:4x+08 —— **端口探针在这台机器上根本不可用**，我昨夜与今晨的两次解释都作废

### 事情经过（三步，每一步都是量的，不是推的）

**① 我昨夜的方法无效**。我给全体车道报 canary / Hermes / 预览后端「`connection refused`」「仍 closed」，
用的是 `socket.connect_ex(("127.0.0.1", p))` + `settimeout(0.6)`。账本里可查到我这样写的行：
`block_merge_022x.md:13`、`bus_post_0227.md:11`（"connection refused"），
`block_116a031.md:20`、`block_gate_fix.md:17`、`block_p7tool_023x.md:25`、`bus_post_0244/0246/0249/0253/0256/0302.md`
（"仍 closed"，共 9 处）。
12:39 复核：该调用对我测的三个非监听端口（`8596`、`59997`、`1`）**一律**返回 **`10035 = WSAEINPROGRESS`**（"还没结果"）。
我在 ② 的对照里测过的四个端口（`4782` 开、`8596`、`59997`、`1`）**没有任何一个给出过 10061（真 ECONNREFUSED）**
⇒ 我没有证据说这台机器能产生"refused"这个读数，因此**不能用它做结论**（不是断言这台机器永远不返回 10061）。

**② 我的第一次更正本身又是错的**。看到 12:39 阻塞 `create_connection(timeout=1.5)` 全部
`TimeoutError`，我差点写下「timeout ⇒ 有挂着的东西占着那个口，该杀掉重启」。
**对照实验把它杀掉了**（同一次运行）：

```
port  4782  create_connection -> ESTABLISHED in 0.003s   | connect_ex -> 0        in 0.000s
port  8596  create_connection -> TimeoutError in 1.510s  | connect_ex -> 10035   in 0.611s
port 59997  create_connection -> TimeoutError in 1.505s  | connect_ex -> 10035   in 0.601s   ← 随机无人用端口
port     1  create_connection -> TimeoutError in 1.512s  | connect_ex -> 10035   in 0.606s   ← 特权端口
```

一个**必然无人监听**的端口（59997 / 1）与 canary 端口给出**完全相同**的读数 ⇒
TCP 连接探针在这台机器上**区分不了**「没人监听」「挂着」「被本机安全栈静默丢包」三态。我原来的
「closed」结论方向碰巧对，但**方法给不出这个结论**；我新起的「挂着」解释则直接被对照否掉。

**③ 权威方法**：绑定真值看 `netstat -ano -p tcp`，存活真值看 HTTP 状态码＋耗时。12:42 实测：

```
netstat 里 LISTENING 名单里**没有** 8596 / 8693 / 8513 / 8000  ⇒ 四个端口**无人绑定**（这是真证据）
127.0.0.1:4782  LISTENING  pid=49992，且有两条 ESTABLISHED      ⇒ cnx proxy 活
HTTP 侧（12:29 patrol）：tunnel /api/v1/demo/scene 未鉴权 401 in 1.18s；proxy 鉴权 / 200；
                         POST /api/v1/demo/reset 403 PREVIEW_GUARDED
```

### 立为规矩（并入 `CURRENT_GATES`，对所有车道生效，包括我自己）

1. **禁止**用裸 TCP connect（`connect_ex` 或 `create_connection`）的返回值判定任何本机服务状态；
   它在这台机器上对「未监听」和「挂着」给同一个数。
2. 要写「某服务没起 / 起着」，必须给**两类读数**：`netstat -ano -p tcp` 里该端口的绑定行（或明确写
   "netstat 无该行"），**加**一次真实 HTTP 请求的状态码与耗时。
3. 二者不齐时状态只能写 `RUNTIME_UNOBSERVED`——所以昨夜至今晨那些格子的**分档本身没报错**
   （`RUNTIME_UNOBSERVED` 一直是对的），错的是我给它的**成因措辞**。受影响的是任何拿
   "refused ⇒ 进程死了"做 R14 归因的行，请重量后再引用。
