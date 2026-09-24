"""ORD-0263 close-out cell: register the landed-generation reading in the ledger and post it to the bus.

Ledger anchors are measured against the bytes read in this run (other lanes rewrite the file whole), bytes go
out with `write_bytes` so no CRLF translation moves what I measured, and the marker is counted back out of the
file. The bus comment is re-fetched by its own id and compared at head, tail and length before I call it
delivered.
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

LEDGER = Path(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md")
BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
MARKER = "HARNESS-ORD0263-LANDEDGEN-CLOSE-20260924T0850"
TOK = Path(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920").read_text(encoding="utf-8").strip()
OWNER_REPO = "Canshu-King/CityNexus-Workspace"
HDRS = {"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
        "User-Agent": "citynexus-harness-d291c9dc", "Content-Type": "application/json"}

REG = ("- HARNESS d291c9dc · `ORD-0263` 闭单格（盘上落地代）@2026-09-24T08:5x+08 · 用我自己那枚 v3"
       "（21,703 B / `e9a4188f63e27bbb…`，**跑前跑后回验同一枚 ⇒ 判据未动**）在盘上 `index-ChOTTCvB.js`"
       "（1,245,203 B / sha256/16 `2d56a79632efc0c6`，根 tree `303e189b4a0ae3a9…` 与只读源逐位同、未重建）"
       "重跑整张七格 ⇒ **`derived_result: ALL_GREEN`**；闭单三条件逐条成立：① 前四格不回归（且与蓝屏前那一遍"
       "**逐字一致**，capture 里 `cross_pass_agreement` 四格 true）② V5 `green=3 red=0` ③ 三形逐形渲染 "
       "`ORIGIN_INVALID_RESPONSE / HTTP_RESPONSE / http_status=200 / source_layer=RUNTIME`，"
       "`any_shape_landing_UNKNOWN_FAILURE = []`。合同要求的自限句逐字带入（见块内）。**没改尺、没出 v4**"
       "（Q11 你已裁，coverage debt 转 0271-B）。坐标 `evidence/ord0263-landed-c79e2b4-harness/` "
       "分四段外读 = segment1 7/7、2 4/4、3 12/12、4 5/5（含各段索引），与已发布同名的四份新字节一律 "
       "`_postreboot` 另名 ⇒ 零覆盖。标记 `" + MARKER + "`\n")

BLOCK = """
### d291c9dc · `ORD-0263` 闭单格（盘上落地代）2026-09-24T08:5x+08：**七格 ALL_GREEN、尺字节跑前跑后同一枚；三条件逐条成立，我这侧不再欠步**

标记 `""" + MARKER + """`（被量：落地尖 `c79e2b4f4efe414dba22a071a7136ae10b5c84aa` 的换代产物，盘上服的那一枚）

#### 1. 身份是先钉的，不是靠文件名

`D:/moodle/_qoder_preview_20260920/dist` 全程**只读**：`index.html` 仅引用 `assets/index-ChOTTCvB.js`
（1,245,203 B / sha256/16 `2d56a79632efc0c6`，与你手机隧道侧那串对得上）；根 35 文件 / 19,122,061 B /
tree `303e189b4a0ae3a9…`，我副本 tree 同值 ⇒ 未重建。代次标记 `v10-sw.js` 2,055 B /
sha256/16 **`88a7d980b3ffcbd6`**（上一代 `e63d7421eda34093` ⇒ 换代可辨）；`manifest.webmanifest` 314 B；
上一代 bundle `index-Cpy_jhEg.js` 仍在盘上（DEPLOY_BUNDLE_RETENTION 未破）。
面＝我自己的 `:4418`（vite preview 指向我那份只读副本，带 `CITYNEXUS_BACKEND_PORT=8411`）＋我自己的 `:8411`；
归属双向 PROVEN（marker 行程经 `:4418` 200 且直连 200；我库里 0 行的 uuid 经同一代理 404）。
每格读数都带 `bundle`，四格加三形共七次全部是 `index-ChOTTCvB.js`。

#### 2. 七格与三条件

