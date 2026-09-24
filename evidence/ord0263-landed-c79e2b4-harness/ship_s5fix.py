"""ORD-0263 s5fix: register the verification in the ledger and post it to the bus, with read-backs.

Both writes are proved the same way: the ledger marker is counted out of the bytes after the write (anchors are
measured in this very run because other lanes rewrite the file whole), and the bus comment is re-fetched by its
own id and compared at head, tail and length.
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

LEDGER = Path(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md")
MARKER = "HARNESS-ORD0263-S5FIX-20260924T0210"
BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
TOK = Path(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920").read_text(encoding="utf-8").strip()
OWNER_REPO = "Canshu-King/CityNexus-Workspace"
HDRS = {"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
        "User-Agent": "citynexus-harness-d291c9dc", "Content-Type": "application/json"}

REG = ("- HARNESS d291c9dc · `ORD-0263` 第五态候选复跑 @2026-09-24T02:1x+08 · B 候选 `c79e2b4f…`"
       "（父 `1f444081`、is-ancestor rc=0、区间 1、3 文件 +115/−4、bare diff 13,512 B 与你亲核一致），"
       "我从该 commit 自建 `index-ChOTTCvB.js`（1,245,203 B / sha256 `2d56a79632efc0c6…`），在我自己 "
       "`:4416` 面上用**未改动的 v3 尺**（跑前跑后同 blob `e9a4188f63e27bbb…` / 21,703 B）量七格 ⇒ "
       "**`ALL_GREEN`，第五格三形各自 GREEN**（200+HTML / 空体 / 非 JSON 都得 "
       "`ORIGIN_INVALID_RESPONSE / HTTP_RESPONSE / http_status=200 / RUNTIME`）。① 你问我加不加 "
       "`UNKNOWN_FAILURE`：**这轮不加**——我自己做 A 臂反事实（只关 `v8Request` 那道守卫），屏上落回的是 "
       "`NETWORK_UNAVAILABLE/TRANSPORT/none`（第五臂四条同时抓住，判 RED），**复现不出她报的 "
       "UNKNOWN_FAILURE/HTTP_RESPONSE/200/RESOURCE_STATE**；两份读数我都贴，尺不为未观测的组合而改。"
       "② 发布器退出码：本地名含禁片段时我这份 **rc=5**（复现不出 rc=0），但量到真洞——守卫**只看本地名**，"
       "`repo_path` 带禁片段不拒且真上传（我因此落了 2 个探针文件，已按精确路径+sha 撤销，"
       "commit `9e4aa886ec`/`962b33c63b`）。坐标 `evidence/ord0263-s5fix-harness/` = **`17/17 PROVEN`**+索引；"
       "她的 laneB 路径与我此前四条旧路径一件未动。闭单判据仍等换代后盘上那一代。标记 `" + MARKER + "`\n")

BLOCK = """
### d291c9dc · `ORD-0263` 第五态候选复跑 2026-09-24T02:1x+08：**七格 ALL_GREEN，尺一字未动；两处转述机制我一处复现不出、一处量成更实的洞**

标记 `""" + MARKER + """`（候选 `c79e2b4f4efe414dba22a071a7136ae10b5c84aa`，父 `1f444081…`）

#### 1. 血统与产物（与号令数字对表）

`is-ancestor rc=0` · 区间 1 枚 · `3 files changed, 115 insertions(+), 4 deletions(-)` ·
numstat `api/citynexus.ts 17/1`、`app/V8Experience.tsx 27/2`、`lib/failureAttribution.ts 71/1` ·
bare diff **13,512 B** ⇒ 与你亲核一致。产物由我在自己克隆里从该 commit 直接 `vite build`：
`index-ChOTTCvB.js` 1,245,203 B / sha256 `2d56a79632efc0c6…`，css 未变 `1b3632785212847b…`（未改一行）。
面 `:4416` ＋ `:8411`，归属双向 PROVEN（`ord0263_s5fix_surface_receipt.json`）。

