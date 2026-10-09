r"""用 **GitHub 服务器时间** 判"谁的活落了账本但她还没醒" —— 这一把才是今晚该有的尺。

09-26 08:30 发现 `pending_check` 瞎了五小时：号令者从 06:45 起块头写成 `### CMDR 07:50 — ...`
（空格 + HHMM，没有 MMDD），而我的正则只认 `### CMDR-MMDD-HHMM` ⇒ 它一直把 03:35 那块当"最新"，
06:45 / 06:56 / 07:50 三块（里面有 Q72/Q73 裁定和"15 格 Q64 残留按 owner 派单"）根本没进视野。
再叠上今晚量到的"个别车道把块头时间标到未来 89 分钟"，**任何用车道自己写的时间做的判据都不可信**。

⇒ 只用两样硬东西：
  · 块**落账本的服务器时间**（commit committer date，Z）
  · 车道**最后一次写自己 JSONL 的本地时间**
落账本 晚于 她最后落盘 且那块点到她的 id ⇒ 候选。块头是不是她自己的（作者=被点名人）单独判，作者不算被点名。
"""
import glob
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
API = "https://api.github.com"
REPO = "Canshu-King/CityNexus"
BRANCH = "commander/control"
PATH = "CITYNEXUS_AGENT_CONTROL.md"
HDR = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
       "User-Agent": "cnx-patrol", "X-GitHub-Api-Version": "2022-11-28"}
import wake_names as WN  # 09-28 16:58：旧表只认 8 位 id，号令者写「给 n3 与 ORD-0383 车道」就全漏
LANES = WN.ID8
NAME_TO_ID = {v: k for k, v in WN.ID8.items()}
STATE = os.path.join(HERE, "wake_from_commits_state.json")
ALIVE_H = float(os.environ.get("WAKE_ALIVE_H", "6"))   # 与 _why_stopped_r1.py 的在册判据同一个数：流水 6 小时没动＝不是今夜的可叫醒窗口
HEAD = re.compile(r"^\+### ([^\n]*)")