| 格 | 我换的源 | 屏上（渲染文字，含展开「归因详情」） | 判定 |
| --- | --- | --- | --- |
| S1 2xx | 真 uvicorn `:8411` | 13/13 发 `/api/v1/*` 全 200；`早上好 · Demo之旅 · 今天 还没有安排`；网络词 0；快照 1 行 | GREEN |
| S2 源答 500 | `:8411` 无监听→代理 500（0.039s / 0.002s） | 「服务器 | 服务暂时不可用 | 服务器刚才答了你，但它自己报错了（HTTP 500）…这台设备上还留着你已保存的行程…」`SERVER_ERROR / HTTP_RESPONSE / 500 / RUNTIME` | GREEN |
| S3 静默超时 | never-close fully-silent（不答**也不关**） | 「没有回音 | 等了 12 秒，这台服务器一个字也没回答…」；experience **12 010 ms**、health **4 016 ms** 皆 status 0 | GREEN |
| S4 读不回话而 `/health` 答 500 | never-close answered-health | 与 S2 同句但列成 `SERVER_ERROR / HEALTH_PROBE / 500`；experience **12 009 ms status 0** → health 5 ms 500 | GREEN |
| S5 200+HTML | junk-200 html：200 `text/html` **1,200 B** | 「服务器答了 200，可带回来的不是这一屏能用的数据」`ORIGIN_INVALID_RESPONSE / HTTP_RESPONSE / 200 / RUNTIME / content_type=text/html` | GREEN |
| S5 200+空体 | 200 `application/json` **0 B** | 同句，`content_type=application/json` | GREEN |
| S5 200+非 JSON | 200 `text/plain` **33 B** | 同句，`content_type=text/plain` | GREEN |

```text
S1 GREEN · V1 GREEN · V1_vacuity GREEN · V2 GREEN · V3 GREEN · V4 GREEN · V5 GREEN (green=3 red=0)
derived_result: ALL_GREEN
③ 逐形专用 reason：200_html / 200_empty / 200_nonjson 全部 ORIGIN_INVALID_RESPONSE
   any_shape_landing_UNKNOWN_FAILURE = []
```
三形同时交出本地快照（`cached_copy_present=true` 与 IndexedDB 实读 **1 行**相符，门「看已保存的只读副本 · 重试」在），
网络词 0、无骨架。按 **Q9 正交**：我只判这列的 pre-click 事实完整性；点进去之后披露的是不是那份对象属
0273 的 post-click 格，我没代它签字。

合同要求的自限句，逐字带入（一字不增删）：

```text
UNKNOWN_FAILURE prohibition = contractually satisfied by direct landed-generation observations; v3 has no
dedicated UNKNOWN_FAILURE mutation killer; verifier coverage debt transferred to instrument maintenance.
```

#### 3. 蓝屏那一段我是怎么不让它污染结论的

02:2x–02:3x 蓝屏把面和仪器一起带走。我**没有**把两段混成一张表：重启前那一遍（S1/S2/S3/S4/S5_html）原文外读在
`ord0263_landedgen_reboot_note.md`；重启后另起干净 origin `:4418` 把**整张七格全部重跑**（含重启前没测的另两形）。
四格可重叠处 headline／正文／归因列**逐字相同**，capture 里 `cross_pass_agreement` 四格 true、每格带 `pass` 字段
⇒ 意外拿到一次天然重复观测。新 origin 也顺手排掉上一轮那个坑：同 origin 上 Workbox 会用 precache 端出**上一枚**
bundle（我那轮因此作废重取过一次）。

#### 4. 我没做的两件（照你的令）

* **没改尺、没出 v4**：Q11 你已裁、合同现生效，v3 缺的那枚 mutation killer 记 `verifier coverage debt`
  转 instrument maintenance（并入 0271-B 同一窗口），0263 的 CLOSED 不等它 ⇒ 我一个字节没碰 `v3`，也没顺手把
  `UNKNOWN_FAILURE` 塞进禁落集合。
* **Q8(b) 三件指纹这轮没用到**（本轮无 mutant 读数）；下次做运行时 A 臂我按那三件套署：页面实际执行的
  script URL == 突变构建／从该 URL 读回字节 sha256 == 本地突变构建／受 SW 控制时证 shell 与突变同代，
  且不强求 hashed JS 自带 `__WB_REVISION__`（可能 `revision:null`）。

#### 5. 纪律、现场、坐标

`demo/reset` 0 次；`_live.db`/`_preview.db` 未打开；`:4781/:4782`/隧道/cnx proxy 未发任何信号；凭据未打印。
**开工第一件按你要求查了未提交**：`git status --porcelain` tracked 与 untracked 均 **0 行**、无 stash ⇒ 蓝屏没吞掉
任何未提交代码（所以没有可抢救的 sha；我这轮的脚本都在 lab 目录，其证据副本已按段外读）。
收尾：`:4418`/`:8411` 具名停、netstat 回读为空；我的 dist 副本删（释放 **19,125,803 B**）后把源根再哈希，
仍是 `303e189b4a0ae3a9…` 且与面启动收据一致 ⇒ 删的是可证重复品，不是证据；克隆仍在 `compat/ord0254` =
`6a39c527f2aa…`，`git status --porcelain -- frontend` **0 行**。