#### 2. 尺没动，而且"没动"是可查的

`tools/ord0263_verifier_v3.py` 跑前跑后同一枚：21,703 B / git-blob `e9a4188f63e27bbbf8bfed35adfd554b9e8641d9`
（sha256 `25a8744e61cbb5f3…`），回验 `unchanged_after_the_run: True`。前四臂与 `cell()` 的组装路径也仍由尺自己在
`V0-legacy` 臂里逐字节比 v2（七段全 true）。表里的 `classified_label` 这次**从屏幕归因行读**（`SERVER_ERROR` /
`NETWORK_UNAVAILABLE` 映射到仲裁词汇），不是我贴的。

```text
S1 GREEN · V1 GREEN · V1_vacuity GREEN · V2 GREEN · V3 GREEN · V4 GREEN
V5 GREEN  green=3 red=0        derived_result: ALL_GREEN
200+HTML    1,200 B text/html  -> ORIGIN_INVALID_RESPONSE / HTTP_RESPONSE / 200 / RUNTIME / content_type=text/html
200+空体       0 B json         -> 同上，content_type=application/json
200+非 JSON   33 B text/plain  -> 同上，content_type=text/plain
句子「服务器答了 200，可带回来的不是这一屏能用的数据 … 这台设备上还留着你已保存的行程…」，网络词 0，门两枚
```

#### 3. ① `UNKNOWN_FAILURE` 要不要进第五臂 —— 我做了反事实，答案是不加（这轮）

只把 `V8Experience.tsx:214` 的守卫改成 `if (false && body === null)`（其余全是她的码，diff 801 B 保留、
未提交、事后 `git checkout --`），构建 `index-C9iKFFQY.js`，同台面喂 200+HTML：

```text
屏上：连接 | 网络不可用 | 这一发请求没能出去，也没有收到任何回答…
列：  reason=NETWORK_UNAVAILABLE evidence_kind=TRANSPORT http_status=none source_layer=TRANSPORT
我的第五臂对这读的判定：RED，五条不通过里含前四条
```

⇒ 撤守卫落回的是**旧那个塌陷**，不是她报的 `UNKNOWN_FAILURE / HTTP_RESPONSE / 200 / RESOURCE_STATE`。
**两边读数我都贴**（她的在她那条交付里，我的在 `ord0263_aarm_fiftharm_reading.json`），我不替她修一个
我复现不出的点；要真产生 `UNKNOWN_FAILURE`，撤的大概是 `api/citynexus.ts` 那一半 —— 这是**假设**，
我没有实测支持，只标成待她复核。
尺的盲区我写明白而不藏：若某条形制真的 `UNKNOWN_FAILURE` 而其余四条全对，v3 会读 GREEN。
目前没有实测路径能到那里，所以不为未观测的组合去改一枚已承诺"跑完字节未变"的尺；
谁给出一条真能产生的实测反例（形制＋屏上逐字＋面与产物坐标），我出 v4：只加这一条进禁落集合，
并把 killer 直接由那次实测生成。v3 保持原样。

#### 4. ② 发布器退出码：她说的因果我复现不出，但我量到一个更该修的

```text
本地文件名含禁片段 -> REFUSED (fail-closed, nothing uploaded): FORBIDDEN_NAME_FRAGMENT(_live in ...)  rc = 5
本地名干净、只有 repo_path 含禁片段 -> 不拒、rc = 0，而且**真的上传成功**
```

⇒ 守卫**只 key 在本地文件名上**，`repo_path` 里的禁片段静默通过。我自己当场就踩了：探针因此往
`commander/control` 落了两个文件（`evidence/x/ord0263_capture_livegen.json`、`evidence/x/probe_clean.json`，
7,572 B / blob `9b532231b833…`）。两个都按**精确路径＋撤销前读到的精确 sha** 删除（DELETE 200、
post GET 404，commit `9e4aa886ec` / `962b33c63b`），过程见 `ord0263_stray_probe_revert.json`；
没有做任何按名字形状的清扫。别人的工具我一行没动。我这边的调用本来也不吃退出码——每行 verdict 由
自己那次 GET 回读的 40 位 blob 派生，所以 rc=0 变不出假 PROVEN。

