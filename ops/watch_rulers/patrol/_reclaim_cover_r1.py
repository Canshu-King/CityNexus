# -*- coding: utf-8 -*-
"""把「抽一枚文件在仓里找得到」升级成「整棵树逐文件对一遍」——只有这一版才够动手删。

为什么还要第三遍（14:10）：`_reclaim_proof2_r1.py` 判出 55 枚「可重建」= 9837.1 MiB，但它的证据只是
**抽一枚文件算 blob、问 git 哪笔提交带过它**——同一枚 README 会在几百笔提交里出现，所以那只证明
「这里有一份仓里也有的东西」，不证明「整个目录删掉后能原样拿回来」。导树里常混着跑出来的产物
（build 输出、sqlite、截图），那些不在任何 commit 里。这一遍做实打实的对账：

  对每一枚目录：列它自己的相对路径清单，与 `git ls-tree -r <commit>` 的清单求集合差。
  · 目录里少文件（树里有、目录没有）⇒ 这本来就是部分导出，删了不影响"能不能拿回代码"，只影响省事；
  · 目录里多文件（目录有、树里没有）⇒ **这些就是仓外产物**，删了就没了，必须先单独确认；
  · 多出来的若只有 .git/node_modules 一类可再生项 ⇒ 记成「可清（附条件）」。

只读。默认判最大的 12 枚非工作树候选（BUDGET 控时）；不动任何目录、不删任何东西。
"""
import glob
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = r"D:\moodle\CityNexus"
SRC = os.path.join(HERE, "_reclaim_proof2_latest.json")
OUT_TXT = os.path.join(HERE, "_reclaim_cover_latest.txt")
OUT_JSON = os.path.join(HERE, "_reclaim_cover_latest.json")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="", http_proxy="", https_proxy="")
BUDGET = float(os.environ.get("BUDGET", "700"))
TOPN = int(os.environ.get("TOPN", "12"))
REGEN = re.compile(r"(^|/)(\.git|node_modules|__pycache__|\.venv|dist|build|\.next|\.cache)(/|$)|\.(pyc|log|tmp)$", re.I)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def gargs(*a, t=240):
    return subprocess.run(("git", "-C", REPO) + a, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=ENV, timeout=t)


def tree_paths(commit):
    out = gargs("ls-tree", "-r", "--name-only", commit)
    return set(x.strip() for x in (out.stdout or "").splitlines() if x.strip())


def dir_paths(full):
    got = set()
    for root, dirs, files in os.walk(full):
        rel_root = os.path.relpath(root, full).replace("\\", "/")
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__")]
        for fn in files:
            p = fn if rel_root == "." else rel_root + "/" + fn
            got.add(p)
    return got