def get(url):
    r = urllib.request.Request(url, headers=HDR)
    try:
        import sys
        sys.path.insert(0, r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
        import ghnet
        st, body = ghnet.urlopen(r, timeout=90)
        return json.loads(body.decode())
    except urllib.error.HTTPError as e:
        return {"__http__": e.code}
    except Exception as e:
        return {"__err__": type(e).__name__}


def last_write(key):
    ps = glob.glob(os.path.join(BASE, key + "*.jsonl"))
    return max(os.stat(p).st_mtime for p in ps) if ps else 0.0


def parse_z(s):
    return time.mktime(time.strptime(s, "%Y-%m-%dT%H:%M:%SZ")) - time.timezone


def blocks_from_commit(sha_url):
    """返回 [(块头, 整块文本)]。只看块头会漏 —— 号令者 07:50 那块把 owner 写在正文里
    （"现尖 15 格 Q64 残留按 owner 派单"），块头只有他自己的时间。"""
    det = get(sha_url)
    out = []
    if isinstance(det, dict):
        for fl in det.get("files") or []:
            if fl.get("filename") != PATH:
                continue
            cur = None
            for line in (fl.get("patch") or "").split("\n"):
                if not line.startswith("+") or line.startswith("+++"):
                    continue
                text = line[1:]
                m = HEAD.match(line)
                if m:
                    cur = [m.group(1).strip(), [text]]
                    out.append(cur)
                elif cur is not None:
                    cur[1].append(text)
    return [(h, "\n".join(b)) for h, b in out]


def decline_key(sha, lane):
    return "%s|%s" % (sha[:8], lane)


def load_declines():
    try:
        return set(json.load(io.open(STATE, encoding="utf-8")))
    except Exception:
        return set()


def save_declines(d):
    json.dump(sorted(d), io.open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=0)


def record_decline(sha, lane, why):
    d = load_declines()
    d.add(decline_key(sha, lane))
    save_declines(d)
    print("DECLINED %s (%s) 理由=%s 已记入 %s，同一枚块不再反复报" % (
        lane, sha[:8], why, os.path.basename(STATE)))
    return 0


def main():
    if "--declined" in sys.argv:
        i = sys.argv.index("--declined")
        return record_decline(sys.argv[i + 1], sys.argv[i + 2],
                              sys.argv[i + 3] if i + 3 < len(sys.argv) else "?")
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - hours * 3600))
    cs = get("%s/repos/%s/commits?sha=%s&path=%s&since=%s&per_page=40" % (
        API, REPO, urllib.parse.quote(BRANCH), urllib.parse.quote(PATH), since))
    if not isinstance(cs, list):
        print("QUERY_FAIL", json.dumps(cs, ensure_ascii=False)[:200])
        return 1
    now = time.time()
    dec = load_declines()
    print("账本提交 %d 枚（最近 %.1f 小时，服务器时间）| 已判过不敲 %d 条" % (len(cs), hours, len(dec)))
    hits = 0
    cand_rows = []
    stale_rows = []
    for c in cs[::-1]:
        sha = c["sha"]
        when = parse_z(c["commit"]["committer"]["date"])
        for head, body in blocks_from_commit(c["url"]):
            ids_head = [k for k in LANES if k in head]
            owner = ids_head[0] if ids_head else None
            # 块头常常只写花名（`### CMDR … · 号令者 · …`，里面没有 8 位 id），
            # 那一枚就是作者，不能算「被点名」——否则我自己的判据会把号令者叫成候选。
            head_names = WN.named_in(head)
            owner_nm = LANES.get(owner) or (head_names[0] if head_names else None)
            # 两层都认：正文里的 8 位 id + 车道花名（lane N2 / 给 n3 / ORD-0383 车道 / 道0370 …）
            named_ids = set(k for k in LANES if k in body and k != owner)
            for nm in WN.named_in(head + chr(10) + body, exclude_owner=owner_nm):
                k = NAME_TO_ID.get(nm)
                if k and k != owner:
                    named_ids.add(k)
            # 车道的自交块正文里常常写着自己的 8 位 id 与花名（18:19 那块就是），
            # 两层都要按作者剔掉，否则我会把「它自己交了」当成「有人在等它」
            named = [k for k in LANES if k in named_ids and k != owner and LANES[k] != owner_nm
                     # 09-29 05:28：号令者本人的两个会话实例都**不是车道**，永远不该进待敲门名单
                     # （05:28 那轮 N3 的自交块里出现了「号令者」四个字，把我自己的会话 id 列成了候选）。
                     and k not in ("494abfd7", "6efab655")]
            # 09-28 20:52 加的一眼：状态板/普查类块会把所有车道名字列在一张表里（道tokens 20:41 那块就是这样，
            # 一次把 N2/map/AI/道0369 全列成"被点名"），那不是在派单。真正的派单块都带一个指向记号
            # （`ORD-#### →`、`→ 车道`、`谁手空谁领`、`请只做`、`派 ORD-####`）。没记号又点了 >=4 家的块
            # 一律不转达，只打一行 CENSUS_LIKE 让下一眼的人看见我为什么跳过。
            DISPATCH_PAT = re.compile(r"ORD-\d{4}\s*→|→\s*(?:车道|前端|任意)|谁手空谁领|请只做|派\s*ORD-\d{4}")
            cmdr_head = bool(re.search(r"CMDR|号令者", head))
            para_of = {}
            census_like = (len(named) >= 4 and not DISPATCH_PAT.search(head + chr(10) + body))
            if census_like and cmdr_head:
                # 09-29 04:47 加的一眼：号令者现在喜欢一块里连派 8~12 张（04:34 那块 ORD-0433…ORD-0443 各点名一条车道），
                # 这种块既像状态板又真是派单：整块放行会一次敲醒十家，整块拒掉会把新单漏掉（我 04:47 就是这么手工补的）。
                # ⇒ 只保留「同一段落里同时出现 ORD-#### 与且仅与这一家」的车道，并把转达正文收窄成那一段。
                for p in re.split(r"\n\s*\n", body):
                    ids = set(k for k in LANES if k in p)
                    for n in WN.named_in(p):
                        if NAME_TO_ID.get(n):
                            ids.add(NAME_TO_ID[n])
                    ids = set(k for k in ids if k != owner and LANES.get(k) != owner_nm)
                    if len(ids) == 1 and re.search(r"ORD-\d{4}", p):
                        para_of.setdefault(list(ids)[0], []).append(p)
                if para_of:
                    named = [k for k in named if k in para_of]
                    census_like = False
            if census_like:
                named = []
            tags = []
            notes = []
            skipped = []
            # 09-29 03:15 加的一眼：块头没有号令者标记的块 = 车道自己的交件块。车道在自己的块里
            # 引用别人的单号与会话 id 很常见（N2 03:04 那块把 rel 的 ORD-0428 列成「我能接、但要点名」），
            # 那不是在派单——转达了只会让被引用的车道以为有人在等它。这类块一律不转达，只打一行让下一眼的人看见。
            if not cmdr_head:
                named = []
            if census_like:
                notes.append("CENSUS_LIKE：这块列了 >=4 家却没有指向记号，判为状态板而非派单 ⇒ 不转达")
            if not cmdr_head:
                notes.append("NON_CMDR_HEAD：块头不是号令者 ⇒ 车道的交件块不构成派单，不转达")
            if para_of:
                notes.append("PER_ORDER_PARA：整块像状态板，但 %d 段各自只点一家且带单号 ⇒ 逐家收窄转达" % len(para_of))
            lag = (now - when) / 60.0
            for k in named:
                lw = last_write(k)
                if not (lw and when > lw and (now - lw) / 60.0 >= 8.0):
                    continue
                # 名册按文件系统推：流水几小时没动的窗口不是今夜在干的活，转达给它没有意义，
                # 而且旧块会永远满足 `when > lw` ⇒ 每一轮都把它当新候选报一次（10-03 06:1x 现形：
                # a68b0631 静 938 分被 CMDR 03:16 那块反复点名，每 12 分钟误报一回，谁照着敲就敲到无关窗口）。
                idle_min = (now - lw) / 60.0
                if idle_min > ALIVE_H * 60.0:
                    stale_rows.append({"lane": LANES.get(k, k), "id8": k, "idle_min": round(idle_min, 1),
                                       "why": u"流水 %.1f 小时没动＝不在今夜名册" % (idle_min / 60.0)})
                    continue
                if decline_key(sha, k) in dec:
                    skipped.append(LANES[k])
                    continue
                tags.append("%s idle=%.1fm 落账本(%s)之后没动" % (
                    LANES[k], (now - lw) / 60.0, time.strftime("%H:%M", time.localtime(when))))
                # 给 relay.py 留一份可复核的清单：谁、哪一块、服务器时间、块正文
                # （整块像状态板但段内只点一家时，正文收窄成那一家那一段，relay.py 就不会把十家的名单一起转达）
                cand_rows.append({"lane": LANES[k], "id8": k, "sha": sha,
                                  "commit_at": c["commit"]["committer"]["date"],
                                  "idle_min": round((now - lw) / 60.0, 1),
                                  "head": head,
                                  "body": (chr(10) + chr(10)).join(para_of[k]) if para_of.get(k) else body})
            flag = "  <== 候选" if tags else ("  [已判过不敲: %s]" % "、".join(skipped) if skipped else "")
            print("  %s %s (+%.0fm) 作者=%-7s 点到=%-26s %s%s%s" % (
                c["commit"]["committer"]["date"], sha[:8], lag,
                LANES.get(owner, "?"), "、".join(LANES[k] for k in named) or "（无人）",
                head[:80], flag, ("" if not notes else "  ‖ " + " ‖ ".join(notes))))
            if tags:
                hits += len(tags)
                for t in tags:
                    print("        · %s" % t)
    io.open(os.path.join(HERE, "wake_candidates.json"), "w", encoding="utf-8", newline="\n").write(
        json.dumps({"measured_at": time.strftime("%Y-%m-%dT%H:%M:%S+08"), "window_h": hours,
                    "candidates": cand_rows, "stale_filtered": stale_rows},
                   ensure_ascii=False, indent=1))
    print("candidates=%d  (明细写 wake_candidates.json)" % hits)
    # 滤掉多少、滤掉谁必须当场打出来：一声不响地少报，比多报更难被发现
    if stale_rows:
        print("名册外滤掉 %d 条：%s" % (
            len(stale_rows), "、".join(u"%s(静 %.0f 分)" % (s["lane"], s["idle_min"]) for s in stale_rows)))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