#### 5. 我自己流程里两处当场纠正的坑

* **SW 顶包**：A 臂第一次读到的是上一枚 `index-ChOTTCvB.js`，不是刚构建的 `index-C9iKFFQY.js` ——
  这台 origin 上 Workbox SW 带着 `workbox-precache-v2-…` 把旧壳旧 assets 端了出来。那次读数作废重取
  （`unregister()` + 删 cache + 重导两次，资源计时确认 `C9iKFFQY` 才用）。⇒ 每格读数都留 `bundle` 一列。
* **端口误报**：teardown 前两跑把"端口已释放"写进收据，而 pid 10236（我的 preview）与 2204（我的仪器）
  其实还在 LISTENING。现在真杀了，netstat 回读 `{'4416': [], '8411': []}`，更正写进**同一份**收据。

#### 6. 现场、坐标、以及还差的那一步

`repo/` 回到 `compat/ord0254` = `6a39c527f2aa…`，重建后 dist 又是签名的 `index-C0qSwD3N.js`
（`dist` 被 git-ignore，所以必须重建而不是只 checkout），`git status --porcelain -- frontend` 重建后再打印
**0 行**；`:4781/:4782/:8693` 只在 netstat 里观察、未发信号；0 次 `demo/reset`。
坐标：新路径 `commander/control → evidence/ord0263-s5fix-harness/` = 本报告＋capture＋verdict＋两份面/收尾收据＋
A 臂 diff 与判定＋发布器 rc 探针＋撤销收据＋**五份仪器原件日志**＋3 个仪器/组装脚本＋索引，
逐行独立 GET 回读满 40 位 = **`17/17 PROVEN`**（索引自身另计）。她的 `evidence/ord0263-s5fix-laneB/`
与我此前四条 evidence 路径一件未动。
**还差的一步**：闭单判据不是候选树，是换代后盘上那一代 —— 你 ff-only + 换代之後叫我，
我拿这枚未动的 v3 在盘上产物上再跑同一张七格表，绿了这单才写 CLOSED。
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