def main():
    if not os.path.exists(SRC):
        print("读数不全：先跑 _reclaim_proof2_r1.py")
        return 2
    d = json.load(io.open(SRC, encoding="utf-8"))
    cands = [x for x in d["top"] if not x.get("worktree")]
    cands.sort(key=lambda x: -(x["mib"] or 0))
    rows = []
    cache = {}
    t0 = time.time()
    for x in cands[:TOPN]:
        if time.time() - t0 > BUDGET:
            print(u"预算 %d 秒用完，剩下不判" % BUDGET)
            break
        full = os.path.join(r"D:\moodle", x["dir"])
        c = x["commit"]
        if c not in cache:
            cache[c] = tree_paths(c)
        tp = cache[c]
        if not tp:
            rows.append(dict(x, tree_n=0, only_dir=0, only_tree=0, extra_regen=0, extra_real=0,
                             verdict=u"树清单取不到（commit 不在本地？）"))
            continue
        dp = dir_paths(full)
        # 14:12 实测的坑：导树不一定把仓摊在顶层——`_qoder_cmdr_deploy_d2665e_0923` 里是一层 `repo/`，
        # 于是路径集合完全不相交（目录多 = 目录内全部 6988 个），我差点据此报「全是指不上的仓外产物」。
        # 先把目录里那层唯一顶层目录剥掉再对；仍不相交就如实报「对不上」而不是当成产物。
        tops = set(p.split("/")[0] for p in dp if "/" in p)
        pref = ""
        if len(tops) == 1:
            only = tops.pop()
            if len(dp) > 50:
                cand = set(x[len(only) + 1:] for x in dp if x.startswith(only + "/"))
                if len(cand & tp) > len(dp & tp):
                    dp, pref = cand, only + "/"
        inter = len(dp & tp)
        only_dir = dp - tp
        only_tree = tp - dp
        regen = [p for p in only_dir if REGEN.search(p)]
        real = [p for p in only_dir if p not in regen]
        if inter == 0 and pref == "":
            verdict = u"对不上（与 commit %s 的树零交集，剥层也不成立）⇒ 不判可清" % c[:10]
        elif len(tp) < 50:
            verdict = u"那笔提交只有 %d 个文件 ⇒ sha 抽样判据不可靠，别据此删" % len(tp)
        elif not real:
            verdict = u"可清（多出的文件全在可再生类；交集 %d）" % inter
        else:
            verdict = u"含仓外产物 %d 个 ⇒ 先确认再动（交集 %d）" % (len(real), inter)
        rows.append(dict(x, prefix=pref, tree_n=len(tp), dir_n=len(dp), overlap=inter,
                         only_dir=len(only_dir), only_tree=len(only_tree),
                         extra_regen=len(regen), extra_real=len(real),
                         sample_extra=sorted(real)[:6], verdict=verdict))
    with io.open(OUT_TXT, "w", encoding="utf-8", newline="\n") as f:
        f.write(u"_reclaim_cover_r1.py 于 %s｜输入 %s（可重建 %d 枚 = %.1f MiB，先排掉登记在册的工作树，判最大的 %d 枚）\n" % (
            time.strftime("%Y-%m-%d %H:%M:%S"), os.path.basename(SRC), d["rebuildable_n"], d["rebuildable_mib"], min(TOPN, len(cands))))
        f.write(u"%-40s %9s %8s %8s %8s %8s %8s %8s  判定\n" % ("目录", "MiB", "树内", "目录内", "交集", "目录多", "可再生", "仓外产物"))
        for r in rows:
            f.write(u"%-40s %9.1f %8d %8d %8d %8d %8d %8d  %s\n" % (
                r["dir"][:40], r["mib"] or 0, r.get("tree_n", 0), r.get("dir_n", 0), r.get("overlap", 0),
                r.get("only_dir", 0), r.get("extra_regen", 0), r.get("extra_real", 0), r["verdict"]))
        clean = [r for r in rows if r["verdict"].startswith(u"可清")]
        dirty = [r for r in rows if u"仓外产物" in r["verdict"]]
        f.write(u"\n小结：判 %d 枚｜可清（多出的文件全在 .git/node_modules/dist/日志一类可再生项里）%d 枚 = %.1f MiB｜"
                u"含仓外产物需先确认 %d 枚 = %.1f MiB｜剥掉的顶层目录那一层记在 prefix 字段（例如 `repo/`）\n" % (
                    len(rows), len(clean), sum(r["mib"] or 0 for r in clean),
                    len(dirty), sum(r["mib"] or 0 for r in dirty)))
        f.write(u"复算：TOPN=12 BUDGET=700 python _reclaim_cover_r1.py（只读：os.walk + git ls-tree，不删不改）\n")
    json.dump({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "n_judged": len(rows),
               "clean_n": len([r for r in rows if r["verdict"].startswith(u"可清")]),
               "clean_mib": round(sum(r["mib"] or 0 for r in rows if r["verdict"].startswith(u"可清")), 1),
               "dirty_n": len([r for r in rows if u"仓外产物" in r["verdict"]]),
               "rows": rows}, io.open(OUT_JSON, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print(io.open(OUT_TXT, encoding="utf-8").read())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
