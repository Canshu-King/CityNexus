# ORD-0263 附录：把我那格判据改到不空转，并用它跑 B 的候选

车道：HARNESS `d291c9dc`（我）。只测不改产品码；没动尺；没在进程内替换 BASE。
被验对象：B 候选 `a380287033da6ff0bd36b8e1baa6f79c61ad03bd`（父 `dea8410`，re-parent 到权威尖
`035721357da99a43c276f5803df83c3b08c1361c`）。
构建产物 `index-Ce5-8mHb.js` / `index-Dd5F3CW4.css`，我起了自己的面 `http://127.0.0.1:4413`
（`CITYNEXUS_BACKEND_PORT=8411`）。坐标 blob 一律见索引文件，正文不重复抄（抄了就会对不上表）。

---

## 1. 你指出的洞成立，我把那一格重定向了

我 v1 的 S2 断言写的是「渲染文字里应当出现 `shell.offlineMsg` 那句网络话」。在权威尖上这句话**已经没有
发射方**（`git grep -n offlineMsg 03572135…` 只有 `i18n/LocaleContext.tsx:718`（zh）与 `:32`（en）两处词典
条目，全仓 2 处命中、0 处调用；该 grep 在 `_qoder_integration_20260919` 树内只读执行——我自己的克隆
`git cat-file -t 03572135…` 报 `unable to parse object`，所以那一句的可复现现场在那棵树里），
所以那条断言在当前树上**永远为假**——一个不可能开火的判据不是判据。这是 B 发现的，我确认属实并认账。

`tools/ord0263_verifier_v2.py` 里 V1 改成合取，三件同时成立才算绿：

1. 点名服务（`服务(暂时)?不可用|服务器…答|origin answered|HTTP \d{3}`）；
2. 交出本地快照（`本地快照|已保存的行程|只读的已保存|saved snapshot|read-only snapshot`）；
3. 网络词为 0（`网络不可用|离线 · 只读|OFFLINE|network is down|连不上`）。

并加了一枚专门盯这个洞的臂 `V1-vacuity`：三件**全缺**（错句 simply 消失）必须读红。

### 两向证明（不是我自己宣布的，是同一枚判据在两份真机读数上的两个方向）

| 侧 | 来源 | V1 | V2 | V3 | V4 | derived_result |
| --- | --- | --- | --- | --- | --- | --- |
| 旧树真红 | `ord0263_capture_measured.json`（我在 17:0x 于未修文案的 canary 面上真测：「网络不可用 · 正在显示只读的已保存行程。」） | RED | RED | RED | RED | `RED_CELLS:` 四臂（下表名缩略，全文见收据） |
| B 候选真绿 | `ord0263_capture_b_candidate.json`（本轮四格实测） | GREEN | GREEN | GREEN | GREEN | `ALL_GREEN` |

判据自检：`SELFTEST GREEN (14/14)`，含 4 枚 killer（错句仍红、空消失仍红、撤掉 read deadline 仍红、
把 S4 折进网络臂仍红）。

**一处边界我要说清**：「权威尖上那一格静默缺失」我没有真机实测，只有静态 grep（无发射方）+ 自检里的合成
fixture。原因就是这个洞本身——那棵树上这一格不产生任何文案，任何"实测"都必然是空的，测不出新东西。
所以它记为合成臂，不冒充现场读数。

## 2. B 候选四格：全部现场读数（同一个 Chrome 上下文，`snapshot_rows=1` 贯穿）

状态是靠换我自己 `:8411` 上的进程做到的，不是 mock：
`真 uvicorn`（归属见 `ord0263_backend_restart_for_b.json`：marker 行 + netstat 46348，其父 9644＝我 spawn 的句柄）→
`无监听`（proxy 自己答 500）→ `tools/mixed_origin_port.py`（health 500 json，其余路径挂 40 s）→
`tools/silent_api_port.py`（接 TCP 永不答）。

### S1 2xx → LIVE

线上：`/api/v1/health` 200 in 0.005s、journey 200 in 0.006s。
屏幕：`晚上好 | Demo之旅 | 10月10日 09:00 — 10月10日 19:00 · 1 位旅行者 · 1 天 | 今天 | 还没有安排`。
网络词 0。B 顺手把游标那句话改诚实了：「服务器没有给出这一分钟的执行游标，这一屏的时间按行程的时间窗来读」。

### S2 origin 答 500 + 有快照 → ORIGIN_ERROR_WITH_SNAPSHOT

线上：health 500 in 0.003s、journey 500 in 0.004s、壳 200（`:8411` 无监听，500 是 preview 代理给的）。
屏幕原句（导航后 6.9 s 已定）：

> 服务器 ／ 服务暂时不可用
> 「服务器刚才答了你，但它自己报错了（HTTP 500）。这是服务暂时不可用，不是你填错了什么。这台设备上还留着
> 你已保存的行程，用下面的按钮可以只读查看这份本地快照；也可以稍后重试。」
> 门：看已保存的只读副本 · 重试 · 归因详情

网络词 0、`navigator.onLine=true`、快照行 1。三件合取齐了。

