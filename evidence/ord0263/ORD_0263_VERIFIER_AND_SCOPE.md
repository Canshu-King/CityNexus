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

## 5. 第七枚尺 `149e9c6dbe6debca`（106,731 B，commit `18959e4af448`）——在我面上重跑

坐标核对：分支尖即此枚（`149e9c6dbe6debcac92041bb192761c1cf1aa2a7`，106,731 B）。三件见证按 **blob 前缀**在 `evidence/gates/` 里搜到并回读：
```text
指挥官面  deploy_bundle_crosssurface_selftest_cmdr_149e9c6d.json     26,322 B  8becfad825cc184c…  63/63 GREEN  base :4781
第二面    deploy_bundle_crosssurface_selftest_foreign_149e9c6d.json  26,449 B  dc2f1e540d55bc91…  63/63 GREEN  base :4981
修前反证  deploy_bundle_foreign_surface_before_fix_bb09b925.json     25,876 B  4d4df8e087dc9a0d…  60/63 RED    base :4981
   修前红的正是三枚 SIDES killer（foreign_dist_without_base / dotdot_traversal / foreign_base_with_cmdr_serve 全 got=OK 而非 REFUSED）
```
**我这面的结果：`SELFTEST GREEN (65/65 arms matched)`，零格因混侧而红。** 65 = 你的 63 + 我导出 `CNX_DEPLOY_SELFTEST_OLD_REF` 才有的 B2/B2-neg。逐格（只列与这次修法有关的）：
```text
ENV-integrity:operators_base_survived_the_whole_selftest                     GREEN   （at_entry=final_base=http://127.0.0.1:4412）
BASE-restore:default_base_used_and_operators_value_handed_back               GREEN
BASE-restore-killer:wrong_base_or_lost_operators_value_is_red                RED     （双向都有）
SIDES-true_positive:this_runs_own_pair_agrees / pair_still_passes_after_the_borrowed_block   OK
SIDES-killer:foreign_dist_without_base / dotdot_traversal / foreign_base_with_cmdr_serve     REFUSED ×3   ← 你问的三枚，在我的配对下不再红
PAIR-true_positive:declared_base_with_its_own_root_is_a_pair                 A_PAIR
PAIR-killer:defaulted_base_over_a_foreign_root_is_not_a_pair                 NOT_A_PAIR（计入 declared_arms，不冒充 GREEN）
J-true_positive GREEN + 三枚 J-killer RED；F-true_positive 读数现在自带 base=…4412 disk=…\serve
declared_arms = [G-declared:handwritten_sw_without_precache_array, PAIR-killer:defaulted_base_over_a_foreign_root_is_not_a_pair]
pair_binding（自测收据里）：http_base=:4412 declared_via_env=true disk_serve=我的 serve/ resolves 到自身，
   resolved_cmdr_dist=D:\moodle\_qoder_preview_20260920，declares_cmdr_live_explicitly=false
```
真换代同一枚尺也过：`index-DJEINrOl.js/-COUUKhbU.css → index-C0qSwD3N.js/-CBXSx-f9.css`，`A/B/C/D/E + G[DECLARED,GREEN×8] + I + J + F` 全 GREEN、`temporal_obligations: DISCHARGED`、**OVERALL GREEN rc=0**（`deploy_..._0923_181406.json` 67,169 B；收据里新增 `gauge{path,bytes,sha256}`，把"哪一枚尺"钉进收据本身）。
两条口径差异我如实记：`pair_binding` 与 `declared_arms` 只出现在**自测**收据里，deploy 收据里这两枚是 `null`；另外你诊断的那次我 42/48 里除了三枚 SIDES，还有 `J-true_positive` 与 `F-true_positive` 两格也是这次 ENV-integrity 修好的（我这轮它们都 GREEN）。
