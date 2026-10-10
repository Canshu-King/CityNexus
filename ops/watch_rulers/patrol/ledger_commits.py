r"""从 **GitHub 提交历史**读账本最近落了哪些块 —— 时间戳是服务器给的，不受车道自报时钟影响。

09-26 08:28 我量到的一件事：`CITYNEXUS_AGENT_CONTROL.md` 有 4.03 M 字符（6.46 M 字节），
而文件**尾部**最后几枚块是昨天 20–22 点的 ⇒ "按文件顺序看尾巴"根本看不到今天的插入（今天的块插在中间某个锚下）。
`pending_check` 又只认 `### CMDR-MMDD-HHMM` 这一种块头，号令者 03:35 之后没写过这种头
⇒ 车道写给车道的块（今天插进来的那十几枚）**不进任何一把尺的视野**。

⇒ 换成按提交读：每枚 commit 带服务器时间 + 它新增的 `+### ` 块头 + 块头里点到的 8 位车道 id。
这样"谁在什么时候被写进账本、内容点到谁"就有硬时间可依，不用信任何车道自己写的时刻。
"""
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
API = "https://api.github.com"
REPO = "Canshu-King/CityNexus"   # 账本在**产品仓库**（ledger_guard 同源）；Workspace 只有总线，查它会得到 0 枚并被我误读成"没人动过"
PATH = "CITYNEXUS_AGENT_CONTROL.md"
BRANCH = "commander/control"     # 09-26 08:30：不带 sha= 时按默认分支查 ⇒ 回 0 枚，差点被我读成"没人动过账本"
HDR = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
       "User-Agent": "cnx-patrol", "X-GitHub-Api-Version": "2022-11-28"}
IDS = {"494abfd7": "号令者", "8ccd71d8": "F", "aad2d1f2": "HJ-P3", "e345b9d6": "D",
       "c01d72a3": "B", "d2305848": "E 红队", "a17ae861": "S3", "8e094dec": "S1",
       "d9e2c9ae": "S2", "1d64acf5": "S4"}


def get(url):
    r = urllib.request.Request(url, headers=HDR)
    try:
        import sys
        sys.path.insert(0, r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
        import ghnet
        st, body = ghnet.urlopen(r, timeout=90)
        return json.loads(body.decode())
    except urllib.error.HTTPError as e:
        return {"__http__": e.code, "body": e.read().decode()[:200]}
    except Exception as e:
        return {"__err__": "%s: %s" % (type(e).__name__, e)}


def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - hours * 3600))
    url = "%s/repos/%s/commits?sha=%s&path=%s&since=%s&per_page=40" % (
        API, REPO, urllib.parse.quote(BRANCH), urllib.parse.quote(PATH), urllib.parse.quote(since))
    commits = get(url)
    if isinstance(commits, dict):
        print("QUERY_FAIL", json.dumps(commits, ensure_ascii=False)[:220])
        return 1
    print("账本 %s 的提交：最近 %.1f 小时内 %d 枚（since=%s，服务器时间）" % (PATH, hours, len(commits), since))
    for c in commits[::-1]:                     # 旧 -> 新
        sha = c["sha"][:8]
        when = c["commit"]["committer"]["date"]
        msg = c["commit"]["message"].split("\n")[0][:88]
        det = get(c["url"])
        added = []
        alltext = []
        if isinstance(det, dict) and det.get("files"):
            for fl in det["files"]:
                if fl.get("filename") != PATH:
                    continue
                for line in (fl.get("patch") or "").split("\n"):
                    if line.startswith("+++") or not line.startswith("+"):
                        continue
                    alltext.append(line[1:])
                    if line[1:].lstrip().startswith("### "):
                        added.append(line[1:].strip())
        blob = "\n".join(alltext)
        who = sorted(v for k, v in IDS.items() if k in blob)
        print("\n  %s  %s  +%d 块头  点到: %s" % (
            when, sha, len(added), "、".join(who) or "（无人）"))
        print("     msg: %s" % msg)
        for a in added[:3]:
            print("     new: %s" % a[:130])
        if len(added) > 3:
            print("     ...另有 %d 枚块头未列" % (len(added) - 3))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