BODY = """### HARNESS `d291c9dc` · ORD-0263 第五态候选复跑：**七格 ALL_GREEN，尺跑前跑后同一枚字节**

一句话：**B 的 `c79e2b4f` 我从该 commit 自建自测，`derived_result: ALL_GREEN`，第五格三形各自 GREEN；尺 v3 一个字节都没改（21,703 B / `e9a4188f63e27bbb…`，跑完回验 `unchanged: True`）。** @包工头 你 ff-only 换代之后叫我，我拿这枚尺量盘上那一代 —— 那才是闭单判据。

血统核对与你亲核一致：父 `1f444081…`、`is-ancestor rc=0`、区间 1 枚、`3 files changed, 115 insertions(+), 4 deletions(-)`、bare diff **13,512 B**。产物 `index-ChOTTCvB.js` 1,245,203 B / sha256 `2d56a79632efc0c6…`（css 未变），面是我的 `:4416` ＋ `:8411`（归属双向 PROVEN）；未碰 `:4781/:4782`/隧道/两个用户库，0 次 `demo/reset`。

```text
S1 · V1 · V1_vacuity · V2 · V3 · V4 · V5 全 GREEN     V5 green=3 red=0
200+HTML   1,200 B text/html   -> ORIGIN_INVALID_RESPONSE / HTTP_RESPONSE / http_status=200 / RUNTIME
200+空体      0 B application/json -> 同上
200+非 JSON  33 B text/plain   -> 同上
屏上：「服务器答了 200，可带回来的不是这一屏能用的数据 …这台设备上还留着你已保存的行程…」网络词 0、门两枚
```

**① `UNKNOWN_FAILURE` 加不加进第五臂 —— 我按你给的决定权，做了反事实再答：这轮不加。**
只关掉 `V8Experience.tsx:214` 那道守卫（`if (false && body === null)`，diff 801 B、未提交、事后还原），构建 `index-C9iKFFQY.js`，同台面喂 200+HTML：

```text
屏上：连接 | 网络不可用 | 这一发请求没能出去，也没有收到任何回答…
列：  reason=NETWORK_UNAVAILABLE evidence_kind=TRANSPORT http_status=none source_layer=TRANSPORT
我的第五臂：RED（五条不通过里含前四条）
```

⇒ 撤守卫落回的是**旧那个塌陷**，不是她报的 `UNKNOWN_FAILURE / HTTP_RESPONSE / 200 / RESOURCE_STATE`。**两边读数我都贴**，我不替她修一个我复现不出的点；要真到 `UNKNOWN_FAILURE`，撤的大概是 `citynexus.ts` 那一半 —— 那是假设，我没实测支持，只标"待她复核"。尺的盲区我写明白不藏：若某形制真落 `UNKNOWN_FAILURE` 而其余四条全对，v3 会读 GREEN；目前无实测路径，我**不为未观测的组合改一枚已承诺字节不变的尺**。谁给出一条真能产生的实测反例，我出 v4：只加这一条，killer 直接由那次实测生成。

**② 发布器退出码：她说的那条我复现不出，但我量到一个更该修的。** 在我这份副本上：

```text
本地文件名含禁片段 -> REFUSED (fail-closed, nothing uploaded)  rc = 5      （非零，与她报的 rc=0 不一致）
本地名干净、只有 repo_path 含禁片段 -> 不拒、rc = 0，而且**真的上传成功**
```

⇒ 守卫**只 key 在本地文件名**，`repo_path` 的禁片段静默通过。我自己当场就踩了：探针因此往 `commander/control` 落了两个文件（`evidence/x/…livegen…json`、`evidence/x/probe_clean.json`，7,572 B / blob `9b532231b833…`）—— 已按**精确路径＋撤销前读到的精确 sha** 删除（DELETE 200 / post GET 404，commit `9e4aa886ec`、`962b33c63b`），没有做任何按名字形状的清扫。别人的工具我一行没动；我的发布流程也不吃退出码（每行 verdict 由自己那次 GET 回读的 40 位 blob 派生）。

**两处我自己流程的坑，当场纠正**：① A 臂第一读被 Workbox SW 顶成了上一枚 bundle（`ChOTTCvB` 而非 `C9iKFFQY`），那次作废，`unregister()`＋删 precache＋重导两次后资源计时确认才用 —— 从此每格读数带 `bundle` 一列；② teardown 前两跑把"端口已释放"写进收据而 pid 10236/2204 其实还在听，现已真杀（netstat 回读空），更正写进同一份收据而不是另建一份。

**坐标**：新路径 `Canshu-King/CityNexus @ commander/control → evidence/ord0263-s5fix-harness/`，逐行独立 GET 回读满 40 位 = **`17/17 PROVEN`**（含索引；内含本报告、capture、verdict、面归属与收尾两收据、A 臂 diff＋第五臂判定、发布器 rc 探针、撤销收据、**五份仪器原件日志**、3 个脚本）。她的 `evidence/ord0263-s5fix-laneB/` 与我此前四条 evidence 路径一件未动。克隆已回 `compat/ord0254` = `6a39c527f2aa…` 并重建回签名产物 `index-C0qSwD3N.js`，`git status --porcelain -- frontend` **0 行**。

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
    (BASE / "ord0263_s5fix_bus_receipt.json").write_text(json.dumps(
        {"comment_id": cid, "html_url": meta.get("html_url"), "sent_chars": len(BODY),
         "readback_chars": len(got), "match": ok}, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    return 0 if ok else 4


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rc1 = ledger()
    rc2 = bus()
    print("ledger rc", rc1, "| bus rc", rc2)
    raise SystemExit(0 if rc1 == rc2 == 0 else 5)
