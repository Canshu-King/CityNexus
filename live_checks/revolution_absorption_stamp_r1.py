# -*- coding: utf-8 -*-
"""ORD-0607 对账腿：把 carried 与 absorbed_on 算成有主的读数，而不是整列空着。

这把尺只做三件事，且与常驻尺 live_checks/revolution_absorption_check_r1.py 的口径一致（那个文件一字节没改）：

  · 逐枚现算「该枝相对现尖独有的内容」：`git diff --name-status <尖> <枝尖>` 里 A/M 那些路径 = 枝有而尖没有的内容；
    D 不算独有（那是尖独有的）。
  · carried：`git merge-base --is-ancestor <枝尖> <尖>` 为真 = 整根携带，逐枚现算，不抄旧值。
  · absorbed_on：只在该枝**零独有内容**时才填，填的是尖上最近一次动过它那批路径的那枚提交（`git rev-list -1 <尖> -- <路径>`），
    所以它天然是尖的祖先。零独有内容以外的枝一律留空并写明还差几枚文件——这一条是「不批量预填」的硬保证。

用法：
  python revolution_absorption_stamp_r1.py                 # 只报分布，不写文件
  python revolution_absorption_stamp_r1.py --emit <目录>   # 再写 stamped.tsv 与 _absorption_stamp_<日期>.tsv
退出码：
  0 = 每枚枝都有归属读数（carried 全有值，且每个非空 absorbed_on 都是尖的祖先）
  9 = 有退化（表里某个 absorbed_on 不是当前尖的祖先，或某枚枝的 sha 取不到）
  3 = 现读数据取不到（ls-remote 或对象库）
"""
import argparse
import collections
import datetime
import os
import subprocess
import sys

WORK = os.environ.get("CNX_WORK_REPO", "D:/moodle/CityNexus")
TIPREF = "refs/heads/mirror/integration-frontend-apple-pass1"
MANIFEST_REL = "docs/REVOLUTION_ABSORPTION_MANIFEST.tsv"
COLS = ("name sha fork ahead behind prod test doc other artifact mod_total mod_real "
        "carried verdict absorbed_on").split()
REP_A_NAME = "gpt/revolution-r33-open-world-journey-adaptation"


