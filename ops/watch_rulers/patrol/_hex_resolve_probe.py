r"""把「待发块里那些 40 位坐标到底能不能在远端解出来」量出来。

07:43 我记了一条"root 只剩 D"的形状但说"成因没有读数"。07:54 项目记忆里躺着一条同类的门行为
（一枚解不出的手写 40 位会拒掉整块 ⇒ 作者只能改名重投）。这正好是 **可量的**：
把待发块与已插入块的 40 位坐标各取出来，逐个到两个远端仓库探 blob，看两侧的"解不出率"差多少。
差得明显才支持"门把 D 的块拒在外面"，不差就是我又一次拿形状当成因。
"""
import concurrent.futures as cf
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
HDR = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
       "User-Agent": "cnx-patrol", "X-GitHub-Api-Version": "2022-11-28"}
REPOS = ["Canshu-King/CityNexus-Workspace", "Canshu-King/CityNexus"]
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROC = os.path.join(INBOX, "_processed")
PENDING = ["d-e345b9d6_0605.md", "d-e345b9d6_0633.md", "d-e345b9d6_0707.md", "d-e345b9d6_0810.md"]
CONTROL = ["S1-q64sweep_0710.md.inserted_071620", "b-c01d72a3_0723.md.inserted_072520",
           "S3-stateboard_0643.md.inserted_064458", "cmdr_0656.md.inserted_070757",
           "S2-hermes-port_0655.md.inserted_065555"]
HEX40 = re.compile(r"\b[0-9a-f]{40}\b")


def get(url):
    r = urllib.request.Request(url, headers=HDR)
    try:
        with urllib.request.urlopen(r, timeout=30) as x:
            return x.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return -1


def probe(item):
    repo, sha = item
    st = get("https://api.github.com/repos/%s/git/blobs/%s" % (repo, sha))
    if st != 200:                              # 不是 blob 就当 commit 再试一次
        st2 = get("https://api.github.com/repos/%s/commits/%s" % (repo, sha))
        return (repo, sha, st, st2, st2 == 200)
    return (repo, sha, st, None, True)


def tokens(path):
    if not os.path.isfile(path):
        print("MISSING %s  <- 文件名不对，这一格会算成 0 枚坐标" % path)
        return set()
    return set(HEX40.findall(io.open(path, encoding="utf-8", errors="replace").read()))


def main():
    groups = {}
    for name in PENDING:
        groups[name] = {"pending": True, "toks": tokens(os.path.join(INBOX, name))}
    for name in CONTROL:
        groups[name] = {"pending": False, "toks": tokens(os.path.join(PROC, name))}
    allsh = sorted({s for g in groups.values() for s in g["toks"]})
    items = [(r, s) for s in allsh for r in REPOS]
    print("files=%d  unique_40hex=%d  requests<=%d" % (len(groups), len(allsh), 2 * len(items)))
    res = {}
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for repo, sha, st, st2, ok in ex.map(probe, items):
            res.setdefault(sha, {})[repo] = (st, st2, ok)
    rows = []
    for name, g in sorted(groups.items()):
        hit = sum(1 for s in g["toks"] if any(v[2] for v in res.get(s, {}).values()))
        miss = len(g["toks"]) - hit
        side = "PENDING " if g["pending"] else "INSERTED"
        rows.append((side, name, len(g["toks"]), hit, miss))
        print("%s %-46s 40hex=%2d  可解=%2d  不可解=%2d" % (side, name, len(g["toks"]), hit, miss))
    for side in ("PENDING ", "INSERTED"):
        sel = [r for r in rows if r[0] == side]
        n = sum(r[2] for r in sel)
        m = sum(r[4] for r in sel)
        if n:
            print("%s 合计：%d 枚坐标，不可解 %d 枚（%.0f%%）" % (side.strip(), n, m, 100.0 * m / n))
    un = [s for s in allsh if not any(v[2] for v in res.get(s, {}).values())]
    print("两侧都解不出的坐标（逐枚，最多列 12）：")
    for s in un[:12]:
        where = [n for n, g in groups.items() if s in g["toks"]]
        print("   %s  @ %s" % (s, "、".join(sorted(where))))
    io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "_hex_resolve_probe.json"), "w", encoding="utf-8").write(
        json.dumps({"rows": rows, "unresolvable": un,
                    "per_token": {s: {r: res[s][r] for r in REPOS if r in res.get(s, {})} for s in allsh}},
                   ensure_ascii=False, indent=1))
    print("WROTE _hex_resolve_probe.json")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