### S3 源完全不应答 → NETWORK_UNREACHABLE_WITH_SNAPSHOT（B 自造的中文标签「没有回音」）

线上：health 000 in 10.0s、journey 000 in 10.0s、壳 200。页面侧 400 ms 采样：骨架最后一次在
**16 004 ms**，带标签的错误带首次出现在 **16 407 ms**，一直到 46.0 s 不再变化。屏幕原句：

> 没有回音 ／ 等了 12 秒，这台服务器一个字也没回答
> 「这一发读取到了期限仍然没有任何回答：服务器既没有拒绝，也没有答应，它只是没有说话。你的行程数据没有丢，
> 这台设备上有已保存的行程，用下面的按钮可以只读查看这份本地快照；也可以再试一次。」
> 门：看已保存的只读副本 · 重试 · 归因详情

**16.4 s 与 12 s 的差我两个数都留着**：app 自称期限 12 s（`READ_DEADLINE_MS = 12_000`），16.4 s 是从
navigationStart 量到出句，中间是壳解析＋boot 之前那段没有请求在跑。挑好看的写 12 s 就是虚报。

### S4（B 加的第四态：health 答 500、那一发读永远不答）→ 归 ORIGIN_ERROR

线上双证：health 500 application/json in 0.004s；journey 读 000 in 30.0s（仪器挂 40 s）。
采样：骨架最后 11 909 ms，12 307 ms 出「服务器／服务暂时不可用（HTTP 500）」，稳定到 47.1 s。
这一格正是旧判据看不见的形态——它读起来跟断网一模一样。B 用 `probeHealth()` 的四个分开的
事实（`{answered,status,ok,timed_out}`，`V8Experience.tsx:210`）把它分开了，且没有说成网络问题。

四格之间还要不塌成一类：`V3` 检查 S2 与 S3 的句子和标签不同（实测不同），且 S3 不是骨架。

## 3. 你的病因二更正：我照做了，而且是量出来的，不是推出来的

你原话的问题是「只修 `requestJson` 不修 `v8Request`，骨架屏是否一模一样」。

静态先摆出来（B 树上 `git grep`）：`V8Experience.tsx` 里 `v8Request` **20** 处、`requestJson` **0** 处；
boot 那串读全在 `:554 :573 :589 :592 :593 :596 :615`；`requestJson` 只活在 `api/citynexus.ts` 和
`features/inbox/JourneyInboxWorkbench.tsx`。B 把期限包在了 `v8Request` 自己身上（`:185
fetchWithReadDeadline`）。

但"推出来"不够，我做了单变量突变（只在我自己的克隆工作树，未提交）：`api/citynexus.ts:644` 的
`fetchWithReadDeadline` **保留**，只把 `V8Experience.tsx:185` 退回裸 `fetch` —— 即"修了另一臂、没修这一臂"。
构建 `index-B8w70bTP.js`，同一 Chrome 上下文、同一静默源、同一 400 ms 采样器，看 72 秒：

| | 突变树（只修 requestJson） | B 正式构建 |
| --- | --- | --- |
| 样本数 | 181（7 987 → 79 986 ms） | 覆盖到 45 996 ms |
| 骨架样本占比 | **1.0（全程）** | 出句即止 |
| 带标签错误带出现次数 | **0** | 16 407 ms 起 |
| 「重试」门 | **0** | 1 |
| 交出快照的话 | **无** | 有 |
| IndexedDB 快照行 | 1（数据在，不是没内容） | 1 |

派生答案：**YES —— 一模一样，而且永远不收**。`ord0263_cause2_v8request_receipt.json` 里这个 YES 是从
「骨架占比==1.0 且 标签带出现 0 次 且 门 0 且 无快照句 且 B 侧窗口内已出句」算出来的，不是我手写的。
所以你的更正成立：只修 `requestJson` 对这个屏幕**没有任何影响**，我上一版把病因只记在 `probeHealth` 上不完整。

突变后：`git checkout -- frontend/src/app/V8Experience.tsx` → `git status --porcelain -- frontend` 0 行 →
重新构建回 `index-Ce5-8mHb.js`（与被验构建一致，已回读）。

## 4. 没做与边界

* B 的分支 **不在 GitHub 上**：`git ls-remote https://github.com/Canshu-King/CityNexus.git
  refs/heads/agent/b-c01d72a3-ord0263` 返回空行。所以 `a380287033da…` 只是**本地坐标**（我从本地远端
  `D:/moodle/_qoder_integration_20260919` fetch 到的），不能说"可外读"。可外读的只有本附录这些 evidence blob。
* 权威尖的 S2 静默缺失是静态＋合成，不是现场（理由见 §1 末）。
* 三态文案我判的是**语义合取**，没有去断言 B 的中文措辞必须逐字怎样； arbiter 词汇与屏幕标签之间的翻译
  规则写进了 capture 的 `label_derivation`，标签本身是从渲染文字派生的（`typed_in_by_verifier: false`），
  要不同意那条映射可以直接指着它改。
* 屏幕上的「没有回音」「服务暂时不可用」这些标签是 B 的措辞，不是 arbiter 的英文码；我没让他改成我的词。
