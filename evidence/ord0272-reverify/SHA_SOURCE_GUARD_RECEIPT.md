# ORD-0272 · 同代复验 r3：SHA 来源兜底（不拿别人的 HEAD 给自己的读数盖章）

lane F `8ccd71d8` · 2026-09-25T02:32:25+08:00

## 缺陷是包工头实测出来的，不是我推出来的

他把落地快照解在**另一个仓库里面**（`_qoder_cmdr_ref_20260921\live_checks\`）跑 r2 ⇒ 八格的
`exact_sha` 全变成那台仓库的 HEAD（`e9efec6bff2f…`），不是落地 sha `dcae1bc964…`；把快照搬到没有
`.git` 的目录重跑才对。原因：r2 用 `git -C <tree> rev-parse HEAD`，**它会往上走**，于是拿到外层仓库的
HEAD 并理直气壮地盖章。

## r3 的规则（四条，逐条可复跑）

```text
① 被验树自己就是 git 根         -> HEAD 可信；给了申报就必须相等，不等 -> SHA_SOURCE_MISMATCH
② 树在别的仓库里面（往上解析到 HEAD） -> 一律 SHA_SOURCE_MISMATCH，**哪怕申报值恰好等于外层 HEAD**
③ 周围没有 .git（纯 git archive 导出） -> 允许，但只盖"申报戳"，并写明 content_provenance=declared-only
                                            （读数只证明『这一代能跑』，不证明『这一代 == 该 sha』）
④ 既没申报、又没有 ① 的可信 HEAD  -> SHA_SOURCE_UNTRUSTED（拿不出坐标就明说，不出读数）
```

②里那半句"哪怕申报值恰好等于它"是我第一版 r3 的真实洞：我先写成"申报 != HEAD 才拒"，于是
"嵌在别的仓库 + 申报外层 HEAD"这一例被放行为 GATE-GREEN —— 下面第 3 行读数就是它，改完之后它被拒。

## 六形读数（本机现跑，退出码一并给）

| 形状 | 申报 sha | verdict | exit | 盖章用的 sha | 内容来源 | 与预期 |
|---|---|---|---|---|---|---|
| 干净导出（周围无 .git）+ 申报落地 sha | `dcae1bc964` | **GATE-GREEN** | 0 | dcae1bc964 | declared-only：本树周围无 .g | 符合 |
| 嵌在别的仓库里 + 申报落地 sha | `dcae1bc964` | **SHA_SOURCE_MISMATCH** | 6 | — | — | 符合 |
| 嵌在别的仓库里 + 申报外层仓库自己的 HEAD（第一版 r3 的洞） | `8ad10f3e2b` | **SHA_SOURCE_MISMATCH** | 6 | — | — | 符合 |
| 嵌在别的仓库里 + 不申报 | `—` | **SHA_SOURCE_MISMATCH** | 6 | — | — | 符合 |
| 干净导出 + 不申报 | `—` | **SHA_SOURCE_UNTRUSTED** | 6 | — | — | 符合 |
| 没有门的树（反向：不能假装绿） | `dcae1bc964` | **NOT-PRESENT** | 3 | dcae1bc964 | declared-only：本树周围无 .g | 符合 |

## 四向自测（`--selftest`，一条命令）

```text
[selftest] 有门的树 -> GATE-GREEN（八格 8/8 绿）
[selftest] 没门的树 -> NOT-PRESENT
[selftest] 错根探针（backend/…::x 必被判不匹配）-> BITES
[selftest] 嵌在别的仓库里的导出树 -> SHA_SOURCE_MISMATCH（被拒：不给别人的 HEAD 盖章）
SELFTEST_PASS
```

四向是：有门的树算读数 / 没门的树必须 `NOT-PRESENT` / **错根 nodeid 探针必须 BITES**（r2 那件的严格化）/
**嵌在别的仓库里的快照必须被拒**（本件新增）。少任何一向自测就不给 `SELFTEST_PASS`。

## 用法（给落地方与 verifier）

```text
python o272_reverify_r3.py --tree <落地仓库根> --expect-sha <落地 sha> [--gen <bundle 名>]
# 快照解在别的仓库里 -> 会被拒；搬到没有 .git 的目录即可（读数会标明 declared-only）
python o272_reverify_r3.py --selftest --tree <干净导出> --absent-tree <没门的树> \
       --nested-tree <故意解在某个仓库里的导出> --expect-sha <落地 sha>
```
`--expect-sha` 也可以省：`--gen` 里含 40 位十六进制时按申报值处理。

## 坐标

```text
evidence/ord0272-reverify/o272_reverify_r3.py            （本件仪器）
evidence/ord0272-reverify/SHA_SOURCE_GUARD_RECEIPT.md    （本件）
evidence/ord0272-reverify/sha_source_readings.json       （六形 + 自测原始读数）
```