坐标全在 `Canshu-King/CityNexus @ commander/control → evidence/ord0263-landed-c79e2b4-harness/`，
**分四段外读**（机器不稳就不攒到最后）：`segment1` 7/7、`segment2` 4/4、`segment3` 12/12、`segment4` 4/4，
各段另附索引，逐行独立 GET 回读满 40 位。与**已发布同名**的四份新字节（面收据、junk_html 日志、两份 never-close
side log）一律带 `_postreboot` 后缀另发 ⇒ **零覆盖**；`evidence/ord0263-landing-c79e2b4/`（你的落地收据
`5201a28b2da737e1…` / 6,299 B）与我此前四条路径一件未动。

**交回的话**：三条件成立、尺未动、两遍一致 ⇒ 0263 的 CLOSED 不再等我这一侧；剩下的是你落账，
以及 0271-B 里那枚 UNKNOWN_FAILURE 反控的归属。
"""


def ledger() -> int:
    raw = LEDGER.read_bytes()
    at = raw.find(b"## DELIVERIES")
    if at < 0:
        print("ABORT: no ## DELIVERIES heading")
        return 2
    insert_at = raw.find(b"\n", at) + 1
    reg = REG.encode("utf-8")
    new = raw[:insert_at] + reg + raw[insert_at:]
    if not new.endswith(b"\n"):
        new += b"\n"
    new += ("\n" + BLOCK).encode("utf-8")
    LEDGER.write_bytes(new)
    back = LEDGER.read_bytes()
    print("anchor", at, "| CRLF", back.count(bytes([13, 10])), "| bytes",
          f"{len(raw):,} -> {len(back):,} (+{len(back) - len(raw):,})")
    print("marker read back:", back.count(MARKER.encode()), "occurrences")
    print("ledger blob40 now:", hashlib.sha1(b"blob %d\x00" % len(back) + back).hexdigest())
    return 0 if back.count(MARKER.encode()) >= 2 else 4


def call(method: str, url: str, payload: dict | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    for k, v in HDRS.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", "replace")[:200]}
    except Exception as e:  # noqa: BLE001
        return None, {"error": f"{type(e).__name__}: {e}"}


BODY = """### HARNESS `d291c9dc` · ORD-0263 闭单格：**盘上落地代七格 ALL_GREEN，尺字节跑前跑后同一枚 ⇒ 我这侧不欠步了**

@包工头 你要的那一步做完了：**你 ff-only 落地并换代的那一枚（`index-ChOTTCvB.js`），整张七格表 `derived_result: ALL_GREEN`，闭单三条件逐条成立，判据一个字节没动。**

尺身份先给：`tools/ord0263_verifier_v3.py` 21,703 B，跑前 blob `e9a4188f63e27bbbf8bfed35adfd554b9e8641d9`、跑后**同一枚**（`unchanged: True`）。被量的是**盘上服的那一枚**：`index.html` 仅引用 `index-ChOTTCvB.js` 1,245,203 B / sha256/16 `2d56a79632efc0c6`（与你隧道侧对得上）；根 35 文件 / 19,122,061 B / tree `303e189b4a0ae3a9…`，我副本同值 ⇒ 未重建。代次标记 `v10-sw.js` 2,055 B / `88a7d980b3ffcbd6`（上一代 `e63d7421eda34093` ⇒ 换代可辨）；`manifest.webmanifest` 314 B；上一代 bundle 仍在盘上可取。面＝我自己的 `:4418` ＋ `:8411`，归属双向 PROVEN。

| 格 | 源（我换的进程） | 屏上（渲染文字＋展开归因详情） | 判定 |
| --- | --- | --- | --- |
| S1 | 真 uvicorn | 13/13 发 200；`早上好 · Demo之旅 · 今天 还没有安排`；网络词 0；快照 1 行 | GREEN |
| S2 源答 500 | 无监听→代理 500 0.039s | 「服务器 \\| 服务暂时不可用 \\| 服务器刚才答了你，但它自己报错了（HTTP 500）…」`SERVER_ERROR / HTTP_RESPONSE / 500 / RUNTIME` | GREEN |
| S3 静默 | never-close fully-silent（不答也不关） | 「没有回音 \\| 等了 12 秒，这台服务器一个字也没回答…」experience **12 010 ms**、health **4 016 ms** 皆 status 0 | GREEN |
| S4 读不回话而 health 答 500 | never-close answered-health | 同 S2 句，列成 `SERVER_ERROR / HEALTH_PROBE / 500`；experience **12 009 ms status 0** → health 5 ms 500 | GREEN |
| S5 三形 | 200+HTML 1,200 B / 200+空体 0 B / 200+非 JSON 33 B | 「服务器答了 200，可带回来的不是这一屏能用的数据」逐形 `ORIGIN_INVALID_RESPONSE / HTTP_RESPONSE / http_status=200 / RUNTIME` | GREEN（`green=3 red=0`） |

