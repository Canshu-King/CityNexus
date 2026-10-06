# -*- coding: utf-8 -*-
"""逐文件对树的清理判据（r2）：只对「多出来的文件全在可再生类」的目录判可清，其余一律不下结论。

三遍才走到能用（前两遍的读数都留在档里，别当成可以同时信）：
  第 1 遍 `_reclaim_size_r1.py`：只从目录名里找 40/12 位 sha ⇒ 报「可重建 0 枚」（假阴：短 sha 没认到）。
  第 2 遍 `_reclaim_proof2_r1.py`：环视切 6—12 位 + 抽一枚文件算 blob 问哪笔提交带过 ⇒ 报「55 枚 = 9837.1 MiB 可重建」（虚高）。
  第 3 遍（本文件）：逐文件对树。14:16 实测把第 2 遍打回——最大的 12 枚里 11 枚与那笔抽样命中的提交**零交集**，
      而那笔提交整棵树只有 9 个文件（README 这类 blob 会在几百笔提交里出现，命中它是运气）。

判法（只读）：
  · 候选提交试三枚：抽样那笔、名字里的 sha、权威尖；取**交集最大**的那枚，判定里写下用的是哪枚。
  · 导树可能把仓套在一层目录里（例如 `repo/`），先试剥掉那层再对，剥了哪层记在 prefix。
  · 多出来的文件分两类：可再生（.git/node_modules/dist/日志/pyc）与仓外产物；只有前者才判可清。
  · 零交集 ⇒ 「对不上」；既不算可清也不算仓外产物。预算用完就报「剩下不判」，不外推。
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


def resolve(tok):
    r = gargs("rev-parse", "--verify", "-q", tok + "^{commit}", t=40)
    out = (r.stdout or "").strip()
    return out if (r.returncode == 0 and len(out) == 40) else ""


def tree_paths(commit):
    out = gargs("ls-tree", "-r", "--name-only", commit)
    return set(x.strip() for x in (out.stdout or "").splitlines() if x.strip())


def dir_paths(full):
    got = set()
    for root, dirs, files in os.walk(full):
        rel = os.path.relpath(root, full).replace("\\", "/")
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv")]
        for fn in files:
            got.add(fn if rel == "." else rel + "/" + fn)
    return got


def main():
    if not os.path.exists(SRC):
        print(u"读数不全：先跑 _reclaim_proof2_r1.py")
        return 2
    d = json.load(io.open(SRC, encoding="utf-8"))
    cands = [x for x in d["top"] if not x.get("worktree")]
    cands.sort(key=lambda y: -(y["mib"] or 0))
    tipline = (gargs("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").stdout or "").split()
    tipsha = tipline[0] if tipline and len(tipline[0]) == 40 else ""
    rows, cache = [], {}
    t0 = time.time()
    for x in cands[:TOPN]:
        if time.time() - t0 > BUDGET:
            print(u"预算 %d 秒用完，剩下不判（已判 %d 枚）" % (BUDGET, len(rows)))
            break
        full = os.path.join(r"D:\moodle", x["dir"])
        dp0 = dir_paths(full)
        cc = [x.get("commit") or ""]
        m = re.search(r"(?<![0-9a-f])([0-9a-f]{6,12})(?![0-9a-f])", x["dir"])
        if m:
            cc.append(resolve(m.group(1)))
        cc.append(tipsha)
        best = None
        for c in [y for y in dict.fromkeys(cc) if y]:
            if c not in cache:
                cache[c] = tree_paths(c)
            tp = cache[c]
            if not tp:
                continue
            tops = set(p.split("/")[0] for p in dp0 if "/" in p)
            dp, pref = dp0, ""
            if len(tops) == 1 and len(dp0) > 50:
                only = list(tops)[0]
                stripped = set(y[len(only) + 1:] for y in dp0 if y.startswith(only + "/"))
                if len(stripped & tp) > len(dp0 & tp):
                    dp, pref = stripped, only + "/"
            inter = len(dp & tp)
            if best is None or inter > best[0]:
                best = (inter, c, tp, dp, pref)
        if best is None:
            rows.append(dict(x, commit="", prefix="", tree_n=0, dir_n=len(dp0), overlap=0,
                             only_dir=len(dp0), only_tree=0, extra_regen=0, extra_real=0,
                             sample_extra=[], verdict=u"树清单全取不到（本地仓里没这些对象）"))
            continue
        inter, c, tp, dp, pref = best
        only_dir = dp - tp
        only_tree = tp - dp
        regen = [p for p in only_dir if REGEN.search(p)]
        real = [p for p in only_dir if p not in regen]
        if inter == 0:
            verdict = u"对不上（试过的每笔提交都零交集）⇒ 不判可清"
        elif len(tp) < 50:
            verdict = u"那笔提交只有 %d 个文件 ⇒ 抽样判据不可靠，别据此删" % len(tp)
        elif not real:
            verdict = u"可清（多出 %d 个都在可再生类；交集 %d，用 %s）" % (len(only_dir), inter, c[:10])
        else:
            verdict = u"含仓外产物 %d 个 ⇒ 先确认再动（交集 %d，用 %s）" % (len(real), inter, c[:10])
        rows.append(dict(x, commit=c, prefix=pref, tree_n=len(tp), dir_n=len(dp), overlap=inter,
                         only_dir=len(only_dir), only_tree=len(only_tree), extra_regen=len(regen),
                         extra_real=len(real), sample_extra=sorted(real)[:6], verdict=verdict))
    clean = [r for r in rows if r["verdict"].startswith(u"可清")]
    dirty = [r for r in rows if u"仓外产物" in r["verdict"]]
    none = [r for r in rows if r["verdict"].startswith(u"对不上") or r["verdict"].startswith(u"那笔提交")
            or r["verdict"].startswith(u"树清单")]
    with io.open(OUT_TXT, "w", encoding="utf-8", newline="\n") as f:
        f.write(u"_reclaim_cover_r2.py 于 %s｜输入 %s（第 2 遍报可重建 %d 枚 = %.1f MiB；本遍逐文件对树，先排掉登记在册的工作树，判最大的 %d 枚）\n" % (
            time.strftime("%Y-%m-%d %H:%M:%S"), os.path.basename(SRC), d["rebuildable_n"], d["rebuildable_mib"], len(rows)))
        f.write(u"%-40s %9s %8s %8s %8s %8s %8s %8s  判定\n" % ("目录", "MiB", "树内", "目录内", "交集", "目录多", "可再生", "仓外产物"))
        for r in rows:
            f.write(u"%-40s %9.1f %8d %8d %8d %8d %8d %8d  %s\n" % (
                r["dir"][:40], r["mib"] or 0, r.get("tree_n", 0), r.get("dir_n", 0), r.get("overlap", 0),
                r.get("only_dir", 0), r.get("extra_regen", 0), r.get("extra_real", 0), r["verdict"]))
        f.write(u"\n小结：判 %d 枚｜可清 %d 枚 = %.1f MiB｜含仓外产物 %d 枚 = %.1f MiB｜对不上或判据不可靠 %d 枚 = %.1f MiB\n" % (
            len(rows), len(clean), sum(r["mib"] or 0 for r in clean), len(dirty),
            sum(r["mib"] or 0 for r in dirty), len(none), sum(r["mib"] or 0 for r in none)))
        f.write(u"复算：TOPN=12 BUDGET=700 python _reclaim_cover_r2.py（只读：os.walk + git ls-tree，不删不改）\n")
    json.dump({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "tip": tipsha, "n_judged": len(rows),
               "clean_n": len(clean), "clean_mib": round(sum(r["mib"] or 0 for r in clean), 1),
               "dirty_n": len(dirty), "unmatched_n": len(none), "rows": rows},
              io.open(OUT_JSON, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    print(io.open(OUT_TXT, encoding="utf-8").read())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
