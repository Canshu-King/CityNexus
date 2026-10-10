"""账本体积哨兵（只读，独立于号令者自己的写盘路径）。

背景：号令者今晚差点用"contents API 读到 0 字节 ⇒ 基于空文整写"把整本账本覆盖掉
（恢复靠 d87b802b 那棵树）。这条失效模式会一次毁掉所有车道的共同记忆，
所以我这边独立盯远端 blob 的字节数：任何一次下降超过 SHRINK_PCT 就报警，
并把"上一枚好尺寸 + 当时的 commit"记在状态文件里，方便回滚时直接取坐标。

用法：python ledger_guard.py            # 单次检查
      python ledger_guard.py --log      # 同时往 ledger_guard.log 追加一行
"""
import base64
import json
import os
import sys
import time
import urllib.request

TOK_PATH = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
REPO = "Canshu-King/CityNexus"
BRANCH = "commander/control"
PATH = "CITYNEXUS_AGENT_CONTROL.md"
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "ledger_guard_state.json")
LOG = os.path.join(HERE, "ledger_guard.log")
SHRINK_PCT = 5.0


def hdr():
    return {"Authorization": "Bearer " + open(TOK_PATH, encoding="utf-8").read().strip(),
            "Accept": "application/vnd.github+json",
            "User-Agent": "cnx-ledger-guard",
            "X-GitHub-Api-Version": "2022-11-28"}


def get(url, tries=4):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=hdr())
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = "%s: %s" % (type(e).__name__, e)
            time.sleep(1.5 * (k + 1))
    raise RuntimeError("GET %s failed: %s" % (url, last))


def main():
    log = "--log" in sys.argv
    # 1) 分支上该路径最新一笔提交
    cs = get("https://api.github.com/repos/%s/commits?sha=%s&path=%s&per_page=3"
             % (REPO, BRANCH, PATH))
    if not cs:
        print("NO_COMMITS for path"); return 2
    c = cs[0]
    sha = c["sha"]
    when = c["commit"]["committer"]["date"]
    # 2) 该提交里该路径的 blob 与 size。
    #    注意：contents 路由对 5MB+ 文件会把 content 置空，但 size/sha 元数据仍然给 ⇒ 只取元数据，
    #    绝不用它返回的 content 判断"文件是不是空的"（那条坑今晚已经踩过一次）。
    ent = get("https://api.github.com/repos/%s/contents/%s?ref=%s" % (REPO, PATH, sha))
    if not isinstance(ent, dict) or "sha" not in ent:
        print("METADATA_UNUSABLE commit=%s" % sha); return 3
    blob = ent["sha"]
    size = int(ent.get("size") or 0)
    if size == 0:
        # size 读不到时退到 blob 元数据（git/blobs 只回 size+base64，不下载 content 字段之外的东西）
        meta = get("https://api.github.com/repos/%s/git/blobs/%s" % (REPO, blob))
        size = int(meta["size"])
    # 3) 与上一枚好读数比
    prev = {}
    if os.path.exists(STATE):
        try:
            prev = json.load(open(STATE, encoding="utf-8"))
        except Exception:
            prev = {}
    psize = int(prev.get("size") or 0)
    line = "[%s] remote size=%d blob=%s commit=%s@%s prev=%d" % (
        time.strftime("%H:%M:%S"), size, blob[:12], sha[:10], when[11:16], psize)
    alarm = ""
    if psize and size < psize * (100.0 - SHRINK_PCT) / 100.0:
        alarm = "  >>> ALARM 账本缩小 %.1f%%（%d -> %d），上一枚好尺寸在 commit %s blob %s" % (
            100.0 * (psize - size) / psize, psize, size, prev.get("commit"), prev.get("blob"))
    elif size == 0:
        alarm = "  >>> ALARM 远端账本 0 字节"
    print(line + alarm)
    if not alarm:
        json.dump({"size": size, "blob": blob, "commit": sha, "date": when},
                  open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if log:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + alarm + "\n")
    return 1 if alarm else 0


if __name__ == "__main__":
    sys.exit(main())
