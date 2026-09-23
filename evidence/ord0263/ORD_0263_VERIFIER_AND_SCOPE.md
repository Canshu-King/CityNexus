# ORD-0263 附录 · 范围收窄后的判据与不会自动变绿的三格（HARNESS `d291c9dc`）

## 0. 先按你 17:20 的收窄对齐

`evidence/release/commander_release_walk_0923_1723.json` blob **`34c6aaab1584132ec3a4bab22bf771119177b2e8`**（2,390 B，我已按坐标回读并存档）里三条我照收：
- 发布代资源名与换代收据逐字相同（`index-DJEINrOl.js` / `index-COUUKhbU.css`，`PROVEN_MATCHES_RELEASE`）；
- **404 那一臂已经对了**：屏上「连接正常 / 这台服务器上没有这一趟行程了 / … 这不是网络问题：服务器刚才答得出来」+ `[选一趟行程] [重试] [归因详情]`，`HONEST_404_STATE_NOT_NETWORK`；
- 于是本单要盯的只剩两臂：**5xx + 本地快照**、**无应答（timeout/DNS/connect）**。

**我把你的现网读数只当"对照"，不当我的基线**：我的三格全部在我自己的夹具上判（`:4411` 壳 + `:8411` 我自己的库/我自己的静默端口），基线缺失这点我也写在"没测"里（我没有 53fe8e8 的面）。

## 1. 三格判据 + 三把 killer（`tools/ord0263_verifier.py`）

判据的输入只有**测到的字段**：`origin_answer{status,thrown}`、`settled_within_deadline`、`seconds_to_settle`、`snapshot_present`、`rendered_text`、`classified_label`、`doors{retry}`、`navigator_onLine`。缺一律 `NOT_MEASURED`（不是绿）。

| 格 | 判据 | 今天（我的实测夹具） |
|---|---|---|
| **V1 `5xx + 快照`** | 源站答了非 2xx 且有快照 ⇒ 文案必须**指名服务**+**说明展示快照**，且**不得**出现 `网络不可用/离线 · 只读/OFFLINE` | **RED**（`says_network_words=true`，service/snapshot 词都 false） |
| **V2 `无应答`** | fetch 从未拿到响应 ⇒ 必须 (a) 在**截止期限内 settle**、(b) 被标成**自己的类**、(c) 展示快照、(d) 留门；仍停在骨架屏即 fail | **RED**（`settled_within_deadline=false`、`classified_label=null`、`retry_door=0`、`still_on_loading_skeleton=true`，快照其实在） |
| **V3 不得塌成一类** | 两臂必须各自有被分类的文案且不同；骨架屏不算分类 | **RED**（`s3_is_unclassified_skeleton=true`） |

三把 killer 让"格子会不会说红"这件事本身被证过（`SELFTEST GREEN (7/7)`，`ord0263_verifier_selftest.json` blob `d8a6f27daacde4e7…`）：
- `V1-killer:today_s_network_words_must_be_red` ⇒ RED ✓（配上正确文案时 true_positive 为 GREEN ✓）；
- **`V2-killer:remove_the_read_deadline_and_the_cell_goes_red` ⇒ RED ✓** —— 你要的那条：把 per-read 截止期限拿掉（今天 `requestJson()` 的真实形状），这一格必须红；有期限时它 GREEN ✓；
- `V3-killer:one_sentence_for_both_arms_is_red` ⇒ RED ✓（两臂共用同一句话就红，专门拦"改一处交差"）；
- `V2-killer:missing_deadline_field_is_not_measured_not_green` ⇒ `NOT_MEASURED` ✓（A-3：字段缺失不许读成通过）。

**自测 GREEN 不代表产品修好了**，只代表这把判据能分辨红绿；判我这条线交付的仍然是 §2 那三格今天的 RED。

## 2. 修的人要同时动两处（一行改不出来）

```text
V8Experience.tsx:198  return response.ok;            ← 把"答非2xx"和"根本没答"塌成一个 false（V1 的病因）
api/citynexus.ts:642  async function requestJson<T>  ← 该请求路径里没有 AbortController/超时（V2 的病因：:601 的 await 永不 settle，catch 不执行，busy 恒 true）
```
只改文案：V1 会绿、V2 与 V3 仍红（今天就停在这一点上）。

## 3. ORD-0254 在第六枚尺上的收尾结论（D-1 closeout）

`live_checks/deploy_bundle.py` 分支尖 = **`7f2a2f0aea393c91069c789a4d5e8fac83fca5a1` / 96,631 B**（与你的坐标相符；自测凭据 `9b5726a4f1d45eeef82c412550ccadab9283365d` 21,085 B，53/53 GREEN，base `:4781` —— 那是你量的现网，不是我量的）。

- **§红-1 结论：`NOT_REPRODUCED_ON_7f2a2f0a`。** 两枚 F base 都配上跑完 `main()`：`crash=False`、`rc=0`、**OVERALL GREEN**，并写出收据（`ord0263_deploy_gauge_receipt.json` 里 `F_proxy_tunnel: GREEN`）。源码里那句聚合现在也是 `any(p.get("verdict") …)`（第 970 行）。
- **真换代第二次也在同一枚尺上过**：`old_refs [/assets/index-DJEINrOl.js, index-COUUKhbU.css] → new_refs [index-C0qSwD3N.js, index-CBXSx-f9.css]`，`B GREEN / old_refs_absent True`，切换 5 个根文件，备份 `dist_bak_173420_…`；臂集新增的 `J_name_content_binding GREEN` 与 **`temporal_obligations: DISCHARGED`** 都按预期走绿。
- 我没有改尺的任何字节（`ruler_unchanged=True`，运行前后 blob 复验），也不再进程内替换 `BASE`：全部走 `CNX_DEPLOY_BASE / PROXY_BASE / TUNNEL_BASE / SELFTEST_ROOT`。

## 4. 现场与未测

清理：三端口按 PID 具名杀、netstat 复测松手；`serve/`、`dist_bak_*`、我自己的 `canary_8411.db*`、MCP 侧 `cnxshots`（703,167 B）按具名清单删，**释放 17,217,486 B**；`repo/`、`patches/`、收据与截图保留。
未测/不声明：基线面对照（无 53fe8e8 canary ⇒ 不宣称回归）；鉴权代理与公网链（禁止端口 0 次访问）；S3 的 DNS 失败与"加载后连接被拒"变体（只造了 timeout 那一种，但因为没有 per-read 期限，三者今天同形）；AI 路径（我这台 `CITYNEXUS_AI_ENABLED=false`）。
