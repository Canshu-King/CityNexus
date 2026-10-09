# -*- coding: utf-8 -*-
"""把「未证明可重建」那 93 枚真正判一遍：名字里是短 sha（6—12 位）也算，且去目录里找落档的 sha。

为什么再来一遍（14:00）：`_reclaim_size_r1.py` 第一版只认目录名里的 40 位或 12 位 sha，
结果 142 枚量到的里面「可重建 0 枚」——这不可能全对：像 `_qoder_cmdr_deploy_d2665e_0923` 这种
名字里就带着 7 位短 sha（d2665e），导出树本来就是 `git archive <sha>` 出来的。
判据写松了会把能清的算成不能清（白占盘），写紧了会把不能清的算成能清（丢证据）——
所以这一版两头都要有证据：短 sha 必须能在仓里 rev-parse 成 commit，或者目录里有一枚落档的 sha 文件。

只读：`git rev-parse --verify`、`cat-file -t`、列目录找 sha 文件；不删、不改、不动任何人的目录。
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
SRC = os.path.join(HERE, "_reclaim_sizes_latest.json")
OUT_TXT = os.path.join(HERE, "_reclaim_proof2_latest.txt")
OUT_JSON = os.path.join(HERE, "_reclaim_proof2_latest.json")
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY="", http_proxy="", https_proxy="")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BUDGET = float(os.environ.get("BUDGET", "600"))


def gargs(*a, t=90):
    return subprocess.run(("git", "-C", REPO) + a, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=ENV, timeout=t)


def resolve(tok):
    """短 sha → 完整 commit（取不到返回空）。只用本地对象，不 fetch。"""
    try:
        r = gargs("rev-parse", "--verify", "-q", tok + "^{commit}", t=30)
    except Exception:
        return ""
    out = (r.stdout or "").strip()
    return out if (r.returncode == 0 and len(out) == 40) else ""


def content_proof(full):
    """名字里没有 sha 时的第二路：抽几个文件算 blob，问 git「哪一笔提交带过这枚 blob」。

    取到 ⇒ 这份内容在仓里存在，按那枚 commit 与路径能 `git archive` 回来；取不到就明说取不到，
    不下「不能删」的结论（很多目录装的是跑出来的产物，本来就不在仓里）。
    """
    cands = []
    for pt in ("backend/app/*.py", "*.md", "backend/*.py", "frontend/*.json", "*/*.py"):
        try:
            cands += glob.glob(os.path.join(full, pt))[:2]
        except Exception:
            pass
    for f in cands[:4]:
        try:
            if not os.path.isfile(f) or os.path.getsize(f) > 2000000:
                continue
            h = (gargs("hash-object", f, t=60).stdout or "").strip()
        except Exception:
            continue
        if len(h) != 40:
            continue
        try:
            r = gargs("log", "--all", "--find-object=" + h, "--format=%H", "-1", t=150)
        except Exception:
            continue
        c = [x for x in (r.stdout or "").splitlines() if len(x.strip()) == 40]
        if c:
            return c[0].strip(), h, os.path.relpath(f, full)
    return "", "", ""


def markers(d):
    """目录里有没有落档的 sha（号令者/车道常把基座尖写进小文件）。"""
    found = []
    pats = ("*sha*.txt", "*sha*.json", "*head*.txt", "SNAPSHOT*", "*base*.txt", "*gen*.json")
    for pt in pats:
        try:
            found += glob.glob(os.path.join(d, pt))[:3]
        except Exception:
            pass
    out = []
    for f in found[:12]:
        try:
            if os.path.getsize(f) > 200000:
                continue
            blob = io.open(f, "rb").read()[:4000].decode("utf-8", "replace")
        except Exception:
            continue
        out += re.findall(r"\b[0-9a-f]{7,40}\b", blob)[:6]
    return out


def main():
    if not os.path.exists(SRC):
        print("读数不全：先跑 _reclaim_size_r1.py")
        return 2
    d = json.load(io.open(SRC, encoding="utf-8"))
    rows = d["rows"]
    t0 = time.time()
    ok = []
    unknown = []
    for r in rows:
        if time.time() - t0 > BUDGET:
            print(u"预算 %d 秒用完，还有 %d 枚没判（不猜、不外推）" % (BUDGET, len(rows)))
            break
        full = os.path.join(r"D:\moodle", r["dir"])
        # 形制坑两处（14:02—14:03 实测）：① `\b` 在 `_…_d2665e_…` 里切不出 token（`_` 是单词字符，
        # 上下都是单词字符就没有边界）；② 换成环视之后仍然 0 枚，因为名字里那枚短 sha 只有 6 位
        # （`d2665e`），而我写的是 {7,12}。同一枚手工 rev-parse 是解析得成 commit 的。
        # 现在收 6—12 位；真有歧义时 git 会报 ambiguous ⇒ resolve 返回空，不会把不能清的算成能清。
        toks_name = [t for t in re.findall(r"(?<![0-9a-f])([0-9a-f]{6,12})(?![0-9a-f])", r["dir"])]
        toks_name.sort(key=lambda t: (0 if re.search("[a-f]", t) else 1, -len(t)))
        toks = list(toks_name)
        toks += [x for x in markers(full) if 6 <= len(x) <= 40]
        hit = ""
        for tok in dict.fromkeys(toks):
            c = resolve(tok)
            if c:
                hit = c
                break
        via = "名字/落档 sha"
        sample = ""
        if not hit:
            c2, blob, sample = content_proof(full)
            if c2:
                hit, via = c2, "内容比对（抽文件算 blob，再问哪笔提交带过它）"
        if hit:
            ok.append({"dir": r["dir"], "mib": r["mib"], "idle_h": r["idle_h"], "token": toks[:4],
                       "commit": hit, "via": via, "sample": sample,
                       "has_git": r["has_git"], "worktree": r["worktree"],
                       "rebuild": u'git -C D:/moodle/CityNexus archive %s | tar -x -C "D:/moodle/%s"' % (hit[:12], r["dir"])})
        else:
            unknown.append(r)
    tot_ok = sum(x["mib"] or 0 for x in ok)
    with io.open(OUT_TXT, "w", encoding="utf-8", newline="\n") as f:
        f.write(u"_reclaim_proof2_r1.py 于 %s｜输入 %s（候选 %d 枚、量到 %d 枚）\n" % (
            time.strftime("%Y-%m-%d %H:%M:%S"), os.path.basename(SRC), d["n_candidates"], d["n_measured"]))
        f.write(u"判成可重建（名字或目录内的 sha 文件能在 CityNexus 里 rev-parse 成 commit）：%d 枚 = %.1f MiB\n" % (len(ok), tot_ok))
        f.write(u"仍然未证明：%d 枚（其中登记在册不能 rm 的另算）\n\n" % len(unknown))
        for x in sorted(ok, key=lambda y: -(y["mib"] or 0))[:20]:
            f.write(u"  %-40s %8.1f MiB  闲置 %5.1f h  commit=%s%s\n" % (
                x["dir"][:40], x["mib"] or 0, x["idle_h"], x["commit"][:12],
                u"｜在册工作树" if x["worktree"] else u""))
        f.write(u"\n重建形制（一枚一条，不执行）：\n")
        for x in sorted(ok, key=lambda y: -(y["mib"] or 0))[:6]:
            f.write(u"  %s\n" % x["rebuild"])
        f.write(u"\n边界：判「可重建」只到「这个 sha 在本地仓里是一个 commit」为止；目录里若有仓外产物"
                u"（build 输出、跑出来的库、截图）那些东西不在这个 commit 里，删了就没了——所以这一版是**给号令者缩范围**，不是放行清单。\n")
    json.dump({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "rebuildable_n": len(ok),
               "rebuildable_mib": round(tot_ok, 1), "unproven_n": len(unknown),
               "top": sorted(ok, key=lambda y: -(y["mib"] or 0))[:40]},
              io.open(OUT_JSON, "w", encoding="utf-8", newline="\n"), ensure_ascii=False, indent=1)
    io.open(OUT_TXT, "a", encoding="utf-8", newline="\n").write(
        u"复算：python _reclaim_proof2_r1.py（BUDGET 可改）\n")
    print(open(OUT_TXT, encoding="utf-8").read()[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