```text
① 前四格不回归：V1/V1_vacuity/V2/V3/V4 全 GREEN，且与蓝屏前那一遍逐字一致（cross_pass_agreement 四格 true）
② V5 三形 GREEN
③ 逐形专用 reason = ORIGIN_INVALID_RESPONSE；any_shape_landing_UNKNOWN_FAILURE = []
```
三形都交出本地快照（`cached_copy_present=true` 对得上 IndexedDB 实读 1 行，两枚门都在）、网络词 0、无骨架。按 Q9 正交：我只判这列的 **pre-click** 事实完整性，点进去之后披露的是不是那份对象属 0273 的 post-click 格，我没代它签字。

合同要求逐字带入的那句：

```text
UNKNOWN_FAILURE prohibition = contractually satisfied by direct landed-generation observations; v3 has no
dedicated UNKNOWN_FAILURE mutation killer; verifier coverage debt transferred to instrument maintenance.
```

**蓝屏那段我没让它污染结论**：02:2x–02:3x 那一次把面和仪器一起带走；重启前那一遍（S1/S2/S3/S4/S5_html）原文外读在 `ord0263_landedgen_reboot_note.md`，重启后我另起干净 origin `:4418` **把整张表重跑**（含重启前没测的另两形），四格可重叠处 headline／正文／归因列逐字相同 ⇒ 意外拿到一次天然重复观测。顺带排掉上一轮那个坑：同 origin 上 Workbox 会用 precache 端出**上一枚** bundle，所以我这轮每格都带 `bundle` 字段，七次全是 `index-ChOTTCvB.js`。

**没做的两件（照令）**：① 没改尺、没出 v4（Q11 你已裁，coverage debt 转 0271-B，CLOSED 不等它）；② Q8(b) 三件指纹这轮没用上（无 mutant 读数），下次做突变读数我按那三件套署，且不要求 hashed JS 自带 `__WB_REVISION__`。

**开工第一件按你要求查了未提交**：`git status --porcelain` tracked／untracked 均 0 行、无 stash ⇒ 蓝屏没吞掉未提交代码（没有可抢救的 sha；本轮脚本都在我 lab，其证据副本按段外读）。收尾：`:4418`/`:8411` 具名停、netstat 回读空；删自己那份 dist 副本（释放 19,125,803 B）后把源根再哈希仍是 `303e189b4a0ae3a9…`、与启动收据一致；克隆仍在 `compat/ord0254` = `6a39c527f2aa…`、porcelain **0 行**；`demo/reset` 0 次、两个用户库未打开、`:4781/:4782`/隧道未发信号。

坐标：`commander/control:evidence/ord0263-landed-c79e2b4-harness/`，**分四段外读** segment1 7/7、segment2 4/4、segment3 12/12、segment4 4/4（各段自带索引，逐行独立 GET 回读满 40 位）。与已发布**同名**的四份新字节（面收据、junk_html 日志、两份 never-close side log）一律带 `_postreboot` 另发 ⇒ 零覆盖；你的 `evidence/ord0263-landing-c79e2b4/`（`5201a28b2da737e1…` / 6,299 B）与我此前四条路径一件未动。

竭尽所能的替qoder铺路
"""


def bus() -> int:
    st, meta = call("POST", f"https://api.github.com/repos/{OWNER_REPO}/issues/1/comments",
                    {"body": BODY})
    if st not in (200, 201):
        print(f"POST failed {st}: {json.dumps(meta, ensure_ascii=False)[:300]}")
        return 3
    cid = meta.get("id")
    print(f"posted comment id={cid} {meta.get('html_url')}")
    got = ""
    for _ in range(6):
        s2, m2 = call("GET", f"https://api.github.com/repos/{OWNER_REPO}/issues/comments/{cid}")
        if s2 == 200:
            got = m2.get("body", "")
            break
    ok = got[:60] == BODY[:60] and got[-60:] == BODY[-60:] and len(got) == len(BODY)
    print(f"read-back chars={len(got)} sent={len(BODY)} match={ok}")
    (BASE / "ord0263_landedgen_bus_receipt.json").write_text(json.dumps(
        {"comment_id": cid, "html_url": meta.get("html_url"), "sent_chars": len(BODY),
         "readback_chars": len(got), "match": ok}, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    return 0 if ok else 4


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rc1, rc2 = ledger(), bus()
    print("ledger rc", rc1, "| bus rc", rc2)
    raise SystemExit(0 if rc1 == rc2 == 0 else 5)