def git(*a):
    p = subprocess.run(["git", "-C", WORK] + list(a), capture_output=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def strict_ancestor(a, b):
    """True when a is an ancestor of b and a != b (a branch cannot carry itself)."""
    if a == b:
        return False
    return git("merge-base", "--is-ancestor", a, b)[0] == 0


def pick_reps(rows):
    """One representative sha per family (the `fork` column).

    族A 用计划与对账表都点名的代表枝；其余族取「本族里携带别人最多的那枚」，携带数并列时按名字典序，
    保证两次跑出同一个代表。口径出处：docs/REVOLUTION_ABSORPTION_FIVE_YEAR_PLAN.md:11。
    """
    fam = {}
    for r in rows:
        fam.setdefault(r["fork"][:10], []).append(r)
    reps = {}
    for k, v in fam.items():
        if any(r["name"] == REP_A_NAME for r in v):
            reps[k] = next(r["sha"] for r in v if r["name"] == REP_A_NAME)
            continue
        best, bc = None, -1
        for r in sorted(v, key=lambda x: x["name"]):
            c = sum(1 for r2 in v if strict_ancestor(r2["sha"], r["sha"]))
            if c > bc:
                bc, best = c, r["sha"]
        reps[k] = best
    return reps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit", default=None)
    args = ap.parse_args()

    rc, out, err = git("ls-remote", "origin", TIPREF)
    tip = out.split("\t")[0].strip() if out else ""
    if len(tip) != 40:
        print("RC3 ls-remote failed: %s" % err[:160])
        return 3
    raw = git("show", "%s:%s" % (tip, MANIFEST_REL))[1]
    if not raw:
        print("RC3 manifest unreadable on %s" % tip)
        return 3
    lines = [l for l in raw.split("\n") if l.strip()]
    hdr = lines[0].split("\t")
    if hdr != COLS:
        print("RC9 manifest header changed: %s" % hdr)
        return 9
    # a stripped tail can eat the last row's trailing empty field; pad by name so no column shifts
    rows = [dict(zip(COLS, (l.split("\t") + [""] * (len(COLS) - len(l.split("\t"))))))
            for l in lines[1:]]

    reps = pick_reps(rows)
    recs, regressions = [], []
    for r in rows:
        name, sha = r["name"], r["sha"]
        if git("cat-file", "-e", "%s^{commit}" % sha)[0] != 0:
            regressions.append((name, "branch sha not in object library"))
            recs.append(dict(r, carried_new="", absorbed_new="", unique=-1, added=-1,
                             modified=-1, missing=-1, why="UNREADABLE", why_car=""))
            continue
        diff = git("diff", "--name-status", tip, sha)[1]
        added, modified = [], []
        for ln in diff.splitlines():
            parts = ln.split("\t")
            if len(parts) < 2:
                continue
            st = parts[0]
            if st.startswith("A"):
                added.append(parts[-1])
            elif st.startswith(("M", "R")):
                modified.append(parts[-1])
        uniq = added + modified
        rep = reps.get(r["fork"][:10])
        carried_new = "YES" if strict_ancestor(sha, rep) else "NO"
        why_car = "本族代表自身，不被携带" if sha == rep else ""
        ancestor_of_tip = git("merge-base", "--is-ancestor", sha, tip)[0] == 0
        absorbed_new = ""
        why = ""
        if not uniq:
            if ancestor_of_tip:
                absorbed_new = sha
                why = "整根在尖的历史里"
            else:
                touched = [p for p in git("diff", "--name-only", git("merge-base", tip, sha)[1],
                                          sha)[1].splitlines() if p.strip()]
                cand = git("rev-list", "-1", tip, "--", *touched[:50])[1].split("\n")[0].strip() \
                    if touched else ""
                if cand and git("merge-base", "--is-ancestor", cand, tip)[0] == 0:
                    absorbed_new = cand
                    why = "零独有内容，吸收代=尖上最近动过它那批路径的那枚提交"
                else:
                    why = "零独有内容但找不到可证的吸收代，留空"
        else:
            why = "新增未在线上 %d 枚、与尖不同 %d 枚" % (len(added), len(modified))
        old_abs = (r.get("absorbed_on") or "").strip()
        if old_abs and git("merge-base", "--is-ancestor", old_abs, tip)[0] != 0:
            regressions.append((name, "existing absorbed_on %s is not an ancestor of tip" % old_abs[:12]))
        recs.append(dict(r, carried_new=carried_new, absorbed_new=absorbed_new or old_abs,
                         unique=len(uniq), missing=len(uniq), added=len(added),
                         modified=len(modified), why=why, why_car=why_car))

    # internal consistency gate: the carried column computed here must agree with the verdict column
    carried_yes = {x["name"] for x in recs if x["carried_new"] == "YES"}
    claims = {x["name"] for x in recs if (x.get("verdict") or "").strip() == "CARRIED_BY_REP"}
    if carried_yes != claims:
        regressions.append(("carried-vs-verdict",
                            "computed YES=%s but verdict CARRIED_BY_REP=%s" % (
                                sorted(carried_yes), sorted(claims))))

    dist = collections.Counter()
    for x in recs:
        dist["零独有内容" if x["unique"] == 0 else ("取不到" if x["unique"] < 0 else "仍有独有内容")] += 1
    print("tip=%s rows=%d" % (tip, len(recs)))
    print("carried 现算：YES=%d NO=%d（表里原值填了 %d 条）" % (
        sum(1 for x in recs if x["carried_new"] == "YES"),
        sum(1 for x in recs if x["carried_new"] == "NO"),
        sum(1 for x in recs if (x.get("carried") or "").strip())))
    print("absorbed_on 有主读数=%d（其中本尺新算出 %d 条，原表已有 %d 条）" % (
        sum(1 for x in recs if x["absorbed_new"]),
        sum(1 for x in recs if x["absorbed_new"] and not (x.get("absorbed_on") or "").strip()),
        sum(1 for x in recs if (x.get("absorbed_on") or "").strip())))
    print("分布：%s" % dict(dist))
    nfilled = sum(1 for x in recs if x["absorbed_new"])
    nzero = sum(1 for x in recs if x["unique"] == 0)
    print("两口径：尺口径（absorbed_on 非空即算已吸收）已吸收=%d 未吸收=%d | "
          "内容口径（相对尖零独有内容才算已吸收）已吸收=%d 仍有独有内容=%d | 差=%d" % (
              nfilled, len(recs) - nfilled, nzero, len(recs) - nzero, nfilled - nzero))
    for x in sorted(recs, key=lambda y: -(y["unique"] if y["unique"] >= 0 else 0)):
        print("   %-56s uniq=%-4d (A=%-4d M=%-4d) carried=%-3s absorbed_on=%-40s %s%s" % (
            x["name"][:56], x["unique"], x["added"], x["modified"], x["carried_new"],
            (x["absorbed_new"] or "-")[:40], x["why"][:40],
            (" | " + x["why_car"]) if x["why_car"] else ""))
    print("退化=%d" % len(regressions))
    for g in regressions:
        print("   REGRESS %s" % (g,))

    if args.emit:
        os.makedirs(args.emit, exist_ok=True)
        day = datetime.datetime.now().strftime("%Y%m%d")
        tsv = os.path.join(args.emit, "_absorption_stamp_%s.tsv" % day)
        with open(tsv, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("branch\tsha\tunique_vs_tip\tadded_vs_tip\tmodified_vs_tip\tcarried_now\t"
                     "absorbed_on_new\tabsorbed_on_old\tbasis\twhy\n")
            for x in recs:
                fh.write("%s\t%s\t%d\t%d\t%d\t%s\t%s\t%s\t%s\t%s\n" % (
                    x["name"], x["sha"], x["unique"], x["added"], x["modified"], x["carried_new"],
                    x["absorbed_new"] or "-", (x.get("absorbed_on") or "-").strip() or "-",
                    tip, (x["why"] + (" | " + x["why_car"] if x["why_car"] else ""))))
        man = os.path.join(args.emit, "REVOLUTION_ABSORPTION_MANIFEST.stamped.tsv")
        with open(man, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\t".join(COLS) + "\n")
            for x in recs:
                vals = [x["name"], x["sha"], x["fork"], x["ahead"], x["behind"], x["prod"],
                        x["test"], x["doc"], x["other"], x["artifact"], x["mod_total"],
                        x["mod_real"], x["carried_new"], x["verdict"], x["absorbed_new"]]
                fh.write("\t".join(vals) + "\n")
        print("EMIT %s %s" % (tsv, man))

    if regressions:
        return 9
    unfilled = sum(1 for x in recs if not x["carried_new"])
    return 0 if unfilled == 0 else 4


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
